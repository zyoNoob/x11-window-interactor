import Xlib
import Xlib.XK
import Xlib.display
import Xlib.X
import Xlib.protocol.event
import subprocess
import numpy as np
import time
import random
import mss
import threading
import os
import sys

try:
    import cv2
except ImportError:
    cv2 = None  # Handle case where OpenCV is not installed

# Import sapiagent for human-like mouse control
try:
    from sapiagent import MouseController, init_controller

    SAPIAGENT_AVAILABLE = True
except ImportError:
    SAPIAGENT_AVAILABLE = False
    print("Warning: sapiagent library not available. Mouse control will not work.")


class X11WindowInteractor:
    def __init__(self, window_id=None, update_interval=1.0, model_path=None):
        # Initialize MSS for screen capture
        self.sct = mss.mss()
        # Connect to the X11 display
        self.display = Xlib.display.Display()
        self.root = self.display.screen().root

        # If no window_id provided, prompt the user to select a window
        if window_id is None:
            self.window_id = self.prompt_window_id()
        else:
            self.window_id = window_id

        # Create a resource object for the target window
        self.window = self.display.create_resource_object("window", self.window_id)
        # Retrieve initial window information (position and size)
        self.window_info = self.get_window_info()

        # Initialize sapiagent MouseController for human-like mouse movements
        if SAPIAGENT_AVAILABLE:
            if model_path is None:
                # Auto-find model path relative to this file's directory
                potential_path = os.path.join(
                    os.path.dirname(__file__),
                    "sapiagent-custom",
                    "output",
                    "models",
                    "fcn_dx_dy_mse_supervised.pth",
                )
                if os.path.exists(potential_path):
                    model_path = potential_path
            self.mouse_controller = MouseController(
                model_path=model_path,
                model_type="fcn",
            )
        else:
            self.mouse_controller = None

        # Set up background updater thread for window info
        self._stop_updater = threading.Event()
        self._update_interval = update_interval
        self._updater_thread = threading.Thread(
            target=self._background_updater, daemon=True
        )
        self._updater_thread.start()

    def prompt_window_id(self):
        # Prompt the user to click on a window, then parse its ID using xwininfo
        print("Click on the target window after running this...")
        result = subprocess.run(["xwininfo"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "Window id:" in line:
                return int(line.split()[3], 16)
        raise Exception("Unable to get window ID.")

    def get_window_info(self):
        # Run xwininfo to get the position and size of the target window
        result = subprocess.run(
            ["xwininfo", "-id", str(self.window_id)], capture_output=True, text=True
        )
        info = {}
        for line in result.stdout.split("\n"):
            if "Absolute upper-left X:" in line:
                info["x"] = int(line.split()[-1])
            elif "Absolute upper-left Y:" in line:
                info["y"] = int(line.split()[-1])
            elif "Width:" in line:
                info["width"] = int(line.split()[-1])
            elif "Height:" in line:
                info["height"] = int(line.split()[-1])
        return info

    def update(self):
        # Update the stored window information
        self.window_info = self.get_window_info()

    def _background_updater(self):
        # Background thread to periodically update window info
        while not self._stop_updater.is_set():
            self.update()
            time.sleep(self._update_interval)

    def stop(self):
        """Call this to stop the background updater thread."""
        self._stop_updater.set()
        self._updater_thread.join()

    def get_relative_cursor_position(self):
        # Get the current cursor position relative to the window
        pointer = self.root.query_pointer()
        relative_x = pointer.root_x - self.window_info["x"]
        relative_y = pointer.root_y - self.window_info["y"]
        return relative_x, relative_y

    def activate(self):
        # Activate (focus) the window by sending a FocusIn event
        event = Xlib.protocol.event.FocusIn(
            window=self.window,
            mode=Xlib.X.NotifyNormal,
            detail=Xlib.X.NotifyAncestor,
        )
        self.window.send_event(event, propagate=True)
        self.display.flush()
        time.sleep(0.05)

    def click(self, relative_x, relative_y, button=1):
        """
        Simulate a mouse click at the given relative coordinates using sapiagent.

        This method uses the sapiagent library for human-like mouse movements and clicks.

        Parameters:
            relative_x (int): X coordinate relative to the window.
            relative_y (int): Y coordinate relative to the window.
            button (int): Mouse button to click (1=left, 2=middle, 3=right).
        """
        if SAPIAGENT_AVAILABLE and self.mouse_controller is not None:
            # Convert relative coordinates to absolute screen coordinates
            absolute_x = self.window_info["x"] + relative_x
            absolute_y = self.window_info["y"] + relative_y

            # Map button number to button name
            button_map = {1: "left", 2: "middle", 3: "right"}
            button_name = button_map.get(button, "left")

            motion_duration = random.uniform(0.02, 0.4)

            # Perform the click using sapiagent
            self.mouse_controller.click_at(
                absolute_x, absolute_y, button=button_name, duration=motion_duration
            )
        else:
            # Fallback to xdotool if sapiagent is not available
            self._click_xdotool(relative_x, relative_y, button)

    def _click_xdotool(self, relative_x, relative_y, button=1):
        """Simulates a click using the 'xdotool' command-line utility."""
        # NOTE: Requires the 'xdotool' command-line utility to be installed.
        window_id_hex = hex(self.window_id)
        shell_command = (
            f"xdotool windowfocus {window_id_hex} && "
            f"xdotool mousemove --window {window_id_hex} {relative_x} {relative_y} && "
            f"sleep {random.uniform(0.1, 0.5):.2f} && "  # Add a random delay for application to update rendering
            f"xdotool click {button}"
        )
        try:
            subprocess.run(
                shell_command, shell=True, check=True, capture_output=True, text=True
            )
        except FileNotFoundError:
            print(
                "Error: 'xdotool' command not found. Please install it to use the 'xdotool' click method."
            )
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while running xdotool: {e}\nStderr: {e.stderr}")

    def _click_xlib(self, relative_x, relative_y, button=1):
        """Simulates a click using the python-xlib library."""
        # Move cursor first (optional but can help with some UIs)
        motion = Xlib.protocol.event.MotionNotify(
            time=Xlib.X.CurrentTime,
            root=self.root,
            window=self.window,
            same_screen=1,
            child=Xlib.X.NONE,
            root_x=self.window_info["x"] + relative_x,
            root_y=self.window_info["y"] + relative_y,
            event_x=relative_x,
            event_y=relative_y,
            state=0,
            is_hint=0,
            detail=0,
        )
        # Press and release events
        press = Xlib.protocol.event.ButtonPress(
            time=Xlib.X.CurrentTime,
            root=self.root,
            window=self.window,
            same_screen=1,
            child=Xlib.X.NONE,
            root_x=0,
            root_y=0,
            event_x=relative_x,
            event_y=relative_y,
            state=0,
            detail=button,
        )
        release = Xlib.protocol.event.ButtonRelease(
            time=Xlib.X.CurrentTime,
            root=self.root,
            window=self.window,
            same_screen=1,
            child=Xlib.X.NONE,
            root_x=0,
            root_y=0,
            event_x=relative_x,
            event_y=relative_y,
            state=0,
            detail=button,
        )

        # Send the events in order
        self.window.send_event(motion, propagate=True)
        self.display.sync()
        self.window.send_event(press, propagate=True)
        time.sleep(random.uniform(0.05, 0.1))
        self.window.send_event(release, propagate=True)
        self.display.sync()

    def send_key(self, keys):
        """
        Send a key press to the window.

        Parameters:
            keys (str or list): Single keysym (e.g. 'a') or a list of keysyms (e.g. ['Control_L', 'c'])
        """
        if isinstance(keys, str):
            keys = [keys]

        # Convert keysyms to keycodes
        keycodes = [
            self.display.keysym_to_keycode(Xlib.XK.string_to_keysym(k)) for k in keys
        ]

        # Press all modifier keys except the last (main key)
        for keycode in keycodes[:-1]:
            press = Xlib.protocol.event.KeyPress(
                time=Xlib.X.CurrentTime,
                root=self.root,
                window=self.window,
                same_screen=1,
                child=Xlib.X.NONE,
                root_x=0,
                root_y=0,
                event_x=0,
                event_y=0,
                state=0,
                detail=keycode,
            )
            self.window.send_event(press, propagate=True)

        # Press and release the main key
        main_keycode = keycodes[-1]
        press = Xlib.protocol.event.KeyPress(
            time=Xlib.X.CurrentTime,
            root=self.root,
            window=self.window,
            same_screen=1,
            child=Xlib.X.NONE,
            root_x=0,
            root_y=0,
            event_x=0,
            event_y=0,
            state=0,
            detail=main_keycode,
        )
        self.window.send_event(press, propagate=True)
        self.display.sync()
        time.sleep(random.uniform(0.05, 0.1))
        release = Xlib.protocol.event.KeyRelease(
            time=Xlib.X.CurrentTime,
            root=self.root,
            window=self.window,
            same_screen=1,
            child=Xlib.X.NONE,
            root_x=0,
            root_y=0,
            event_x=0,
            event_y=0,
            state=0,
            detail=main_keycode,
        )
        self.window.send_event(release, propagate=True)

        # Release modifier keys in reverse order
        for keycode in reversed(keycodes[:-1]):
            release = Xlib.protocol.event.KeyRelease(
                time=Xlib.X.CurrentTime,
                root=self.root,
                window=self.window,
                same_screen=1,
                child=Xlib.X.NONE,
                root_x=0,
                root_y=0,
                event_x=0,
                event_y=0,
                state=0,
                detail=keycode,
            )
            self.window.send_event(release, propagate=True)

        self.display.sync()

    def capture(self, xywh: tuple = None) -> np.ndarray:
        # Capture a screenshot of the window or a subregion of it
        if xywh:
            x, y, w, h = xywh
            x += self.window_info["x"]
            y += self.window_info["y"]
        else:
            x = self.window_info["x"]
            y = self.window_info["y"]
            w = self.window_info["width"]
            h = self.window_info["height"]

        # Use mss to grab the screen region and convert it to a numpy array
        img_array = np.array(
            self.sct.grab({"left": x, "top": y, "width": w, "height": h})
        )
        return img_array

    def select_roi_interactive(self) -> tuple[int, int, int, int] | None:
        """
        Allows the user to interactively select a rectangular region of interest (ROI)
        within the target window using the external 'slop' utility.

        Requires 'slop' to be installed on the system (e.g., sudo apt install slop).

        Returns:
            A tuple (x, y, width, height) representing the selected ROI relative
            to the window's top-left corner, or None if the selection was cancelled,
            failed, or did not overlap with the window.
        """
        # Ensure window info is reasonably up-to-date
        self.update()
        win_x = self.window_info.get("x")
        win_y = self.window_info.get("y")
        win_w = self.window_info.get("width")
        win_h = self.window_info.get("height")

        if None in [win_x, win_y, win_w, win_h]:
            print("Error: Could not retrieve valid window geometry.")
            return None

        print("Drag the mouse to select a rectangular region...")
        try:
            # Run slop to capture selection geometry (absolute screen coordinates)
            # -f specifies the output format: x y width height
            result = subprocess.run(
                ["slop", "-f", "%x %y %w %h"],
                capture_output=True,
                text=True,
                check=True,  # Raise exception on non-zero exit code (e.g., user cancel)
            )
            output = result.stdout.strip()
            if not output:
                print("Selection cancelled or failed (empty output).")
                return None

            sel_x_abs, sel_y_abs, sel_w, sel_h = map(int, output.split())

        except FileNotFoundError:
            print(
                "Error: 'slop' command not found. Please install it (e.g., 'sudo apt install slop')."
            )
            return None
        except subprocess.CalledProcessError:
            # Likely occurred if the user cancelled the selection (e.g., Esc key)
            print("Selection cancelled or failed (slop exited abnormally).")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while running slop: {e}")
            return None

        # Convert absolute screen coordinates to window-relative coordinates
        rel_x = sel_x_abs - win_x
        rel_y = sel_y_abs - win_y

        # --- Clamp the selection to the window boundaries ---
        # Find the intersection rectangle between the selection and the window
        intersect_x1 = max(rel_x, 0)
        intersect_y1 = max(rel_y, 0)
        intersect_x2 = min(rel_x + sel_w, win_w)
        intersect_y2 = min(rel_y + sel_h, win_h)

        # Calculate the width and height of the intersection
        final_w = intersect_x2 - intersect_x1
        final_h = intersect_y2 - intersect_y1

        # If the intersection has no area, the selection was outside the window
        if final_w <= 0 or final_h <= 0:
            print("Selected region is outside the target window.")
            return None

        # The top-left corner of the final ROI is the top-left of the intersection
        final_x = intersect_x1
        final_y = intersect_y1

        print(
            f"Selected ROI (relative to window): x={final_x}, y={final_y}, w={final_w}, h={final_h}"
        )
        return (final_x, final_y, final_w, final_h)

    def select_roi_interactive_cv(
        self, image: np.ndarray = None
    ) -> tuple[int, int, int, int] | None:
        """
        Allows the user to interactively select a rectangular ROI using OpenCV.
        Displays the current window content (or a provided image) and lets the user
        draw a rectangle.

        Requires 'opencv-python' to be installed (`pip install opencv-python`).

        Parameters:
            image (np.ndarray, optional): A pre-captured image (NumPy array) to use
                                          for selection instead of capturing a new one.
                                          Should be in a format OpenCV can handle (e.g., BGR, BGRA).
                                          Defaults to None, which triggers a new capture.

        Returns:
            A tuple (x, y, width, height) relative to the top-left corner of the
            displayed image/window content, or None if OpenCV is not installed,
            capture fails, or selection is cancelled.
        """
        if cv2 is None:
            print("Error: OpenCV (cv2) is not installed. Cannot use this method.")
            print("Try installing it: pip install opencv-python")
            return None

        img_bgr = None
        if image is None:
            # Capture the current state of the window if no image provided
            print("Capturing window content...")
            img_capture = self.capture()
            if img_capture is None or img_capture.size == 0:
                print("Error: Failed to capture window content for OpenCV selection.")
                return None
            # MSS captures in BGRA, OpenCV typically uses BGR
            img_bgr = cv2.cvtColor(img_capture, cv2.COLOR_BGRA2BGR)
        else:
            # Use the provided image
            print("Using provided image...")
            if (
                image.ndim == 3 and image.shape[2] == 4
            ):  # Check if it's likely BGRA or RGBA
                # Convert RGBA/BGRA to BGR if necessary
                img_bgr = cv2.cvtColor(
                    image, cv2.COLOR_BGRA2BGR
                )  # Or COLOR_RGBA2BGR if input is RGBA
            elif image.ndim == 3 and image.shape[2] == 3:  # Assume BGR or RGB
                img_bgr = image  # Assume it's already BGR or compatible
            elif image.ndim == 2:  # Grayscale
                img_bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            else:
                print("Error: Provided image has unsupported format/dimensions.")
                return None

        if img_bgr is None or img_bgr.size == 0:
            print("Error: Image processing failed.")
            return None

        # Dictionary to store mouse callback state
        roi_data = {
            "drawing": False,
            "start_point": None,
            "end_point": None,
            "roi": None,
        }
        window_name = "Select ROI - Drag Mouse | ENTER: Confirm | ESC: Cancel"

        def mouse_callback(event, x, y, flags, param):
            # Clamp coordinates coming from OpenCV window to image bounds
            x = max(0, min(x, img_bgr.shape[1] - 1))
            y = max(0, min(y, img_bgr.shape[0] - 1))

            if event == cv2.EVENT_LBUTTONDOWN:
                param["drawing"] = True
                param["start_point"] = (x, y)
                param["end_point"] = (x, y)  # Initialize end point
                param["roi"] = None  # Reset final ROI on new click
            elif event == cv2.EVENT_MOUSEMOVE:
                if param["drawing"]:
                    param["end_point"] = (x, y)
            elif event == cv2.EVENT_LBUTTONUP:
                param["drawing"] = False
                param["end_point"] = (x, y)
                # Calculate final ROI (ensure x1 < x2, y1 < y2)
                x1 = min(param["start_point"][0], param["end_point"][0])
                y1 = min(param["start_point"][1], param["end_point"][1])
                x2 = max(param["start_point"][0], param["end_point"][0])
                y2 = max(param["start_point"][1], param["end_point"][1])
                # Ensure width/height are at least 1 if start/end are same point click
                w = max(1, x2 - x1)
                h = max(1, y2 - y1)
                param["roi"] = (x1, y1, w, h)

        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(window_name, mouse_callback, roi_data)

        print("Select ROI in the OpenCV window. Press ENTER to confirm, ESC to cancel.")

        while True:
            display_img = img_bgr.copy()  # Draw on a copy
            start = roi_data["start_point"]
            end = roi_data["end_point"]

            # Draw rectangle: green while drawing, red when finalized
            if start and end:
                if roi_data["drawing"]:
                    cv2.rectangle(display_img, start, end, (0, 255, 0), 1)  # Green
                elif roi_data["roi"]:
                    x, y, w, h = roi_data["roi"]
                    cv2.rectangle(
                        display_img, (x, y), (x + w, y + h), (0, 0, 255), 2
                    )  # Red (thicker)

            cv2.imshow(window_name, display_img)
            key = cv2.waitKey(20) & 0xFF

            if key == 27:  # ESC key
                print("Selection cancelled.")
                roi_data["roi"] = None
                break
            elif key == 13:  # Enter key
                if roi_data["roi"]:
                    print(f"Selected ROI: {roi_data['roi']}")
                    break
                else:
                    print("No ROI selected. Please drag the mouse to select.")

        cv2.destroyAllWindows()
        # Force closing any potential lingering windows
        for i in range(5):
            cv2.waitKey(1)

        return roi_data["roi"]

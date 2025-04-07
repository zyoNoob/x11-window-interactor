import Xlib
import Xlib.display
import Xlib.X
import Xlib.protocol.event
import subprocess
import numpy as np
import time
import mss
import threading


class X11WindowInteractor:
    def __init__(self, window_id=None, update_interval=1.0):
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
        self.window = self.display.create_resource_object('window', self.window_id)
        # Retrieve initial window information (position and size)
        self.window_info = self.get_window_info()

        # Set up background updater thread for window info
        self._stop_updater = threading.Event()
        self._update_interval = update_interval
        self._updater_thread = threading.Thread(target=self._background_updater, daemon=True)
        self._updater_thread.start()

    def prompt_window_id(self):
        # Prompt the user to click on a window, then parse its ID using xwininfo
        print("Click on the target window after running this...")
        result = subprocess.run(['xwininfo'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "Window id:" in line:
                return int(line.split()[3], 16)
        raise Exception("Unable to get window ID.")

    def get_window_info(self):
        # Run xwininfo to get the position and size of the target window
        result = subprocess.run(['xwininfo', '-id', str(self.window_id)], capture_output=True, text=True)
        info = {}
        for line in result.stdout.split('\n'):
            if 'Absolute upper-left X:' in line:
                info['x'] = int(line.split()[-1])
            elif 'Absolute upper-left Y:' in line:
                info['y'] = int(line.split()[-1])
            elif 'Width:' in line:
                info['width'] = int(line.split()[-1])
            elif 'Height:' in line:
                info['height'] = int(line.split()[-1])
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
        relative_x = pointer.root_x - self.window_info['x']
        relative_y = pointer.root_y - self.window_info['y']
        return relative_x, relative_y

    def activate(self):
        # Activate (focus) the window by sending a FocusIn event
        event = Xlib.protocol.event.FocusIn(
            time=Xlib.X.CurrentTime,
            window=self.window,
            mode=Xlib.X.NotifyNormal,
            detail=Xlib.X.NotifyAncestor
        )
        self.window.send_event(event, propagate=True)
        self.display.flush()
        time.sleep(0.05)

    def click(self, relative_x, relative_y, button=1):
        """
        Simulate a mouse click at the given relative coordinates.

        Parameters:
            relative_x (int): X coordinate relative to the window
            relative_y (int): Y coordinate relative to the window
            button (int): Mouse button to click (1 = left, 2 = middle, 3 = right)
        """
        # Move cursor first (optional but can help with some UIs)
        motion = Xlib.protocol.event.MotionNotify(
            time=Xlib.X.CurrentTime,
            root=self.root,
            window=self.window,
            same_screen=1,
            child=Xlib.X.NONE,
            root_x=self.window_info['x'] + relative_x,
            root_y=self.window_info['y'] + relative_y,
            event_x=relative_x,
            event_y=relative_y,
            state=0,
            is_hint=0,
            detail=0
        )
        self.window.send_event(motion, propagate=True)
        self.display.sync()
        time.sleep(0.05)

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
            detail=button
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
            detail=button
        )
        self.window.send_event(press, propagate=True)
        self.display.sync()
        time.sleep(0.05)
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
        keycodes = [self.display.keysym_to_keycode(Xlib.XK.string_to_keysym(k)) for k in keys]

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
                detail=keycode
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
            detail=main_keycode
        )
        self.window.send_event(press, propagate=True)
        self.display.sync()
        time.sleep(0.05)
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
            detail=main_keycode
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
                detail=keycode
            )
            self.window.send_event(release, propagate=True)

        self.display.sync()

    def capture(self, xywh: tuple = None) -> np.ndarray:
        # Capture a screenshot of the window or a subregion of it
        if xywh:
            x, y, w, h = xywh
            x += self.window_info['x']
            y += self.window_info['y']
        else:
            x = self.window_info['x']
            y = self.window_info['y']
            w = self.window_info['width']
            h = self.window_info['height']

        # Use mss to grab the screen region and convert it to a numpy array
        img_array = np.array(self.sct.grab({'left': x, 'top': y, 'width': w, 'height': h}))
        return img_array
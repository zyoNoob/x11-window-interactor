import Xlib
import Xlib.display
import Xlib.X
import Xlib.protocol.event
import subprocess
import numpy as np
import cv2
import time
import ctypes
import os

class X11WindowInteractor:
    def __init__(self, window_id=None):
        self.LibName_ = 'prtscn.so'
        self.AbsLibPath_ = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + self.LibName_
        self.display = Xlib.display.Display()
        self.root = self.display.screen().root
        if window_id is None:
            self.window_id = self.prompt_window_id()
        else:
            self.window_id = window_id
        self.window = self.display.create_resource_object('window', self.window_id)
        self.window_info = self.get_window_info()

    def prompt_window_id(self):
        print("Click on the target window after running this...")
        result = subprocess.run(['xwininfo'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "Window id:" in line:
                return int(line.split()[3], 16)
        raise Exception("Unable to get window ID.")

    def get_window_info(self):
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

    def get_relative_cursor_position(self):
        pointer = self.root.query_pointer()
        relative_x = pointer.root_x - self.window_info['x']
        relative_y = pointer.root_y - self.window_info['y']
        return relative_x, relative_y

    def activate(self):
        # Make the window active by setting focus
        event = Xlib.protocol.event.FocusIn(
            time=Xlib.X.CurrentTime,
            window=self.window,
            mode=Xlib.X.NotifyNormal,
            detail=Xlib.X.NotifyAncestor
        )
        self.window.send_event(event, propagate=True)
        self.display.flush()
        time.sleep(0.05)

    def click(self, relative_x, relative_y):
        # Send synthetic MotionNotify to simulate mouse hover
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
            detail=1  # Left click
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
            detail=1
        )
        self.window.send_event(press, propagate=True)
        self.display.sync()
        time.sleep(0.05)
        self.window.send_event(release, propagate=True)
        self.display.sync()

    def send_key(self, keysym):
        keycode = self.display.keysym_to_keycode(keysym)
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
        self.window.send_event(press, propagate=True)
        self.display.sync()
        time.sleep(0.05)
        self.window.send_event(release, propagate=True)
        self.display.sync()

    def capture(self, tlwh: tuple = None) -> np.ndarray:
        """
        Capture a region of the screen using the TLWH format.
        
        Parameters:
            tlwh (tuple): (top, left, width, height) coordinates and dimensions
                         If None, captures the entire window
        
        Returns:
            np.ndarray: BGR image (OpenCV format)
        """
        if not hasattr(self, 'grab'):
            self.grab = ctypes.CDLL(self.AbsLibPath_)
            self.grab.getScreen.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_ubyte)]
            self.grab.getScreen.restype = None

        if tlwh:
            x, y, w, h = tlwh
            x += self.window_info['x']
            y += self.window_info['y']
        else:
            x = self.window_info['x']
            y = self.window_info['y']
            w = self.window_info['width']
            h = self.window_info['height']

        objlength = w * h * 3
        result = (ctypes.c_ubyte * objlength)()

        self.grab.getScreen(x, y, w, h, result)
        
        # Convert to numpy array and reshape
        img_array = np.frombuffer(result, dtype=np.uint8).reshape(h, w, 3)
        # Convert from RGB to BGR for OpenCV compatibility
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        return img_array

import Xlib
import Xlib.display
import Xlib.X
import Xlib.protocol.event
import subprocess
import numpy as np
import time
import mss

class X11WindowInteractor:
    def __init__(self, window_id=None):
        self.sct = mss.mss()
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

    def capture(self, xywh: tuple = None) -> np.ndarray:
        """
        Capture a region of the screen using the XYWH format.
        
        Parameters:
            xywh (tuple): (x, y, width, height) coordinates and dimensions
                         If None, captures the entire window
        
        Returns:
            np.ndarray: RGB image
        """
        if xywh:
            x, y, w, h = xywh
            x += self.window_info['x']
            y += self.window_info['y']
        else:
            x = self.window_info['x']
            y = self.window_info['y']
            w = self.window_info['width']
            h = self.window_info['height']

        img_array = np.array(self.sct.grab({'left':x, 'top':y, 'width':w, 'height':h}))
        
        return img_array

# 🖱️ x11-window-interactor

`x11-window-interactor` is a Python utility for automating interaction with X11 windows on Linux. It allows you to:

- 🔍 Identify and target X11 windows
- 🔄 Automatically keep window position/size information updated in the background
- 🖱️ Send mouse clicks to specific relative coordinates in the window
- ⌨️ Send keyboard keypresses directly to the window (supports various key types)
- 📸 Capture screenshots of a window into NumPy arrays (compatible with OpenCV, Pillow, etc.)

This tool is ideal for GUI automation, testing, and custom tooling in X environments.

---

## 💪 Features

- **Find window by clicking on it (via `xwininfo`)**
- **Background thread** to keep window geometry (position, size) updated.
- **Send mouse events** to any coordinates within the window
- **Send keypresses** directly to the application (even in background) using simple key names
- **Capture the window** into a NumPy array using `mss` for high performance
- **Get relative cursor position** for easier automation script building
- **Activate/Focus** the target window

---

## 👷️ Requirements

- Python 3.8+
- Linux with X11
- X utilities installed (`xwininfo`)
- Packages:
  - `python-xlib`
  - `numpy`
  - `mss`

### Setting up the Python environment

Use `uv` (or `pip`) to install dependencies. If you have `pyproject.toml` configured for `uv`:

```bash
uv sync
```

Or install manually:

```bash
pip install python-xlib numpy mss
```

---

## 📁 Project Structure

```
x11-window-interactor/
├── main.py                # Example usage
├── x11_interactor.py      # Core X11WindowInteractor class
├── pyproject.toml
├── README.md
├── .gitignore
└── .venv/                 # Virtual environment (optional)
```

---

## 🚀 Usage

### 1. Create the Interactor

```python
from x11_interactor import X11WindowInteractor
import time

# Prompt user to click on a window
interactor = X11WindowInteractor(update_interval=0.5) # Update window info every 0.5 seconds

# Or provide a specific window ID (e.g., obtained from 'xwininfo' or 'wmctrl -lG')
# window_id = 0x1234567 # Replace with actual ID
# interactor = X11WindowInteractor(window_id=window_id)

print(f"Interactor created for window ID: {interactor.window_id}")
print(f"Initial window info: {interactor.window_info}")

# Allow some time for the background updater to potentially get new info
time.sleep(1)
print(f"Updated window info: {interactor.window_info}")

```

### 2. Activate the Window (Optional)

```python
# Bring the window to the foreground and focus it
interactor.activate()
time.sleep(0.1) # Small delay often helps
```

### 3. Get Cursor Coordinates Relative to the Window

```python
relative_x, relative_y = interactor.get_relative_cursor_position()
print(f"Cursor position relative to window: ({relative_x}, {relative_y})")
```

### 4. Click Inside the Window

```python
# Click at (x=50, y=100) relative to window's top-left corner
interactor.click(50, 100)

# Click with the right mouse button (button=3)
# interactor.click(50, 100, button=3)
```

### 5. Send a Keypress

The `send_key` method accepts a string for a single key or a list of strings for key combinations (like Ctrl+C). Key names generally follow the standard X11 keysym names, but without the `XK_` prefix.

```python
# Send a single character 'a'
interactor.send_key('a')
time.sleep(0.1)

# Send an uppercase 'A' (Shift + a)
interactor.send_key(['Shift_L', 'a']) # Use Shift_L or Shift_R
time.sleep(0.1)

# Send Ctrl+C (useful for copying)
interactor.send_key(['Control_L', 'c']) # Use Control_L or Control_R
time.sleep(0.1)

# Send Alt+Tab (useful for switching windows, though activate() is better for targeting)
interactor.send_key(['Alt_L', 'Tab']) # Use Alt_L or Alt_R
time.sleep(0.1)

# Send function key F5
interactor.send_key('F5')
time.sleep(0.1)

# Send Enter/Return key
interactor.send_key('Return')
time.sleep(0.1)

# Send Escape key
interactor.send_key('Escape')
time.sleep(0.1)

# Send Numpad Enter key
interactor.send_key('KP_Enter')
time.sleep(0.1)

# Send Numpad number 5
interactor.send_key('KP_5')
time.sleep(0.1)

# Send Delete key
interactor.send_key('Delete')
time.sleep(0.1)
```

**Common Key Names:**

*   **Modifiers:** `Shift_L`, `Shift_R`, `Control_L`, `Control_R`, `Alt_L` (Meta), `Alt_R`, `Super_L` (Win), `Super_R`
*   **Function Keys:** `F1`, `F2`, ..., `F12`
*   **Navigation:** `Home`, `End`, `Page_Up`, `Page_Down`, `Left`, `Right`, `Up`, `Down`
*   **Editing:** `BackSpace`, `Delete`, `Insert`
*   **Special:** `Tab`, `Return` (Enter), `Escape`, `space`
*   **Numpad:** `KP_0`...`KP_9`, `KP_Add`, `KP_Subtract`, `KP_Multiply`, `KP_Divide`, `KP_Decimal`, `KP_Begin` (Num 5 when NumLock off), `KP_Enter`, `Num_Lock`
*   **Characters:** `'a'`, `'b'`, `'A'`, `'1'`, `'!'`, `'-'`, etc. (Use the character itself, modifiers like Shift handled separately if needed)

You can often find the exact keysym name you need by running the `xev` command in a terminal and pressing the desired key. Look for the name in parentheses after "keysym".

### 6. Capture Screenshot

```python
import cv2 # Optional: for displaying the image

# Capture the entire window
img_array = interactor.capture()

# The result is a NumPy array (BGRA format from mss)
print(f"Captured image shape: {img_array.shape}")

# Example: Display with OpenCV (requires opencv-python)
# Convert BGRA to BGR for cv2.imshow
# bgr_image = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
# cv2.imshow("Window Snapshot", bgr_image)
# cv2.waitKey(0)
# cv2.destroyAllWindows()

# OR capture a specific region relative to the window using XYWH format
# XYWH = (relative_x, relative_y, width, height)
xywh = (10, 20, 100, 50) # Capture a 100x50 region starting at (10, 20) within the window
img_region = interactor.capture(xywh)
print(f"Captured region shape: {img_region.shape}")

# Example: Save the region using Pillow (requires Pillow)
# from PIL import Image
# img = Image.frombytes('RGB', (img_region.shape[1], img_region.shape[0]), img_region, 'raw', 'BGRX') # Adjust based on mss format
# img.save('window_region.png')

```

### 7. Stop the Background Updater

When you are finished interacting with the window, stop the background thread.

```python
interactor.stop()
print("Background updater stopped.")
```

---

## 📷 Screenshots

*Image not included – just a placeholder*

---

## 🧠 How It Works

- Uses `python-xlib` to communicate directly with the X11 windowing system
- Utilizes `xwininfo` (called via `subprocess`) to let the user pick a target window initially
- Runs a background thread (`threading`) to periodically call `xwininfo` and keep the window's position and size (`geometry`) updated. This handles cases where the window is moved or resized after initialization.
- Sends low-level synthetic mouse (`ButtonPress`, `ButtonRelease`) and keyboard (`KeyPress`, `KeyRelease`) events directly to the window.
- Uses the high-performance `mss` library for efficient screen capture, returning a NumPy array.

---

## ⚠️ Limitations

- Only works in X11 (not Wayland)
- Application must not block synthetic events (some toolkits ignore them)

---

## 🧪 Example

Run the included example:

```bash
uv run main.py
```

---

## 📜 License

MIT License

---

## 🤝 Contributing

PRs, issues, and improvements are welcome! Feel free to fork and enhance this utility for your automation needs.

---

## ✨ Author

Made with ❤️ by [zyoNoob](https://github.com/zyoNoob)

# 🖱️ x11-window-interactor

`x11-window-interactor` is a Python utility for automating interaction with X11 windows on Linux. It allows you to:

- 🔍 Identify and target X11 windows
- 🖱️ Send mouse clicks to specific relative coordinates in the window
- ⌨️ Send keyboard keypresses directly to the window
- 📸 Capture screenshots of a window into OpenCV-compatible image arrays

This tool is ideal for GUI automation, testing, and custom tooling in X environments.

---

## 💪 Features

- **Find window by clicking on it (via `xwininfo`)**
- **Send mouse events** to any coordinates within the window
- **Send keypresses** directly to the application (even in background)
- **Capture the window** into a `cv2`-ready NumPy array
- **Get relative cursor position** for easier automation script building

---

## 👷️ Requirements

- Python 3.8+
- Linux with X11
- X utilities installed (`xwininfo`)
- Packages:
  - `python-xlib`
  - `numpy`
  - `opencv-python`
  - `gcc` (for compiling the C code)
  - `libx11-dev` (X11 development headers)

### Building the C Library

The screen capture functionality uses a C library for improved performance. To build it:

```bash
gcc -shared -O3 -lX11 -fPIC -Wl,-soname,prtscn -o prtscn.so prtscn.c
```

To setup the python environment use uv toolkit.

```bash
uv sync
```

The library must be in the same directory as `x11_interactor.py`.

---

## 📁 Project Structure

```
x11-window-interactor/
├── main.py                # Example usage
├── x11_interactor.py      # Core X11WindowInteractor class
├── pyproject.toml
├── README.md
├── .gitignore
├── prtscn.c               # C library for screen capture
├── prtscn.so              # Compiled C library
└── .venv/                 # Virtual environment (optional)
```

---

## 🚀 Usage

### 1. Create the Interactor

```python
from x11_interactor import X11WindowInteractor

interactor = X11WindowInteractor()
```

### 2. Get Cursor Coordinates Relative to the Window

```python
print(interactor.get_relative_cursor_position())
```

### 3. Click Inside the Window

```python
# Click at (x=200, y=300) relative to window
interactor.click(200, 300)
```

### 4. Send a Keypress

```python
from Xlib import XK

# Send a keypress (e.g., 'A')
interactor.send_key(XK.XK_A)
```

### 5. Capture Screenshot

```python
# Capture the entire window
img = interactor.capture()
# Now you can use it with OpenCV
cv2.imshow("Window Snapshot", img)
cv2.waitKey(0)

# OR capture a specific region using TLWH format
# TLWH = (top, left, width, height)
tlwh = (100, 100, 300, 200)
# This will grab a (300x200) cropped image from the coordinates (100,100)
img = interactor.capture(tlwh)
# Now you can use it with OpenCV
cv2.imshow("Window Snapshot", img)
cv2.waitKey(0)
```

### 6. Benchmark Capture Performance

```python
# Run benchmark to measure capture performance
interactor.benchmark_capture(num_frames=100)
```

---

## 📷 Screenshots



*Image not included – just a placeholder*

---

## 🧠 How It Works

- Uses `Xlib` to communicate directly with the X11 windowing system
- Utilizes `xwininfo` to let the user pick a target window
- Sends low-level synthetic mouse and keyboard events directly to the window
- Uses a high-performance C library for screen capture, which reads raw pixel data from the X11 display using `XGetImage` and converts it into a usable format with NumPy + OpenCV

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

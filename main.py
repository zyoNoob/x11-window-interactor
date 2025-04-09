from x11_interactor import X11WindowInteractor
from Xlib import XK
import time
import numpy as np
# Optional: Import cv2 if you want to display images captured or used for ROI selection
try:
    import cv2
except ImportError:
    cv2 = None

def benchmark_capture(interactor, num_frames=100):
    """
    Benchmark the capture function by capturing multiple frames and calculating average FPS.
    """
    times = []

    print("Starting benchmark...")
    for i in range(num_frames):
        start_time = time.time()
        _ = interactor.capture()
        end_time = time.time()
        
        times.append(end_time - start_time)
        
        # Show progress
        if (i + 1) % 10 == 0:
            print(f"Captured {i + 1}/{num_frames} frames")
    
    # Calculate statistics
    times = np.array(times)
    avg_time = np.mean(times)
    fps = 1.0 / avg_time

    print("\nBenchmark Results:")
    print(f"Average time per frame: {avg_time:.4f} seconds")
    print(f"Average FPS: {fps:.2f}")
    print(f"Min time: {np.min(times):.4f} seconds")
    print(f"Max time: {np.max(times):.4f} seconds")
    print(f"Standard deviation: {np.std(times):.4f} seconds")

def main():
    interactor = X11WindowInteractor()
    interactor.activate()
    coordinates = interactor.get_relative_cursor_position()

    time.sleep(2)
    # Example usage
    interactor.activate()
    print("Cursor relative to window:", coordinates)
    interactor.click(coordinates[0], coordinates[1])
    time.sleep(1) # Reduced sleep time
    interactor.send_key('1')
    time.sleep(1) # Reduced sleep time

    # --- Example for select_roi_interactive (requires 'slop') ---
    print("\nAttempting ROI selection using 'slop'...")
    roi_slop = interactor.select_roi_interactive()
    if roi_slop:
        print(f"ROI selected via slop: {roi_slop}")
        # Example: Capture the selected ROI
        img_roi_slop = interactor.capture(xywh=roi_slop)
        print(f"Captured slop ROI shape: {img_roi_slop.shape}")
        # Optional: Display with OpenCV
        if cv2:
            try:
                cv2.imshow("Slop ROI Capture", cv2.cvtColor(img_roi_slop, cv2.COLOR_BGRA2BGR))
                cv2.waitKey(2000) # Display for 2 seconds
                cv2.destroyWindow("Slop ROI Capture")
            except Exception as e:
                print(f"Could not display slop ROI image with OpenCV: {e}")
    else:
        print("ROI selection with slop failed or was cancelled.")

    time.sleep(1)

    # --- Example for select_roi_interactive_cv (requires 'opencv-python') ---
    print("\nAttempting ROI selection using OpenCV...")
    # You can optionally pass a pre-captured image:
    # initial_capture = interactor.capture()
    # roi_cv = interactor.select_roi_interactive_cv(image=initial_capture)
    # Or let it capture internally:
    roi_cv = interactor.select_roi_interactive_cv()
    if roi_cv:
        print(f"ROI selected via OpenCV: {roi_cv}")
        # Example: Capture the selected ROI
        img_roi_cv = interactor.capture(xywh=roi_cv)
        print(f"Captured OpenCV ROI shape: {img_roi_cv.shape}")
        # Optional: Display with OpenCV
        if cv2:
            try:
                cv2.imshow("OpenCV ROI Capture", cv2.cvtColor(img_roi_cv, cv2.COLOR_BGRA2BGR))
                cv2.waitKey(2000) # Display for 2 seconds
                cv2.destroyWindow("OpenCV ROI Capture")
            except Exception as e:
                print(f"Could not display OpenCV ROI image with OpenCV: {e}")
    else:
        print("ROI selection with OpenCV failed or was cancelled.")

    time.sleep(1)

    # Run benchmark
    benchmark_capture(interactor)

    # Stop the background updater before exiting
    print("\nStopping background updater...")
    interactor.stop()
    print("Interactor stopped.")

if __name__ == "__main__":
    main()

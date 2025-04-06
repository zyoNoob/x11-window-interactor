from x11_interactor import X11WindowInteractor
from Xlib import XK
import cv2
import time
import numpy as np

def benchmark_capture(interactor, num_frames=100):
    """
    Benchmark the capture function by capturing multiple frames and calculating average FPS.
    """
    times = []
    
    print("Starting benchmark...")
    for i in range(num_frames):
        start_time = time.time()
        img = interactor.capture()
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
    coordinates = interactor.get_relative_cursor_position()

    time.sleep(5)
    # Example usage
    interactor.activate()
    print("Cursor relative to window:", coordinates)
    interactor.click(coordinates[0], coordinates[1])
    time.sleep(0.1)
    
    # Run benchmark
    benchmark_capture(interactor)

if __name__ == "__main__":
    main()

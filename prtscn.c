// COMPILE - gcc -O3 -Wall -fPIC -shared prtscn.c -o prtscn.so -lX11 -lXext -Wl,-soname=prtscn

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <X11/X.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/extensions/XShm.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <unistd.h>

static Display *display = NULL;
static Window root;
static XImage *ximage = NULL;
static XShmSegmentInfo shminfo;
static int capture_x = 0;
static int capture_y = 0;
static int capture_width = 0;
static int capture_height = 0;
static long last_capture_us = 0;

long current_time_us() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec * 1000000L + tv.tv_usec;
}

// init_capture(x, y, width, height)
int init_capture(int x, int y, int w, int h) {
    display = XOpenDisplay(NULL);
    if (!display) return -1;

    root = DefaultRootWindow(display);
    capture_x = x;
    capture_y = y;
    capture_width = w;
    capture_height = h;

    ximage = XShmCreateImage(display, DefaultVisual(display, 0),
                             DefaultDepth(display, 0), ZPixmap, NULL, &shminfo,
                             capture_width, capture_height);
    if (!ximage) return -2;

    shminfo.shmid = shmget(IPC_PRIVATE,
                           ximage->bytes_per_line * ximage->height,
                           IPC_CREAT | 0777);
    if (shminfo.shmid < 0) return -3;

    shminfo.shmaddr = ximage->data = (char *)shmat(shminfo.shmid, 0, 0);
    shminfo.readOnly = False;

    if (!XShmAttach(display, &shminfo)) return -4;

    return 0;
}

int capture_frame(unsigned char *data) {
    if (!ximage) return -1;

    long start = current_time_us();

    XShmGetImage(display, root, ximage, capture_x, capture_y, AllPlanes);

    int index = 0;
    for (int y = 0; y < ximage->height; ++y) {
        for (int x = 0; x < ximage->width; ++x) {
            unsigned long pixel = XGetPixel(ximage, x, y);
            unsigned char r = (pixel & ximage->red_mask) >> 16;
            unsigned char g = (pixel & ximage->green_mask) >> 8;
            unsigned char b = (pixel & ximage->blue_mask);
            data[index++] = r;
            data[index++] = g;
            data[index++] = b;
        }
    }

    long end = current_time_us();
    last_capture_us = end - start;

    return 0;
}

long get_last_capture_time_us() {
    return last_capture_us;
}

void close_capture() {
    if (!display) return;

    XShmDetach(display, &shminfo);
    XDestroyImage(ximage);
    shmdt(shminfo.shmaddr);
    shmctl(shminfo.shmid, IPC_RMID, 0);
    XCloseDisplay(display);
    display = NULL;
}
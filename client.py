from picamera import PiCamera
from picamera.array import PiRGBArray
import cv2
import time
import io

camera = PiCamera()
resolution = (320, 240)
camera.resolution = resolution
camera.framerate = 60
raw_capture = PiRGBArray(camera, size=resolution)
#raw_capture = io.BytesIO()

smoothing = 0.9
average_fps = 0

time.sleep(1)
start = time.time()

for frame in camera.capture_continuous(raw_capture, format="bgr", use_video_port=True):

    cv2.imshow("Frame", frame.array)
    cv2.waitKey(1) & 0xFF

    raw_capture.seek(0)
    raw_capture.truncate(0)

    time_taken = time.time() - start
    current_fps = 1./time_taken
    average_fps = average_fps * smoothing + current_fps * (1 - smoothing)        
    print average_fps

    start = time.time()


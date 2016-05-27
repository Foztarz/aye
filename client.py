from picamera import PiCamera
from picamera.array import PiRGBArray
import cv2
import time

camera = PiCamera()
camera.resolution = (320, 240)
camera.framerate = 15
raw_capture = PiRGBArray(camera, size=(320,240))

smoothing = 0.9
average_fps = 0

time.sleep(1)
start = time.time()

for frame in camera.capture_continuous(raw_capture, format="bgr", use_video_port=True):

    #cv2.imshow("Frame", frame.array)
    #cv2.waitKey(1) & 0xFF
    raw_capture.truncate(0)

    time_taken = time.time() - start
    current_fps = 1./time_taken
    average_fps = average_fps * smoothing + current_fps * (1 - smoothing)        
    print average_fps

    start = time.time()

    

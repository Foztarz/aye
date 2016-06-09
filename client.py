from picamera import PiCamera
from picamera.array import PiRGBArray
import cv2
import time
import io
import socket
import struct

millis = lambda: int(round(time.time() * 1000))

camera = PiCamera()
resolution = (320, 240)
camera.resolution = resolution
camera.framerate = 30
raw_capture = io.BytesIO()

time.sleep(2)

smoothing = 0.9
average_fps = 0

while True:
    try:
        consumer_socket = socket.socket()
        consumer_socket.connect(('172.24.1.1', 8123))
        consumer = consumer_socket.makefile('wb')
        reference_millis = struct.unpack('<Q', consumer.read(struct.calcsize('<Q')))[0]
        drift = reference_millis - millis() 

        print("Drift is %f" % drift)

        start = time.time()

        try:
            for frame in camera.capture_continuous(raw_capture, format="jpeg", use_video_port=True):

                consumer.write(struct.pack('<L', raw_capture.tell()))
                consumer.write(struct.pack('<Q', millis() + drift))
                consumer.flush()
                raw_capture.seek(0)

                consumer.write(raw_capture.read())
                raw_capture.seek(0)
                raw_capture.truncate(0)

                time_taken = time.time() - start
                current_fps = 1./time_taken
                average_fps = average_fps * smoothing + current_fps * (1 - smoothing)        
                print average_fps

                start = time.time()

        finally:
            consumer.close()
            consumer_socket.close()
    except Exception as e:
        continue

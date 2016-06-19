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

CONSUMER_ADDRESS = '172.24.1.1'

while True:
    try:
        consumer_tcp_socket = socket.socket()
        consumer_tcp_socket.connect((CONSUMER_ADDRESS, 8123))
        consumer_tcp = consumer_tcp_socket.makefile('wb')

        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        reference_millis = struct.unpack('<Q', consumer_tcp.read(struct.calcsize('<Q')))[0]
        consumer_port = struct.unpack('<L', consumer_tcp.read(struct.calcsize('<L')))[0]
        drift = reference_millis - millis() 

        print("Drift is %f" % drift)

        start = time.time()

        try:
            for frame in camera.capture_continuous(raw_capture, format="jpeg", use_video_port=True):

                udp_socket.sendto(struct.pack('<L', raw_capture.tell()), (CONSUMER_ADDRESS, consumer_port))
                udp_socket.sendto(struct.pack('<Q', millis() + drift), (CONSUMER_ADDRESS, consumer_port))
                raw_capture.seek(0)

                udp_socket.sendto(raw_capture.read(), (CONSUMER_ADDRESS, consumer_port))
                raw_capture.seek(0)
                raw_capture.truncate(0)

                time_taken = time.time() - start
                current_fps = 1./time_taken
                average_fps = average_fps * smoothing + current_fps * (1 - smoothing)        
                print average_fps

                start = time.time()

        finally:
            consumer_tcp.close()
            consumer_tcp_socket.close()
            udp_socket.close()
    except Exception as e:
        continue

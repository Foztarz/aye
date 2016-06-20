from picamera import PiCamera
from picamera.array import PiRGBArray
import cv2
import time
import io
import socket
import struct
import errno
import os
import datetime
import numpy as np

millis = lambda: int(round(time.time() * 1000))
timestamp = lambda: "{:%Y-%m-%d-%H:%M:%S}-".format(datetime.datetime.utcnow()) + str(millis())

camera = PiCamera()
resolution = (320, 240)
camera.resolution = resolution
camera.framerate = 30
raw_capture = io.BytesIO()

time.sleep(2)

smoothing = 0.9
average_fps = 0

CONSUMER_ADDRESS = '172.24.1.1'
WORKING_DIRECTORY = '/home/pi/aye-data'

hostname = socket.gethostname()

print "[%s] Trying to connect to consumer..." % hostname

def raw_to_cv(raw_image):
    return cv2.imdecode(np.fromstring(raw_image, dtype=np.uint8), 1)

while True:
    try:
        consumer_tcp_socket = socket.socket()
        consumer_tcp_socket.connect((CONSUMER_ADDRESS, 8123))
        consumer_tcp = consumer_tcp_socket.makefile('wb')

        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        reference_millis = struct.unpack('<Q', consumer_tcp.read(struct.calcsize('<Q')))[0]
        consumer_port = struct.unpack('<L', consumer_tcp.read(struct.calcsize('<L')))[0]

        directory = "%s/%s" % (WORKING_DIRECTORY, timestamp())
        os.makedirs(directory)

        drift = reference_millis - millis() 

        print("[%s] Drift is %f" % (hostname, drift))

        drift_file = open(directory + "/drift.txt", "w")
        drift_file.write(str(drift) + "\n")
        drift_file.close()

        try:
            start = time.time()

            count = 0

            FORMAT = "jpeg"
            for frame in camera.capture_continuous(raw_capture, format=FORMAT, use_video_port=True):

                message = struct.pack('<L', raw_capture.tell()) + struct.pack('<Q', millis() + drift)
                raw_capture.seek(0)
                raw_image = raw_capture.read()
                message = message + raw_image

                cv2.imwrite("%s/%s-%d-%s.%s" % (directory, hostname, count, timestamp(), FORMAT), raw_to_cv(raw_image))

                if len(message) > 64000:
                    print "Message is too long:", len(message)
                else:
                    udp_socket.sendto(message, (CONSUMER_ADDRESS, consumer_port))

                raw_capture.seek(0)
                raw_capture.truncate(0)

                time_taken = time.time() - start
                current_fps = 1./time_taken
                average_fps = average_fps * smoothing + current_fps * (1 - smoothing)        
                print average_fps

                start = time.time()
                count = count + 1

        finally:
            consumer_tcp.close()
            consumer_tcp_socket.close()
            udp_socket.close()
    except socket.error, e:
        if e[0] == errno.ECONNREFUSED:
            continue
        else:
            raise

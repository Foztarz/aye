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

BUFFER_SIZE = 100

def millis(drift_ms = 0):
    return int(round(time.time() * 1000)) + drift_ms

def timestamp(drift_ms = 0):
    time_plus_drift = datetime.datetime.utcnow() + datetime.timedelta(milliseconds=drift_ms)
    return "t{:%Y-%m-%d-%H:%M:%S}m".format(time_plus_drift) + str(millis(drift))

#def raw_to_cv(raw_image):
#    return cv2.imdecode(np.fromstring(raw_image, dtype=np.uint8), 1)

buffer = []
#def save_image(image_name, image):
#    global buffer
#    buffer.append((image_name, image))
#    if len(buffer) > BUFFER_SIZE:
#        for image_name, image in buffer:
#            cv2.imwrite(image_name, image)
#        buffer = []

camera = PiCamera()
resolution = (320, 240)
camera.resolution = resolution
camera.framerate = 5
raw_capture = io.BytesIO()

time.sleep(2)

smoothing = 0.9
average_fps = 0

CONSUMER_ADDRESS = '172.24.1.1'
WORKING_DIRECTORY = '/home/pi/aye-data'

hostname = socket.gethostname()

print "[%s] Trying to connect to consumer..." % hostname

while True:
    try:
        consumer_tcp_socket = socket.socket()
        consumer_tcp_socket.connect((CONSUMER_ADDRESS, 8123))
        consumer_tcp = consumer_tcp_socket.makefile('wb')

        reference_millis = struct.unpack('<Q', consumer_tcp.read(struct.calcsize('<Q')))[0]

        drift = reference_millis - millis() 

        print("[%s] Drift is %f" % (hostname, drift))

        directory = "%s/%s%s" % (WORKING_DIRECTORY, hostname, timestamp(drift))
        os.makedirs(directory)

        try:
            start = time.time()

            count = 0

            FORMAT = "png"
            for frame in camera.capture_continuous(raw_capture, format=FORMAT, use_video_port=True):

                message = struct.pack('<L', raw_capture.tell()) + struct.pack('<Q', millis() + drift)
                consumer_tcp.write(message)
                consumer_tcp.flush()

                raw_capture.seek(0)
                raw_image = raw_capture.read()

                #save_image("%s/%s-%d-%s.%s" % (directory, hostname, count, timestamp(drift), FORMAT), raw_to_cv(raw_image))

                consumer_tcp.write(raw_image)
                consumer_tcp.flush()

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
    except socket.error, e:
        if e[0] == errno.ECONNREFUSED:
            continue
        else:
            raise

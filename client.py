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

INDOOR_SHUTTER_SPEED = 33243
OUTDOOR_SHUTTER_SPEED = 200

INDOOR_AWB_GAINS = (1, 2)
OUTDOOR_AWB_GAINS = (2, 1)

BUFFER_SIZE = 100

def freeze_camera_settings(camera, indoor = False):
    if indoor:
        camera.shutter_speed = INDOOR_SHUTTER_SPEED
    else:
        camera.shutter_speed = OUTDOOR_SHUTTER_SPEED

    camera.exposure_mode = 'off'
    #g = camera.awb_gains
    #camera.awb_mode = 'off'
    #time.sleep(1)

    #if indoor:
    #    camera.awb_gains = INDOOR_AWB_GAINS
    #else: 
    #    camera.awb_gains = OUTDOOR_AWB_GAINS

    print "Camera properties frozen at:"
    print "iso", camera.iso
    print "shutter_speed preferred", camera.exposure_speed, " actual ", camera.shutter_speed
    #print "awb_gains preferred", g, " actual ", camera.awb_gains
    print "analog_gain", camera.analog_gain
    print "digital_gain", camera.digital_gain

def millis(drift_ms = 0):
    return int(round(time.time() * 1000)) + drift_ms

def timestamp(drift_ms = 0):
    time_plus_drift = datetime.datetime.utcnow() + datetime.timedelta(milliseconds=drift_ms)
    return "t{:%Y-%m-%d-%H:%M:%S}m".format(time_plus_drift) + str(millis(drift))

def raw_to_cv(raw_image):
    return cv2.imdecode(np.fromstring(raw_image, dtype=np.uint8), 1)

buffer = []
def save_image(image_name, image):
    global buffer
    buffer.append((image_name, image))
    if len(buffer) > BUFFER_SIZE:
        for image_name, image in buffer:
            cv2.imwrite(image_name, image)
        buffer = []

camera = PiCamera()
resolution = (320, 240)
camera.resolution = resolution
camera.framerate = 5
raw_capture = io.BytesIO()

camera.iso = 100
time.sleep(2)

freeze_camera_settings(camera)

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

        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        reference_millis = struct.unpack('<Q', consumer_tcp.read(struct.calcsize('<Q')))[0]
        consumer_port = struct.unpack('<L', consumer_tcp.read(struct.calcsize('<L')))[0]

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
                raw_capture.seek(0)
                raw_image = raw_capture.read()
                grayscale_image = cv2.imdecode(np.fromstring(raw_image, dtype=np.uint8), 0)
                message = message + cv2.imencode('.'+FORMAT, grayscale_image)[1].tostring()

                save_image("%s/%s-%d-%s.%s" % (directory, hostname, count, timestamp(drift), FORMAT), raw_to_cv(raw_image))

                if len(message) > 64000:
                    print "Message is too long:", len(message), " truncating..."
                    message = message[:64000]

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

from picamera import PiCamera
from picamera.array import PiRGBArray
import time
import io
import socket
import struct
import errno
import os
import datetime
import numpy as np
import datetime
import cv2

CONSUMER_ADDRESS = '172.24.1.1'
WORKING_DIRECTORY = '/home/pi/aye-data'
HOSTNAME = socket.gethostname()
FORMAT = "raw.jpeg"


def timestamp(dt):
    time_plus_drift = dt 
    return "t{:%Y-%m-%d-%H:%M:%S}".format(dt)

def timestamp_from_millis(millis):
    return timestamp(datetime.datetime.fromtimestamp(millis/1000))

def cv2_from_bytes(image_bytes):
    image_stream = io.BytesIO()
    image_stream.write(image_bytes)

    image_stream.seek(0)
    data = np.fromstring(image_stream.getvalue(), dtype=np.uint8)
    image = cv2.imdecode(data, 1)

    return image

class PanoramaImageProducer:
    def __init__(self):
        self.camera = PiCamera()
        resolution = (2592, 1944) # http://picamera.readthedocs.io/en/release-1.10/fov.html
        self.camera.resolution = resolution
        self.camera.framerate = 5
        self.raw_capture = io.BytesIO()
        time.sleep(2)

    def connect_to_consumer(self):
        print "[%s] trying to connect to consumer..." % HOSTNAME
        consumer_tcp_socket = socket.socket()
        consumer_tcp_socket.connect((CONSUMER_ADDRESS, 8123))
        self.consumer = consumer_tcp_socket.makefile('wb')

        data_label_length = struct.unpack('<L', self.consumer.read(struct.calcsize('<L')))[0]
        data_label = self.consumer.read(data_label_length)
        millis = struct.unpack('<Q', self.consumer.read(struct.calcsize('<Q')))[0]

        print "[%s] millis %d" % (HOSTNAME, millis)
        print "[%s] sending sample image" % HOSTNAME
        self.directory = "%s/%s-%s%s" % (WORKING_DIRECTORY, HOSTNAME, data_label, timestamp_from_millis(millis))
        os.makedirs(self.directory)

        if HOSTNAME == 'aye-vis':
            self.consumer.write(struct.pack('<L', self.camera.exposure_speed))
            self.consumer.flush()

        image_bytes = self.capture()
        image = cv2_from_bytes(image_bytes)
        smaller_image = cv2.resize(image, (320, 240)) 
        smaller_image_bytes = cv2.imencode('.jpg', smaller_image)[1].tostring()
        self.consumer.write(struct.pack('<L', len(smaller_image_bytes)))
        self.consumer.write(smaller_image_bytes)
        self.consumer.flush()

        self.save(image, "test", millis, self.directory)


    def start(self):
        print "[%s] ready to capture" % HOSTNAME

        if 'pol' in HOSTNAME:
            shutter_speed = struct.unpack('<L', self.consumer.read(struct.calcsize('<L')))[0]
            print("Setting shutter speed to %d" % shutter_speed)
            self.camera.shutter_speed = shutter_speed
            self.camera.exposure_mode = 'off'

        while True:
            millis = struct.unpack('<Q', self.consumer.read(struct.calcsize('<Q')))[0]
            if millis == 0:
                print "Received end signal from orchestrator"
                break

            image_id_size = struct.unpack('<L', self.consumer.read(struct.calcsize('<L')))[0]

            image_id = self.consumer.read(image_id_size)

            if self.save(self.capture(), image_id, millis, self.directory):
                self.consumer.write('ok')
                self.consumer.flush()
            else:
                self.consumer.write('no')
                self.consumer.flush()

    def capture(self):
        self.raw_capture.seek(0)
        self.raw_capture.truncate(0)

        self.camera.capture(self.raw_capture, format="jpeg", bayer=True) #http://picamera.readthedocs.io/en/release-1.10/recipes2.html#raw-bayer-data-captures
        self.raw_capture.seek(0)

        return self.raw_capture.read()

    def save(self, image, image_id, millis, directory):
        image_name = "%s-%s%s.%s" % (HOSTNAME, image_id, timestamp_from_millis(millis), FORMAT)
        file = open(os.path.join(directory, image_name), 'w')
        file.write(image)
        file.close()

        return True


if __name__ == "__main__":
    panorama_image_producer = PanoramaImageProducer()

    panorama_image_producer.connect_to_consumer()

    panorama_image_producer.start()


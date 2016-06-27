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

CONSUMER_ADDRESS = '172.24.1.1'
WORKING_DIRECTORY = '/home/pi/aye-data'
HOSTNAME = socket.gethostname()
FORMAT = "raw.jpeg"


def timestamp(dt):
    time_plus_drift = dt 
    return "t{:%Y-%m-%d-%H:%M:%S}".format(dt)

def timestamp_from_millis(millis):
    return timestamp(datetime.datetime.fromtimestamp(millis))

class PanoramaImageProducer:
    def __init__(self):
        self.camera = PiCamera()
        resolution = (2592, 1945) # http://picamera.readthedocs.io/en/release-1.10/fov.html
        self.camera.resolution = resolution
        self.camera.framerate = 5
        self.raw_capture = io.BytesIO()

    def connect_to_consumer(self):
        print "[%s] trying to connect to consumer..." % HOSTNAME
        consumer_tcp_socket = socket.socket()
        consumer_tcp_socket.connect((CONSUMER_ADDRESS, 8123))
        self.consumer = consumer_tcp_socket.makefile('wb')

        millis = struct.unpack('<Q', self.consumer.read(struct.calcsize('<Q')))[0]

        print "[%s] sending sample image" % HOSTNAME
        image = self.capture()
        self.consumer.write(struct.pack('<Q', 32768))
        self.consumer.write(image[:32768]) # exclude raw data
        self.consumer.flush()

        self.directory = "%s/%s-%s" % (WORKING_DIRECTORY, HOSTNAME, timestamp_from_millis(millis))
        os.makedirs(self.directory)

    def start(self):
        time.sleep(2)
        
        print "[%s] ready to capture" % HOSTNAME

        while True:
            millis = struct.unpack('<Q', self.consumer.read(struct.calcsize('<Q')))[0]
            if millis == -1:
                print "Received end signal from orchestrator"
                break

            image_id_size = struct.unpack('<L', self.consumer.read(struct.calcsize('<L')))[0]

            image_id = self.consumer.read(image_id_size)

            if self.save(self.capture(), image_id, self.directory):
                self.consumer.write('ok')
                self.consumer.flush()
            else:
                self.consumer.write('no')

    def capture(self):
        self.camera.capture(self.raw_capture, format="jpeg", bayer=True) #http://picamera.readthedocs.io/en/release-1.10/recipes2.html#raw-bayer-data-captures
        return self.raw_capture

    def save(self, image, image_id, directory):
        image_name = "%s-%s.%s" % (HOSTNAME, image_id, FORMAT)
        file = open(os.path.join(directory, image_name), 'w')
        file.write(image)
        file.close()


if __name__ == "__main__":
    panorama_image_producer = PanoramaImageProducer()

    panorama_image_producer.connect_to_consumer()

    panorama_image_producer.start()


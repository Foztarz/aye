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

CONSUMER_ADDRESS = '172.24.1.1'
WORKING_DIRECTORY = '/home/pi/aye-data'
HOSTNAME = socket.gethostname()
FORMAT = "raw.png"

class PanoramaImageProducer:
    def __init__(self):
        self.camera = PiCamera()
        resolution = (320, 240)
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
        self.consumer.write(struct.pack('<Q', len(image)))
        self.consumer.write(image)
        self.consumer.flush()

        # TODO make function for timestamp from millis
        self.directory = "%s/%s%s" % (WORKING_DIRECTORY, HOSTNAME, timestamp(millis))
        os.makedirs(self.directory)

    def start(self):
        time.sleep(2)
        
        print "[%s] ready to capture" % HOSTNAME

        millis = struct.unpack('<Q', self.consumer.read(struct.calcsize('<Q')))[0]
        image_id_size = struct.unpack('<L', self.consumer.read(struct.calcsize('<L')))[0]

        image_id = self.consumer.read(image_id_size)

        if self.save(self.capture(), image_id, self.directory):
            self.consumer.write('ok')
            self.consumer.flush()
        else:
            self.consumer.write('no')

    def capture(self):
        #TODO capture still, raw, high res image from camera
        pass

    def save(self, image, image_id, directory):
        image_name = "%s-%s.%s" % (HOSTNAME, image_id, FORMAT)
        file = open(os.path.join(directory, image_name), 'w')
        file.write(image)
        file.close()


if __name__ == "__main__":
    panorama_image_producer = PanoramaImageProducer()

    panorama_image_producer.connect_to_consumer()

    panorama_image_producer.start()


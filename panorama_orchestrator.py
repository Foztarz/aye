from panorama_control import PanoramaControl
import socket
import select
import struct
import time
import io
import numpy as np
import cv2
import sys

millis = lambda: int(round(time.time() * 1000))

class PanoramaOrchestrator:
    address_to_name = {
        '172.24.1.91' : 'pol-0',
        '172.24.1.97' : 'pol-45',
        '172.24.1.1' : 'pol-90',
        '172.24.1.118' : 'aye-uv',
        '172.24.1.87': 'aye-ir',
        '172.24.1.137': 'aye-vis'
    }

    def __init__(self, data_label):
        self.tcp_socket = socket.socket()
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('0.0.0.0', 8123))
        self.tcp_socket.listen(0)

        self.producers = []
        self.file_to_name = {}
        self.data_label = data_label

    def connect(self):
        while True:
            ready_to_read, ready_to_write, in_error = \
                    select.select(
                            [self.tcp_socket] + self.producers, # potential readers
                            [], # potential writers
                            [], # potential errors
                            1) 
            for to_read in ready_to_read:
                if to_read is self.tcp_socket:
                    connection, address = self.tcp_socket.accept()
                    producer_address = address[0]
                    print("New connection from %s (%s)" % (producer_address, self.address_to_name[producer_address]))
                    file = connection.makefile('rb')
                    file.write(struct.pack('<L', len(self.data_label)))
                    file.write(self.data_label)
                    file.write(struct.pack('<Q', millis()))
                    file.flush()

                    self.producers.append(file)

                    producer_name = self.address_to_name[producer_address]
                    if producer_name == 'aye-vis':
                        self.polarization_shutter = struct.unpack('<L', file.read(struct.calcsize('<L')))[0]
                        print "Polarization shutter is %d" % self.polarization_shutter

                    self.file_to_name[file] = producer_name 

            if len(self.producers) == len(self.address_to_name.keys()):
                print("All producers are connected.")
                break

    def capture(self, use_pan, use_tilt):
        for producer in self.producers:
            if 'pol' in self.file_to_name[producer]:
                producer.write(struct.pack('<L', self.polarization_shutter))
                producer.flush()

        panorama_control = PanoramaControl(use_pan=use_pan, use_tilt=use_tilt, pan_step_degrees = 5)

        while panorama_control.step():
            time.sleep(1)
            (pan, pan_degrees), (tilt, tilt_degrees) = panorama_control.get_status()
            image_id = '%s-%d-%s-%d-%s' % (pan, pan_degrees, tilt, tilt_degrees, self.data_label)

            if not pan:
                image_id = '%s-%d-%s' % (tilt, tilt_degrees, self.data_label)

            if not tilt:
                image_id = '%s-%d-%s' % (pan, pan_degrees, self.data_label)

            if not tilt and not pan:
                image_id = '%s' % self.data_label

            for producer in self.producers:
                producer_name = self.file_to_name[producer]

                success = False
                print('Asking for image from producer %s' % producer_name)

                producer.write(struct.pack('<Q', millis()))
                producer.write(struct.pack('<L', len(image_id)))
                producer.write(image_id)
                producer.flush()

            responses = 0
            while responses < len(self.producers):
                ready_to_read, ready_to_write, in_error = \
                        select.select(
                                self.producers, # potential readers
                                [], # potential writers
                                [], # potential errors
                                1) 

                for producer in ready_to_read:
                    responses = responses + 1
                    result = struct.unpack('<L', producer.read(struct.calcsize('<L')))[0]
                    if result != 0:
                        producer_name = self.file_to_name[producer]
                        print('Producer %s produced an error code %d.' % (producer_name, result))

        for producer in self.producers:
            producer.write(struct.pack('<Q', 0))

        print "Panorama capture complete"

    def consume(self, file):
        image_len = struct.unpack('<L', file.read(struct.calcsize('<L')))[0]
        print "Image length is %d" % image_len

        data = file.read(image_len)

        image_stream = io.BytesIO()
        image_stream.write(data)

        image_stream.seek(0)
        data = np.fromstring(image_stream.getvalue(), dtype=np.uint8)
        image = cv2.imdecode(data, 1)

        return image


if __name__ == "__main__":
    panorama_orchestrator = PanoramaOrchestrator(sys.argv[1])

    # connect to clients, display preview and wait for user adjustments
    panorama_orchestrator.connect() 

    # capture the panorama
    panorama_orchestrator.capture(use_pan=True, use_tilt=False)

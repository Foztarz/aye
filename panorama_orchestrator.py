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
        samples = {}
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
                    self.file_to_name[file] = self.address_to_name[producer_address]
                else:
                    producer_name = self.file_to_name[to_read]
                    image = self.consume(to_read)

                    samples[producer_name] = image

            if len(self.producers) == len(self.address_to_name.keys()):
                for producer_name, image in samples.items():
                    cv2.imshow(producer_name, image)
                    cv2.waitKey(1)

                break

    def capture(self):
        panorama_control = PanoramaControl()

        while panorama_control.step():
            status = panorama_control.status()
            image_id = '%s-panorama-part-%s' % (self.data_label, '-'.join(map(str, status)))
            for producer in self.producers:
                producer_name = self.file_to_name[producer]
                success = False
                while attempt < 3: 
                    producer.write(struct.pack('<Q', millis()))
                    producer.write(struct.pack('<L', len(image_id)))
                    producer.write(image_id)
                    producer.flush()
                    ok = producer.read(2)
                    if ok == 'ok':
                        success = True
                        break
                    else: 
                        retry = retry + 1
                        print('Producer %s did not respond ok on %d attempt' % (producer_name, attempt))

                if not success:
                    print('Failed to contact producer %s. Panorama capture failed at %s.' % (producer_name, image_id))

        producer.write(struct.pack('<Q', -1))
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
    panorama_orchestrator.capture()

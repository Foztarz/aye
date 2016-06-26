from panorama_control import PanoramaControl

class PanoramaOrchestrator:
    address_to_name = {
        '172.24.1.91' : 'pol-0',
        '172.24.1.97' : 'pol-45',
        '172.24.1.1' : 'pol-90',
        '172.24.1.118' : 'aye-uv',
        '172.24.1.87': 'aye-ir',
        '172.24.1.137': 'aye-vis'
    }

    def __init__(self):
        tcp_socket = socket.socket()
        tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_socket.bind(('0.0.0.0', 8123))
        tcp_socket.listen(0)

        self.producers = []
        self.file_to_name = []

    def connect(self):
        while True:
            ready_to_read, ready_to_write, in_error = \
                    select.select(
                            [tcp_socket] + producers, # potential readers
                            [], # potential writers
                            [], # potential errors
                            60) 
         for to_read in ready_to_read:
            if to_read is tcp_socket:
                connection, address = tcp_socket.accept()
                producer_address = address[0]
                print("New connection from %s (%s)" % (producer_address, address_to_name[producer_address]))
                file = connection.makefile('rb')
                file.write(struct.pack('<Q', millis()))
                file.flush()

                self.producers.append(file)
                self.file_to_name[file] = self.address_to_name[producer_address]
            else:
                producer_name = file_to_name[to_read]
                try:
                    image, timestamp = consume(to_read)
                except Exception, message:
                    print "Exception consuming %s" % producer_name, message
                    continue

                if image is None:
                    print("Image from %s is None" % producer_name)
                    continue

                cv2.imshow(producer_name, image)
                key = cv2.waitKey(1) & 0xFF
                if key == 'N':
                    break

    def capture(self):
        panorama_control = PanoramaControl()

        while panorama_control.step():
            status = panorama_control.status()
            image_id = 'panorama-%s' % '-'.join(map(str, status))
            # size of image_id should be constant 
            for producer in producers:
                producer_name = file_to_name[producer]
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

        print "Panorama capture complete"

    def consume(file):
        expected_image_len_size = struct.calcsize('<L')
        image_len_timestamp = file.read(expected_image_len_size + expected_timestamp_size)

        image_len = struct.unpack('<L', image_len_timestamp[:expected_image_len_size])[0]

        data = file.read(image_len)

        image_stream = io.BytesIO()
        image_stream.write(data)

        image_stream.seek(0)
        data = np.fromstring(image_stream.getvalue(), dtype=np.uint8)
        image = cv2.imdecode(data, 1)

        return image


if __name__ == "__main__":
    panorama_orchestrator = PanoramaOrchestrator()

    # connect to clients, display preview and wait for user adjustments
    panorama_orchestrator.connect() 

    # capture the panorama
    panorama_orchestrator.capture()

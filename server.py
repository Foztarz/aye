import io
import socket
import struct
import cv2
import time
import numpy as np
import select

def consume(connection_file, address, average_fps):
    start = time.time()
    image_len = struct.unpack('<L', connection_file.read(struct.calcsize('<L')))[0]
    # Construct a stream to hold the image data and read the image
    # data from the connection
    image_stream = io.BytesIO()
    image_stream.write(connection_file.read(image_len))
    # Rewind the stream, open it as an image with PIL and do some
    # processing on it
    image_stream.seek(0)
    data = np.fromstring(image_stream.getvalue(), dtype=np.uint8)
    image = cv2.imdecode(data, 1)
    
    #print('Image is %dx%d' % image.size)
    #image.verify()
    #print('Image is verified')
    cv2.imshow(address, image)
    cv2.waitKey(1) & 0xFF
    time_taken = time.time() - start

    current_fps = 1./time_taken
    average_fps = average_fps * smoothing + current_fps * (1 - smoothing)

    print('%s FPS %f' % (address, average_fps))

    return average_fps


server_socket = socket.socket()
server_socket.bind(('0.0.0.0', 8123))
server_socket.listen(0)

# Accept a single connection and make a file-like object out of it
# connection = server_socket.accept()[0].makefile('rb')

smoothing = 0.9

producers = []
file_to_address = {}
producer_fps = {}

try:
    while True:
        ready_to_read, ready_to_write, in_error = \
                select.select(
                        [server_socket] + producers, # potential readers
                        [], # potential writers
                        [], # potential errors
                        60) 
        for to_read in ready_to_read:
            if to_read is server_socket:
                connection, address = server_socket.accept()
                print("New connection from %s" % str(address[0]))
                file = connection.makefile('rb')
                producers.append(file)
                file_to_address[file] = address[0]
                producer_fps[file] = 0
            else:
                producer_fps[to_read] = consume(to_read, file_to_address[to_read], producer_fps[to_read])
finally:
    for producer in producers:
        producer.close()
    server_socket.close()

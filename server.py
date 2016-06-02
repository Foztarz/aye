import io
import socket
import struct
import cv2
import time
import numpy as np

server_socket = socket.socket()
server_socket.bind(('0.0.0.0', 8123))
server_socket.listen(0)

# Accept a single connection and make a file-like object out of it
connection = server_socket.accept()[0].makefile('rb')

smoothing = 0.9
average_fps = 0

try:
    while True:
        # Read the length of the image as a 32-bit unsigned int. If the
        # length is zero, quit the loop
        start = time.time()
        image_len = struct.unpack('<L', connection.read(struct.calcsize('<L')))[0]
        if not image_len:
            break
        # Construct a stream to hold the image data and read the image
        # data from the connection
        image_stream = io.BytesIO()
        image_stream.write(connection.read(image_len))
        # Rewind the stream, open it as an image with PIL and do some
        # processing on it
        image_stream.seek(0)
	data = np.fromstring(image_stream.getvalue(), dtype=np.uint8)
        image = cv2.imdecode(data, 1)
	
        #print('Image is %dx%d' % image.size)
        #image.verify()
        #print('Image is verified')
	cv2.imshow('Frame', image)
	cv2.waitKey(1) & 0xFF
        time_taken = time.time() - start

        current_fps = 1./time_taken
        average_fps = average_fps * smoothing + current_fps * (1 - smoothing)

        print('FPS %f' % average_fps)
finally:
    connection.close()
    server_socket.close()

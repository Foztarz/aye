import io
import socket
import struct
import cv2
import time
import numpy as np
import select

SYNCHRONIZED_THRESHOLD_MS = 30

millis = lambda: int(round(time.time() * 1000))

# TODO have queues for each producer, once they all have the same millis (or within X millis of each other) show

def consume(connection_file):
    start = time.time()
    image_len = struct.unpack('<L', connection_file.read(struct.calcsize('<L')))[0]
    timestamp = struct.unpack('<Q', connection_file.read(struct.calcsize('<Q')))[0]

    image_stream = io.BytesIO()
    image_stream.write(connection_file.read(image_len))

    image_stream.seek(0)
    data = np.fromstring(image_stream.getvalue(), dtype=np.uint8)
    image = cv2.imdecode(data, 1)
    
    time_taken = time.time() - start

    return image, timestamp

def synchronized(producer_address, timestamp, queues):
    synchronized = True
    for other_producer_address, queue in queue.items():
        other_timestamp = queue[0][1]
        if producer_address is not other_producer_address:
            synchronized = synchronized and (abs(timestamp - other_timestamp) < SYNCHRONIZED_THRESHOLD_MS)

    return synchronized

def show(queues):
    for producer_address, queue in queues.items():
        image = queue[0][0]
        cv2.imshow(producer_address, image)
    cv2.waitKey(1) & 0xFF                 

def pop(queues):
    for producer_address, queue in queues.items():
        queues[producer_address] = queue[1:]

server_socket = socket.socket()
server_socket.bind(('0.0.0.0', 8123))
server_socket.listen(0)

smoothing = 0.9

producers = []
file_to_address = {}
queues = {}

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
            else:
                producer_address = file_to_address[to_read]
                image, timestamp = consume(to_read)


                # IMPORTANT we are assuming no packet loss - otherwise it is possible that the received timestamp is later than the earliest received of other producers and it is still the earliest for this producer

                # add image, timestamp to producer queue 

                if not queues.has_key(producer_address):
                    # this is the earliest timestamp for producer 
                    # if it is close to the other two, display and pop the first in the queue
                    if synchronized(producer_address, timestamp, queues):
                        show(queues)
                        pop(queues)
                    else:
                        # else, discard the other two (as we are not going to receive an earlier timestamp for producer due to TCP)
                        for other_producer_address, queue in queues.items():
                            if other_producer_address is not producer_address:
                                queues[other_producer_address] = queue[1:]
                else:
                    queues[producer_address] += [(image, timestamp)]

finally:
    for producer in producers:
        producer.close()
    server_socket.close()

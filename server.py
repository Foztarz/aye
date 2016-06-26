#!/usr/bin/python

import io
import socket
import struct
import cv2
import time
import numpy as np
import select
import sys
import random
from operator import itemgetter
import ipdb

import aye_utils

import stokes

address_to_name = {
        '172.24.1.91' : 'pol-0',
        '172.24.1.97' : 'pol-45',
        '172.24.1.1' : 'pol-90',
        '172.24.1.118' : 'aye-uv',
        '172.24.1.87': 'aye-ir',
        '172.24.1.137': 'aye-vis'
        }

millis = lambda: int(round(time.time() * 1000))
hessians = {}
hessianSearchCounts = {}
hessianSearchErrors = {}

def consume(file):
    expected_image_len_size = struct.calcsize('<L')
    expected_timestamp_size = struct.calcsize('<Q')
    image_len_timestamp = file.read(expected_image_len_size + expected_timestamp_size)

    image_len = struct.unpack('<L', image_len_timestamp[:expected_image_len_size])[0]
    timestamp = struct.unpack('<Q', image_len_timestamp[expected_image_len_size:expected_image_len_size+expected_timestamp_size])[0]

    data = file.read(image_len)

    image_stream = io.BytesIO()
    image_stream.write(data)

    image_stream.seek(0)
    data = np.fromstring(image_stream.getvalue(), dtype=np.uint8)
    image = cv2.imdecode(data, 1)

    return image, timestamp

tcp_socket = socket.socket()
tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
tcp_socket.bind(('0.0.0.0', 8123))
tcp_socket.listen(0)

smoothing = 0.9

producers = []
file_to_name = {}

try:
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

                producers.append(file)
                file_to_name[file] = address_to_name[producer_address]
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
                cv2.waitKey(1) & 0xFF
finally:
    for producer in producers:
        producer.close()

    tcp_socket.close()


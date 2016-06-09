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

import stokes

address_to_name = {
        '172.24.1.91' : 'pol-0',
        '172.24.1.97' : 'pol-45',
        '172.24.1.1' : 'pol-90'
        }

SYNCHRONIZED_THRESHOLD_MS = 60

millis = lambda: int(round(time.time() * 1000))
hessians = {}
hessianSearchCounts = {}
hessianSearchErrors = {}

load_homographies = False
if len(sys.argv) > 1 and sys.argv[1] == 'load':
    print("Loading homographies from previously calculated hessians")
    load_homographies = True


def save_homography(from_name, to_name, homography):
    np.savez('/home/pi/aye/data/homography-%s-to-%s' % (from_name, to_name), homography=homography)

def load_homography(from_name, to_name):
    data = np.load('/home/pi/aye/data/homography-%s-to-%s.npz' % (from_name, to_name))
    return data['homography']

def ensure_initialized(dictionary, key1, key2, default):
    if not dictionary.has_key(key1):
        dictionary[key1] = {}
    if not dictionary[key1].has_key(key2):
        dictionary[key1][key2] = default

def warp(frame1, frame1_name, frame2, frame2_name):
    global hessians, hessianSearchCounts, hessianSearchErrors
    
    ensure_initialized(hessians, frame1_name, frame2_name, None)
    ensure_initialized(hessianSearchCounts, frame1_name, frame2_name, 20)
    ensure_initialized(hessianSearchErrors, frame1_name, frame2_name, sys.maxint)

    hessian = hessians[frame1_name][frame2_name]
    hessianSearchCount = hessianSearchCounts[frame1_name][frame2_name]
    hessianSearchError = hessianSearchErrors[frame1_name][frame2_name]

    frame1_gray = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    frame2_gray = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    if hessian is not None and hessianSearchCount == 0:
        warped_frame1 = cv2.warpPerspective(frame1_gray, hessian, (frame1_gray.shape[1],frame1_gray.shape[0]))

        return warped_frame1
    else:
        if load_homographies:
            hessian = load_homography(frame1_name, frame2_name)
            hessianSearchCount = 0

        elif random.random() > 0.95:

            surf = cv2.xfeatures2d.SURF_create()

            print("Shapes %s %s" % (str(frame1.shape), str(frame2.shape)))
            kp1, des1 = surf.detectAndCompute(frame1,None)
            kp2, des2 = surf.detectAndCompute(frame2,None)

            if des1 is not None and des2 is not None:
                print("Descriptors length %d %d" % (len(des1), len(des2)))
                # BFMatcher with default params
                bf = cv2.BFMatcher()
                matches = bf.knnMatch(des1, des2, k=2)

                # Apply ratio test
                good = []
                for m,n in matches:
                    if m.distance < 0.75*n.distance:
                        good.append(m)

                if good > 20:
                    src_pts = np.float32([ kp1[m.queryIdx].pt for m in good ]).reshape(-1,1,2)
                    dst_pts = np.float32([ kp2[m.trainIdx].pt for m in good ]).reshape(-1,1,2)

                    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

                    warped_frame1 = cv2.warpPerspective(frame1_gray,H,(frame1_gray.shape[1],frame1_gray.shape[0]))
                    errorMatrix = np.abs(warped_frame1 - frame2_gray)
                    error = np.sum(errorMatrix);
                    if error < hessianSearchError:
                        hessianSearchError = error
                        hessian = H

                    print("[HessianSearch %d] Error is %d best is %d" % (hessianSearchCount, error, hessianSearchError))

                    cv2.imshow('error', errorMatrix)
                    cv2.waitKey(1) & 0xFF

                    hessianSearchCount = hessianSearchCount - 1

                    if hessianSearchCount == 0:
                        save_homography(frame1_name, frame2_name, hessian)

    hessians[frame1_name][frame2_name] = hessian
    hessianSearchCounts[frame1_name][frame2_name] = hessianSearchCount
    hessianSearchErrors[frame1_name][frame2_name] = hessianSearchError

    return None

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

def synchronized_test(t1, t2):
    return t1 is not None and t2 is not None and abs(t1 - t2) < SYNCHRONIZED_THRESHOLD_MS

def synchronized(t1, t2, t3):
    return synchronized_test(t1,t2) and synchronized_test(t2,t3) and synchronized_test(t1,t3)

def head(queues, name):
    if not queues.has_key(name):
        return None, None
    queue = queues[name]
    if queue is None or len(queue) < 1:
        return None, None
    
    return queue[0]

    #images = []
    #names = []
    #for producer_name, queue in queues.items():
    #    image = queue[0][0]
    #    images.append(image)
    #    names.append(producer_name)
    #    cv2.imshow(producer_name, image)
    #    cv2.waitKey(1) & 0xFF                 
def show(first90image, first45image, first0image):
    warped45to90 = None
    warped0to90 = None
    if first90image is not None and first45image is not None:
        warped45to90 = warp(first45image, 'pol-45', first90image, 'pol-90')        
    if first90image is not None and first0image is not None:
        warped0to90 = warp(first0image, 'pol-0', first90image, 'pol-90')        

    if warped45to90 is not None and warped0to90 is not None:
        gray90 = cv2.cvtColor(first90image, cv2.COLOR_BGR2GRAY)

        intensity, degree, angle = stokes.getStokes(warped0to90, warped45to90, gray90)
        hsv_list = stokes.toHSV(intensity, degree, angle)
        print map(lambda a: a.shape, [intensity, degree, angle])

        hsv = cv2.merge(hsv_list)
        hsvInBGR = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        cv2.imshow("stokes-intensity", np.int8(intensity))
        cv2.imshow("stokes-degree", degree)
        cv2.imshow("stokes-angle", angle)
        cv2.imshow("stokes-hsv", hsvInBGR)
        cv2.waitKey(1) & 0xFF                 

def pop(queues):
    for producer_name in queues.keys():
        current = queues[producer_name]
        queues[producer_name] = current[1:]

server_socket = socket.socket()
server_socket.bind(('0.0.0.0', 8123))
server_socket.listen(0)

smoothing = 0.9

producers = []
file_to_name = {}
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
                producer_address = address[0]
                print("New connection from %s (%s)" % (producer_address, address_to_name[producer_address]))
                file = connection.makefile('rb')
                producers.append(file)

                file.write(struct.pack('<Q', millis()))
                file.flush()

                file_to_name[file] = address_to_name[producer_address]
                queues = {}
            else:
                producer_name = file_to_name[to_read]
                image, timestamp = consume(to_read)

                # IMPORTANT we are assuming no packet loss - otherwise it is possible that the received timestamp is later than the earliest received of other producers and it is still the earliest for this producer

                # add image, timestamp to producer queue 

                queues.setdefault(producer_name, []).append((image, timestamp))

                first90image, first90timestamp = head(queues, 'pol-90')
                first45image, first45timestamp = head(queues, 'pol-45')
                first0image, first0timestamp = head(queues, 'pol-0')

                if first90image is None or first45image is None or first0image is None:
                    print("At least one queue is empty")
                elif synchronized(first90timestamp, first45timestamp, first0timestamp):
                    show(first90image, first45image, first0image)
                    pop(queues)
                else:
                    heads = [('pol-90', first90timestamp),('pol-45', first45timestamp),('pol-0', first0timestamp)]
                    heads = filter(lambda h: h[1] is not None, heads)
                    heads.sort(key=itemgetter(1))
                    print heads
                    earliest_key, earliest_timestamp = heads[0]
                    queues[earliest_key] = queues[earliest_key][1:]
                    ## else, discard the ones that are not close enough 
                    ## TODO remove first images that are to early of each other to be synchronized
                    #for other_producer_name, queue in queues.items():
                    #    if other_producer_name is producer_name:
                    #        continue
                    #    discard_until = -1
                    #    for index, (_, other_timestamp) in enumerate(queue):
                    #        if abs(timestamp - other_timestamp) > SYNCHRONIZED_THRESHOLD_MS:
                    #            discard_until = index
                    #    queues[other_producer_name] = queue[discard_until+1:]

                print map(len, queues.values())

finally:
    for producer in producers:
        producer.close()
    server_socket.close()


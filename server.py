import io
import socket
import struct
import cv2
import time
import numpy as np
import select
import sys

SYNCHRONIZED_THRESHOLD_MS = 30

millis = lambda: int(round(time.time() * 1000))

hessian = None
hessianSearchCount = 40  
if len(sys.argv) > 1 and sys.argv[1] == 'load':
    hessianSearchCount = 0

frame1_pts = []
frame2_pts = []
object_pts = []
image_size = (9,6)

square_size = 2.8 # size of chessboard square in cm
corner_coordinates = np.zeros((np.prod(image_size), 3), np.float32)
corner_coordinates[:, :2] = np.indices(image_size).T.reshape(-1, 2)
corner_coordinates *= square_size

calibrated = False

def save_stereo_calibrate(cam_mat_left, dist_coefs_left, cam_mat_right, dist_coefs_right, rot_mat, trans_vec, e_mat, f_mat):
    np.savez('stereo_calibrate', cam_mat_left=cam_mat_left, dist_coefs_left=dist_coefs_left, cam_mat_right=cam_mat_right, dist_coefs_right=dist_coefs_right, rot_mat=rot_mat, trans_vec=trans_vec, e_mat=e_mat, f_mat=f_mat)
def load_stereo_calibrate():
    data = np.load('stereo_calibrate.npz')
    return data['cam_mat_left'], data['dist_coefs_left'], data['cam_mat_right'], data['dist_coefs_right'], data['rot_mat'], data['trans_vec'], data['e_mat'], data['f_mat']

def stereo_calibrate(frame_size):
    if len(object_pts) > 0:
        rms, camera_matrix_1, dist_coefs_1, rvecs, tvecs = cv2.calibrateCamera(object_pts, frame1_pts, frame_size, None, None)

        print("\nRMS:", rms)
        print("camera matrix:\n", camera_matrix_1)
        print("distortion coefficients: ", dist_coefs_1.ravel())

        rms, camera_matrix_2, dist_coefs_2, rvecs, tvecs = cv2.calibrateCamera(object_pts, frame2_pts, frame_size, None, None)

        print("\nRMS:", rms)
        print("camera matrix:\n", camera_matrix_2)
        print("distortion coefficients: ", dist_coefs_2.ravel())

        criteria = (cv2.TERM_CRITERIA_MAX_ITER + cv2.TERM_CRITERIA_EPS,
                100, 1e-5)
        flags = (cv2.CALIB_FIX_ASPECT_RATIO + cv2.CALIB_ZERO_TANGENT_DIST +
                cv2.CALIB_SAME_FOCAL_LENGTH)
        (retval, cam_mat_left, dist_coefs_left,
                cam_mat_right, dist_coefs_right,
                rot_mat, trans_vec, e_mat,
                f_mat) = cv2.stereoCalibrate(object_pts, frame1_pts, frame2_pts,  camera_matrix_1, dist_coefs_1, camera_matrix_2, dist_coefs_2, frame_size)#, criteria=criteria, flags=flags)
        save_stereo_calibrate(cam_mat_left, dist_coefs_left, cam_mat_right, dist_coefs_right, rot_mat, trans_vec, e_mat, f_mat);
        hessian = f_mat
    else: 
        print "Skipping calibration"
        cam_mat_left, dist_coefs_left, cam_mat_right, dist_coefs_right, rot_mat, trans_vec, e_mat, f_mat = load_stereo_calibrate()

    return cam_mat_left, dist_coefs_left, cam_mat_right, dist_coefs_right, rot_mat, trans_vec, e_mat, f_mat

def warp(frame1, frame2):
    global hessian, hessianSearchCount, frame1_pts, frame2_pts, corner_coordinates, object_pts, cam_mat_left, dist_coefs_left, cam_mat_right, dist_coefs_right, rot_mat, trans_vec, e_mat, f_mat, calibrated
    frame1_gray =cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    frame2_gray =cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    frame_size = (frame1.shape[1], frame1.shape[0])

    if hessianSearchCount == 0:
        if not calibrated:
            cam_mat_left, dist_coefs_left, cam_mat_right, dist_coefs_right, rot_mat, trans_vec, e_mat, f_mat = stereo_calibrate(frame_size)
            calibrated = True

        rect_left = np.array([])
        rect_right = np.array([])
        _, _, proj_left, proj_right, q_mat, _, _ = cv2.stereoRectify(cam_mat_left, dist_coefs_left, cam_mat_right, dist_coefs_right, frame_size, rot_mat, trans_vec, rect_left, rect_right, alpha=1, flags=cv2.CALIB_ZERO_DISPARITY)

        rectified_cam_mat_left = np.array([])
        map1, map2 = cv2.initUndistortRectifyMap(cam_mat_left, dist_coefs_left, rect_left, rectified_cam_mat_left, frame_size, cv2.CV_32FC1)
        rectified_1 = cv2.remap(frame1, map1, map2, cv2.INTER_LINEAR)
        rectified_cam_mat_right = np.array([])
        map1, map2 = cv2.initUndistortRectifyMap(cam_mat_right, dist_coefs_right, rect_right, rectified_cam_mat_right, frame_size, cv2.CV_32FC1)
        rectified_2 = cv2.remap(frame2, map1, map2, cv2.INTER_LINEAR)

        #warped_frame1 = cv2.warpPerspective(frame1_gray, hessian, frame_size)
        cv2.imshow('rectified_1', rectified_1)
        cv2.imshow('rectified_2', rectified_2)

        rectified1_gray =cv2.cvtColor(rectified_1, cv2.COLOR_BGR2GRAY)
        rectified2_gray =cv2.cvtColor(rectified_2, cv2.COLOR_BGR2GRAY)
        merged = cv2.merge((rectified1_gray, rectified2_gray, rectified1_gray)) 
        cv2.imshow('merged_12', merged)
        cv2.waitKey(1) & 0xFF
    else:
        found, corners_1 = cv2.findChessboardCorners(frame1, image_size)
        if not found:
            print "Chessboard not found"
            return
        found, corners_2 = cv2.findChessboardCorners(frame2, image_size)
        if not found:
            print "Chessboard not found"
            return

        object_pts.append(corner_coordinates)

        cv2.cornerSubPix(frame1_gray, corners_1, (11, 11), (-1, -1),
                (cv2.TERM_CRITERIA_MAX_ITER + cv2.TERM_CRITERIA_EPS, 30, 0.01))
        cv2.cornerSubPix(frame2_gray, corners_2, (11, 11), (-1, -1),
                (cv2.TERM_CRITERIA_MAX_ITER + cv2.TERM_CRITERIA_EPS, 30, 0.01))

        frame1_pts.append(corners_1)
        frame2_pts.append(corners_2)

        cv2.drawChessboardCorners(frame1, image_size, corners_1, True)
        cv2.drawChessboardCorners(frame2, image_size, corners_2, True)

        cv2.imshow('frame1_wcorners', frame1)
        cv2.imshow('frame2_wcorners', frame2)
        cv2.waitKey(1) & 0xFF

        hessianSearchCount = hessianSearchCount - 1

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
    for other_producer_address, queue in queues.items():
        if len(queue) == 0: 
            synchronized = False
            break
        other_timestamp = queue[0][1]
        if producer_address is not other_producer_address:
            synchronized = synchronized and (abs(timestamp - other_timestamp) < SYNCHRONIZED_THRESHOLD_MS)

    return synchronized

def show(queues):
    images = []
    for producer_address, queue in queues.items():
        image = queue[0][0]
        images.append(image)
        cv2.imshow(producer_address, image)
        cv2.waitKey(1) & 0xFF                 

    if len(images) > 1:
        warp(images[0], images[1])        

def pop(queues):
    for producer_address in queues.keys():
        current = queues[producer_address]
        queues[producer_address] = current[1:]

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
                queues = {}
            else:
                producer_address = file_to_address[to_read]
                image, timestamp = consume(to_read)

                # IMPORTANT we are assuming no packet loss - otherwise it is possible that the received timestamp is later than the earliest received of other producers and it is still the earliest for this producer

                # add image, timestamp to producer queue 

                queues.setdefault(producer_address, []).append((image, timestamp))

                image, timestamp = queues[producer_address][0]
                # this is the earliest timestamp for producer 
                # if it is close to the other two, display and pop the first in the queue
                if synchronized(producer_address, timestamp, queues):
                    show(queues)
                    pop(queues)
                else:
                    # else, discard the ones that are not close enough 
                    for other_producer_address, queue in queues.items():
                        if other_producer_address is producer_address:
                            continue
                        discard_until = -1
                        for index, (_, other_timestamp) in enumerate(queue):
                            if abs(timestamp - other_timestamp) > SYNCHRONIZED_THRESHOLD_MS:
                                discard_until = index
                        queues[other_producer_address] = queue[discard_until+1:]

                #print map(len, queues.values())

finally:
    for producer in producers:
        producer.close()
    server_socket.close()


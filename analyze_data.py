import os
from operator import itemgetter
import ipdb
import cv2
import stokes
import numpy as np
import aye_utils

DATA_DIRECTORY = os.path.expanduser("~/aye-data/")
SYNCHRONIZED_THRESHOLD_MS = 30

def get_files_in_directory(directory):
    files = []
    for sequence_directory_name in os.listdir(directory):
        files.append(os.path.join(directory, sequence_directory_name))

    return files

def get_sequence_directories():
    print "Looking in ", DATA_DIRECTORY
    sequence_directories = filter(os.path.isdir, get_files_in_directory(DATA_DIRECTORY))

    return sequence_directories

def get_synchronized(reference_millis, sequence, start_from):
    count = 0
    for image_name in sequence[start_from:]:
        millis = parse_millis(image_name) 
        if abs(millis - reference_millis) <= SYNCHRONIZED_THRESHOLD:
            return image_name, millis, start_from + count

        count = count + 1

    return None, None, None

def split_name(image_file_path):
    return os.path.splitext(os.path.split(image_file_path)[-1])[0]

def parse_millis(image_file_path):
    return int(split_name(image_file_path).split('m')[-1])

def parse_hostname(image_file_path):
    return split_name(image_file_path).split('t')[0]

def parse_orientation(image_file_path):
    return int(parse_hostname(image_file_path).split('-')[2])

def get_aye_pol_image(image_name):
    return parse_orientation(image_name), parse_millis(image_name), cv2.imread(image_name)

def head(queues, name):
    if not queues.has_key(name):
        return None, None
    queue = queues[name]
    if queue is None or len(queue) < 1:
        return None, None
    
    return queue[0]

def synchronized_test(t1, t2):
    return t1 is not None and t2 is not None and abs(t1 - t2) < SYNCHRONIZED_THRESHOLD_MS

def synchronized(t1, t2, t3):
    return synchronized_test(t1,t2) and synchronized_test(t2,t3) and synchronized_test(t1,t3)

def pop(queues):
    for producer_name in queues.keys():
        current = queues[producer_name]
        queues[producer_name] = current[1:]

def synchronize(directories0n45n90):
    sequences = map(get_files_in_directory, directories0n45n90)

    map(list.sort, sequences)

    queues = {}
    positions = [0] * len(sequences)
    while True:
        for index, sequence in enumerate(sequences):
            position = positions[index]
            if len(sequence) <= position:
                return
            image_name = sequence[position]
            positions[index] = position + 1
            producer_name, timestamp, image = get_aye_pol_image(image_name)

            queues.setdefault(producer_name, []).append((image, timestamp))

            first90image, first90timestamp = head(queues, 90)
            first45image, first45timestamp = head(queues, 45)
            first0image, first0timestamp = head(queues, 0)

            if first90image is None or first45image is None or first0image is None:
                pass
            elif synchronized(first90timestamp, first45timestamp, first0timestamp):
                yield [(0, first0image, first0timestamp), (45, first45image, first45timestamp), (90, first90image, first90timestamp)]
                pop(queues)
            else:
                heads = [(90, first90timestamp),(45, first45timestamp),(0, first0timestamp)]
                heads = filter(lambda h: h[1] is not None, heads)
                heads.sort(key=itemgetter(1))
                latest_timestamp = heads[-1][1]
                late_heads = filter(lambda h: not synchronized_test(h[1], latest_timestamp), heads)
                for late_key, _ in late_heads:
                    queues[late_key] = queues[late_key][1:]

            print positions
            #print zip(queues.keys(), map(len, queues.values()))
            if max(map(len, queues.values())) > 500:
                print("Queues are too big, emptying them to prevent memory freeze")
                queues = {}

def get_latest_data():
    sequence_directories = get_sequence_directories()
    millis_sequence_categories = zip(map(parse_millis, sequence_directories), sequence_directories)
    millis_sequence_categories.sort(reverse=True)
    orientation_to_directory = {}
    for millis, sequence_directory in millis_sequence_categories:
        orientation = parse_orientation(sequence_directory)
        orientation_to_directory[orientation] = sequence_directory
        if len(orientation_to_directory.keys()) == 3:
            return synchronize(orientation_to_directory.values())
    return None

data = []

def interactive():
    global data
    try:
        cv2.namedWindow("0")
        cv2.namedWindow("45")
        cv2.namedWindow("90")

        for data in get_latest_data():
            current_data = data
            map(lambda d: cv2.imshow(str(d[0]), d[1]), data)
            gray0 = cv2.cvtColor(data[0][1], cv2.COLOR_BGR2GRAY)
            gray45 = cv2.cvtColor(data[1][1], cv2.COLOR_BGR2GRAY)
            gray90 = cv2.cvtColor(data[2][1], cv2.COLOR_BGR2GRAY)
            stokesI, stokesQ, stokesU, polInt, polDoLP, polAoP = stokes.getStokes(gray0, gray45, gray90)
            cv2.imshow('stokes-i', normalized_uint8(stokesI, 500))
            cv2.imshow('stokes-q', normalized_uint8(stokesQ, 255))
            cv2.imshow('stokes-u', normalized_uint8(stokesU, 255))
            cv2.imshow('linear-intensity', normalized_uint8(polInt, 255))
            cv2.imshow('linear-degree', polDoLP)
            H = np.uint8((polAoP+(3.1416/2))*(180/3.1416))
            S = 255*np.ones((240,320), 'uint8')
            V = 255*np.ones((240,320), 'uint8')
            cv2.imshow('angle', cv2.cvtColor(cv2.merge([H,S,V]), cv2.COLOR_HSV2BGR))

            cv2.imshow('hsv', cv2.cvtColor(cv2.merge(stokes.toHSV(polInt, polDoLP, polAoP)), cv2.COLOR_HSV2BGR))
            cv2.waitKey()
    finally:
        cv2.destroyAllWindows()

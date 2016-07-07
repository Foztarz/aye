import os
from operator import itemgetter, methodcaller
import ipdb
import cv2
import stokes
import numpy as np
import aye_utils
import rpi_raw
import sys

SUFFIX = 'aye-analyze'
DATA_DIRECTORY = os.path.expanduser("~/aye-data/")
SYNCHRONIZED_THRESHOLD_MS = 30

def get_files_in_directory(directory):
    files = []
    for sequence_directory_name in os.listdir(directory):
        files.append(os.path.join(directory, sequence_directory_name))

    return files

def get_sequence_directories(directory = DATA_DIRECTORY):
    sequence_directories = filter(os.path.isdir, get_files_in_directory(directory))

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

            print(positions)
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
    cv2.namedWindow("0")
    cv2.namedWindow("45")
    cv2.namedWindow("90")

    for data in get_latest_data():
        current_data = data
        map(lambda d: cv2.imshow(str(d[0]), d[1]), data)
        display(data)
        cv2.waitKey()

gray0, gray45, gray90, stokesI, stokesQ, stokesU, polInt, polDoLP, polAoP = None, None, None, None, None, None, None, None, None

def gray(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def small(image):
    return cv2.resize(image, (480, 360))

def display(data):
    global gray0, gray45, gray90, stokesI, stokesQ, stokesU, polInt, polDoLP, polAoP
    gray0 = gray(data[0][1])
    gray45 = gray(data[1][1])
    gray90 = gray(data[2][1])
    stokesI, stokesQ, stokesU, polInt, polDoLP, polAoP = stokes.getStokes(gray0, gray45, gray90)
    cv2.imshow('stokes-i', aye_utils.normalized_uint8(stokesI, 500))
    cv2.imshow('stokes-q', aye_utils.normalized_uint8(stokesQ, 255))
    cv2.imshow('stokes-u', aye_utils.normalized_uint8(stokesU, 255))
    cv2.imshow('linear-intensity', aye_utils.normalized_uint8(polInt, 255))
    cv2.imshow('linear-degree', polDoLP)
    cv2.imshow('angle', cv2.cvtColor(cv2.merge(stokes.angle_hsv(polAoP)), cv2.COLOR_HSV2BGR))

    cv2.imshow('hsv', cv2.cvtColor(cv2.merge(stokes.toHSV(polInt, polDoLP, polAoP)), cv2.COLOR_HSV2BGR))

def save_stokes(stokesI, stokesQ, stokesU):
    dir = 'stokes'
    if not os.path.isdir(dir):
        os.mkdir(dir)

    cv2.imwrite('/'.join([dir, 'stokes-i.png']), stokesI)
    cv2.imwrite('/'.join([dir, 'stokes-q.png']), stokesQ)
    cv2.imwrite('/'.join([dir, 'stokes-u.png']), stokesU)

def suffixed(str):
    return "%s-%s" % (str, SUFFIX)

def display_stokes(images):
    stokesI, stokesQ, stokesU, polInt, polDoLP, polAoP = stokes.getStokes(images[0], images[1], images[2])

    normalized_stokesI = aye_utils.normalized_uint8(stokesI, 500)
    normalized_stokesQ = aye_utils.normalized_uint8(stokesQ, 255)
    normalized_stokesU = aye_utils.normalized_uint8(stokesU, 255)
    save_stokes(normalized_stokesI, normalized_stokesQ, normalized_stokesU)

    cv2.imshow(suffixed('0'), images[0])
    cv2.imshow(suffixed('45'), images[1])
    cv2.imshow(suffixed('90'), images[2])
    cv2.imshow(suffixed('stokes-i'), normalized_stokesI)
    cv2.imshow(suffixed('stokes-q'), normalized_stokesQ)
    cv2.imshow(suffixed('stokes-u'), normalized_stokesU)
    angle_image = cv2.cvtColor(cv2.merge(stokes.angle_hsv(polAoP)), cv2.COLOR_HSV2BGR) 
    cv2.imshow(suffixed('angle'), angle_image)

    angle_in_degrees = stokes.angle_to_hue(polAoP)

    line_width = 100
    # TODO Sample region not just one point
    # TODO do it for multiple regions not just center
    middle_point = (angle_in_degrees.shape[1]/2,angle_in_degrees.shape[0]/2)
    line_point1 = np.array(middle_point)
    line_point2 = np.array(middle_point)

    angle_at_center_degrees = angle_in_degrees[middle_point]
    angle_at_center_rad = np.deg2rad(angle_at_center_degrees)
    print "Angle at center %d %f" % (angle_at_center_degrees, angle_at_center_rad)

    line_point1 = np.sum([line_point1, (np.cos(angle_at_center_rad)*line_width/2, np.sin(angle_at_center_rad)*line_width/2)], 0).astype(int)
    line_point2 = np.sum([line_point2, (np.cos(angle_at_center_rad+np.pi)*line_width/2, np.sin(angle_at_center_rad+np.pi)*line_width/2)], 0).astype(int)
    
    angle_image_with_line = cv2.arrowedLine(angle_image, tuple(line_point1), tuple(line_point2), (0,0,0))

    #cv2.imshow(suffixed('angle-downsampled'), small(cv2.pyrDown(cv2.pyrDown(angle_image))))
    cv2.imshow(suffixed('angle-with-line'), angle_image_with_line)

def parse_zenith_time(file_path):
    time_text = os.path.split(file_path)[-1].split('-')[-1]
    hours = int(time_text.split(':')[0])
    minutes = int(time_text.split(':')[1])
    return hours*60 + minutes

def minutes_to_hour_minutes(minutes):
    return '%d:%02d' % (minutes/60, minutes % 60)

def update_control_view(minutes, rotation):
    font = cv2.FONT_HERSHEY_SIMPLEX
    img = np.zeros((480, 320))
    cv2.putText(img, minutes_to_hour_minutes(minutes), (10,25), font, 1, (255,255,255),2,cv2.LINE_AA)
    cv2.putText(img, str(rotation), (10,50), font, 1, (255,255,255),2,cv2.LINE_AA)
    cv2.imshow(suffixed('control'), img)

def parse_rotation(sevilla_zenith_image_path):
    return int(os.path.split(sevilla_zenith_image_path)[-1].split('-')[4])

# assumes only one file per polarization orientation in the directory
def visualize_sevilla_zenith(directory, use_raw=True, first=None):
    zenith_times = filter(lambda f: 'azim' in f, get_files_in_directory(directory))
    zenith_times = map(itemgetter(1), sorted(zip(map(parse_zenith_time, zenith_times), zenith_times)))
    zenith_time_rotation = []
    time_points = len(list(zenith_times))
    print('%d time points' % time_points)
    max_data_points = 0
    count = 0
    for zenith_time in  zenith_times:
        pol_files = filter(lambda f: 'pol' in f, get_files_in_directory(zenith_time))
        files_length = len(list(pol_files))
        data_points = files_length / 3
        if files_length % 3 != 0 or files_length == 0:
            print("Number of files in folder should be divisible by 3 : %s"% zenith_time)
            continue

        max_data_points = max(data_points, max_data_points)
        print('%d rotation points' % data_points)

        rotation_sorted_pol_files = map(itemgetter(1), sorted(zip(map(parse_rotation, pol_files), pol_files)))
        rotation_sorted_pol_0 = filter(lambda a: parse_orientation(a) == 0, rotation_sorted_pol_files)
        rotation_sorted_pol_45 = filter(lambda a: parse_orientation(a) == 45, rotation_sorted_pol_files)
        rotation_sorted_pol_90 = filter(lambda a: parse_orientation(a) == 90, rotation_sorted_pol_files)

        if use_raw:
            images0 = map(methodcaller('demosaic'), map(lambda f: rpi_raw.from_raw_jpeg(f), rotation_sorted_pol_0))
            images45 = map(methodcaller('demosaic'), map(lambda f: rpi_raw.from_raw_jpeg(f), rotation_sorted_pol_45))
            images90 = map(methodcaller('demosaic'), map(lambda f: rpi_raw.from_raw_jpeg(f), rotation_sorted_pol_90))
        else: 
            images0 = map(cv2.imread, rotation_sorted_pol_0)
            images45 = map(cv2.imread, rotation_sorted_pol_45)
            images90 = map(cv2.imread, rotation_sorted_pol_90)

        small_gray0, small_gray45, small_gray90 = map(lambda i: map(small, map(gray, i)), [images0, images45, images90])
        assert map(parse_rotation, rotation_sorted_pol_0) == map(parse_rotation, rotation_sorted_pol_45)
        assert map(parse_rotation, rotation_sorted_pol_0) == map(parse_rotation, rotation_sorted_pol_90)
        zipped_rotation_images = zip(map(parse_rotation, rotation_sorted_pol_0), zip(small_gray0, small_gray45, small_gray90))
        zenith_time_rotation.append(zipped_rotation_images)

        count = count + 1
        if first and first <= count:
            break

    display_trackbar = lambda _: display(cv2.getTrackbarPos('Time Index', suffixed('control')), cv2.getTrackbarPos('Rotation Index', suffixed('control')))
    display = lambda time_index, rotation_index: update_control_view(parse_zenith_time(zenith_times[time_index]), zenith_time_rotation[time_index][rotation_index][0]) or display_stokes(zenith_time_rotation[time_index][rotation_index][1])

    cv2.namedWindow(suffixed('control'))
    cv2.createTrackbar('Time Index', suffixed('control'), 0, time_points, display_trackbar)
    cv2.createTrackbar('Rotation Index', suffixed('control'), 0, max_data_points, display_trackbar)
    while (1):
        k = cv2.waitKey() & 0xFF

        if k == 27:
            break

def file_to_png(file_path):
    image = cv2.imread(file_path)
    cv2.imwrite(os.path.splitext(file_path)[0] + '.png', image)

def raw_to_image(file_path, out=None, ext='.png', to_small=False, to_gray=False):
    image = rpi_raw.from_raw_jpeg(file_path).demosaic()
    if to_small:
        image = small(image)
    if to_gray:
        image = gray(image)

    if out:
        cv2.imwrite(out, image)
    else:
        cv2.imwrite(os.path.splitext(file_path)[0] + ext, image)

if __name__ == '__main__':
    visualize_sevilla_zenith(sys.argv[1], False)

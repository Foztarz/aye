import os
from operator import itemgetter, methodcaller
import ipdb
import cv2
import stokes
import numpy as np
import aye_utils
import rpi_raw
import sys
import matplotlib.pyplot as plt

SUFFIX = 'aye-analyze'
DATA_DIRECTORY = os.path.expanduser("~/aye-data/")
SYNCHRONIZED_THRESHOLD_MS = 30
polarization_degree_cutoff = 0.1
show_subset = False

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

def gray(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def small(image):
    global show_subset
    if show_subset:
        return cv2.resize(image, (720, 640))
    else:
        return cv2.resize(image, (480, 360))

def save_stokes(stokesI, stokesQ, stokesU):
    dir = 'stokes'
    if not os.path.isdir(dir):
        os.mkdir(dir)

    cv2.imwrite('/'.join([dir, 'stokes-q.png']), stokesQ)
    cv2.imwrite('/'.join([dir, 'stokes-u.png']), stokesU)

def suffixed(str):
    return "%s-%s" % (str, SUFFIX)

def point_on_circle(rad, radius):
    return (np.cos(rad + np.pi/2)*radius , np.sin(rad + np.pi/2)*radius)

def pointed_line(angle_deg, x, y, line_length):
    line_point1 = np.array((x,y))
    line_point2 = np.array((x,y))

    angle_rad = np.deg2rad(angle_deg)

    line_point1 = np.sum([line_point1, point_on_circle(angle_rad-np.pi, line_length/2)], 0).astype(int)
    line_point2 = np.sum([line_point2, point_on_circle(angle_rad, line_length/2)], 0).astype(int)
    
    return line_point1, line_point2

class PixelInfo:
    def __init__(self, named_images):
        self.named_images = named_images

    def output(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            for name, image in self.named_images:
                print("[%s] %s" % (name, image[(y,x)]))

def sunny(image, sun_at_degrees):
    middle = np.array(image.shape[:2]) / 2
    sun_orbit_radius = 100
    sun_direction = point_on_circle(np.deg2rad(sun_at_degrees), sun_orbit_radius) + middle
    return cv2.arrowedLine(image, tuple(middle[::-1]), tuple(sun_direction.astype(int)[::-1]), color=(0., 1., 1.), thickness=1)

def with_evectors_and_sun(pol_angle_radians, linear_degree, rotation):
    downsample = 15
    angle_in_degrees = stokes.angle_to_hue(pol_angle_radians, invert=True)
    pol_angle_radians_downsampled = small(pol_angle_radians[::downsample, ::downsample])
    linear_degree_downsampled = small(linear_degree[::downsample, ::downsample])
    angle_image_downsampled = cv2.cvtColor(cv2.merge(stokes.angle_hsv(pol_angle_radians_downsampled, linear_degree_downsampled)), cv2.COLOR_HSV2BGR) 
    angle_in_degrees_downsampled = stokes.angle_to_hue(pol_angle_radians_downsampled, invert=True)

    width = angle_in_degrees.shape[0]
    height = angle_in_degrees.shape[1]
    sample_step = downsample

    angle_image_with_lines = angle_image_downsampled
    for x in range(sample_step, width, sample_step):
        for y in range(sample_step, height, sample_step):
            point1, point2 = pointed_line(angle_in_degrees_downsampled[(x,y)], x, y, sample_step - 3)
            angle_image_with_lines = cv2.arrowedLine(angle_image_with_lines, tuple(point1[::-1]), tuple(point2[::-1]), (0,0,0))

    system_orientation_sun_starting_angle = 110
    angle_image_with_lines_and_sun = sunny(angle_image_with_lines, system_orientation_sun_starting_angle + rotation)

    return angle_image_with_lines_and_sun, angle_in_degrees_downsampled

def display_labeled_images(labeled_images):
    global show_subset
    labels_subset = ['0', 'linear-degree', 'angle-evectors']
    for label, image in labeled_images:
        if not show_subset or label in labels_subset:
            cv2.imshow(suffixed(label), image)

def rotate(images, angle):
    size = (images[0].shape[1], images[0].shape[0])
    center = (size[0]/2, size[1]/2)
    scale = 1
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, scale)
    
    return map(lambda i: cv2.warpAffine(i, rotation_matrix, size), images)

def central_region(time_rotation_image):
    (time, rotation), image = time_rotation_image
    return (time, rotation), small(image[90:270, 80:400])

def shift(rotation_images, shift_amount):
    starting_rotation = rotation_images[0][0][1]

    cutoff = -1
    for index, ((time, rotation), images) in enumerate(rotation_images):
        if abs(rotation - starting_rotation - shift_amount) <= 5:
            cutoff = index
            break

    assert cutoff is not -1, "Could not shift 45"

    time_rotation, images = zip(*rotation_images[cutoff:])

    return zip(time_rotation, rotate(images, -shift_amount))

def monocular(rotation_images):
    time_rotations, images = zip(*rotation_images)
    time_rotation_monocular = zip(time_rotations, map(itemgetter(0), images))

    rotation_images0 = map(central_region, time_rotation_monocular)
    rotation_images45 = map(central_region, shift(time_rotation_monocular, 45))
    rotation_images90 = map(central_region, shift(time_rotation_monocular, 90))

    return zip(rotation_images0, rotation_images45, rotation_images90)

def get_angle_pol_degree(images, invert=False):
    stokesI, stokesQ, stokesU, intensity, linear_degree, angle = stokes.getStokes(images[0], images[1], images[2])
    angle_degrees = stokes.angle_to_hue(angle, invert)
    return angle_degrees, linear_degree

def degree_cutoff(angle_pol_degree):
    angle, pol_degree = angle_pol_degree
    mask = pol_degree > polarization_degree_cutoff

    if not np.any(mask):
        print("Empty mask, returning unmasked")
        return angle

    return angle[mask]

def get_median_polarization_angles(images, invert_angle=False):
    angles, linear_degrees = zip(*map(lambda a: get_angle_pol_degree(a, invert_angle), images))
    median_polarization_angles = map(np.median, angles) 

    median_polarization_angles_degree_cutoff = map(np.median, map(degree_cutoff, zip(angles, linear_degrees)))

    return median_polarization_angles, median_polarization_angles_degree_cutoff

def get_graph_data(monocular_time_rotation_images, time_rotation_images):
    (time_rotations0, images0), (time_rotations45, images45), (time_rotations90, images90) = map(lambda a: zip(*a), zip(*monocular_time_rotation_images))
    rotations = map(itemgetter(1), time_rotations0)

    median_polarization_angles_monocular, median_polarization_angles_degree_cutoff_monocular = get_median_polarization_angles(zip(images0, images45, images90), True)

    time_rotations, images = zip(*time_rotation_images)
    median_polarization_angles, median_polarization_angles_degree_cutoff = get_median_polarization_angles(images)
    
    monocular_data_size = len(median_polarization_angles_monocular)
    median_polarization_angles = median_polarization_angles[:monocular_data_size]
    median_polarization_angles_degree_cutoff = median_polarization_angles_degree_cutoff[:monocular_data_size]

    return rotations, median_polarization_angles_monocular, median_polarization_angles_degree_cutoff_monocular, median_polarization_angles, median_polarization_angles_degree_cutoff

def save_graphs(time, save_directory, rotations, median_angles_monocular, median_angles_degree_cutoff_monocular, median_angles, median_angles_degree_cutoff):
    plt.close('all')
    hour_minutes = minutes_to_hour_minutes(time)
    plt.figure(figsize=(13, 10))
    plt.title("Motor rotation versus e-vectors at %s" % hour_minutes)
    show_graphs(rotations, median_angles_monocular, median_angles_degree_cutoff_monocular, median_angles, median_angles_degree_cutoff)
    if not os.path.isdir(save_directory):
        os.makedirs(save_directory)
    plt.savefig('%s/%s.png' % (save_directory, hour_minutes), bbox_inches='tight')

def show_graphs(rotations, median_angles_monocular, median_angles_degree_cutoff_monocular, median_angles, median_angles_degree_cutoff):
    #blue, = plt.plot(rotations, median_angles, 'b', label='Median e-vector orientation')
    #magenta, = plt.plot(rotations, median_angles_degree_cutoff, 'm', label='As above, but only >%d%% polarization' % (100*polarization_degree_cutoff))
    #red, = plt.plot(rotations, median_angles_monocular, 'r', label='Median e-vector orientation (Monocular)')
    green, = plt.plot(rotations, median_angles_degree_cutoff_monocular, 'g', label='Median e-vector orientation (monocular), only >%d%% polarization' % (100*polarization_degree_cutoff))

    plt.axis([0, 250, -90, 90])
    plt.yticks(range(-90, 91, 20))
    plt.legend(loc=9, bbox_to_anchor=(0, -0.1), ncol=1, mode="expand", borderaxespad=0.)

def display_stokes(time_rotation_images, rotation_index, save_directory = None):
    monocular_time_rotation_images = monocular(time_rotation_images)
    if rotation_index >= len(monocular_time_rotation_images):
        print("No image for rotation index %d" % rotation_index)
        return
    ((time0, rotation0), image0),((time45, rotation45), image45),((time90, rotation90), image90) = monocular_time_rotation_images[rotation_index]

    assert time0 == time45 and time45 == time90

    time = time0

    images = [image0, image45, image90]

    stokesI, stokesQ, stokesU, polInt, polDoLP, polAoP = stokes.getStokes(image0, image45, image90)

    normalized_stokesI = aye_utils.normalized_uint8(stokesI, 500)
    normalized_stokesQ = aye_utils.normalized_uint8(stokesQ, 255)
    normalized_stokesU = aye_utils.normalized_uint8(stokesU, 255)
    angle_image = cv2.cvtColor(cv2.merge(stokes.angle_hsv(polAoP)), cv2.COLOR_HSV2BGR) 
    angle_evectors, angle_in_degrees_downsampled = with_evectors_and_sun(polAoP, polDoLP, rotation0)

    normalized_degree = aye_utils.normalized_uint8(polDoLP, 1)
    normalized_angle = aye_utils.normalized_uint8(angle_image, 1)
    normalized_angle_evectors = aye_utils.normalized_uint8(angle_evectors, 1)

    labels = ['0', '45', '90', 'linear-degree', 'stokes-u', 'angle', 'angle-evectors']
    labeled_images = zip(labels, [images[0], images[1], images[2], normalized_degree, normalized_stokesU, normalized_angle, normalized_angle_evectors])


    rotations, median_angles_monocular, median_angles_degree_cutoff_monocular, median_angles, median_angles_degree_cutoff = get_graph_data(monocular_time_rotation_images, time_rotation_images)
    if save_directory:
        #save_labeled_images(time, rotation0, labeled_images, save_directory)
        save_graphs(time, save_directory, rotations, median_angles_monocular, median_angles_degree_cutoff_monocular, median_angles, median_angles_degree_cutoff)
    else:
        update_control_view(time, rotation0, rotation45, rotation90)
        display_labeled_images(labeled_images)
        pixel_info = PixelInfo([('angle', angle_in_degrees_downsampled), ('pol-degree', polDoLP)]) 
        cv2.setMouseCallback(suffixed('angle-with-lines'), pixel_info.output)
        cv2.setMouseCallback(suffixed('linear-degree'), pixel_info.output)
        show_graphs(rotations, median_angles_monocular, median_angles_degree_cutoff_monocular, median_angles, median_angles_degree_cutoff)


def parse_zenith_time(file_path):
    time_text = os.path.split(file_path)[-1].split('-')[-1]
    hours = int(time_text.split(':')[0])
    minutes = int(time_text.split(':')[1])
    return hours*60 + minutes

def minutes_to_hour_minutes(minutes):
    return '%d:%02d' % (minutes/60, minutes % 60)

def update_control_view(minutes, rotation0, rotation45, rotation90):
    font = cv2.FONT_HERSHEY_SIMPLEX
    img = np.zeros((480, 320))
    cv2.putText(img, minutes_to_hour_minutes(minutes), (10,25), font, 1, (255,255,255),2,cv2.LINE_AA)
    cv2.putText(img, str(rotation0), (10,50), font, 1, (255,255,255),2,cv2.LINE_AA)
    cv2.putText(img, str(rotation45), (10,75), font, 1, (255,255,255),2,cv2.LINE_AA)
    cv2.putText(img, str(rotation90), (10,100), font, 1, (255,255,255),2,cv2.LINE_AA)
    cv2.imshow(suffixed('control'), img)

def parse_rotation(sevilla_zenith_image_path):
    return int(os.path.split(sevilla_zenith_image_path)[-1].split('-')[4])

def visualize_sevilla_zenith(directory, use_raw=True, first=None, last=None, save_directory = False):
    plt.ion()

    zenith_times = filter(lambda f: 'azim' in f, get_files_in_directory(directory))
    parsed_zenith_times = map(parse_zenith_time, zenith_times)
    zenith_times = map(itemgetter(1), sorted(zip(parsed_zenith_times, zenith_times)))
    zenith_time_rotation = []
    time_points = len(list(zenith_times))
    print('%d time points' % time_points)
    max_data_points = 0
    count = -1

    for zenith_time in zenith_times:
        count = count + 1
        if first and first > count:
            zenith_time_rotation.append([])
            continue
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

        small_gray0 = map(lambda i: small(gray(i)), images0)
        small_gray45 = map(lambda i: small(gray(i)), images45)
        small_gray90 = map(lambda i: small(gray(i)), images90)
        rotations = map(parse_rotation, rotation_sorted_pol_0)
        time_rotations = [(parse_zenith_time(zenith_time), rotation) for rotation in rotations]
        zipped_rotation_images = zip(time_rotations, zip(small_gray0,small_gray45, small_gray90))
        zenith_time_rotation.append(zipped_rotation_images)

        if last and last <= count:
            break

    if save_directory:
        print("Saving to %s" % save_directory)
        save(zenith_time_rotation, save_directory)
    else:
        display_trackbar = lambda _: display(cv2.getTrackbarPos('Time Index', suffixed('control')), cv2.getTrackbarPos('Rotation Index', suffixed('control')))
        display = lambda time_index, rotation_index: plt.close('all') or display_stokes(zenith_time_rotation[time_index], rotation_index)

        cv2.namedWindow(suffixed('control'))
        cv2.createTrackbar('Time Index', suffixed('control'), 0, time_points, display_trackbar)
        cv2.createTrackbar('Rotation Index', suffixed('control'), 0, max_data_points, display_trackbar)

        while (1):
            k = cv2.waitKey() & 0xFF

            if k == 27:
                break

def save(time_rotation_images, save_directory):
    for rotation_images in time_rotation_images:
        display_stokes(rotation_images, 0, save_directory=save_directory)

def save_labeled_images(time, rotation, labeled_images, directory):
    hour_minutes = minutes_to_hour_minutes(time)
    time_directory = "%s/%s" % (directory, hour_minutes)
    if not os.path.isdir(time_directory):
        os.makedirs(time_directory)

    for label, image in labeled_images:
        cv2.imwrite('/'.join([time_directory, '%s-%s-%s.png' % (hour_minutes, rotation, label)]), image)

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
    show_subset = False
    visualize_sevilla_zenith(sys.argv[1], use_raw=False, save_directory="sevilla-zenith-motor-rotation-vs-evectors-mono-filtered")

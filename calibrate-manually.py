import cv2
import sys
import numpy as np
import ipdb
import os
import pickle
import aye_utils
from operator import itemgetter

TRANSFORMATION_SUFFIX = '.transformation.txt'

def suffixed(str):
    return "%s-%s" % (str, SUFFIX)

SUFFIX = 'aye-analyze'

def get_pol_files_in_directory(directory):
    files = []
    for file in os.listdir(directory):
        if 'pol' in file and TRANSFORMATION_SUFFIX not in file:
            files.append(os.path.join(directory, file))

    return [*map(itemgetter(1), sorted(zip(map(parse_hostname, files), files)))]

def reset_to_original():
    global images, images_original
    images = list(map(lambda a: a.copy(), images_original))

def put_center_text(image, text):
    rows, cols = image.shape
    middle = (cols//2, rows//2)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(image, text, middle, font, 1, (128,128,128), 2, cv2.LINE_AA)

def show():
    global images
    transformed = []
    for index, image in enumerate(images):
        rows, cols = image.shape
        number = index + 1
        (x, y) = get_translation(number)
        translation_matrix = np.float32([[1,0,x], [0,1,y]])
        dst = cv2.warpAffine(image, translation_matrix, (cols,rows))
        alpha = get_rotation(number)
        center = (cols/2, rows/2)
        rotation_matrix = cv2.getRotationMatrix2D(center, alpha, 1)
        dst = cv2.warpAffine(dst, rotation_matrix, (cols,rows))
        transformed.append(dst)

    merged = cv2.merge(transformed)
    cv2.imshow(suffixed("merged"), merged)
    reset_to_original()

def get_translation(image_number):
    global translations

    return translations.setdefault(image_number, (0,0))

def translate(delta_x, delta_y):
    global selection, translations

    old_x, old_y = get_translation(selection)
    translations[selection] = (old_x + delta_x, old_y + delta_y)
    print("New translation for %d: %s" % (selection,  translations[selection]))

def get_rotation(image_number):
    global rotations

    return rotations.setdefault(image_number, 0)

def rotate(delta_alpha):
    global selection, rotations

    old_alpha = get_rotation(selection)
    rotations[selection] = old_alpha + delta_alpha
    print("New rotation for %d: %d" % (selection, rotations[selection]))

def save_transformations(dir = None):
    global image_names

    for index, image_name in enumerate(image_names):
        number = index + 1
        rotation = get_rotation(number)
        translation = get_translation(number)
        transformation_file_name = determine_transformation_file_name(image_name, dir)
        pickle.dump((rotation, translation), open(transformation_file_name, 'wb'))

    print("Saved transformations to %s" % os.path.split(determine_transformation_file_name(image_names[0], dir))[0])


def parse_hostname(image_name):
    matcher = aye_utils.pol_hostnames_pattern.search(image_name)
    if matcher is not None:
        return image_name[matcher.start():matcher.end()]
    else:
        print("Could not parse hostname from: %s" % image_name)
        return None

def determine_transformation_file_name(image_name, dir):
    if dir is None:
        transformation_file_name = image_name + TRANSFORMATION_SUFFIX 
    else:
        transformation_file_name = dir + '/' + parse_hostname(image_name) + TRANSFORMATION_SUFFIX

    return transformation_file_name

def load_transformations(dir=None):
    global image_names, translations, rotations

    for index, image_name in enumerate(image_names):
        number = index + 1
        transformation_file_name = determine_transformation_file_name(image_name, dir)
        if os.path.isfile(transformation_file_name):
            rotation, translation = pickle.load(open(transformation_file_name, 'rb'))
            rotations[number] = rotation
            translations[number] = translation
            print("Loaded translation %s and rotation %s for %d" % (translation, rotation, number))


image_names = get_pol_files_in_directory(sys.argv[1])
if len(sys.argv) > 2:
    save_load_directory = sys.argv[2]
else:
    save_load_directory = None

assert len(image_names) == 3, "Expected 3 polarization files, got: %s" % image_names

images_original = [*map(lambda f: cv2.imread(f, 0), image_names)]
images = None
reset_to_original()

assert len(images) == 3, "Populating images from original failed"

translations = {}
rotations = {}
mode = None
selection = None

load_transformations(save_load_directory)

while 1:
    assert len(images) == 3
    k = cv2.waitKey(100) & 0xFF

    if k == 27:
        if selection is not None:
            selection = None
        else:
            save_transformations(save_load_directory)
            break

    elif k > ord('1') and k < ord('4'):
        image_number = k - ord('0')
        transformation = (get_rotation(image_number), get_translation(image_number))
        print("Selected %d. Transformation: %s" % (image_number, transformation))
        selection = image_number
        mode = None

    elif selection is not None and k == ord('t'):
        mode = "translate"
        print("Entering mode %s for %d" % (mode, selection))

    elif selection is not None and k == ord('r'):
        mode = "rotate"
        print("Entering mode %s for %d" % (mode, selection))

    elif mode is not None:
        if mode is "translate":
            if k == 81: # left
                translate(-1, 0)
            elif k == 82: # up 
                translate(0, -1)
            elif k == 83: # right
                translate(1, 0)
            elif k == 84: # down 
                translate(0, 1)
        if mode is "rotate":
            if k == 81: # left
                rotate(1)
            elif k == 83: # right
                rotate(-1)

    elif k != 255:
        print("Unknown key pressed: %d" %  k)

    if selection is not None:
        description = str(selection)
        if mode is not None:
            description += mode[0]

        put_center_text(images[selection - 1], description)


    show()

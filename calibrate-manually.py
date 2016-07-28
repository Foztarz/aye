import cv2
import sys
import numpy as np
import ipdb
import os
import pickle

def get_pol_files_in_directory(directory):
    files = []
    for file in os.listdir(directory):
        if 'pol' in file and '.transformation' not in file:
            files.append(os.path.join(directory, file))

    return files

def reset_to_original():
    global images, images_original
    images = list(map(lambda a: a.copy(), images_original))

def put_center_text(image, text):
    rows, cols = image.shape
    middle = (cols/2, rows/2)
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
    cv2.imshow("merged", merged)
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

def save_transformations():
    global image_names

    for index, image_name in enumerate(image_names):
        number = index + 1
        rotation = get_rotation(number)
        translation = get_translation(number)
        transformation_file_name = image_name + '.transformation'
        pickle.dump((rotation, translation), open(transformation_file_name, 'w'))

    print("Saved transformations")

def load_transformations():
    global image_names, translations, rotations

    for index, image_name in enumerate(image_names):
        number = index + 1
        transformation_file_name = image_name + '.transformation'
        if os.path.isfile(transformation_file_name):
            rotation, translation = pickle.load(open(transformation_file_name, 'r'))
            rotations[number] = rotation
            translations[number] = translation
            print("Loaded translation %s and rotation %s for %d" % (translation, rotation, number))


image_names = get_pol_files_in_directory(sys.argv[1])
assert len(image_names) == 3, "Expected 3 polarization files, got: %s" % image_names

images_original = map(lambda f: cv2.imread(f, 0), image_names)
images = None
reset_to_original()

assert len(images) == 3, "Populating images from original failed"

translations = {}
rotations = {}
mode = None
selection = None

load_transformations()

while 1:
    assert len(images) == 3
    k = cv2.waitKey(100) & 0xFF

    if k == 27:
        if selection is not None:
            selection = None
        else:
            save_transformations()
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

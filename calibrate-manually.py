import cv2
import sys
import numpy as np
import ipdb
import os
import pickle
import aye_utils
from operator import itemgetter

TRANSFORMATION_SUFFIX = '.transformation.pickle'

def suffixed(str):
    return "%s-%s" % (str, SUFFIX)

SUFFIX = 'aye-analyze'

def get_pol_files_in_directory(directory):
    files = []
    for file in os.listdir(directory):
        if 'pol' in file and TRANSFORMATION_SUFFIX not in file:
            files.append(os.path.join(directory, file))

    return [*map(itemgetter(1), sorted(zip(map(parse_hostname, files), files)))]

def put_center_text(image, text):
    rows, cols = image.shape
    middle = (cols//2, rows//2)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(image, text, middle, font, 1, (128,128,128), 2, cv2.LINE_AA)

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

class ManualCalibrator:

    def reset_to_original(self):
        self.images = list(map(lambda a: a.copy(), self.images_original))

    def show(self):
        transformed = []
        for index, image in enumerate(self.images):
            rows, cols = image.shape
            number = index + 1
            (x, y) = self.get_translation(number)
            translation_matrix = np.float32([[1,0,x], [0,1,y]])
            dst = cv2.warpAffine(image, translation_matrix, (cols,rows))
            alpha = self.get_rotation(number)
            center = (cols/2, rows/2)
            rotation_matrix = cv2.getRotationMatrix2D(center, alpha, 1)
            dst = cv2.warpAffine(dst, rotation_matrix, (cols,rows))
            transformed.append(dst)

        merged = cv2.merge(transformed)
        cv2.imshow(suffixed("merged"), merged)
        self.reset_to_original()
        return transformed

    def get_translation(self, image_number):
        return self.translations.setdefault(image_number, (0,0))

    def translate(self, delta_x, delta_y):
        old_x, old_y = self.get_translation(self.selection)
        self.translations[self.selection] = (old_x + delta_x, old_y + delta_y)
        print("New translation for %d: %s" % (self.selection,  self.translations[self.selection]))

    def get_rotation(self, image_number):
        return self.rotations.setdefault(image_number, 0)

    def rotate(self, delta_alpha):
        old_alpha = self.get_rotation(self.selection)
        self.rotations[self.selection] = old_alpha + delta_alpha
        print("New rotation for %d: %d" % (self.selection, self.rotations[self.selection]))

    def save_transformations(self, dir = None):
        for index, image_name in enumerate(self.image_names):
            number = index + 1
            rotation = self.get_rotation(number)
            translation = self.get_translation(number)
            transformation_file_name = determine_transformation_file_name(image_name, dir)
            pickle.dump((rotation, translation), open(transformation_file_name, 'wb'))

        print("Saved transformations to %s" % os.path.split(determine_transformation_file_name(self.image_names[0], dir))[0])

    def load_transformations(self, dir=None):
        for index, image_name in enumerate(self.image_names):
            number = index + 1
            transformation_file_name = determine_transformation_file_name(image_name, dir)
            if os.path.isfile(transformation_file_name):
                rotation, translation = pickle.load(open(transformation_file_name, 'rb'))
                self.rotations[number] = rotation
                self.translations[number] = translation
                print("Loaded translation %s and rotation %s for %d" % (translation, rotation, number))

    def __init__(self, image_names, save_load_directory=None):
        if save_load_directory is not None:
            if not os.path.isdir(save_load_directory):
                os.makedirs(save_load_directory)
        assert len(image_names) == 3, "Expected 3 polarization files, got: %s" % image_names

        self.save_load_directory = save_load_directory
        self.image_names = image_names
        self.images_original = [*map(lambda f: cv2.imread(f, 0), image_names)]
        self.images = None
        self.reset_to_original()

        assert len(self.images) == 3, "Populating images from original failed"

        self.translations = {}
        self.rotations = {}
        self.selection = None

    def start(self):
        self.load_transformations(self.save_load_directory)
        mode = None
        transformed = None

        while 1:
            assert len(self.images) == 3
            k = cv2.waitKey(100) & 0xFF

            if k == 27:
                if self.selection is not None:
                    self.selection = None
                else:
                    break

            elif k > ord('1') and k < ord('4'):
                image_number = k - ord('0')
                transformation = (self.get_rotation(image_number), self.get_translation(image_number))
                print("Selected %d. Transformation: %s" % (image_number, transformation))
                self.selection = image_number
                mode = None

            elif self.selection is not None and k == ord('t'):
                mode = "translate"
                print("Entering mode %s for %d" % (mode, self.selection))

            elif self.selection is not None and k == ord('r'):
                mode = "rotate"
                print("Entering mode %s for %d" % (mode, self.selection))

            elif mode is not None:
                if mode is "translate":
                    if k == 81: # left
                        self.translate(-1, 0)
                    elif k == 82: # up 
                        self.translate(0, -1)
                    elif k == 83: # right
                        self.translate(1, 0)
                    elif k == 84: # down 
                        self.translate(0, 1)
                if mode is "rotate":
                    if k == 81: # left
                        self.rotate(1)
                    elif k == 83: # right
                        self.rotate(-1)

            elif k != 255:
                print("Unknown key pressed: %d" %  k)

            if self.selection is not None:
                description = str(self.selection)
                if mode is not None:
                    description += mode[0]

                put_center_text(self.images[self.selection - 1], description)

            transformed = self.show()

        self.save_transformations(self.save_load_directory)

        return transformed

if __name__ == '__main__':
    image_names = get_pol_files_in_directory(sys.argv[1])
    if len(sys.argv) > 2:
        save_load_directory = sys.argv[2]
        if not os.path.isdir(save_load_directory):
            os.makedirs(save_load_directory)
    else:
        save_load_directory = None

    ManualCalibrator(image_names, save_load_directory).start()

import stokes
import aye_utils
import cv2
import numpy as np

def small(image):
    return cv2.resize(image, (480, 360))

def point_on_circle(rad, radius):
    return (np.cos(rad + np.pi/2)*radius , np.sin(rad + np.pi/2)*radius)

def pointed_line(angle_deg, x, y, line_length):
    line_point1 = np.array((x,y))
    line_point2 = np.array((x,y))

    angle_rad = np.deg2rad(angle_deg)

    line_point1 = np.sum([line_point1, point_on_circle(angle_rad-np.pi, line_length/2)], 0).astype(int)
    line_point2 = np.sum([line_point2, point_on_circle(angle_rad, line_length/2)], 0).astype(int)
    
    return line_point1, line_point2

def hue_and_evectors(angle_radians, downsample = 15, degree = None):
    angle_in_degrees = stokes.angle_to_hue(angle_radians)
    angle_radians_downsampled = small(angle_radians[::downsample, ::downsample])
    if degree is not None:
        degree_downsampled = small(degree[::downsample, ::downsample])
    else:
        degree_downsampled = None

    angle_image_downsampled = cv2.cvtColor(cv2.merge(stokes.angle_hsv(angle_radians_downsampled, degree_downsampled)), cv2.COLOR_HSV2BGR) 
    angle_in_degrees_downsampled = stokes.angle_to_hue(angle_radians_downsampled, invert=True)

    width, height = angle_in_degrees.shape[:2]
    sample_step = downsample

    angle_image_with_lines = angle_image_downsampled
    for x in range(sample_step, width, sample_step):
        for y in range(sample_step, height, sample_step):
            point1, point2 = pointed_line(angle_in_degrees_downsampled[(x,y)], x, y, sample_step - 3)
            angle_image_with_lines = cv2.arrowedLine(angle_image_with_lines, tuple(point1[::-1]), tuple(point2[::-1]), (0,0,0))
    return angle_image_with_lines
class Polarizer:
    def __init__(self, images):
        self.images = images

        image0, image45, image90 = images

        stokesI, stokesQ, stokesU, self.intensity, self.degree, self.angle = stokes.getStokes(image0, image45, image90)

    def get_parameters(self):
        return self.angle, self.degree, self.intensity

    def pretty_angle(self, angle, downsample=15, degree=None):
        return hue_and_evectors(angle, downsample, degree)

    def pretty_degree(self, degree):
        normalized_degree = aye_utils.normalized_uint8(degree, 1)
        return normalized_degree 

    def pretty_intensity(self, intensity):
        normalized_intensity = aye_utils.normalized_uint8(intensity, 500)
        return normalized_intensity 


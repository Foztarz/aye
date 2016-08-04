"""
Assumes calibrate_folder and segment_folder have already been applied"
"""

from calibrate_manually import ManualCalibrator, get_pol_files_in_directory, suffixed
from grabcut import Segmenter
from polarizer import Polarizer
import sys
import cv2
import os
import numpy as np 
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import ipdb

def get_folders_in_directory(directory):
    folders = []
    for file in os.listdir(directory):
        folder = os.path.join(directory, file)
        if os.path.isdir(folder):
            folders.append(folder)

    return [*sorted(folders)]

def update_control_view(folder_name):
    font = cv2.FONT_HERSHEY_SIMPLEX
    img = np.zeros((480, 640))
    cv2.putText(img, folder_name, (10,50), font, 1, (255,255,255),2,cv2.LINE_AA)
    cv2.imshow(suffixed('control'), img)

def show(folder):
    global segmenter, manual_calibrator, polarizer
    folder_name = os.path.split(folder)[1]
    update_control_view(folder_name)
    manual_calibrator = ManualCalibrator(get_pol_files_in_directory(folder), "terra-transformations")
    segmenter = Segmenter(manual_calibrator.image_names[0])
    polarizer = Polarizer(manual_calibrator.get_calibrated())
    #show_manual_calibrator()
    #show_segmented()
    #show_polarized()
    show_graph()

def show_graph():
    global fig
    if fig:
        plt.close(fig)
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    angle, degree, intensity = polarizer.get_parameters()
    downsample = 1
    flat_parameters = [*map(lambda a: a.flatten()[::downsample], [angle, degree, intensity])]
    mask = segmenter.get_mask()
    flat_mask = mask.flatten()[::downsample]
    ground_filter = lambda a: a[flat_mask==255]
    sky_filter = lambda a: a[flat_mask==0]
    ground_angle, ground_degree, ground_intensity = [*map(ground_filter, flat_parameters)]
    sky_angle, sky_degree, sky_intensity = [*map(sky_filter, flat_parameters)]
    ax.scatter(ground_angle, ground_degree, ground_intensity, c='r')
    ax.scatter(sky_angle, sky_degree, sky_intensity, c='b')
    ax.set_xlabel('Angle')
    ax.set_ylabel('Degree')
    ax.set_zlabel('Intensity')
    plt.show()

def show_manual_calibrator():
    global manual_calibrator

    print("Showing %s" % folder_name)
    manual_calibrator.show()

def calibrated_show(window_name, image):
    calibrated_mask = manual_calibrator.get_calibrated_mask(manual_calibrator.get_calibrated())
    apply_mask = lambda c: cv2.bitwise_and(c, c, mask=calibrated_mask)
    cv2.imshow(suffixed(window_name), apply_mask(image))

def show_segmented():
    global segmenter

    mask = segmenter.get_mask()
    calibrated_show('segmentation', mask)

def show_polarized():
    global polarizer


    angle, degree, intensity = polarizer.get_parameters()

    calibrated_show('angle', polarizer.pretty_angle(angle, downsample=10))
    calibrated_show('angle-weighted', polarizer.pretty_angle(angle, downsample=10, degree=degree))
    calibrated_show('degree', polarizer.pretty_degree(degree))
    intensity = polarizer.pretty_intensity(intensity)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(intensity, "intensity", (10,50), font, 1, (255,255,255),2,cv2.LINE_AA)
    calibrated_show('intensity', intensity)

manual_calibrator = None
segmenter = None
polarizer = None
fig = None
directory = sys.argv[1]
folders = get_folders_in_directory(directory)
print("%d directories" % len(folders))

calibrate = lambda index: show(folders[index])
cv2.namedWindow(suffixed('control'))
cv2.createTrackbar('Folder', suffixed('control'), 0, len(folders)-1, calibrate)
#show(folders[0])
plt.ion()

while (1):
    k = cv2.waitKey() & 0xFF

    if k == 27:
        break

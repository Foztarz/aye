from calibrate_manually import ManualCalibrator, get_pol_files_in_directory, suffixed
import grabcut
import sys
import cv2
import os
import numpy as np 

def get_folders_in_directory(directory):
    folders = []
    for file in os.listdir(directory):
        folder = os.path.join(directory, file)
        if os.path.isdir(folder):
            folders.append(folder)

    return [*sorted(folders)]

def update_control_view(folder_name):
    font = cv2.FONT_HERSHEY_SIMPLEX
    img = np.zeros((480, 320))
    cv2.putText(img, folder_name, (10,50), font, 1, (255,255,255),2,cv2.LINE_AA)
    cv2.imshow(suffixed('control'), img)

def show_manual_calibrator(folder):
    global manual_calibrator

    folder_name = os.path.split(folder)[1]
    print("Showing %s" % folder_name)
    update_control_view(folder_name)
    manual_calibrator = ManualCalibrator(get_pol_files_in_directory(folder), "terra-transformations")
    manual_calibrator.show()

manual_calibrator = None
directory = sys.argv[1]
folders = get_folders_in_directory(directory)
print("%d directories" % len(folders))

calibrate = lambda index: show_manual_calibrator(folders[index])
cv2.namedWindow(suffixed('control'))
cv2.createTrackbar('Folder', suffixed('control'), 0, len(folders)-1, calibrate)
show_manual_calibrator(folders[0])

while (1):
    k = cv2.waitKey() & 0xFF

    if k == 27:
        break
    elif k == ord('s'):
        grabcut.start(manual_calibrator.image_names[0])

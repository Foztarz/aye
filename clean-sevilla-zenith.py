import numpy as np
import math
import sys
import analyze_data
import os
import shutil
from operator import itemgetter
import ipdb

# Run over grouped sevilla data

def save_new_rotation(old_rotation_file_path, new_rotation, output_directory):
    old_rotation = analyze_data.parse_rotation(old_rotation_file_path)
    new_rotation_file_name = os.path.split(old_rotation_file_path)[-1].replace('pan-%d-' % old_rotation, 'pan-%d-' % new_rotation)

    if not os.path.isdir(output_directory):
        os.makedirs(output_directory)
    shutil.copy2(old_rotation_file_path, os.path.join(output_directory, new_rotation_file_name))

input_directory = sys.argv[1]
output_directory = sys.argv[2]

zenith_times = filter(lambda f: 'azim' in f, analyze_data.get_files_in_directory(input_directory))
zenith_times = map(itemgetter(1), sorted(zip(map(analyze_data.parse_zenith_time, zenith_times), zenith_times)))

print("Directories to fix: %d" % len(list(zenith_times)))

for zenith_time in zenith_times:
    pol_files = filter(lambda f: 'pol' in f, analyze_data.get_files_in_directory(zenith_time))
    files_length = len(list(pol_files))
    data_points = files_length / 3

    rotation_step = (360-5.)/(data_points-1)
    
    rotation_sorted_pol_files = list(map(itemgetter(1), sorted(zip(map(analyze_data.parse_rotation, pol_files), pol_files))))
    position = 0

    new_directory = os.path.join(output_directory, os.path.split(zenith_time)[-1])

    print("Files to fix: %d" % len(rotation_sorted_pol_files))

    step = 0

    for rotation in np.arange(5, 361, rotation_step):
        rotation = int(rotation)
        if position >= len(rotation_sorted_pol_files):
            print("Out of files at step %d and rotation %d" % (step, rotation))
            break
        step += 1
        from_rotation = analyze_data.parse_rotation(rotation_sorted_pol_files[position])
        count = 0
        while position < len(rotation_sorted_pol_files) and analyze_data.parse_rotation(rotation_sorted_pol_files[position]) == from_rotation:
                save_new_rotation(rotation_sorted_pol_files[position], rotation, new_directory)
                position += 1
                count += 1
                
        assert count == 3

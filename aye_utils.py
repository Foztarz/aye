import numpy as np

def normalized_uint8(array, divider=None):
    if divider is None:
        divider = np.amax(array) 
    return np.uint8(255*array/divider)



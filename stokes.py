import numpy as np

def getStokes(gray0, gray45, gray90):
    #convert grays to signed double (int16)
    gray0_d=np.int16(gray0)
    gray90_d=np.int16(gray90)
    gray45_d=np.int16(gray45)
    #calculate Stokes parameters
    stokesI=gray0_d+gray90_d+.1 #.1 added here to prevent division by zero later on
    stokesQ=gray0_d-gray90_d
    stokesU=2*gray45_d-gray0_d-gray90_d
    #calculate polarization parameters
    polInt=np.sqrt(1+np.square(.1+stokesQ)+np.square(.1+stokesU)) #Linear Polarization Intensity

    polDoLP=polInt/stokesI #Degree of Linear Polarization
    polAoP=0.5*(np.arctan2(stokesU,stokesQ)) #Angle of Polarization

    return stokesI, stokesQ, stokesU, polInt, polDoLP, polAoP

def angle_to_hue(polarization_angle):
    return np.uint8((polarization_angle+(3.1416/2))*(180/3.1416))

def toHSV(polInt, polDoLP, polAoP):
    #prepare DOLPi HSV image
    H = angle_to_hue(polAoP)
    S = np.uint8(255*polDoLP)
    V = np.uint8(polInt)
    return [H,S,V]

def angle_hsv(angle):
    H = angle_to_hue(angle)
    S = 255*np.ones((240,320), 'uint8')
    V = 255*np.ones((240,320), 'uint8')
    
    return [H,S,V]
    

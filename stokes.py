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

def toHSV(polInt, polDoLP, polAoP):
    #prepare DOLPi HSV image
    H=np.uint8((polAoP+(3.1416/2))*(180/3.1416))
    S=np.uint8(255*(polDoLP/np.amax(polDoLP)))
    V=np.uint8(255*(polInt/np.amax(polInt)))
    return [H,S,V]
    

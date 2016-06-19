def getStokes(image0, image45, image90):
    #convert images to signed double (int16)
    image0_d=np.int16(image0)
    image90_d=np.int16(image90)
    image45_d=np.int16(image45)
    #calculate Stokes parameters
    stokesI=image0_d+image90_d+.1 #.1 added here to prevent division by zero later on
    stokesQ=image0_d-image90_d
    stokesU=2*image45_d-image0_d-image90_d
    #calculate polarization parameters
    polInt=np.sqrt(1+np.square(.1+stokesQ)+np.square(.1+stokesU)) #Linear Polarization Intensity

    polDoLP=polInt/stokesI #Degree of Linear Polarization
    polAoP=0.5*(np.arctan2(stokesU,stokesQ)) #Angle of Polarization

    return polInt, polDoLP, polAoP

def showHSV(polInt, polDoLP, polAoP):
    #prepare DOLPi HSV image
    H=np.uint8((polAoP+(3.1416/2))*(180/3.1416))
    S=np.uint8(255*(polDoLP/np.amax(polDoLP)))
    V=np.uint8(255*(polInt/np.amax(polInt)))
    hsv=cv2.merge([H,S,V])
    hsvInBGR=cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    cv2.imshow("stokes-hsv", DOLPiHSVinBGR)

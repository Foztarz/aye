#!/usr/bin/env python
'''
===============================================================================
Modified Interactive Image Segmentation using GrabCut algorithm.

This sample shows interactive image segmentation using grabcut algorithm.

USAGE:
    python grabcut.py <filename>

README FIRST:
    Two windows will show up, one for input and one for output.

    At first, in input window, draw a rectangle around the object using
mouse right button. Then press 'n' to segment the object (once or a few times)
For any finer touch-ups, you can press any of the keys below and draw lines on
the areas you want. Then again press 'n' for updating the output.

Key '0' - To select areas of sure background
Key '1' - To select areas of sure foreground
Key '2' - To select areas of probable background
Key '3' - To select areas of probable foreground

Key 'n' - To update the segmentation
Key 'r' - To reset the setup
Key 's' - To save the results
===============================================================================
'''

# Python 2/3 compatibility
from __future__ import print_function

import numpy as np
import cv2
import sys
from calibrate_manually import suffixed
import os

BLUE = [255,0,0]        # rectangle color
RED = [0,0,255]         # PR BG
GREEN = [0,255,0]       # PR FG
BLACK = [0,0,0]         # sure BG
WHITE = [255,255,255]   # sure FG

DRAW_BG = {'color' : BLACK, 'val' : 0}
DRAW_FG = {'color' : WHITE, 'val' : 1}
DRAW_PR_FG = {'color' : GREEN, 'val' : 3}
DRAW_PR_BG = {'color' : RED, 'val' : 2}

MASK_SUFFIX = '.mask.png'

# setting up flags
rect = (0,0,1,1)
drawing = False         # flag for drawing curves
rectangle = False       # flag for drawing rect
rect_over = False       # flag to check if rect drawn
rect_or_mask = 100      # flag for selecting rect or mask mode
value = DRAW_FG         # drawing initialized to FG
thickness = 3           # brush thickness

def onmouse(event,x,y,flags,param):
    global img,img2,drawing,value,mask,rectangle,rect,rect_or_mask,rect_over

    # Draw Rectangle
    if event == cv2.EVENT_RBUTTONDOWN:
        rectangle = True

    elif event == cv2.EVENT_MOUSEMOVE:
        if rectangle == True:
            img = img2.copy()
            rows, cols = img.shape[:2]
            rect = (0,0,cols,y)
            cv2.rectangle(img,(0,0),(cols,y),BLUE,2)
            rect_or_mask = 0

    elif event == cv2.EVENT_RBUTTONUP:
        rows, cols = img.shape[:2]
        rectangle = False
        rect_over = True
        cv2.rectangle(img,(0,0),(cols,y),BLUE,2)
        rect = (0,0,cols,y)
        rect_or_mask = 0

    if event == cv2.EVENT_LBUTTONDOWN:
        if rect_over == False:
            print("first draw rectangle \n")
        else:
            drawing = True
            cv2.circle(img,(x,y),thickness,value['color'],-1)
            cv2.circle(mask,(x,y),thickness,value['val'],-1)

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing == True:
            cv2.circle(img,(x,y),thickness,value['color'],-1)
            cv2.circle(mask,(x,y),thickness,value['val'],-1)

    elif event == cv2.EVENT_LBUTTONUP:
        if drawing == True:
            drawing = False
            cv2.circle(img,(x,y),thickness,value['color'],-1)
            cv2.circle(mask,(x,y),thickness,value['val'],-1)

def start(file_path):
    Segmenter(file_path).start()

class Segmenter:
    def __init__(self, file_path):
        global img,img2,drawing,value,mask,rectangle,rect,rect_or_mask,rect_over
        self.file_path = file_path
        img = cv2.imread(self.file_path)
        img2 = img.copy()                               # a copy of original image
        if os.path.isfile(self.file_path + MASK_SUFFIX):
            self.mask2 = cv2.imread(self.file_path + MASK_SUFFIX, 0)
            print("Loaded existing mask.")
        else:
            self.mask2 = np.zeros(img.shape[:2],dtype = np.uint8) # mask initialized to PR_BG
        output = np.zeros(img.shape,np.uint8)           # output image to be shown
        mask = np.zeros(img.shape[:2],dtype = np.uint8) # mask initialized to PR_BG

    def start(self):
        global img,img2,drawing,value,mask,rectangle,rect,rect_or_mask,rect_over,mask2

        # input and output windows
        cv2.namedWindow(suffixed('output'))
        cv2.namedWindow(suffixed('input'))
        cv2.setMouseCallback(suffixed('input'),onmouse)
        cv2.moveWindow(suffixed('input'),img.shape[1]+10,90)

        print(" Instructions: \n")
        print(" Draw a rectangle around the object using right mouse button \n")

        while(1):

            cv2.imshow(suffixed('output'),output)
            cv2.imshow(suffixed('input'),img)
            k = 0xFF & cv2.waitKey(1)

            # key bindings
            if k == 27:         # esc to exit
                break
            elif k == ord('0'): # BG drawing
                print(" mark background regions with left mouse button \n")
                value = DRAW_BG
            elif k == ord('1'): # FG drawing
                print(" mark foreground regions with left mouse button \n")
                value = DRAW_FG
            elif k == ord('2'): # PR_BG drawing
                value = DRAW_PR_BG
            elif k == ord('3'): # PR_FG drawing
                value = DRAW_PR_FG
            elif k == ord('s'): # save image
                cv2.imwrite(self.file_path+MASK_SUFFIX, self.mask2)
                print(" Result saved as image \n")
            elif k == ord('r'): # reset everything
                print("resetting \n")
                rect = (0,0,1,1)
                drawing = False
                rectangle = False
                rect_or_mask = 100
                rect_over = False
                value = DRAW_FG
                img = img2.copy()
                mask = np.zeros(img.shape[:2],dtype = np.uint8) # mask initialized to PR_BG
                output = np.zeros(img.shape,np.uint8)           # output image to be shown
            elif k == ord('n'): # segment the image
                print(""" For finer touchups, mark foreground and background after pressing keys 0-3
                and again press 'n' \n""")
                if (rect_or_mask == 0):         # grabcut with rect
                    bgdmodel = np.zeros((1,65),np.float64)
                    fgdmodel = np.zeros((1,65),np.float64)
                    cv2.grabCut(img2,mask,rect,bgdmodel,fgdmodel,1,cv2.GC_INIT_WITH_RECT)
                    rect_or_mask = 1
                elif rect_or_mask == 1:         # grabcut with mask
                    bgdmodel = np.zeros((1,65),np.float64)
                    fgdmodel = np.zeros((1,65),np.float64)
                    cv2.grabCut(img2,mask,rect,bgdmodel,fgdmodel,1,cv2.GC_INIT_WITH_MASK)

                self.mask2 = np.where((mask==1) + (mask==3),255,0).astype('uint8')
            output = cv2.bitwise_and(img2,img2,mask=self.mask2)

        cv2.destroyWindow(suffixed('output'))
        cv2.destroyWindow(suffixed('input'))

    def get_mask(self):
        return self.mask2

import sys
sys.path.append('../src/')

import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from copy import deepcopy
import colorTools
import math

#Point to String
def pts(point):
    return '({:.3}, {:.3}, {:.3})'.format(*[float(value) for value in point])

def plot3d(points, xLabel, yLabel, zLabel):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(points[:, 0], points[:, 1], points[:, 2])
    ax.set_xlabel(xLabel)
    ax.set_ylabel(yLabel)
    ax.set_zlabel(zLabel)
    plt.show()

with open('faceColors.json', 'r') as f:
    facesData = f.read()
    facesData = json.loads(facesData)

size = 10


medianDiffs = []

for faceData in facesData:

    if not faceData['successful']:
        continue

    #for key in faceData['captures']:
        #print('CAPTURES {} -> {}'.format(key, faceData['captures'][key]))

    medianDiffs.append([faceData['name'], faceData['medianDiffs']])
   # for key in faceData['medianDiffs']:
   #     print('MEDIAN DIFFS {} -> {}'.format(key, faceData['medianDiffs'][key]))


if len(medianDiffs) == 0:
    print('No Results :(')
else:
    wbBGR = []
    wbHSV = []

    medianBGRs = []
    medianHSVs = []

    for medianDiff in medianDiffs:
        #print('Median Diff :: ' + str(medianDiff))
        name, medianDiff = medianDiff
        leftReflection = np.array(medianDiff['reflections']['left'])
        rightReflection = np.array(medianDiff['reflections']['right'])
        averageReflection = (leftReflection + rightReflection) / 2

        #print('L :: {} | R :: {} | A :: {}'.format(leftReflection, rightReflection, averageReflection))
        
        leftPoint = np.array(medianDiff['regions']['left'])
        rightPoint = np.array(medianDiff['regions']['right'])
        chinPoint = np.array(medianDiff['regions']['chin'])
        foreheadPoint = np.array(medianDiff['regions']['forehead'])

        #leftPointWB = leftPoint
        #rightPointWB = rightPoint
        #chinPointWB = chinPoint
        #foreheadPointWB = foreheadPoint
        #medianBGR = np.median(np.array([leftPoint, rightPoint, chinPoint, foreheadPoint]), axis=0)

        leftPointWB = colorTools.whitebalanceBGRPoints(leftPoint, leftReflection)
        rightPointWB = colorTools.whitebalanceBGRPoints(rightPoint, rightReflection)
        chinPointWB = colorTools.whitebalanceBGRPoints(chinPoint, averageReflection)
        foreheadPointWB = colorTools.whitebalanceBGRPoints(foreheadPoint, averageReflection)
        #medianBGR = np.median(np.array([leftPointWB, rightPointWB, chinPointWB, foreheadPointWB]), axis=0)
        medianBGR = chinPointWB

        leftPointHSV = colorTools.bgr_to_hsv(leftPointWB)
        rightPointHSV = colorTools.bgr_to_hsv(rightPointWB)
        chinPointHSV = colorTools.bgr_to_hsv(chinPointWB)
        foreheadPointHSV = colorTools.bgr_to_hsv(foreheadPointWB)
        #medianHSV = np.median(np.array([leftPointHSV, rightPointHSV, chinPointHSV, foreheadPointHSV]), axis=0)
        medianHSV = chinPointHSV

        wbBGR.append(leftPointWB)
        wbBGR.append(rightPointWB)
        wbBGR.append(chinPointWB)
        wbBGR.append(foreheadPointWB)
        medianBGRs.append(medianBGR)

        wbHSV.append(leftPointHSV)
        wbHSV.append(rightPointHSV)
        wbHSV.append(chinPointHSV)
        wbHSV.append(foreheadPointHSV)
        medianHSVs.append(medianHSV)

        print('{}'.format(name))
        print('\tBGR -> Median :: {} || Left :: {} | Right :: {} | Chin :: {} | Forehead :: {}'.format(pts(medianBGR), pts(leftPointWB), pts(rightPointWB), pts(chinPointWB), pts(foreheadPointWB)))
        print('\tHSV -> Median :: {} || Left :: {} | Right :: {} | Chin :: {} | Forehead :: {}'.format(pts(medianHSV), pts(leftPointHSV), pts(rightPointHSV), pts(chinPointHSV), pts(foreheadPointHSV)))

    wbBGR = np.array(wbBGR)
    wbHSV = np.array(wbHSV)
    wbHSV[:, 0] = colorTools.rotateHue(wbHSV[:, 0])

    medianBGRs = np.array(medianBGRs)
    medianHSVs = np.array(medianHSVs)
    medianHSVs[:, 0] = colorTools.rotateHue(medianHSVs[:, 0])

    #plot3d(wbBGR, 'Blue', 'Green', 'Red')
    #plot3d(wbHSV, 'Hue', 'Saturation', 'Value')
    plot3d(medianBGRs, 'Blue', 'Green', 'Red')
    plot3d(medianHSVs, 'Hue', 'Saturation', 'Value')



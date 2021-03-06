"""Plot and analyze makeup colors from existing brands"""
import csv
import sys
import colorsys
import color
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, '../src')
import colorTools

paths = ['../../scraped/bm_colors/bm_colors.csv', '../../scraped/fenti_colors/fentiColors.csv', '../../scraped/makeupForever/makeupForeverColors.csv']
names = ['Bare Minerals', 'Fenti', 'Makeup Forever']
colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]

sRGB_points = [[], [], []]
linearRGB_points = [[], [], []]
linearHSV_points = [[], [], []]
luminance_points = [[], [], []]
HSV_points = [[], [], []]
HLS_points = [[], [], []]

def plotHSV():
    for index, hsvPoints in enumerate(HSV_points):
        if names[index] != 'Fenti':
            continue

        hsvPoints = np.array(hsvPoints)

        colors = np.array(sRGB_points[index])

        plt.subplot(131)
        plt.scatter(hsvPoints[:, 0], hsvPoints[:, 2], 50, colors)
        plt.xlabel('Hue')
        plt.ylabel('Value')

        plt.subplot(132)
        plt.scatter(hsvPoints[:, 0], list(hsvPoints[:, 1]), 50, colors)
        plt.xlabel('Hue')
        plt.ylabel('Saturation')

        plt.subplot(133)
        plt.scatter(hsvPoints[:, 1], list(hsvPoints[:, 2]), 50, colors)
        plt.xlabel('Saturation')
        plt.ylabel('Value')

        plt.suptitle("HSV " + names[index])
        plt.show()

def plotLinearHSV():
    for index, hsvPoints in enumerate(linearHSV_points):
        if names[index] != 'Fenti':
            continue

        hsvPoints = np.array(hsvPoints)

        colors = np.array(sRGB_points[index])

        plt.subplot(131)
        plt.scatter(hsvPoints[:, 0], hsvPoints[:, 2], 50, colors)
        plt.xlabel('Hue')
        plt.ylabel('Value')

        plt.subplot(132)
        plt.scatter(hsvPoints[:, 0], list(hsvPoints[:, 1]), 50, colors)
        plt.xlabel('Hue')
        plt.ylabel('Saturation')

        plt.subplot(133)
        plt.scatter(hsvPoints[:, 1], list(hsvPoints[:, 2]), 50, colors)
        plt.xlabel('Saturation')
        plt.ylabel('Value')

        plt.suptitle("Linear HSV " + names[index])
        plt.show()

def plotHLS():
    for index, hlsPoints in enumerate(HLS_points):
        hlsPoints = np.array(hlsPoints)

        colors = np.array(sRGB_points[index])

        l_A = np.vstack([hlsPoints[:, 1], np.ones(len(hlsPoints))]).T
        h_m, h_c = np.linalg.lstsq(l_A, hlsPoints[:, 0], rcond=None)[0]

        print('Hue Slope, Constant :: ' + str(h_m) + ' ' + str(h_c))

        plt.subplot(131)
        plt.scatter(hlsPoints[:, 0], hlsPoints[:, 1], 250, colors)
        plt.xlabel('Hue')
        plt.ylabel('Lightness')

        plt.subplot(132)
        plt.scatter(hlsPoints[:, 0], hlsPoints[:, 2], 250, colors)
        plt.xlabel('Hue')
        plt.ylabel('Saturation')

        plt.subplot(133)
        plt.scatter(hlsPoints[:, 2], hlsPoints[:, 1], 250, colors)
        plt.xlabel('Saturation')
        plt.ylabel('Lightness')

        plt.suptitle("HLS " + names[index])
        plt.show()

def plotLAB():
    for index, rgbPoints in enumerate(sRGB_points):
        colors = np.array(sRGB_points[index])
        labPoints = color.rgb2lab(np.array([rgbPoints]), "D65")[0]
        colorTools.bgr

        plt.subplot(131)
        plt.scatter(labPoints[:, 1], labPoints[:, 0], 50, colors)
        plt.xlabel('a*')
        plt.ylabel('L*')

        plt.subplot(132)
        plt.scatter(labPoints[:, 1], labPoints[:, 2], 50, colors)
        plt.xlabel('a*')
        plt.ylabel('b*')

        plt.subplot(133)
        plt.scatter(labPoints[:, 2], labPoints[:, 0], 50, colors)
        plt.xlabel('b*')
        plt.ylabel('L*')

        plt.suptitle("LAB " + names[index])
        plt.show()

def plotRGB():
    for index, rgbPoints in enumerate(sRGB_points):
        colors = np.array(sRGB_points[index])
        rgbPoints = np.array(rgbPoints)

        plt.subplot(131)
        plt.scatter(rgbPoints[:, 0], rgbPoints[:, 1], 50, colors)
        plt.xlabel('R')
        plt.ylabel('G')

        plt.subplot(132)
        plt.scatter(rgbPoints[:, 0], rgbPoints[:, 2], 50, colors)
        plt.xlabel('R')
        plt.ylabel('B')

        plt.subplot(133)
        plt.scatter(rgbPoints[:, 1], rgbPoints[:, 2], 50, colors)
        plt.xlabel('G')
        plt.ylabel('B')

        plt.suptitle("RGB " + names[index])
        plt.show()

def plotLinearRGB():
    for index, rgbPoints in enumerate(linearRGB_points):
        colors = np.array(sRGB_points[index])
        rgbPoints = np.array(rgbPoints)

        plt.subplot(131)
        plt.scatter(rgbPoints[:, 0], rgbPoints[:, 1], 50, colors)
        plt.xlabel('R')
        plt.ylabel('G')

        plt.subplot(132)
        plt.scatter(rgbPoints[:, 0], rgbPoints[:, 2], 50, colors)
        plt.xlabel('R')
        plt.ylabel('B')

        plt.subplot(133)
        plt.scatter(rgbPoints[:, 1], rgbPoints[:, 2], 50, colors)
        plt.xlabel('G')
        plt.ylabel('B')

        plt.suptitle("Linear RGB " + names[index])
        plt.show()

for index, path in enumerate(paths):
    with open(path, 'r', newline='') as f:
        pointReader = csv.reader(f, delimiter=' ', quotechar='|')
        for point in pointReader:
            sRGB_point = np.array([int(i) / 255 for i in point])
            sRGB_points[index].append(sRGB_point)

            #luminance_point = colorTools.getRelativeLuminance(np.flip(np.array([np.copy(linearRGB_point)]), axis=1))
            luminance_point = colorTools.getRelativeLuminance(np.flip(np.array([np.copy(sRGB_point)]), axis=1))
            
            linearRGB_point = colorTools.convert_sBGR_to_linearBGR_float(np.copy(sRGB_point), isFloat=True)
            linearRGB_points[index].append(linearRGB_point)

            #sRGB_point = np.array(sRGB_point)
            HSV_point = colorsys.rgb_to_hsv(*sRGB_point)
            HSV_points[index].append(np.array(HSV_point))
            #HSV_points[index][-1][2] = luminance_point

            linearHSV_point = colorsys.rgb_to_hsv(*linearRGB_point)
            linearHSV_points[index].append(np.array(linearHSV_point))

            HLS_point = colorsys.rgb_to_hls(*sRGB_point)
            HLS_points[index].append(np.array(HLS_point))

            #luminance_points[index].append(luminance_point)

#plotRGB()
#plotLinearRGB()
plotHSV()
plotLinearHSV()
#plotHLS()
plotLAB()

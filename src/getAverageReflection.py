import utils
import saveStep
import cv2
import numpy as np
import colorTools
import alignImages
import cropTools
import colorsys
import math
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def getLeftEyeCrop(capture):
    (lx, ly, w, h) = capture.landmarks.getLeftEyeBB()
    leftEye = capture.image[ly:ly+h, lx:lx+w]
    leftEyeMask = capture.mask[ly:ly+h, lx:lx+w]
    return np.array([leftEye, leftEyeMask, [lx, ly]])

def getRightEyeCrop(capture):
    (rx, ry, w, h) = capture.landmarks.getRightEyeBB()
    rightEye = capture.image[ry:ry+h, rx:rx+w]
    rightEyeMask = capture.mask[ry:ry+h, rx:rx+w]
    return np.array([rightEye, rightEyeMask, [rx, ry]])

def getRightEyeCoords(capture):
    return np.array(capture.landmarks.getRightEyeBB())

def getLeftEyeCoords(capture):
    return np.array(capture.landmarks.getLeftEyeBB())

def getMask(capture, coords):
    [x, y, w, h] = coords
    return capture.mask[y:y+h, x:x+w]

def getCrop(capture, coords):
    [x, y, w, h] = coords
    return capture.image[y:y+h, x:x+w]
    #wbImage = capture.getWhiteBalancedImageToD65()
    #return wbImage[y:y+h, x:x+w]

def getEyeCrops(capture):
    leftEyeCrop = getLeftEyeCrop(capture)
    rightEyeCrop = getRightEyeCrop(capture)
    return np.array([leftEyeCrop, rightEyeCrop])

def getEyeCropsInner(capture):
    (lx, ly, w, h) = capture.landmarks.getLeftEyeInnerBB()
    leftEye = capture.image[ly:ly+h, lx:lx+w]
    leftEyeMask = capture.mask[ly:ly+h, lx:lx+w]

    (rx, ry, w, h) = capture.landmarks.getRightEyeInnerBB()
    rightEye = capture.image[ry:ry+h, rx:rx+w]
    rightEyeMask = capture.mask[ry:ry+h, rx:rx+w]

    return np.array([[leftEye, leftEyeMask, [lx, ly]], [rightEye, rightEyeMask, [rx, ry]]])

def blur(img):
    return cv2.GaussianBlur(img, (9, 9), 0)
    #return cv2.bilateralFilter(img,15,75,75)
    #return cv2.medianBlur(img, 9)

def erode(img):
    kernel = np.ones((5, 5), np.uint16)
    #kernel = np.ones((9, 9), np.uint16)
    morph = cv2.morphologyEx(img, cv2.MORPH_CROSS, kernel)
    return morph

def getReflectionBB(maskedImg):
    img = np.clip(maskedImg * 255, 0, 255).astype('uint8')
    im2, contours, hierarchy = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    areas = [cv2.contourArea(c) for c in contours]
    if not areas:
        print("NO REFLECTION FOUND")
        raise NameError('NO REFLECTION FOUND')

    max_index = np.argmax(areas)
    contour = contours[max_index]

    return cv2.boundingRect(contour)

def maskTopValues(img):
    median = np.median(img)
    std = np.std(img)
    threshold = median + (3 * std)
    img[img < threshold] = 0
    return img

def extractBBMask(img, BB):
    x, y, w, h = BB
    mask = np.ones(img.shape).astype('bool')
    mask[y:y+h, x:x+w] = False
    img[mask] = 0
    return img

def maskReflectionBB(eyes, wb):
    for index, eye in enumerate(eyes):
        if eye.shape[0] * eye.shape[1] == 0:
            raise NameError('Cannot Find #{} Eye'.format(index))

    eyes = [colorTools.convert_sBGR_to_linearBGR_float_fast(eye) for eye in eyes]
    eyes = [colorTools.whitebalance_from_asShot_to_d65(eye, *wb) for eye in eyes]
    greyEyes = [np.mean(eye, axis=2) for eye in eyes]

    kernel = np.ones((3, 3), np.uint16)
    #Relient on second darkest reflection being AT LEAST 2x brighter than darkest
    secondDarkestImage, darkestImage = [cv2.morphologyEx(img, cv2.MORPH_CROSS, kernel) for img in greyEyes[-2:]]
    externalReflections = np.clip((2 * darkestImage) - secondDarkestImage, 0, 10)

    brightestClean = np.clip(greyEyes[0] - externalReflections, 0, 10)
    brightestTopMask = maskTopValues(brightestClean)
    reflectionBB = getReflectionBB(brightestTopMask)

    #x, y, w ,h = reflectionBB
    #crops = [eye[y:y + h, x:x + w] for eye in eyes]
    #cv2.imshow('eye Crops', np.hstack(crops))
    #cv2.waitKey(0)

    return reflectionBB

def cropToBB(image, bb):
    [x, y, w, h] = bb
    return image[y:y+h, x:x+w]

def getAnnotatedEyeStrip(leftReflectionBB, leftOffsetCoords, rightReflectionBB, rightOffsetCoords, capture):
    eyeStripBB = np.array(capture.landmarks.getEyeStripBB())

    eyeWidthPoints = np.append(capture.landmarks.getLeftEyeWidthPoints(), capture.landmarks.getRightEyeWidthPoints(), axis=0)

    eyeWidthPoints -= eyeStripBB[0:2]
    leftOffsetCoords[0:2] -= eyeStripBB[0:2]
    rightOffsetCoords[0:2] -= eyeStripBB[0:2]

    leftReflectionP1 = leftOffsetCoords[0:2] + leftReflectionBB[0:2]
    leftReflectionP2 = leftReflectionP1 + leftReflectionBB[2:4]
    leftReflectionP1 = tuple(leftReflectionP1)
    leftReflectionP2 = tuple(leftReflectionP2)

    rightReflectionP1 = rightOffsetCoords[0:2] + rightReflectionBB[0:2]
    rightReflectionP2 = rightReflectionP1 + rightReflectionBB[2:4]
    rightReflectionP1 = tuple(rightReflectionP1)
    rightReflectionP2 = tuple(rightReflectionP2)

    eyeStrip = np.copy(cropToBB(capture.image, eyeStripBB))

    for [x, y] in eyeWidthPoints:
        cv2.circle(eyeStrip, (x, y), 5, (0, 255, 0), -1)

    cv2.rectangle(eyeStrip, leftReflectionP1, leftReflectionP2, (0, 0, 255), 1)
    cv2.rectangle(eyeStrip, rightReflectionP1, rightReflectionP2, (0, 0, 255), 1)

    return eyeStrip

#Note: both parent and child offsets should originally be measured to the same origin
def calculateRelativeOffset(parentOffset, childOffset):
    return childOffset[0:2] - parentOffset[0:2]

def calculateRepresentativeReflectionPoint(reflectionPoints):
    return np.median(reflectionPoints, axis=0) # Maybe change to only take median of top 10% of brightnesses?

def extractReflectionPoints(reflectionBB, eyeCrop, eyeMask, ignoreMask):
    [x, y, w, h] = reflectionBB


    reflectionCrop = eyeCrop[y:y+h, x:x+w]
    reflectionCrop = colorTools.convert_sBGR_to_linearBGR_float_fast(reflectionCrop)
    reflectionMask = eyeMask[y:y+h, x:x+w]
    #cv2.imshow('Crop', reflectionCrop)
    #cv2.imshow('Mask', reflectionMask.astype('uint8') * 255)
    #cv2.waitKey(0)

    if ignoreMask:
        reflectionMask.fill(False)
    #reflectionMask.fill(False)
    reflectionPoints = reflectionCrop[np.logical_not(reflectionMask)]

    if (reflectionMask.shape[0] == 0) or (reflectionMask.shape[1] == 0):
        raise NameError('Zero width eye reflection')

    cleanPixelRatio = reflectionPoints.shape[0] / (reflectionMask.shape[0] * reflectionMask.shape[1])

    representativeReflectionPoint = calculateRepresentativeReflectionPoint(reflectionPoints)

    if cleanPixelRatio < 0.8:
        raise NameError('Not enough clean non-clipped pixels in eye reflections')

    return [representativeReflectionPoint, cleanPixelRatio]

def getEyeWidth(capture):
    [leftP1, leftP2] = capture.landmarks.getLeftEyeWidthPoints()
    [rightP1, rightP2] = capture.landmarks.getRightEyeWidthPoints()

    leftEyeWidth = max(leftP1[0], leftP2[0]) - min(leftP1[0], leftP2[0])
    rightEyeWidth = max(rightP1[0], rightP2[0]) - min(rightP1[0], rightP2[0])

    return (leftEyeWidth + rightEyeWidth) / 2

def getAverageScreenReflectionColor(captures, leftEyeOffsets, rightEyeOffsets, saveStep):
    wb = captures[0].getAsShotWhiteBalance()
    isSpecialCase = [capture.isNoFlash for capture in captures]

    leftEyeCoords = np.array([getLeftEyeCoords(capture) for capture in captures])
    minLeftWidth = np.min(leftEyeCoords[:, 2])
    minLeftHeight = np.min(leftEyeCoords[:, 3])
    leftEyeCoords = np.array([[x, y, minLeftWidth, minLeftHeight] for x, y, w, h, in leftEyeCoords])

    leftEyeCrops = [getCrop(capture, coords) for capture, coords in zip(captures, leftEyeCoords)]
    leftEyeMasks = [getMask(capture, coords) for capture, coords in zip(captures, leftEyeCoords)]

    leftEyeCrops, leftOffsets = cropTools.cropImagesToOffsets(leftEyeCrops, leftEyeOffsets)
    leftEyeMasks, offsets = cropTools.cropImagesToOffsets(leftEyeMasks, leftEyeOffsets)

    rightEyeCoords = np.array([getRightEyeCoords(capture) for capture in captures])
    minRightWidth = np.min(rightEyeCoords[:, 2])
    minRightHeight = np.min(rightEyeCoords[:, 3])
    rightEyeCoords = np.array([[x, y, minRightWidth, minRightHeight] for x, y, w, h, in rightEyeCoords])

    rightEyeCrops = [getCrop(capture, coords) for capture, coords in zip(captures, rightEyeCoords)]
    rightEyeMasks = [getMask(capture, coords) for capture, coords in zip(captures, rightEyeCoords)]

    rightEyeCrops, rightOffsets = cropTools.cropImagesToOffsets(rightEyeCrops, rightEyeOffsets)
    rightEyeMasks, offsets = cropTools.cropImagesToOffsets(rightEyeMasks, rightEyeOffsets)

    leftReflectionBB = maskReflectionBB(leftEyeCrops, wb)
    rightReflectionBB = maskReflectionBB(rightEyeCrops, wb)

    leftEyeCoords[:, 0:2] += leftOffsets
    rightEyeCoords[:, 0:2] += rightOffsets

    annotatedEyeStrips = [getAnnotatedEyeStrip(leftReflectionBB, leftEyeCoord, rightReflectionBB, rightEyeCoord, capture) for leftEyeCoord, rightEyeCoord, capture in zip(leftEyeCoords, rightEyeCoords, captures)]

    minWidth = min([annotatedEyeStrip.shape[1] for annotatedEyeStrip in annotatedEyeStrips])
    minHeight = min([annotatedEyeStrip.shape[0] for annotatedEyeStrip in annotatedEyeStrips])

    annotatedEyeStrips = [annotatedEyeStrip[0:minHeight, 0:minWidth] for annotatedEyeStrip in annotatedEyeStrips]

    stackedAnnotatedEyeStrips = np.vstack(annotatedEyeStrips)
    saveStep.saveReferenceImageLinearBGR(stackedAnnotatedEyeStrips, 'eyeStrips')

    #RESULTS ARE LINEAR
    leftReflectionStats = np.array([extractReflectionPoints(leftReflectionBB, eyeCrop, eyeMask, ignoreMask) for eyeCrop, eyeMask, ignoreMask in zip(leftEyeCrops, leftEyeMasks, isSpecialCase)])
    rightReflectionStats = np.array([extractReflectionPoints(rightReflectionBB, eyeCrop, eyeMask, ignoreMask) for eyeCrop, eyeMask, ignoreMask in zip(rightEyeCrops, rightEyeMasks, isSpecialCase)])

    averageReflections = (leftReflectionStats[:, 0] + rightReflectionStats[:, 0]) / 2

    averageReflections = [(averageReflection if np.all(averageReflection.astype('bool')) else (averageReflection + np.array([1, 1, 1]))) for averageReflection in averageReflections]

    print('AVERAGE NO, HALF, FULL REFLECTION :: {}'.format(averageReflections))

    #Whitebalance per flash and eye to get luminance levels... Maybe compare the average reflection values?
    #wbLeftReflections = np.vstack([colorTools.whitebalanceBGRPoints(leftReflection, averageReflection) for leftReflection, averageReflection in zip(leftReflectionStats[:, 0], averageReflections)])
    print('Left Reflections :: ' + str(leftReflectionStats[:, 0]))
    wbLeftReflections = np.vstack(leftReflectionStats[:, 0])
    #wbRightReflections = np.vstack([colorTools.whitebalanceBGRPoints(rightReflection, averageReflection) for rightReflection, averageReflection in zip(rightReflectionStats[:, 0], averageReflections)])
    print('Right Reflections :: ' + str(rightReflectionStats[:, 0]))
    wbRightReflections = np.vstack(rightReflectionStats[:, 0])

    #GET Luminance in reflection per flash and eye
    leftReflectionLuminances = [colorTools.getRelativeLuminance([leftReflection])[0] for leftReflection in wbLeftReflections]
    rightReflectionLuminances = [colorTools.getRelativeLuminance([rightReflection])[0] for rightReflection in wbRightReflections]

    eyeWidth = getEyeWidth(captures[0])

    if eyeWidth == 0:
        raise NameError('Zero value Eye Width')

    leftReflectionWidth, leftReflectionHeight = leftReflectionBB[2:4] / eyeWidth
    rightReflectionWidth, rightReflectionHeight = rightReflectionBB[2:4] / eyeWidth

    leftReflectionArea = leftReflectionWidth * leftReflectionHeight
    rightReflectionArea = rightReflectionWidth * rightReflectionHeight

    averageReflectionArea = (leftReflectionArea + rightReflectionArea) / 2

    if min(leftReflectionWidth, rightReflectionWidth) == 0:
        raise NameError('Zero value reflection Width')

    if min(leftReflectionHeight, rightReflectionHeight) == 0:
        raise NameError('Zero value reflection Height')

    reflectionWidthRatio = max(leftReflectionWidth, rightReflectionWidth) / min(leftReflectionWidth, rightReflectionWidth)
    reflectionHeightRatio = max(leftReflectionHeight, rightReflectionHeight) / min(leftReflectionHeight, rightReflectionHeight)

    if (reflectionWidthRatio > 1.5) or (reflectionHeightRatio > 1.25):
        raise NameError('Reflection Sizes are too different!')

    middleIndex = math.floor(len(captures) / 2)

    leftHalfReflectionLuminance = leftReflectionLuminances[middleIndex] * 2 #2x because we are using half
    rightHalfReflectionLuminance = rightReflectionLuminances[middleIndex] * 2 #2x because we are using half

    leftFluxish = leftReflectionArea * leftHalfReflectionLuminance
    rightFluxish = rightReflectionArea * rightHalfReflectionLuminance

    print('LEFT FLUXISH :: {} | AREA ::  {} | LUMINOSITY :: {}'.format(leftFluxish, leftReflectionArea, leftHalfReflectionLuminance))
    print('RIGHT FLUXISH :: {} | AREA ::  {} | LUMINOSITY :: {}'.format(rightFluxish, rightReflectionArea, rightHalfReflectionLuminance))

    return [averageReflections[middleIndex], averageReflectionArea, wbLeftReflections, wbRightReflections]

#def getAverageScreenReflectionColor(captures, saveStep):
#    wb = captures[0].getAsShotWhiteBalance()
#    isSpecialCase = [capture.isNoFlash for capture in captures]
#
#    leftEyeCoords = np.array([getLeftEyeCoords(capture) for capture in captures])
#    leftEyeCrops = [getCrop(capture, coords) for capture, coords in zip(captures, leftEyeCoords)]
#    leftEyeMasks = [getMask(capture, coords) for capture, coords in zip(captures, leftEyeCoords)]
#
#    rightEyeCoords = np.array([getRightEyeCoords(capture) for capture in captures])
#    rightEyeCrops = [getCrop(capture, coords) for capture, coords in zip(captures, rightEyeCoords)]
#    rightEyeMasks = [getMask(capture, coords) for capture, coords in zip(captures, rightEyeCoords)]
#
#    leftEyeCrops, leftEyeOffsets = alignImages.cropAndAlignEyes(leftEyeCrops, wb)
#    rightEyeCrops, rightEyeOffsets = alignImages.cropAndAlignEyes(rightEyeCrops, wb)
#
#    leftEyeMasks, offsets = cropTools.cropImagesToOffsets(leftEyeMasks, leftEyeOffsets)
#    rightEyeMasks, offsets = cropTools.cropImagesToOffsets(rightEyeMasks, rightEyeOffsets)
#
#    leftReflectionBB = maskReflectionBB(leftEyeCrops, wb)
#    rightReflectionBB = maskReflectionBB(rightEyeCrops, wb)
#
#    leftEyeCoords[:, 0:2] += leftEyeOffsets
#    rightEyeCoords[:, 0:2] += rightEyeOffsets
#
#    annotatedEyeStrips = [getAnnotatedEyeStrip(leftReflectionBB, leftEyeCoord, rightReflectionBB, rightEyeCoord, capture) for leftEyeCoord, rightEyeCoord, capture in zip(leftEyeCoords, rightEyeCoords, captures)]
#
#    stackedAnnotatedEyeStrips = np.vstack(annotatedEyeStrips)
#    saveStep.saveReferenceImageLinearBGR(stackedAnnotatedEyeStrips, 'eyeStrips')
#
#    #leftEyeMasksShow = np.hstack(leftEyeMasks)
#    #leftEyeCropsShow = np.hstack(leftEyeCrops).astype('uint8')
#    #leftEyeCropsShow[leftEyeMasksShow] = [255, 255, 255]
#
#    #rightEyeMasksShow = np.hstack(rightEyeMasks)
#    #rightEyeCropsShow = np.hstack(rightEyeCrops).astype('uint8')
#    #rightEyeCropsShow[rightEyeMasksShow] = [255, 255, 255]
#
#    #cv2.imshow('Left Eye Crops', leftEyeCropsShow)
#    #cv2.imshow('Right Eye Crops', rightEyeCropsShow)
#    #cv2.waitKey(0)
#
#    leftReflectionStats = np.array([extractReflectionPoints(leftReflectionBB, eyeCrop, eyeMask, ignoreMask) for eyeCrop, eyeMask, ignoreMask in zip(leftEyeCrops, leftEyeMasks, isSpecialCase)])
#    rightReflectionStats = np.array([extractReflectionPoints(rightReflectionBB, eyeCrop, eyeMask, ignoreMask) for eyeCrop, eyeMask, ignoreMask in zip(rightEyeCrops, rightEyeMasks, isSpecialCase)])
#
#    averageReflections = (leftReflectionStats[:, 0] + rightReflectionStats[:, 0]) / 2
#
#    averageReflections = [(averageReflection if np.all(averageReflection.astype('bool')) else (averageReflection + np.array([1, 1, 1]))) for averageReflection in averageReflections]
#
#    print('AVERAGE NO, HALF, FULL REFLECTION :: {}'.format(averageReflections))
#
#    #Whitebalance per flash and eye to get luminance levels... Maybe compare the average reflection values?
#    #wbLeftReflections = np.vstack([colorTools.whitebalanceBGRPoints(leftReflection, averageReflection) for leftReflection, averageReflection in zip(leftReflectionStats[:, 0], averageReflections)])
#    wbLeftReflections = np.vstack(leftReflectionStats[:, 0])
#    #wbRightReflections = np.vstack([colorTools.whitebalanceBGRPoints(rightReflection, averageReflection) for rightReflection, averageReflection in zip(rightReflectionStats[:, 0], averageReflections)])
#    wbRightReflections = np.vstack(rightReflectionStats[:, 0])
#
#    #GET Luminance in reflection per flash and eye
#    leftReflectionLuminances = [colorTools.getRelativeLuminance([leftReflection])[0] for leftReflection in wbLeftReflections]
#    rightReflectionLuminances = [colorTools.getRelativeLuminance([rightReflection])[0] for rightReflection in wbRightReflections]
#
#    eyeWidth = getEyeWidth(captures[0])
#
#    if eyeWidth == 0:
#        raise NameError('Zero value Eye Width')
#
#    leftReflectionWidth, leftReflectionHeight = leftReflectionBB[2:4] / eyeWidth
#    rightReflectionWidth, rightReflectionHeight = rightReflectionBB[2:4] / eyeWidth
#
#    leftReflectionArea = leftReflectionWidth * leftReflectionHeight
#    rightReflectionArea = rightReflectionWidth * rightReflectionHeight
#
#    averageReflectionArea = (leftReflectionArea + rightReflectionArea) / 2
#
#    if min(leftReflectionWidth, rightReflectionWidth) == 0:
#        raise NameError('Zero value reflection Width')
#
#    if min(leftReflectionHeight, rightReflectionHeight) == 0:
#        raise NameError('Zero value reflection Height')
#
#    reflectionWidthRatio = max(leftReflectionWidth, rightReflectionWidth) / min(leftReflectionWidth, rightReflectionWidth)
#    reflectionHeightRatio = max(leftReflectionHeight, rightReflectionHeight) / min(leftReflectionHeight, rightReflectionHeight)
#
#    if (reflectionWidthRatio > 1.5) or (reflectionHeightRatio > 1.25):
#        raise NameError('Reflection Sizes are too different!')
#
#    middleIndex = math.floor(len(captures) / 2)
#
#    leftHalfReflectionLuminance = leftReflectionLuminances[middleIndex] * 2 #2x because we are using half
#    rightHalfReflectionLuminance = rightReflectionLuminances[middleIndex] * 2 #2x because we are using half
#
#    leftFluxish = leftReflectionArea * leftHalfReflectionLuminance
#    rightFluxish = rightReflectionArea * rightHalfReflectionLuminance
#
#    print('LEFT FLUXISH :: {} | AREA ::  {} | LUMINOSITY :: {}'.format(leftFluxish, leftReflectionArea, leftHalfReflectionLuminance))
#    print('RIGHT FLUXISH :: {} | AREA ::  {} | LUMINOSITY :: {}'.format(rightFluxish, rightReflectionArea, rightHalfReflectionLuminance))
#
#    return [averageReflections[middleIndex], averageReflectionArea, wbLeftReflections, wbRightReflections]

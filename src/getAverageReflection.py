"""Extracts the reflections and sclera from each eye"""
import math
import cv2
import numpy as np
import colorTools
import cropTools
import imageTools

from logger import getLogger
LOGGER = getLogger(__name__, 'app')

def __erode(img):
    """Morphological Erosion Helper Function"""
    kernel = np.ones((5, 5), np.uint16)
    morph = cv2.morphologyEx(img, cv2.MORPH_CROSS, kernel)
    return morph

def __bbToMask(bb, imgShape):
    """Takes a BB and image shape and returns a mask in the dimensions of the image with the BB masked true"""
    img = np.zeros(imgShape)
    img[bb[1]:(bb[1]+bb[3]), bb[0]:(bb[0]+bb[2])] = 1
    return img.astype('bool')

def __getEyeWhiteMask(eyes, reflection_bb, wb):
    """Returns a mask for the Sclera of both the left and right eyes"""
    for index, eye in enumerate(eyes):
        if eye.shape[0] * eye.shape[1] == 0:
            raise ValueError('Cannot Find #{} Eye'.format(index))

    eyes = [colorTools.convert_sBGR_to_linearBGR_float(eye) for eye in eyes]
    eyes = [colorTools.whitebalance_from_asShot_to_d65(eye, *wb) for eye in eyes]

    primarySpecularReflectionBB = np.copy(reflection_bb)
    primarySpecularReflectionBB[0:2] -= reflection_bb[2:4]
    primarySpecularReflectionBB[2:4] *= 3
    primarySpecularReflectionMask = __bbToMask(primarySpecularReflectionBB, eyes[0][:, :, 0].shape)

    eye_blur = [cv2.blur(eye, (5, 5)) for eye in eyes]
    eyes_hsv = [colorTools.naiveBGRtoHSV(eye) for eye in eye_blur]
    eye_s = []
    for eye in eyes_hsv:
        sat = 1 - eye[:, :, 1]
        val = eye[:, :, 2]

        sat[primarySpecularReflectionMask] = 0
        val[primarySpecularReflectionMask] = 0

        sat = sat * val

        eye[:, :, 0] = sat
        eye[:, :, 1] = sat
        eye[:, :, 2] = sat
        eye_s.append(eye)

    diff = eye_s[0] - eye_s[-1]
    diff = np.clip(diff, 0, 255)
    min_diff = np.min(diff)
    max_diff = np.max(diff)

    scaled_diff = (diff - min_diff) / (max_diff - min_diff)
    scaled_diff = np.clip(scaled_diff * 255, 0, 255).astype('uint8')

    _, thresh = cv2.threshold(scaled_diff[:, :, 0], 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)

    kernel = np.ones((9, 9), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    areas = [cv2.contourArea(c) for c in contours]
    totalArea = thresh.shape[0] * thresh.shape[1]
    areaPercents = np.array(areas) / totalArea
    areasMask = areaPercents > 0.01

    possibleContourIndexes = np.arange(len(contours))[areasMask]

    medians = []
    for index in possibleContourIndexes:
        target = np.zeros(thresh.shape, dtype='uint8')
        mask = cv2.drawContours(target, contours, index, 255, cv2.FILLED)
        med = np.median(eye_s[0][mask.astype('bool')])
        medians.append(med)

    max_index = possibleContourIndexes[np.argmax(medians)]

    target = np.zeros(thresh.shape, dtype='uint8')
    sclera_mask = cv2.drawContours(target, contours, max_index, 255, cv2.FILLED)


    masked_scaled_diff = scaled_diff[:, :, 0]
    masked_scaled_diff[np.logical_not(sclera_mask)] = 0
    median = np.median(masked_scaled_diff[sclera_mask.astype('bool')])

    masked_scaled_diff = cv2.GaussianBlur(masked_scaled_diff, (5, 5), 0)
    _, thresh2 = cv2.threshold(masked_scaled_diff, median, 255, cv2.THRESH_BINARY)#+cv2.THRESH_OTSU)

    thresh2 = cv2.morphologyEx(thresh2, cv2.MORPH_OPEN, kernel)
    thresh2 = cv2.morphologyEx(thresh2, cv2.MORPH_CLOSE, kernel)

    contoursRefined, _ = cv2.findContours(thresh2, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    areasRefined = [cv2.contourArea(c) for c in contoursRefined]
    maxIndex = np.argmax(areasRefined)

    target = np.zeros(thresh.shape, dtype='uint8')
    maskRefined = cv2.drawContours(target, contoursRefined, maxIndex, 255, cv2.FILLED).astype('bool')

    return [maskRefined, contoursRefined[maxIndex]]

def __getReflectionBB(eyes, wb):
    """Returns the BB of the device screen specular reflection in the eye"""
    for index, eye in enumerate(eyes):
        if eye.shape[0] * eye.shape[1] == 0:
            raise ValueError('Cannot Find #{} Eye'.format(index))

    eyes = [colorTools.convert_sBGR_to_linearBGR_float(eye) for eye in eyes]
    eyes = [colorTools.whitebalance_from_asShot_to_d65(eye, *wb) for eye in eyes]
    #greyEyes = np.array([np.mean(eye, axis=2) for eye in eyes])
    greyEyes = np.array([np.mean(eye[:, :, 0:2], axis=2) for eye in eyes])


    eyeCropY1 = int(0.15 * greyEyes[0].shape[0])
    eyeCropY2 = int(0.85 * greyEyes[0].shape[0])

    eyeCropX1 = int(0.25 * greyEyes[0].shape[1])
    eyeCropX2 = int(0.75 * greyEyes[0].shape[1])

    croppedGreyEyes = np.array([img[eyeCropY1:eyeCropY2, eyeCropX1:eyeCropX2] for img in greyEyes])

    totalChange = np.sum(croppedGreyEyes[:-1] - croppedGreyEyes[1:], axis=0)
    totalChange = totalChange / np.max(totalChange)

    kernel = np.ones((9, 9), np.uint8)

    totalChangeMask = totalChange > (np.median(totalChange) + np.std(totalChange))
    totalChangeMaskEroded = cv2.erode(totalChangeMask.astype('uint8'), kernel, iterations=1)
    totalChangeMaskOpened = cv2.dilate(totalChangeMaskEroded.astype('uint8'), kernel, iterations=1)

    totalChangeMaskOpenedDilated = cv2.dilate(totalChangeMaskOpened.astype('uint8'), kernel, iterations=1)

    eyeLap = [cv2.Laplacian(imageTools.stretchHistogram(img, [2, 10]), cv2.CV_64F) for img in croppedGreyEyes]
    eyeLap = eyeLap / np.max(eyeLap)

    totalChangeLap = cv2.Laplacian(totalChange, cv2.CV_64F)
    totalChangeLap = totalChangeLap / np.max(totalChangeLap)

    #im2, contours, hierarchy = cv2.findContours(totalChangeMaskOpenedDilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours, _ = cv2.findContours(totalChangeMaskOpenedDilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    #areas = [cv2.contourArea(c) for c in contours]

    highScore = 0
    eyeReflectionBB = None
    #gradientMask = None
    for index, contour in enumerate(contours):
        target = np.zeros(totalChangeMaskOpenedDilated.shape, dtype='uint8')
        drawn = cv2.drawContours(target, contours, index, 255, cv2.FILLED)
        drawn = cv2.morphologyEx(drawn, cv2.MORPH_GRADIENT, kernel)

        borderPoints = totalChangeLap[drawn.astype('bool')]

        if len(borderPoints) > 10:
            borderPointsMedian = np.median(np.sort(borderPoints)[-10:])

            if borderPointsMedian > highScore:
                highScore = borderPointsMedian
                eyeReflectionBB = list(cv2.boundingRect(contour))

    if eyeReflectionBB is None:
        raise ValueError('Could Not Find Reflection BB')

    eyeReflectionBB[0] += eyeCropX1
    eyeReflectionBB[1] += eyeCropY1
    return np.array(eyeReflectionBB)

def __getAnnotatedEyeStrip(leftEyeFeatures, rightEyeFeatures):
    """For Sanity Checking. Return an image with the left and right eyes of each capture with the sclera and device screen reflection over layed"""

    leftReflectionBB, leftScleraContour, leftEyeCrop = leftEyeFeatures
    rightReflectionBB, rightScleraContour, rightEyeCrop = rightEyeFeatures

    leftReflectionP1 = leftReflectionBB[0:2]
    leftReflectionP2 = leftReflectionP1 + leftReflectionBB[2:4]
    leftReflectionP1 = tuple(leftReflectionP1)
    leftReflectionP2 = tuple(leftReflectionP2)

    rightReflectionP1 = rightReflectionBB[0:2]
    rightReflectionP2 = rightReflectionP1 + rightReflectionBB[2:4]
    rightReflectionP1 = tuple(rightReflectionP1)
    rightReflectionP2 = tuple(rightReflectionP2)

    leftEyeCropCopy = np.copy(leftEyeCrop)
    rightEyeCropCopy = np.copy(rightEyeCrop)

    cv2.rectangle(leftEyeCropCopy, leftReflectionP1, leftReflectionP2, (0, 0, 255), 1)
    cv2.rectangle(rightEyeCropCopy, rightReflectionP1, rightReflectionP2, (0, 0, 255), 1)
    #mask =  cv2.drawContours(target, contours, index, 255, cv2.FILLED)
    cv2.drawContours(leftEyeCropCopy, [leftScleraContour], 0, (0, 255, 0), 1)
    cv2.drawContours(rightEyeCropCopy, [rightScleraContour], 0, (0, 255, 0), 1)

    canvasShape = np.max([leftEyeCrop.shape, rightEyeCrop.shape], axis=0)

    originLeft_Y_start = math.floor((canvasShape[0] - leftEyeCropCopy.shape[0]) / 2) #Center vertically
    originLeft_Y_end = -1 * math.ceil((canvasShape[0] - leftEyeCropCopy.shape[0]) / 2) #Center vertically
    originLeft_Y_end = originLeft_Y_end if originLeft_Y_end != 0 else leftEyeCropCopy.shape[0]
    originLeft_X = leftEyeCropCopy.shape[1]

    originRight_Y_start = math.floor((canvasShape[0] - rightEyeCropCopy.shape[0]) / 2) #Center vertically
    originRight_Y_end = -1 * math.ceil((canvasShape[0] - rightEyeCropCopy.shape[0]) / 2) #Center vertically
    originRight_Y_end = originRight_Y_end if originRight_Y_end != 0 else rightEyeCropCopy.shape[0]
    originRight_X = canvasShape[1] - rightEyeCropCopy.shape[1]

    leftEyeCanvas = np.zeros(canvasShape, dtype='uint8')
    rightEyeCanvas = np.zeros(canvasShape, dtype='uint8')

    leftEyeCanvas[originLeft_Y_start:originLeft_Y_end, 0:originLeft_X] = leftEyeCropCopy
    rightEyeCanvas[originRight_Y_start:originRight_Y_end, originRight_X:] = rightEyeCropCopy

    eyeStrip = np.hstack([rightEyeCanvas, leftEyeCanvas]) #Backwards because left refers to the user's left eye

    return eyeStrip

#Note: both parent and child offsets should originally be measured to the same origin
#def calculateRelativeOffset(parentOffset, childOffset):
#    return childOffset[0:2] - parentOffset[0:2]

def __calculateRepresentativeReflectionPoint(reflectionPoints):
    """Calculate the point that should be closest to the true refletion color"""
    numPoints = reflectionPoints.shape[0]

    topTenPercent = int(numPoints / 10) * -1

    #Only take the median of the top 10% of subpixels
    topMedianBlue = np.median(np.array(sorted(reflectionPoints[:, 0]))[topTenPercent:])
    topMedianGreen = np.median(np.array(sorted(reflectionPoints[:, 1]))[topTenPercent:])
    topMedianRed = np.median(np.array(sorted(reflectionPoints[:, 2]))[topTenPercent:])

    newRepValue = [topMedianBlue, topMedianGreen, topMedianRed]
    return np.array(newRepValue)

def __extractScleraPoints(eyes, scleraMask):
    """Return the points in the sclera"""
    eyePoints = [eye[scleraMask] for eye in eyes]
    greyEyePoints = [np.mean(eye, axis=1) for eye in eyePoints]
    topTenthIndex = int(len(greyEyePoints[0]) * 0.9)
    brightestThresholds = [math.floor(sorted(points)[topTenthIndex]) for points in greyEyePoints]
    brightestPointsMasks = [greyPoints > threshold for greyPoints, threshold in zip(greyEyePoints, brightestThresholds)]
    brightestMeans = [np.mean(points[brightestMask], axis=0) for points, brightestMask in zip(eyePoints, brightestPointsMasks)]
    #print('eye points :: {}'.format(brightestThresholds))
    print('Means :: {}'.format(brightestMeans))
    return np.array(brightestMeans) / 255

def __extractReflectionPoints(reflectionBB, eyeCrop):
    """Return the points in the device screen reflection"""
    [x, y, w, h] = reflectionBB

    reflectionCrop = eyeCrop[y:y+h, x:x+w]
    reflectionCrop = colorTools.convert_sBGR_to_linearBGR_float(reflectionCrop)

    #Add together each subpixel mask for each pixel. if the value is greater than 0, one of the subpixels was clipping
    #Just mask = isClipping(Red) or isClipping(Green) or isClipping(Blue)
    clippingMask = np.sum(reflectionCrop == 1.0, axis=2) > 0

    if (reflectionCrop.shape[0] == 0) or (reflectionCrop.shape[1] == 0):
        raise ValueError('Zero width eye reflection')

    cleanPixels = np.sum(np.logical_not(clippingMask).astype('uint8'))
    cleanPixelRatio = cleanPixels / (clippingMask.shape[0] * clippingMask.shape[1])

    if cleanPixelRatio < 0.95:
        raise ValueError('Not enough clean non-clipped pixels in eye reflections')

    threshold = 1/4

    stretchedBlueReflectionCrop = imageTools.simpleStretchHistogram(reflectionCrop[:, :, 0])
    blueMask = stretchedBlueReflectionCrop > threshold

    stretchedGreenReflectionCrop = imageTools.simpleStretchHistogram(reflectionCrop[:, :, 1])
    greenMask = stretchedGreenReflectionCrop > threshold

    stretchedRedReflectionCrop = imageTools.simpleStretchHistogram(reflectionCrop[:, :, 2])
    redMask = stretchedRedReflectionCrop > threshold

    #Mask out any pixels where each Red, Green, and Blue are not above the threshold
    reflectionMask = np.logical_not(np.logical_or(np.logical_or(blueMask, greenMask), redMask))
    inv_reflectionMask = np.logical_not(reflectionMask)
    contours, _ = cv2.findContours(inv_reflectionMask.astype('uint8'), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    areas = [cv2.contourArea(c) for c in contours]
    max_index = np.argmax(areas)

    boundingRectangle = np.array(list(cv2.boundingRect(contours[max_index])))
    boundingRectangle[0] += reflectionBB[0]
    boundingRectangle[1] += reflectionBB[1]

    showMask = np.stack([reflectionMask.astype('uint8'), reflectionMask.astype('uint8'), reflectionMask.astype('uint8')], axis=2) * 255
    maskedReflections = np.copy(reflectionCrop)
    maskedReflections[reflectionMask] = [0, 0, 0]
    stacked = np.vstack([np.clip(reflectionCrop * 255, 0, 255).astype('uint8'), showMask, np.clip(maskedReflections * 255, 0, 255).astype('uint8')])

    reflectionPoints = reflectionCrop[np.logical_not(reflectionMask)]

    representativeReflectionPoint = __calculateRepresentativeReflectionPoint(reflectionPoints)

    return [representativeReflectionPoint, stacked, boundingRectangle]

def getEyeWidth(capture):
    """Returns the average width of the eye"""
    [leftP1, leftP2] = capture.landmarks.getLeftEyeWidthPoints()
    [rightP1, rightP2] = capture.landmarks.getRightEyeWidthPoints()

    leftEyeWidth = max(leftP1[0], leftP2[0]) - min(leftP1[0], leftP2[0])
    rightEyeWidth = max(rightP1[0], rightP2[0]) - min(rightP1[0], rightP2[0])

    return (leftEyeWidth + rightEyeWidth) / 2

def getAverageScreenReflectionColor(captures, leftEyeOffsets, rightEyeOffsets, state):
    """Returns data retreived from the users eye including Screen reflection color, reflection size, and scelra color and luminance"""
    wb = captures[0].whiteBalance

    leftEyeCrops = cropTools.getEyeImagesCroppedToOffsets(captures, leftEyeOffsets, 'left')
    leftReflectionBB = __getReflectionBB(leftEyeCrops, wb)
    leftEyeWhiteMask, leftEyeWhiteContour = __getEyeWhiteMask(leftEyeCrops, leftReflectionBB, wb)
    leftEyeScleraPoints = __extractScleraPoints(leftEyeCrops, leftEyeWhiteMask)

    rightEyeCrops = cropTools.getEyeImagesCroppedToOffsets(captures, rightEyeOffsets, 'right')
    rightReflectionBB = __getReflectionBB(rightEyeCrops, wb)
    rightEyeWhiteMask, rightEyeWhiteContour = __getEyeWhiteMask(rightEyeCrops, rightReflectionBB, wb)
    rightEyeScleraPoints = __extractScleraPoints(rightEyeCrops, rightEyeWhiteMask)

    #RESULTS ARE IN LINEAR COLORSPACE
    #Left Reflection -> lr, Right Reflection -> rr
    lrChosenPoints, lrStacked, lrBoundingRectangle = np.array([__extractReflectionPoints(leftReflectionBB, eyeCrop) for eyeCrop in leftEyeCrops]).T
    rrChosenPoints, rrStacked, rrBoundingRectangle = np.array([__extractReflectionPoints(rightReflectionBB, eyeCrop) for eyeCrop in rightEyeCrops]).T

    refinedLeftReflectionBBs = np.vstack(lrBoundingRectangle)
    refinedRightReflectionBBs = np.vstack(rrBoundingRectangle)

    #Check if any specular reflection is significantly (defined by TOLERANCE) larger or smaller than the others
    TOLERANCE = 0.20
    leftReflectionBBAreas = [bb[2] * bb[3] for bb in refinedLeftReflectionBBs]
    leftReflectionBBAreasMedian = np.median(leftReflectionBBAreas)
    leftMask = np.abs(leftReflectionBBAreas - leftReflectionBBAreasMedian) > (TOLERANCE * leftReflectionBBAreasMedian)

    rightReflectionBBAreas = [bb[2] * bb[3] for bb in refinedRightReflectionBBs]
    rightReflectionBBAreasMedian = np.median(rightReflectionBBAreas)
    rightMask = np.abs(rightReflectionBBAreas - rightReflectionBBAreasMedian) > (TOLERANCE * rightReflectionBBAreasMedian)

    #If either eye has an outlying reflection size, label it as blurry
    #  Often caused by a moving screen (user w/ Shakey hands, unprepared, etc) . It will create a smear effect which makes the reflection appear larger
    blurryMask = np.logical_and(leftMask, rightMask)

    #Save some reference images for spot/sanity checking later
    leftEyeFeatures = [[leftReflectionBBrefined, leftEyeWhiteContour, leftEyeCrop] for leftReflectionBBrefined, leftEyeCrop in zip(refinedLeftReflectionBBs, leftEyeCrops)]
    rightEyeFeatures = [[rightReflectionBBrefined, rightEyeWhiteContour, rightEyeCrop] for rightReflectionBBrefined, rightEyeCrop in zip(refinedRightReflectionBBs, rightEyeCrops)]

    annotatedEyeStrips = [__getAnnotatedEyeStrip(leftEye, rightEye) for leftEye, rightEye in zip(leftEyeFeatures, rightEyeFeatures)]
    stackedAnnotatedEyeStrips = np.vstack(annotatedEyeStrips)
    state.saveReferenceImageBGR(stackedAnnotatedEyeStrips, 'eyeStrips')

    leftReflectionImages = np.hstack(lrStacked)
    state.saveReferenceImageBGR(leftReflectionImages, 'Left Reflections')

    rightReflectionImages = np.hstack(rrStacked)
    state.saveReferenceImageBGR(rightReflectionImages, 'Right Reflections')

    leftReflections = np.vstack(lrChosenPoints)
    rightReflections = np.vstack(rrChosenPoints)

    #GET Luminance in reflection per flash and eye
    leftReflectionLuminances = [colorTools.getRelativeLuminance([leftReflection])[0] for leftReflection in leftReflections]
    rightReflectionLuminances = [colorTools.getRelativeLuminance([rightReflection])[0] for rightReflection in rightReflections]

    eyeWidth = getEyeWidth(captures[0])

    if eyeWidth == 0:
        raise ValueError('Zero Value Eye Width')

    #Put reflection width and height in terms of eye width. Used to approximately compensate for the size of the device illumiating face
    leftReflectionWidth, leftReflectionHeight = np.mean(refinedLeftReflectionBBs[:, 2:4], axis=0) / eyeWidth
    rightReflectionWidth, rightReflectionHeight = np.mean(refinedRightReflectionBBs[:, 2:4], axis=0) / eyeWidth

    leftReflectionArea = leftReflectionWidth * leftReflectionHeight
    rightReflectionArea = rightReflectionWidth * rightReflectionHeight

    averageReflectionArea = (leftReflectionArea + rightReflectionArea) / 2

    if min(leftReflectionWidth, rightReflectionWidth) == 0:
        raise ValueError('Zero value reflection Width')

    if min(leftReflectionHeight, rightReflectionHeight) == 0:
        raise ValueError('Zero value reflection Height')

    reflectionWidthRatio = max(leftReflectionWidth, rightReflectionWidth) / min(leftReflectionWidth, rightReflectionWidth)
    reflectionHeightRatio = max(leftReflectionHeight, rightReflectionHeight) / min(leftReflectionHeight, rightReflectionHeight)

    if (reflectionWidthRatio > 1.5) or (reflectionHeightRatio > 1.25):
        #raise ValueError('Reflection Sizes are too different!')
        print('Reflection Sizes are too different!')

    middleIndex = math.floor(len(captures) / 2)

    leftHalfReflectionLuminance = leftReflectionLuminances[middleIndex] * 2 #2x because we are using the half illuminated capture
    rightHalfReflectionLuminance = rightReflectionLuminances[middleIndex] * 2 #2x because we are using the half illuminated capture

    leftIlluminantMag = leftReflectionArea * leftHalfReflectionLuminance
    rightIlluminantMag = rightReflectionArea * rightHalfReflectionLuminance

    LOGGER.info('LEFT ILLUMINANTE MAG :: %s | AREA ::  %s | LUMINOSITY :: %s', leftIlluminantMag, leftReflectionArea, leftHalfReflectionLuminance)
    LOGGER.info('RIGHT ILLUMINANTE MAG :: %s | AREA ::  %s | LUMINOSITY :: %s', rightIlluminantMag, rightReflectionArea, rightHalfReflectionLuminance)

    leftEye = [leftReflections, leftEyeScleraPoints]
    rightEye = [rightReflections, rightEyeScleraPoints]

    return [leftEye, rightEye, averageReflectionArea, blurryMask]

import utils
import saveStep
import cv2
import numpy as np
import colorTools
import alignImages
import cropTools
import colorsys

def getEyeCrops(capture):
    (lx, ly, w, h) = capture.landmarks.getLeftEyeBB()
    leftEye = capture.image[ly:ly+h, lx:lx+w]

    (rx, ry, w, h) = capture.landmarks.getRightEyeBB()
    rightEye = capture.image[ry:ry+h, rx:rx+w]

    return [[leftEye, [lx, ly]], [rightEye, [rx, ry]]]

def getEyeRegionCrops(capture):
    (x, y, w, h) = capture.landmarks.getLeftEyeRegionBB()
    leftEye = capture.image[y:y+h, x:x+w]

    (x, y, w, h) = capture.landmarks.getRightEyeRegionBB()
    rightEye = capture.image[y:y+h, x:x+w]

    return [leftEye, rightEye]

def blur(img):
    return cv2.GaussianBlur(img, (9, 9), 0)
    #return cv2.bilateralFilter(img,15,75,75)
    #return cv2.medianBlur(img, 9)

def erode(img):
    kernel = np.ones((5, 5), np.uint16)
    morph = cv2.morphologyEx(img, cv2.MORPH_CROSS, kernel)
    return morph




def getReflectionBB(mask):
    img = mask.astype('uint8') * 255
    im2, contours, hierarchy = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    areas = [cv2.contourArea(c) for c in contours]
    max_index = np.argmax(areas)
    contour = contours[max_index]

    return cv2.boundingRect(contour)

def maskReflectionBB(noFlash, halfFlash, fullFlash):
    ogHalfFlash = np.sum(halfFlash, axis=2)
    #ogNoFlash = np.sum(noFlash, axis=2)

    noFlashGrey = np.sum(blur(noFlash), axis=2)
    halfFlashGrey = np.sum(blur(halfFlash), axis=2)
    fullFlashGrey = np.sum(blur(fullFlash), axis=2)

    #cv2.imshow('Grey Blurred', (fullFlashGrey / 3).astype('uint8'))

    halfFlashGrey = np.clip(halfFlashGrey.astype('int32') - noFlashGrey, 0, (256 * 3))
    fullFlashGrey = np.clip(fullFlashGrey.astype('int32') - noFlashGrey, 0, (256 * 3))

    halfFlashGrey = erode(halfFlashGrey)
    fullFlashGrey = erode(fullFlashGrey)
    #cv2.imshow('Grey Eroded', (fullFlashGrey / 3).astype('uint8'))

    noFlashMin = np.min(noFlashGrey)
    noFlashMask = noFlashGrey > (noFlashMin + 10)

    halfFlashMedian = np.median(halfFlashGrey)
    halfFlashStd = np.std(halfFlashGrey)
    halfFlashUpper = halfFlashMedian + (3 * halfFlashStd)
    halfFlashMask = halfFlashGrey > halfFlashUpper

    fullFlashMedian = np.median(fullFlashGrey)
    fullFlashStd = np.std(fullFlashGrey)
    fullFlashUpper = fullFlashMedian + (2 * fullFlashStd)
    fullFlashMask = fullFlashGrey > fullFlashUpper

    roughFlashMask = np.logical_and(halfFlashMask, fullFlashMask)
    roughFlashMask = np.logical_and(roughFlashMask, np.logical_not(noFlashMask))

    #cv2.imshow('rough flash mask', roughFlashMask.astype('uint8') * 255)
    (x, y, w, h) = getReflectionBB(roughFlashMask)
    roughReflectionCrop = ogHalfFlash[y:y+h, x:x+w]
    #cv2.imshow('rough flash crop', (roughReflectionCrop / 3).astype('uint8'))

    #averageValueByColumn = np.sum(roughReflectionCrop, axis=0) / roughReflectionCrop.shape[0]
    medianValueByColumn = np.median(roughReflectionCrop, axis=0)
    #np.flip(averageValueByColumn, 0)
    #averageValueByRow = np.sum(roughReflectionCrop, axis=1) / roughReflectionCrop.shape[1]
    medianValueByRow = np.median(roughReflectionCrop, axis=1)
    #np.flip(averageValueByRow, 0)


    tolerance = 0.4
    columnMedianCuttoff = np.median(medianValueByColumn)
    columnMedianCuttoff -= (tolerance * columnMedianCuttoff)

    rowMedianCuttoff = np.median(medianValueByRow)
    rowMedianCuttoff -= (tolerance * rowMedianCuttoff)

    #print('Median Value By Column :: ' + str(medianValueByColumn) + ' | ' + str(columnMedianCuttoff))
    #print('Median Value By Row :: ' + str(medianValueByRow) + ' | ' + str(rowMedianCuttoff))

    xMask = medianValueByColumn >= columnMedianCuttoff
    yMask = medianValueByRow >= rowMedianCuttoff

    #print('X Mask :: ' + str(xMask))
    #print('Y Mask :: ' + str(yMask))

    xMask = xMask.reshape(1, xMask.shape[0])
    yMask = yMask.reshape(yMask.shape[0], 1)

    refinedMask = np.dot(yMask, xMask)

    #print('Refined Mask :: ' + str(refinedMask))

    #refinedMask = roughReflectionCrop > 100
    (x1, y1, w1, h1) = getReflectionBB(refinedMask)
    refinedReflectionCrop = roughReflectionCrop[y1:y1+h1, x1:x1+w1]

    #cv2.imshow('refined flash crop', (refinedReflectionCrop / 3).astype('uint8'))
    #cv2.waitKey(0)
    return [(x + x1), (y + y1), w1, h1]


#def stretchBW(image):
#    #median = np.median(image)
#    #sd = np.std(image)
#    #lower = median - (3 * sd)
#    #lower = lower if lower > 0 else 0
#    #upper = median + (3 * sd)
#    #upper = upper if upper < 256 else 255
#
#    lower = np.min(image)
#    upper = np.max(image)
#
#    #print('MEDIAN :: ' + str(median))
#    #print('SD :: ' + str(sd))
#    #print('LOWER :: ' + str(lower))
#    #print('UPPER :: ' + str(upper))
#
#    #bounds = np.copy(gray)
#    #bounds[bounds < lower] = lower
#    #bounds[bounds > upper] = upper
#
#    numerator = (image - lower).astype('int32')
#    denominator = (upper - lower).astype('int32')
#    #stretched = (numerator.astype('int32') / denominator.astype('int32'))
#    stretched = (numerator / denominator)
#    #stretched = np.clip(stretched * 255, 0, 255).astype('uint8')
#    stretched = np.clip(stretched * 255, 0, 255).astype('uint8')
#    return stretched

#def getEyeWidths(fullFlashCapture, leftEyeOffsets, leftEyeGreyReflectionMask, rightEyeOffsets, rightEyeGreyReflectionMask):
#    fullFlashEyeStripCoords = np.array(fullFlashCapture.landmarks.getEyeStripBB())
#
#    eyeStripCoordDiff_left = np.array(fullFlashLeftEyeCoord) - fullFlashEyeStripCoords[0:2]
#    eyeStripCoordDiff_right = np.array(fullFlashRightEyeCoord) - fullFlashEyeStripCoords[0:2]
#
#    (x, y, w, h) = fullFlashEyeStripCoords
#    fullFlashEyeStripXStart = x
#    fullFlashEyeStripXEnd = x + w
#    fullFlashEyeStrip = fullFlashCapture.image[y:y+h, x:x+w]
#
#    eyeStripCoordDiff_left += leftEyeOffsets[2]
#    eyeStripCoordDiff_right += rightEyeOffsets[2]

def getAverageScreenReflectionColor(noFlashCapture, halfFlashCapture, fullFlashCapture, saveStep):
    [[noFlashLeftEyeCrop, noFlashLeftEyeCoord], [noFlashRightEyeCrop, noFlashRightEyeCoord]] = getEyeCrops(noFlashCapture)
    [[halfFlashLeftEyeCrop, halfFlashLeftEyeCoord], [halfFlashRightEyeCrop, halfFlashRightEyeCoord]] = getEyeCrops(halfFlashCapture)
    [[fullFlashLeftEyeCrop, fullFlashLeftEyeCoord], [fullFlashRightEyeCrop, fullFlashRightEyeCoord]] = getEyeCrops(fullFlashCapture)

    [noFlashLeftEyeRegionCrop, noFlashRightEyeRegionCrop] = getEyeRegionCrops(noFlashCapture)
    [halfFlashLeftEyeRegionCrop, halfFlashRightEyeRegionCrop] = getEyeRegionCrops(halfFlashCapture)
    [fullFlashLeftEyeRegionCrop, fullFlashRightEyeRegionCrop] = getEyeRegionCrops(fullFlashCapture)

    [leftEyeOffsets, [noFlashLeftEyeCrop, halfFlashLeftEyeCrop, fullFlashLeftEyeCrop]] = alignImages.cropAndAlignEyes(noFlashLeftEyeCrop, halfFlashLeftEyeCrop, fullFlashLeftEyeCrop)
    [rightEyeOffsets, [noFlashRightEyeCrop, halfFlashRightEyeCrop, fullFlashRightEyeCrop]] = alignImages.cropAndAlignEyes(noFlashRightEyeCrop, halfFlashRightEyeCrop, fullFlashRightEyeCrop)

    [noFlashLeftEyeRegionCrop, halfFlashLeftEyeRegionCrop, fullFlashLeftEyeRegionCrop] = cropTools.cropImagesToOffsets([noFlashLeftEyeRegionCrop, halfFlashLeftEyeRegionCrop, fullFlashLeftEyeRegionCrop], np.array(leftEyeOffsets))
    #[noFlashLeftEyeRegionCrop, halfFlashLeftEyeRegionCrop, fullFlashLeftEyeRegionCrop] = [noFlashLeftEyeCrop, halfFlashLeftEyeCrop, fullFlashLeftEyeCrop]
    [noFlashRightEyeRegionCrop, halfFlashRightEyeRegionCrop, fullFlashRightEyeRegionCrop] = cropTools.cropImagesToOffsets([noFlashRightEyeRegionCrop, halfFlashRightEyeRegionCrop, fullFlashRightEyeRegionCrop], np.array(rightEyeOffsets))
    #[noFlashRightEyeRegionCrop, halfFlashRightEyeRegionCrop, fullFlashRightEyeRegionCrop] = [noFlashRightEyeCrop, halfFlashRightEyeCrop, fullFlashRightEyeCrop]

    
    leftEyeBB = fullFlashCapture.landmarks.getLeftEyeBB()
    rightEyeBB = fullFlashCapture.landmarks.getRightEyeBB()

    leftRemainder = np.clip(np.abs((2 * halfFlashLeftEyeRegionCrop.astype('int32')) - (fullFlashLeftEyeRegionCrop.astype('int32') + noFlashLeftEyeRegionCrop.astype('int32'))), 0, 255).astype('uint8')
    rightRemainder = np.clip(np.abs((2 * halfFlashRightEyeRegionCrop.astype('int32')) - (fullFlashRightEyeRegionCrop.astype('int32') + noFlashRightEyeRegionCrop.astype('int32'))), 0, 255).astype('uint8')

    leftRemainderMask = np.max(leftRemainder, axis=2) > 6
    leftRemainderMask = leftRemainderMask.astype('uint8') * 255
    #leftRemainderMask = np.stack((leftRemainderMask, leftRemainderMask, leftRemainderMask), axis=-1)
    rightRemainderMask = np.max(rightRemainder, axis=2) > 6
    rightRemainderMask = rightRemainderMask.astype('uint8') * 255
    #rightRemainderMask = np.stack((rightRemainderMask, rightRemainderMask, rightRemainderMask), axis=-1)

    #cv2.imshow('left linearity', np.hstack((leftRemainder, leftRemainderMask)))
    #cv2.imshow('right linearity', np.hstack((rightRemainder, rightRemainderMask)))
    #cv2.waitKey(0)
    saveStep.saveReferenceImageBGR(leftRemainderMask, 'Left Remainder Eye Mask')
    saveStep.saveReferenceImageBGR(rightRemainderMask, 'Right Remainder Eye Mask')

    fullFlashEyeStripCoords = np.array(fullFlashCapture.landmarks.getEyeStripBB())
    (x, y, w, h) = fullFlashEyeStripCoords
    fullFlashEyeStripXStart = x
    fullFlashEyeStripXEnd = x + w
    #fullFlashEyeStrip = fullFlashCapture.image[y:y+h, x:x+w]
    fullFlashEyeStrip = halfFlashCapture.image[y:y+h, x:x+w]

    eyeStripCoordDiff_left = np.array(fullFlashLeftEyeCoord) - fullFlashEyeStripCoords[0:2]
    eyeStripCoordDiff_right = np.array(fullFlashRightEyeCoord) - fullFlashEyeStripCoords[0:2]

    #FOR REFLECITON
    [x, y, leftReflectionWidth, leftReflectionHeight] = maskReflectionBB(noFlashLeftEyeCrop, halfFlashLeftEyeCrop, fullFlashLeftEyeCrop)
    leftReflectionP1 = (x + eyeStripCoordDiff_left[0], y + eyeStripCoordDiff_left[1])
    leftReflectionP2 = (x + leftReflectionWidth + eyeStripCoordDiff_left[0], y + leftReflectionHeight + eyeStripCoordDiff_left[1])

    leftEyeReflection = halfFlashLeftEyeCrop[y:y+leftReflectionHeight, x:x+leftReflectionHeight]

    print('LEFT EYE REFLECTION :: ' + str(leftEyeReflection))

    leftHighMask = np.max(leftEyeReflection, axis=2) < 253
    #leftLowMask = np.min(leftEyeReflection, axis=2) >= 2
    leftLowMask = np.max(leftEyeReflection, axis=2) >= 2

    leftEyeMask = np.logical_and(leftHighMask, leftLowMask)
    leftEyePoints = leftEyeReflection[leftEyeMask]
    leftClipRatio = leftEyePoints.shape[0] / (leftEyeMask.shape[0] * leftEyeMask.shape[1])
    print('LEFT CLIP RATIO :: ' + str(leftClipRatio))

    leftReflectionMedian = np.median(leftEyePoints, axis=0) * 2 #Multiply by 2 because we got the value from the half flash
    #END FOR REFLECITON

    #FOR REFLECTION
    [x, y, rightReflectionWidth, rightReflectionHeight] = maskReflectionBB(noFlashRightEyeCrop, halfFlashRightEyeCrop, fullFlashRightEyeCrop)
    rightReflectionP1 = (x + eyeStripCoordDiff_right[0], y + eyeStripCoordDiff_right[1])
    rightReflectionP2 = (x + rightReflectionWidth + eyeStripCoordDiff_right[0], y + rightReflectionHeight + eyeStripCoordDiff_right[1])

    rightEyeReflection = halfFlashRightEyeCrop[y:y+rightReflectionHeight, x:x+rightReflectionWidth]

    rightHighMask = np.max(rightEyeReflection, axis=2) < 253
    rightLowMask = np.min(rightEyeReflection, axis=2) >= 2

    rightEyeMask = np.logical_and(rightHighMask, rightLowMask)
    rightEyePoints = rightEyeReflection[rightEyeMask]
    rightClipRatio = rightEyePoints.shape[0] / (rightEyeMask.shape[0] * rightEyeMask.shape[1])
    print('RIGHT CLIP RATIO :: ' + str(rightClipRatio))

    rightReflectionMedian = np.median(rightEyePoints, axis=0) * 2 #Multiply by 2 because we got the value from the half flash
    rightReflectionValue = np.max(rightReflectionMedian)
    #END FOR REFLECTION

    [leftRightPoint, leftLeftPoint] = fullFlashCapture.landmarks.getLeftEyeWidthPoints()
    [rightRightPoint, rightLeftPoint] = fullFlashCapture.landmarks.getRightEyeWidthPoints()

    (x, y, w, h) = fullFlashEyeStripCoords

    leftRightPoint -= [x, y]
    leftLeftPoint -= [x, y]

    rightRightPoint -= [x, y]
    rightLeftPoint -= [x, y]

    cv2.circle(fullFlashEyeStrip, (leftRightPoint[0], leftRightPoint[1]), 5, (0, 255, 0), -1)
    cv2.circle(fullFlashEyeStrip, (leftLeftPoint[0], leftLeftPoint[1]), 5, (0, 255, 0), -1)
    cv2.circle(fullFlashEyeStrip, (rightRightPoint[0], rightRightPoint[1]), 5, (0, 255, 0), -1)
    cv2.circle(fullFlashEyeStrip, (rightLeftPoint[0], rightLeftPoint[1]), 5, (0, 255, 0), -1)
    cv2.rectangle(fullFlashEyeStrip, leftReflectionP1, leftReflectionP2, (0, 0, 255), 1)
    cv2.rectangle(fullFlashEyeStrip, rightReflectionP1, rightReflectionP2, (0, 0, 255), 1)
    saveStep.saveReferenceImageBGR(fullFlashEyeStrip, 'eyeStrip')

    if leftClipRatio < .8:
        print("TOO MUCH CLIPPING!")
        raise NameError('Not enough clean non-clipped pixels in left eye reflections')

    if rightClipRatio < .8:
        print("TOO MUCH CLIPPING!")
        raise NameError('Not enough clean non-clipped pixels in right eye reflections')

    leftEyeWidth = leftRightPoint[0] - leftLeftPoint[0]
    rightEyeWidth = rightRightPoint[0] - rightLeftPoint[0]

    print('Left Eye Width :: ' + str(leftEyeWidth))
    print('Right Eye Width :: ' + str(rightEyeWidth))


    averageEyeWidth = (leftEyeWidth + rightEyeWidth) / 2

    #maxEyeWidth = max([rightEyeWidth, leftEyeWidth])

    print('RIGHT EYE WIDTH :: ' + str(rightEyeWidth))
    print('LEFT EYE WIDTH :: ' + str(leftEyeWidth))
    print('AVERAGE EYE WIDTH :: ' + str(averageEyeWidth))
    #print('MAX EYE WIDTH :: ' + str(maxEyeWidth))

    #blur = 5
    #leftEyeSlitDiff = cv2.GaussianBlur(leftEyeSlitDiff, (blur, blur), 0)
    #rightEyeSlitDiff = cv2.GaussianBlur(rightEyeSlitDiff, (blur, blur), 0)

    #threshold = 64
    #leftEyeSlitDiff = (leftEyeSlitDiff > threshold).astype('uint8') * 255
    #rightEyeSlitDiff = (rightEyeSlitDiff > threshold).astype('uint8') * 255

    #leftEyeSlitStack = np.vstack((leftEyeSlitL.astype('uint8'), leftEyeSlitS.astype('uint8'), leftEyeSlitDiff1, leftEyeSlitDiff2, leftEyeSlitDiff3))
    #rightEyeSlitStack = np.vstack((rightEyeSlitL.astype('uint8'), rightEyeSlitS.astype('uint8'), rightEyeSlitDiff1, rightEyeSlitDiff2, rightEyeSlitDiff3))

    #cv2.imshow('Eye Mask Comparison', np.hstack((rightEyeSlitStack, leftEyeSlitStack)))
    #cv2.waitKey(0)

    #valuesDiff = np.abs((rightReflectionMedian - leftReflectionMedian))
    averageMedian = (leftReflectionMedian + rightReflectionMedian) / 2

    leftReflectionMedian = colorTools.whitebalanceBGRPoints(leftReflectionMedian, averageMedian)
    rightReflectionMedian = colorTools.whitebalanceBGRPoints(rightReflectionMedian, averageMedian)

    print('left reflection median :: ' + str(leftReflectionMedian))
    leftReflectionHLS = colorsys.rgb_to_hls(leftReflectionMedian[2] / 255, leftReflectionMedian[1] / 255, leftReflectionMedian[0] / 255)
    rightReflectionHLS = colorsys.rgb_to_hls(rightReflectionMedian[2] / 255, rightReflectionMedian[1] / 255, rightReflectionMedian[0] / 255)

    print('rightReflectionMedian :: ' + str(rightReflectionMedian))
    print('right HLS :: ' + str(rightReflectionHLS))
    print('leftReflectionMedian :: ' + str(leftReflectionMedian))
    print('left HLS :: ' + str(leftReflectionHLS))

    hueDiff = np.abs(leftReflectionHLS[0] - rightReflectionHLS[0])
    satDiff = np.abs(leftReflectionHLS[2] - rightReflectionHLS[2])

    print('HUE and SAT diff :: ' + str(hueDiff) + ' | ' + str(satDiff)) 



    leftReflectionArea = (leftReflectionWidth / averageEyeWidth) * (leftReflectionHeight / averageEyeWidth)
    rightReflectionArea = (rightReflectionWidth / averageEyeWidth) * (rightReflectionHeight / averageEyeWidth)

    if (max(leftReflectionArea, rightReflectionArea) / min(leftReflectionArea, rightReflectionArea)) > 1.25:
        raise NameError('Reflection Sizes are too different!')

    #averageArea = (leftReflectionArea + rightReflectionArea) / 2

    #averageValue = (leftReflectionValue + rightReflectionValue) / 2
    #fluxish = averageArea * averageValue

    leftReflectionLuminosity = leftReflectionHLS[1]
    rightReflectionLuminosity = rightReflectionHLS[1]

    #leftFluxish = averageArea * leftReflectionLuminosity
    leftFluxish = leftReflectionArea * leftReflectionLuminosity
    print('LEFT FLUXISH :: ' + str(leftFluxish) + ' | AREA :: ' + str(leftReflectionArea) + ' | LUMINOSITY :: ' + str(leftReflectionLuminosity))

    #rightFluxish = averageArea * rightReflectionLuminosity
    rightFluxish = rightReflectionArea * rightReflectionLuminosity
    print('RIGHT FLUXISH :: ' + str(rightFluxish) + ' | AREA :: ' + str(rightReflectionArea) + ' | LUMINOSITY :: ' + str(rightReflectionLuminosity))

    return [averageMedian, leftFluxish, rightFluxish]

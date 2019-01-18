import numpy as np
import cv2

#SinglePixelStep = 1/255
#Scale = 255
#SinglePixelStep = 1

#def getChannelMask(channel, shadowPixels, highlightPixels, scale, singlePixelStep):
#    clippedShadows = channel < (shadowPixels * singlePixelStep)
#    clippedHighlights = channel > scale - (highlightPixels * singlePixelStep)
#    clippedCombined = np.logical_or(clippedHighlights, clippedShadows)
#    return clippedCombined

def getClippedMask(img, shadowPixels=1):#, highlightPixels=254):#, scale=255, step=1):
    highlightPixels = np.iinfo(img.dtype).max - 1
    #[b_channel, g_channel, r_channel] = cv2.split(img)
    #b_clipped_mask = getChannelMask(b_channel, shadowPixels, highlightPixels, scale, step)
    #g_clipped_mask = getChannelMask(g_channel, shadowPixels, highlightPixels, scale, step)
    #r_clipped_mask = getChannelMask(r_channel, shadowPixels, highlightPixels, scale, step)
    #clippedCombined = np.logical_or(b_clipped_mask, g_clipped_mask)
    #clippedCombined = np.logical_or(clippedCombined, r_clipped_mask)

    isSmallSubPixelMask = img < shadowPixels
    isLargeSubPixelMask = img > highlightPixels

    isClippedSubPixelMask = np.logical_or(isSmallSubPixelMask, isLargeSubPixelMask)


    isClippedPixelMask = np.any(isClippedSubPixelMask, axis=2)
    #cv2.imshow('mask', isClippedPixelMask.astype('uint8') * 255)
    #cv2.waitKeyEx(0)
    return isClippedPixelMask

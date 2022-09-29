import os, platform
import numpy as np
from ctypes import cdll, c_int, c_double, POINTER

def PatternClustering(ecg,ridxs,th=0.75):
    '''
    Cluster patterns into different groups based on similarity.
    
    Apply correlation coefficient(CC) as similartity. 
    Any two patterns with CC higher than a threshold are seem as similar.
    Connect similar patterns into groups. And see the persentage of major group.
    
    Parameters:
      ecg: list
          A list of input ecg signal.
      ridxs: list
          A list of indices of R peaks in ecg.
      th: float, optional
          A threshold of correlation coefficient to determine similarity. Default number is 0.9.
    Returns:
      out: float
          The persentage of major group in input signal.
    '''
    # Prepare datas
    ecg = np.array(ecg,dtype='int32')
    ridxs = np.array(ridxs,dtype='int32')
    RRI = np.diff(ridxs)
    RRI = [rri for rri in RRI if 2000 >= 1000*rri/250 >= 250]
    if len(RRI) < 1:
        return 0
    RRIq1 = int(np.percentile(RRI,25))


    # Load dynamic library
    if platform.system() == 'Windows':
        dllPath = os.path.join(os.path.dirname(__file__),"lib","EcgQualityCheck.dll")
    else:
        dllPath = os.path.join(os.path.dirname(__file__),"lib","EcgQualityCheck.so")
    DLL = cdll.LoadLibrary(dllPath)

    # Set input and output format of DLL
    DLL.EcgQualityCheck.argtypes = [POINTER(c_int),c_int,POINTER(c_int),c_int,c_int,c_double]
    DLL.EcgQualityCheck.restype = c_double

    # Transform numpy array to pointer for DLL
    ecgPtr = ecg.ctypes.data_as(POINTER(c_int))
    ridxPtr = ridxs.ctypes.data_as(POINTER(c_int))

    # Call function in DLL
    MajorPer = DLL.EcgQualityCheck(ecgPtr,ecg.size,ridxPtr,ridxs.size,RRIq1,th)

    return MajorPer

def AreaRatio(ecg,ridxs):
    '''
    Response the score based on areas of detected beats.
    
    Calculate areas of beats by given R peaks and uncovered areas.
    Check the ratio between uncovered areas and covered areas of beats.
    The score is higher if all areas are fully covered.
    
    Parameters:
      ecg: list
          A list of input ecg signal.
      ridxs: list
          A list of indices of R peaks in ecg.
    Returns:
      out: float
          The score of how detected beats cover areas in signal.
    '''
    
    # Calculate the median of RRI (unit:samples)
    RRIs = np.diff(ridxs)
    RRIs = [rri for rri in RRIs if 2000 >= 1000*rri/250 >= 250] # filter with ms
    if len(RRIs) < 1:
        return 0

    medRRI = np.median(RRIs)
    forward = int(0.4*medRRI)
    backward = int(0.6*medRRI)

    prevEndIdx = 0 #prevent from overlapping
    beatAreas = []
    missedAreas = []
    
    for i in range(0,len(ridxs)):
        # Set start point
        startIdx = int(ridxs[i] - forward)
        # Left Boundary
        if startIdx < 0:
            startIdx = int(0)
        # Prevent from overlapping
        if startIdx < prevEndIdx:
            startIdx = prevEndIdx

        # Set end point
        endIdx = int(ridxs[i] + backward)
        # Right boundary
        if endIdx >= len(ecg):
            endIdx = int(len(ecg))
        
        # Calculate Areas
        beat = np.absolute(ecg[startIdx:endIdx+1])
        beatArea = np.trapz(beat,dx=1/250)
        beatAreas.append(beatArea)
        if startIdx > prevEndIdx > 0:
            miss = np.absolute(ecg[prevEndIdx:startIdx+1])
            missArea = np.trapz(miss,dx=1/250)
            missedAreas.append(missArea)

        # Update last end point
        prevEndIdx = endIdx

    totalArea = np.trapz(np.absolute(ecg),dx=1/250)
    ideaArea = sum(beatAreas) + sum(missedAreas)
    R1 = ideaArea / totalArea
    ratio2 = max(missedAreas)/np.median(beatAreas)
    R2 = 1-ratio2 if ratio2 < 1 else 0

    return float(R1*R2)
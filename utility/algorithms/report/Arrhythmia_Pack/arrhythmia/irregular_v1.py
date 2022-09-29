import numpy as np
from ..ecg.Rpeak import RPeakDetection
from ..ecg.Rpeak import RRI_filter
from ..ecg.score import AreaRatio, PatternClustering

def Irregular(idx,sig):
    ## rescale signal
    scale = 1
    if 300 >= max(sig) > 150:
        scale = 2
    elif 150 >= max(sig):
        scale = 4
    else:
        scale = 1
    ecg = sig * scale

    ## detect R peaks
    RPeaks = RPeakDetection(ecg)

    ## thresholds
    thr1 = 0.2
    thr2 = 0.35
    
    if len(RPeaks) > 1:        
        Ridx = RPeaks[1:]           
        if len(Ridx) >= 2:         
            ## calculate confidence score
            score0 = PatternClustering(ecg,Ridx,th=0.9)
            score1 = AreaRatio(ecg,Ridx)
            score = score0 * score1

            ## calculate RRI 
            RRIArray = np.diff(Ridx)*1000/250
            RRIArray.astype('int32')
            RRIArray = RRI_filter(RRIArray)
            location1=[]
            location2=[]
            location=[]
            if len(RRIArray) >= 2:
                nowMaxRRI = max(RRIArray)
                nowMinRRI = min(RRIArray)
                meanRRI = np.mean(RRIArray)

                ## detect irreqular heart beats
                ResultFlag = 0

                count1, count2 = 0, 0
                for k in range(1,len(RRIArray)):
                    delta_RRI = (RRIArray[k]-RRIArray[k-1])/RRIArray[k-1]
                    if abs(delta_RRI) >= thr1:
                        count1 += 1
                        location1.append(int(Ridx[k-1]))
                    if abs(delta_RRI) >= thr2:
                        count2 += 1
                        location2.append(int(Ridx[k-1]))

                if count1 >= 2:
                    ResultFlag = 1
                    location=location1
                if count2 >= 2:
                    ResultFlag = 2
                    location=location2

                Ridx=Ridx.astype(int)                
                Dict = {'Index':idx,
                        'scale':scale,
                        'ResultFlag':ResultFlag,
                        'STD':0,
                        'minHR':60000/nowMaxRRI,
                        'maxHR':60000/nowMinRRI,
                        'avgHR':60000/meanRRI,
                        'Ridx':Ridx,
                        'score':score,
                        'location':location
                        }
                return Dict  
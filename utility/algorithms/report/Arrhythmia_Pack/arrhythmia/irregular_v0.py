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
    std_thr = 0.1
    RRI_thr = 0.2

    if RPeaks.size > 1:        
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

            if len(RRIArray) >= 2:
                nowMaxRRI = max(RRIArray)
                nowMinRRI = min(RRIArray)
                meanRRI = np.mean(RRIArray)

                ## detect irreqular heart beats
                ResultFlag = 0
                stdValue = np.std(RRIArray)/np.mean(RRIArray)
                if stdValue >= std_thr:                                
                    ResultFlag = 1

                Var_Count = 0
                for k in range(1,len(RRIArray)):
                    delta_RRI = (RRIArray[k]-RRIArray[k-1])/RRIArray[k-1]
                    if abs(delta_RRI) >= RRI_thr:
                        Var_Count += 1
                        if Var_Count >= 2:
                            ResultFlag = 2 if ResultFlag==0 else 12
                            break
                
                Dict = {'Index':idx,
                        'scale':scale,
                        'ResultFlag':ResultFlag,
                        'STD':stdValue,
                        'minHR':60000/nowMaxRRI,
                        'maxHR':60000/nowMinRRI,
                        'avgHR':60000/meanRRI,
                        'Ridx':Ridx,
                        'score':score
                        }
                return Dict
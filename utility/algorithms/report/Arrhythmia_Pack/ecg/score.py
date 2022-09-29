# -*- coding: utf-8 -*-
"""
Created on Mon Jul 11 15:20:13 2022

@author: SWM-Jared
"""

import numpy as np

def PatternClustering(ecg, ridxs, th=0.75):
    
    if 40 > len(ridxs) > 4:
    
        ecg = np.array(ecg,dtype='int32')
        ridxs = np.array(ridxs,dtype='int32')
        RRI = np.diff(ridxs)
        RRI = [rri for rri in RRI if 2000 >= 1000*rri/250 >= 250]
        if len(RRI) < 1:
            return 0
        rri_q1 = int(np.percentile(RRI,25))
        ##rri_q1 = np.quantile(np.diff(ridxs), 0.25)
        
        before_r = int(0.334 * 0.8 * rri_q1)
        after_r = int(0.667 * 0.8 * rri_q1)
        
        ecgs_list = []   
        
        for rpeak in ridxs:
            n_rpeak_before = int(rpeak - before_r)
            n_rpeak_after = int(rpeak + after_r)
            if n_rpeak_before >= 0 and n_rpeak_after < len(ecg):
                ecgs_list.append(list(map(float,ecg[n_rpeak_before:n_rpeak_after])))
        
        if len(ecgs_list) <= 4:
            return 0
        
        ecgs_coeff = np.corrcoef(ecgs_list)
        
        V = []
        
        for ecg_coeff in ecgs_coeff:
            
            ecgs_th = []
            
            for i_c, coeff in enumerate(ecg_coeff):
                
                if  coeff > th:
                    
                    ecgs_th.append(i_c)
            
            V.append(ecgs_th)
        
        V = sorted( V, key=len, reverse=True)
        
        #print(V)
        
        Relation = []
        
        for i_1 in range(len(V)):
            
            if len(Relation) == 0:
                Relation.append(V[i_1])
            else :
                for i_2 in range(len(V)):
                    inter_num = len(set(V[i_1]) & set(V[i_2]))
                    
                    if inter_num > 0:
                        
                        if len(Relation) == i_2:
                            Relation.append(V[i_1])
                        else :
                            Relation[i_2] = list(set(V[i_1]) | set(Relation[i_2]))
                        break
                    elif inter_num == 0 and i_2 == len(Relation):
                        Relation.append(V[i_1])
                    else :
                        continue
                  
        Relation = sorted([list(t) for t in set(tuple(element) for element in Relation)], key=len, reverse=True)
        
        s = len(Relation[0])/len(ecgs_list)*100
        
        return s
    
    else :
        
        return 0
  
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
    ratio2 = max(missedAreas)/np.median(beatAreas) if len(missedAreas)>0 and len(beatAreas)>0 else 0
    R2 = 1-ratio2 if ratio2 < 1 else 0

    return float(R1*R2)

if __name__ == '__main__':
    
    #ecgs = scipy.io.loadmat('SWMIRB_546C0ED03BFC_1614844253584.mat')['ECG'].ravel()
    
    ID = str(1018)
    
    ecg_file = "ECG_"+ID+".txt"

    with open(ecg_file) as f:
        ecgs = list(map(float,str(f.readlines())[2:-2].split(", ")))
        f.close()
    
    ### R Peak List
    
    rpeak_file = "R_"+ID+".txt"
    
    with open(rpeak_file) as f:
        rpeaks = list(map(float,str(f.readlines())[2:-2].split(", ")))
        rpeaks = list(map(int,rpeaks))
        f.close()
    
    ecgs = np.array(ecgs)
    rpeaks = np.array(rpeaks)
    
    i_max = len(ecgs)//2500
    
    score = []
    
    for i in range(i_max):
    
        ecgs_part = ecgs[i*2500:(i + 1)*2500]
    
        rpeaks_part = []
    
        for rpeak in rpeaks:
            if i*2500 <= rpeak < (i + 1)*2500:
                rpeaks_part.append(rpeak)
        
        rpeaks_part = np.array(rpeaks_part)-i*2500
        
        score.append(PatternClustering(ecgs_part, rpeaks_part, 0.8))
    
    print(score)
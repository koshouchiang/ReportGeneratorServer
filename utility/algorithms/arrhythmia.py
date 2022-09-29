import os, json
import numpy as np
from utility.algorithms.ecg.baseline import BaselineRemove, Rescaling
from utility.algorithms.ecg.Rpeak import RPeakDetection
from utility.algorithms.ecg.score import PatternClustering, AreaRatio


def Irregular(ridx):
    '''
    Determine irregularity by R-R intervals.

    Calculate coefficient of variation (CV) and R-R spread.
    If one of CV and R-R spread is higher than threshold, determine as light irregular.
    If both of CV and R-R spread are higher than threshold, determine as serious irregular.

    Parameters:
        ridx: list
            Locations of R peaks.
    Return:
        ResultFlag: int
            0, Normal
            1, Light Irregular
            2, Serious Irregular
    '''

    ResultFlag = 0

    ## Parameters
    thr1 = 0.2
    thr2 = 0.35
    thr3 = 1.3

    ## calculate RRI
    RRIArray = np.diff(ridx) * 1000 / 250
    RRIArray.astype('int32')

    if len(RRIArray) >= 2:
        ## detect irreqular heart beats

        count1, count2, count3 = 0, 0, 0
        for k in range(1, len(RRIArray)):
            delta_RRI = (RRIArray[k] - RRIArray[k - 1]) / RRIArray[k - 1]
            if abs(delta_RRI) >= thr1:
                count1 += 1
            if abs(delta_RRI) >= thr2:
                count2 += 1
            if abs(delta_RRI) >= thr3:
                count3 += 1
        if count1 >= 2:
            ResultFlag = 1
        if count2 >= 2:
            ResultFlag = 2
        if count3 >= 2:
            ResultFlag = -1

    return ResultFlag


def AbnormalLabeling(ecgArray, ecgType=1):
    '''
    Label type of abnormal with confidence of R peak detection.

    Remove baseline of input ECG and rescale it.
    Detect R peaks in ECG and score the confidence of R peaks.
    Determine the irregularity of detected RRIs.

    Parameters:
        ecgArray: list
            2-D array of N ECG arrays. The length of each ECG array is 2500.
            The shape of ecg_array is (N, 2500).
        ecgType: int
            1: ECG measured by strap.
            2: ECG measured by patch.
    Return:
        out: list
            N results in dictionaries.
            "flag":
                -1, Bad Quality
                0, Normal
                1, Light Irregular
                2, Serious Irregular
            "score":Score of confidence in R peak detection.
    '''

    Output = []
    PassScore = 100

    for sig in ecgArray:
        flag, score = -1, 0
        ridxs = []

        ## remove baseline
        ecg_filt = BaselineRemove(sig)

        ## rescale signal
        ecg_rescale = Rescaling(ecg_filt)

        MinValue = np.min(ecg_rescale)
        MaxValue = np.max(ecg_rescale)
        if (MinValue == MaxValue):
            flag = -2
            PassScore = 100
            Output.append({"flag": flag, "score": PassScore, 'rpeak': ridxs})
            continue

        ## detect R peaks
        RPeaks = RPeakDetection(ecg_rescale)
        if RPeaks[0] >= 4:        
            ridxs = RPeaks[1:]
            score0 = PatternClustering(ecg_rescale, ridxs, th=0.75)
            score1 = AreaRatio(ecg_rescale, ridxs)
            score = score0 * score1

            if score > 0.5: ###沒有漏打R peak下，分數才會超過0.6，才會分析心律不整程度
                flag = Irregular(ridxs)

            ridxs = ridxs.astype('int32').tolist()

        if flag == -1: ###bad quality(R peak不到兩個或是品質分析分數<=0.6分)
            if score>=0.5:
                PassScore=0                
        elif flag == 0: ###normal，但訊號不夠好，需要人工審閱              
            if score < 0.8:
                PassScore = 0
        elif flag == 1:
            if score < 0.85:
                PassScore = 0
        elif flag == 2:
            if score < 0.90:
                PassScore = 0

        ##Output.append({"flag":flag,"score":score,'rpeak':ridxs})
        Output.append({"flag": flag, "score": PassScore, 'rpeak': ridxs})
      
    return Output


if __name__ == "__main__":

    # Prepare input data
    TestFolder = os.path.join(os.path.dirname(__file__), '../test_data')
    TestFolder = os.path.normpath(TestFolder)
    filePaths = [f for f in os.listdir(TestFolder) if f.endswith('srj')]
    filepath = os.path.join(TestFolder, filePaths[0])

    ECGs = []
    with open(filepath, 'r') as srj:
        line = srj.readline()
        while line:
            data = json.loads(line)
            ecg = data['rows']['ecgs']
            ECGs.append(ecg)

            line = srj.readline()

    # Test main function
    Results = AbnormalLabeling(ECGs, ecgType=1)

    for result in Results:
        print(result)

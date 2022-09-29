import numpy as np
from scipy import signal 

def RRI_filter(RRI):
    # remove extreme outlier
    newRRI = [x for x in RRI if 2100 >= x >= 245]

    # filter with median
    Med = np.median(newRRI)
    Lower = Med - 0.55*Med
    Upper = Med + 0.62*Med
    output = [y for y in newRRI if Lower < y < Upper]
    
    return output

def RPeakDetection(ecg, DetectionMode=0): ###DetectionMode==0,一般模式，DetectionMode==1, PVC偵測模式
    ###print('DetectionMode:',DetectionMode)
    fs = 0.12
    fc = 0.3
    W1 = 27 ### ~=(35/360)*250,  35 is optimal parameter found by author in paper
    beta = 0.17
    length = len(ecg)
    ## --------butterworth band-pass filter-------------
    b, a = signal.butter(2, [fs, fc], 'bandpass')
    x = signal.filtfilt(b, a, ecg, padtype='odd', padlen=3*(max(len(b),len(a))-1)) #fit the result of Matlab

    ## -------square function----------
    y = np.multiply(x, x)

    SmoothedSig = np.zeros(length)
    SmoothedOffset = 10 ## 前後共看20的點
    for i in range(0, length):
        if i - SmoothedOffset >= 0 and i + SmoothedOffset < length:
            window = y[i-SmoothedOffset:i+SmoothedOffset+1]
            SmoothedSig[i] = sum(window) / (2*SmoothedOffset+1)
        else:
            if i - SmoothedOffset < 0:
                window = y[:i+SmoothedOffset+1]
            else:
                window = y[i-SmoothedOffset:]
            SmoothedSig[i] = sum(window) / len(window)
    meanValue = np.mean(SmoothedSig)
    Thr1 = meanValue * beta
    QRSLocationArray = np.where(SmoothedSig >= Thr1)[0]
    QRSCadidate_Count = len(QRSLocationArray)
    QRSLocationArray = np.append(QRSLocationArray, 0)

    ##-----------檢查波持續的寬度---------------
    Width = 0
    Thr2 = W1
    start_index = QRSLocationArray[0]
    end_index = 0
    RPeakArray = []
    RPeakHeightArray = []
    for i in range(1, QRSCadidate_Count + 1): ##最後一筆資料後是0, 將其算入，如此最後一個R peak才會被算到
        if QRSLocationArray[i] - QRSLocationArray[i-1] == 1: ## 後減前只有差一，表示是連續的
            Width += 1
            end_index = QRSLocationArray[i]
        else: ##沒有連續了，判斷之前連續了多少個點        
            if Width >= Thr2: ## 連續的點數通過門檻值，是R Peak，收集起來
                MaxIndex = np.argmax(ecg[start_index:end_index+1])
                RPeakArray.append(start_index + MaxIndex)
                RPeakHeightArray.append(ecg[start_index + MaxIndex]) ## 收集濾波後的高度
            start_index = QRSLocationArray[i]
            Width = 0
    RPeakArray = np.asarray(RPeakArray)
    RPeakHeightArray = np.asarray(RPeakHeightArray)
    RPeak_Count = len(RPeakArray)

    ###-----for PVC R peak detection----
    if(DetectionMode==1): ###針對PVC疾病偵測的模式
        if(RPeak_Count==0):
            DetectedRPeakArray=[]
        else:
            DetectedRPeakArray = np.zeros(RPeak_Count + 1)
            DetectedRPeakArray[0] = RPeak_Count
            DetectedRPeakArray[1:] = RPeakArray
        
        return DetectedRPeakArray
    

    ##------------以下為heuristic方法，修正初步得到的R Peak------------------
    RPeakArray_Final = []
    if len(RPeakArray) > 0 :
        sortedArray = np.sort(RPeakHeightArray)
        meanRPeakHeight = np.mean(sortedArray[RPeak_Count//2:]) ## 取前二分之一較高的peak點的平均高度

        ##------------1. 修正R Peak, 太低的為雜訊過濾掉--------
        pass_idx = np.where(RPeakHeightArray >= meanRPeakHeight/2.5)[0]
        RPeak_Count_Refined = len(pass_idx)
        RPeakArray_Refined = np.zeros((RPeak_Count_Refined, 3)) ## 1 放location, 2放高度，3放是否濾除的標示
        RPeakArray_Refined[:,0] = RPeakArray[pass_idx]
        RPeakArray_Refined[:,1] = RPeakHeightArray[pass_idx]

        ##----------2. 距離太近的點，排除之-----------
        ##計算R Peak點之間距離，若距離在62點(248ms)內，則進一步排除高度較低的點
        close_idx = np.where(np.diff(RPeakArray_Refined[:,0]) <= 62)[0] + 1
        for k in close_idx:
            RPH_Diff = RPeakArray_Refined[k-1][1] - RPeakArray_Refined[k][1]
            if RPH_Diff > 0: ###前面較高
                RPeakArray_Refined[k][2] = 1 ###排除後面的
            else:
                RPeakArray_Refined[k-1][2] = 1 ###排除前面的

        ##--------  3.一個一個檢查高度下降狀況，下降不夠快的排除之-------
        JumpOffset = 15 ##向外看15個點，看最低點高度是否小於此peak高度一半以下
        for k in range(0, RPeak_Count_Refined):
            nowLocation = int(RPeakArray_Refined[k][0])
            nowPeakHeight = ecg[nowLocation]
            minHeight = nowPeakHeight
            if nowPeakHeight > 150: ##一般訊號
                SteepThr = nowPeakHeight / JumpOffset
            elif 150 >= nowPeakHeight > 50: ##偏小的訊號
                SteepThr = 13
            else: ##太小的訊號
                SteepThr = 7

            index = 0
            minIndex = 100000
            foundFlag = False
            for q in range(nowLocation+1, nowLocation+JumpOffset+1): ##先檢查右邊
                if length > q >= 0:
                    index += 1
                    if minHeight > ecg[q]:
                        minHeight = ecg[q]
                        minIndex = index
                        Steep = (nowPeakHeight - minHeight) / minIndex
                        if Steep >= SteepThr: ##確定有陡坡
                            foundFlag = True
                            break
                            
            if foundFlag: ##右邊有陡坡，再檢查左邊(使用陡坡比例)
                DeleteFlag = -1
                if nowPeakHeight > 150: ##一般訊號
                    SteepThr = nowPeakHeight / JumpOffset
                elif 150 >= nowPeakHeight > 50: ##訊號高度較小的
                    SteepThr = 7
                else: ##訊號高度很小的
                    if nowPeakHeight >= meanRPeakHeight/2.5: ###高於平均值一半左右，直接過
                        SteepThr = 0
                        DeleteFlag = 0
                    else: 
                        SteepThr = 50 ###太低的，直接封殺
                        DeleteFlag = 1

                foundFlag = False
                if DeleteFlag == 0: ##50以下，高於平均，直接過
                    foundFlag = True
                elif DeleteFlag == 1: ##50以下，又低於平均，直接封殺
                    foundFlag = False
                else: ##50以上，要一個一個再檢查左邊下降狀況
                    minHeight = nowPeakHeight
                    index = 0
                    minIndex = 100000
                    foundFlag = False
                    for q in reversed(range(nowLocation-JumpOffset, nowLocation)):
                        if length > q >= 0:
                            index += 1
                            if minHeight > ecg[q]:
                                minHeight = ecg[q]
                                minIndex = index
                                Steep = (nowPeakHeight - minHeight) / minIndex
                                if Steep >= SteepThr: ##找到陡坡了
                                    foundFlag = True
                                    break

                if not foundFlag: ##沒有通過檢查
                    RPeakArray_Refined[k][2] = 1 ##設定排除之
            else: ##右邊下降速度不夠快，排除之
                RPeakArray_Refined[k][2] = 1 ##設定排除之

            ##--------------最後收集沒有被過濾的candidate R Peak,作為最後結果輸出---------------
            if RPeakArray_Refined[k][2] == 0:
                RPeakArray_Final.append(RPeakArray_Refined[k][0])

    RPeak_Count_Final = len(RPeakArray_Final)
    if(RPeak_Count_Final==0):
        DetectedRPeakArray=[]
    else:
        DetectedRPeakArray = np.zeros(RPeak_Count_Final + 1)
        DetectedRPeakArray[0] = RPeak_Count_Final
        DetectedRPeakArray[1:] = RPeakArray_Final   

    return DetectedRPeakArray

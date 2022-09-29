from email import iterators
import pandas as pd
import shutil
from datetime import date, datetime, timedelta
from zipfile import ZipFile
#from torch import int32
import ujson as json
from time import time
import tqdm, sys
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.patches import Ellipse
import hrvanalysis as hrv
import numpy as np
import os,sys

if os.path.dirname(__file__) not in sys.path: sys.path.append(os.path.dirname(__file__))
for path in sys.path: print(path)

from .Beatinfo_Srj_Time_Parse import document_process_
from .Arrhythmia_Pack.ecg import baseline as BaselineRemove_Obj
from .Arrhythmia_Pack.ecg import Fiducial_v5 as Fiducial_Obj
from .Arrhythmia_Pack.ecg import Rpeak as Rpeak_Obj
from .Arrhythmia_Pack.ecg import score as Score_Obj
from . import ahrs
from .Arrhythmia_Pack.arrhythmia.analysis_v2 import ArrhythmiaDetection
from scipy.ndimage import median_filter

class ExerciseReportGenerator:
    def __init__(self,DBPath): 
        self.BasePath=os.path.dirname(__file__)
        self.DB=self.tempDB=DBPath
        self.IntMaxValue=1000000           
    ####=========================檔案解壓縮===============================
    def search_upzip(self,db_path,target,start,end,export_path):
        startDT = datetime.strptime(start,'%Y%m%d') ###%H%M') ##到時與分
        endDT = datetime.strptime(end,'%Y%m%d')     ###%H%M')  ##到時與分
        ##existFiles = [f.split('.')[0] for f in os.listdir(export_path) if f.endswith('.srj')]
        UnzipFileNameList=[] 
        print("[Progress] Downloading Datas")
        ##t1 = time()
        # 遍蒞所有資料夾
        for D in os.listdir(db_path):
            if(len(D)<8): ##uuid的資料夾不需要parsing資料
                continue

            Folder = os.path.join(db_path,D)
            # 符合日期的資料夾
            if os.path.isdir(Folder):
                ##print('Folder:',Folder)
                date = datetime.strptime(D,'%Y%m%d')
                if date >= startDT and date <= endDT:
                    # 遍歷該日期資料夾的檔案
                    for files in os.listdir(Folder):
                        fileparts = files.split("_")
                        uuid = fileparts[0]
                        
                        # 檢查檔案是否已解壓縮過
                        filename = files.split('.')[0]
                        ##if filename in existFiles:
                        ##    continue
                        if "(" in filename or ")" in filename: ###有些檔案是重復版本，不用再次解壓縮
                            continue
                        # 檢查符合UUID且為zip檔
                        if uuid == target and files.endswith('.zip'):
                            filePath = os.path.join(Folder,files)
                            print('     %s' %filename)
                            # 解壓縮至指定路徑
                            with ZipFile(filePath,'r') as zip:
                                zip.extractall(export_path)
                                UnzipFileNameList.append(filename[0:len(filename)]+'.srj') 
                                ##print("Filename:",filename[0:len(filename)]+'.srj')
        ##t2 = time()
        ##print("  Elapsed time: %.2fs" %(t2-t1))
        return UnzipFileNameList

    ####=================================Data concate============================
    def DataConcate(self,FileList,startTime,endTime,UUID): 
        
        startTime = datetime.strptime(startTime,'%Y%m%d %H%M%S')
        endTime = datetime.strptime(endTime,'%Y%m%d %H%M%S')

        OriginalTimeArray=[]
        ConcateEcgArray=[] 
        MotionDataArray=[]           
        for index in range(len(FileList)):
            NowFilePath=os.path.join(self.DB,UUID,FileList[index])
            with open(NowFilePath,'r') as srj:
                line = srj.readline()
                while line:
                    data = json.loads(line)
                    motions = data['rows']['motions']
                    ecgs=data['rows']['ecgs']
                    tt=data['tt']
                    tt=int(tt/1000)
                    nowtime=datetime.fromtimestamp(tt)
                    ##if(nowday>=NowDay and nowday<=NowDayEnd): ###針對當天的時段Concate Data
                    if(nowtime>=startTime and nowtime<=endTime): ###針對當天的時段Concate Data
                        OriginalTimeArray.append(nowtime)                
                        for m in motions:
                            MotionDataArray.append(m)
                    
                        for n in ecgs:
                            ConcateEcgArray.append(n) 
                
                    line = srj.readline()          
                
        return OriginalTimeArray,ConcateEcgArray    

    ####===============本地端檔案讀取=================================
    def load_data(self,file_path, file_list, startDT, endDT):
        print("[Progress] Loading Datas")
        ##t1 = time()
        lines = []
        for f in file_list:
            with open(os.path.join(file_path,f)) as srj:
                row = srj.readline()
                while row:
                    lines.append(row)
                    row = srj.readline()
        lines = set(lines) # to avoid repeated json strings

        Datas = []
        startTT = startDT.timestamp()*1000
        ###endDT = endDT + timedelta(hours=24)  ##原本做法
        endTT = endDT.timestamp()*1000
        with tqdm.tqdm(total=len(lines),desc='  [進度]',file=sys.stdout) as pbar:
            for line in lines:
                string = json.loads(line)
                if startTT <= string['tt'] <= endTT:
                    Datas.append(string)
                pbar.update()
        Datas.sort(key=lambda i:i['tt'])

        ##t2 = time()
        ##print("  Elapsed time: %.2fs" %(t2-t1))
        return Datas   

    ####===================================RRIFilter============================
    def RRIFilter(self,RRIArray,medianFlag=True):
        FilteredRRIArray=[]
        FinalFilteredRRIArray=[]
        for i in range(len(RRIArray)):  
            if((RRIArray[i]>=285) and (RRIArray[i]<=1300)): ###hr=46~210   for exercise         
                FilteredRRIArray.append(RRIArray[i])
        
        if(medianFlag): ##另外加上中值濾波   
            if(len(FilteredRRIArray)>0):
                RRIMedian=np.median(FilteredRRIArray)
                for i in range(len(FilteredRRIArray)):
                    if((FilteredRRIArray[i]>=(RRIMedian-0.55*RRIMedian)) and (FilteredRRIArray[i]<=RRIMedian+0.62*RRIMedian)):
                    ##if((FilteredRRIArray[i]>=(RRIMedian-0.45*RRIMedian)) and (FilteredRRIArray[i]<=RRIMedian+0.45*RRIMedian)):
                        FinalFilteredRRIArray.append(FilteredRRIArray[i])
            
            return FinalFilteredRRIArray
        else:
            return FilteredRRIArray
        
    ####=================針對PVC偵測的RRI過濾==============================
    def RRIFilter_PVC(self,RRIArray):
        BetweenRange_RRIArray=[]
        FilteredRRIArray=[]
        TempFilteredRRIArray=[]
        BoolFilteredRRI=[]
        for i in range(len(RRIArray)):
            if(RRIArray[i]>=250 and RRIArray[i]<=2000):
                TempFilteredRRIArray.append(RRIArray[i])
            else:
                TempFilteredRRIArray.append(0)
            
                
        for rri in RRIArray:
            if(rri>=250 and rri<=2000):
                BetweenRange_RRIArray.append(rri)      
        
        medianRRI=np.median(BetweenRange_RRIArray)
        
        for rri in TempFilteredRRIArray:
            if(rri<=1.45*medianRRI and rri>=0.65*medianRRI):
                FilteredRRIArray.append(rri)
                BoolFilteredRRI.append(True)
            else:
                BoolFilteredRRI.append(False)
        
        return FilteredRRIArray,BoolFilteredRRI

    ####================動靜態分析=============================
    def StaticAnalysis(self,Motions,SampleRate):
        '''
        Determine static or dynamic of motion data.
        
        Calculate the stantard deviation of the linear acceleration in global coordinate within 2 seconds.
        Set a threshold of stantard deviation to determine static or dynamic.
        
        Arguments:
            Motions: list
                2-D list of raw motion data.
            SampleRate: int or float
                Sample rate of motion data.

        Return:
            out: list
                1-D list of flags of static.
                0: dynamic
                1: static
        '''

        # 將Motion raw data 轉成 numpy array
        SampleNum = len(Motions)
        Motions = np.array(Motions)

        ##Static_label = np.ones(SampleNum,dtype=int) ##test
        
        # 將Motion raw data 轉成對應的數值(dps, g, ...)
        F = np.concatenate((np.ones(3)/114.28, np.ones(3)*0.000061, np.ones(3)*1.5, 1), axis = None)
        Values = Motions * F

        # 擷取ACC and GYR 
        ACC = Values[:,3:6]
        GYR = Values[:,0:3]
        
        # 計算 global & body 座標系的轉換矩陣: C
        orientation = ahrs.filters.Madgwick(acc=ACC*9.80665, gyr=GYR*np.pi/180, frequency=SampleRate)
        C = ahrs.common.orientation.q2R(orientation.Q)
        
        # 將 ACC 轉至 global 坐標系, 扣除 gravity 後得到空間中實際的加速度
        linACC = np.zeros(ACC.shape)
        for i in range(0, SampleNum):
            ACCglob = np.dot(ACC[i], C[i].T)
            linACC[i] = ACCglob - [0,0,1] # notice: C in matlab is the transpose of C in here
        linACC = linACC * 9.81 # g to m/s^2
        
        # 計算實際加速度 2 秒內的標準差
        STD = np.zeros(linACC.shape)
        w_size = 2 * SampleRate
        for i in range(0, SampleNum):
            if i < w_size:
                window = linACC[:i+1]
            else:
                window = linACC[i-w_size+1:i+1]

            if window.shape[0] > 1:
                STD[i] = np.std(window, axis=0)
                
        # 設定標準差的閥值，以定義動態或靜態
        movingTH = 0.5
        Static_label = np.ones(SampleNum,dtype=int)
        for i in range(w_size, SampleNum):
            s = STD[i]

            # 三軸中任一軸的標準差大於閥值就視為動態
            flag = np.sum(s > movingTH)
            if flag == 0:
                Static_label[i] = 1 # Static
            else:
                Static_label[i] = 0 # Dynamic

        
        return Static_label ##,STD  

    ####=============================Calculate RRSpread==============================
    def RRSpreadCalculate(self,RRIArray):    
        MaxRRI=np.max(RRIArray)
        MinRRI=np.min(RRIArray)
        RRSpreadValue=(MaxRRI-MinRRI)/(MaxRRI+MinRRI)
        return RRSpreadValue    

    ####======================PVC 偵測===============================
    def PVC_Report(self,user_info,data_path,start,end,export_path=""):
        '''
        UserId=user_info['id']
        startDate = datetime.strptime(start,'%Y%m%d')
        endDate = datetime.strptime(end,'%Y%m%d')
        Dates = [(startDate+timedelta(days=i)).strftime("%Y%m%d") for i in range((endDate-startDate).days+1)] 
        '''

        startTime = datetime.strptime(start,'%Y%m%d %H%M%S')
        endTime = datetime.strptime(end,'%Y%m%d %H%M%S')        
        startDate = datetime.strptime(start.split(" ")[0], "%Y%m%d")
        endDate = datetime.strptime(end.split(" ")[0], "%Y%m%d")        
        UserId=user_info['id']        
        Dates = [(startDate+timedelta(days=i)).strftime("%Y%m%d") for i in range((endDate-startDate).days+1)]    

        PVCInformation = pd.DataFrame()  
        #### Parse Data
        srjFiles = [f for f in os.listdir(data_path) if f.endswith('.srj')]
        ##data = self.load_data(data_path,srjFiles,startDate,endDate)   
        data = self.load_data(data_path,srjFiles,startTime,endTime)  
        fs=250  ##ECG Sampling Rate
        TotalPVCCount=0
        ##OccuringCountArray=np.zeros(24)  ###計算每個小時發生幾次的陣列    
        for i in range(1,len(data)-1):
            ecg_pre = data[i-1]['rows']['ecgs'] 
            ecg = data[i]['rows']['ecgs']
            ecg_next = data[i+1]['rows']['ecgs'] 
            tt = data[i]['tt']
            dt = datetime.fromtimestamp(int(tt)/1000)
            nowDay = dt.replace(hour=0, minute=0,second=0,microsecond=0)
            ##dayIndex=(nowDay-startDate).days        
            RawEcg=ecg
            ecgtemp=ecg_pre[2500-2*fs:2500] ###前後多抓2秒(避免PCV位於最前或最後被截除)
            ecgtemp.extend(ecg)
            ecgtemp.extend(ecg_next[0:2*fs]) ###前後多抓2秒(避免PCV位於最前或最後被截除)
            ecg=ecgtemp
            ecg=np.array(ecg)
            ecg=BaselineRemove_Obj.BaselineRemove(ecg)       
            RpeakArray=Rpeak_Obj.RPeakDetection(ecg,DetectionMode=1)
            Ridx=RpeakArray[1:len(RpeakArray)]       
            score0 = Score_Obj.PatternClustering(ecg,Ridx)
            score1 = Score_Obj.AreaRatio(ecg, Ridx)
            QualtiyScore = score0 * score1
            if(QualtiyScore<0.8): ##訊號品質不好不分析
                continue
    
            ecg_norm = np.interp(ecg,(ecg.min(),ecg.max()),(0,1)).reshape(len(ecg),1)
            feature = Fiducial_Obj.feature_gen(ecg_norm,250,Ridx)
            QRSArray=feature['QRSArray']
            avgHR=feature['avgHR']
            avgPR=feature['avgPR']
            avgQRS=feature['avgQRS']
            avgQT=feature['avgQT']
            avgQTc=feature['avgQTc']
            RRIArray=np.diff(Ridx)*4    
            for qrs_index in range(len(QRSArray)):
                QRSwidth=QRSArray[qrs_index]
                maxpreoffset=50
                maxlastoffset=50
                nowIndex=int(Ridx[qrs_index])
                preIndex=0
                lastIndex=0
                if(nowIndex<50):
                    maxpreoffset=nowIndex
                    
                if(nowIndex+50>=len(ecg)):
                    maxlastoffset=len(ecg)-nowIndex                          
                    
                if(np.isnan(QRSwidth)):
                    for preoffset in range(maxpreoffset):
                        if(ecg[nowIndex-preoffset]==0 or (ecg[nowIndex-preoffset]>=0 and ecg[nowIndex-preoffset-1]<=0)):
                            preIndex=nowIndex-preoffset
                            break
                            
                    for lastoffset in range(maxlastoffset):
                        if(ecg[nowIndex+lastoffset]==0 or (ecg[nowIndex+lastoffset]>=0 and ecg[nowIndex+lastoffset+1]<=0)):
                            lastIndex=nowIndex+lastoffset
                            break   
                    
                    nowWidth=(lastIndex-preIndex+1)*4/1000.0
                    if(nowWidth>=0.114 and nowWidth<=0.185):  ###寬但適當的QRS回補回去
                        QRSArray[qrs_index]=nowWidth  
                
            BoolArray_large = (QRSArray >= 0.114) 
            BoolArray_small = (QRSArray <= 0.185)
            BoolArray = np.logical_and(BoolArray_large, BoolArray_small)       
            PVC_CandidateIndexArray = np.where(BoolArray)[0]       
            PVC_CandidateIndexArray = [index for index in PVC_CandidateIndexArray if (index<len(QRSArray)-1 and (Ridx[index]>500 and Ridx[index]<3000))]              
            if(len(PVC_CandidateIndexArray)==0):
                continue        
        
            FilteredRRI,BoolFilteredRRI=self.RRIFilter_PVC(RRIArray)
            medianRRI=np.median(FilteredRRI)  
            for qrs_index in PVC_CandidateIndexArray:           
                '''
                fig, ax = plt.subplots(1, figsize=(15,5))            
                ax.plot(ecg_norm*450)
                Y_Axis=np.ones(len(Ridx), dtype=int)
                Y_Axis=np.multiply(Y_Axis,100)        
                ax.plot(Ridx,Y_Axis,'bo')
                ax.plot(Ridx[qrs_index],100,'ro')  
                ax.set_ylim([-300, 500]) 
                '''
                RRI_Previous=RRIArray[qrs_index-1]
                RRI_Next=RRIArray[qrs_index]
                        
                meanLocRRI=(RRI_Previous+RRI_Next)/2
                if(abs(meanLocRRI-medianRRI)>=0.3*medianRRI): ###當下這拍前後RRI過短或過長                
                    '''
                    ax.text(2.0, -250, "Local mean-RRI is too long or too short...",fontsize=15)
                    outputFolder2 = os.path.join(export_path,'NegativePattern_Figure')
                    if not os.path.exists(outputFolder2):
                        os.makedirs(outputFolder2)
                            
                    SavedFileName=os.path.join(outputFolder2,dt.strftime('%Y%m%d')+'_'+dt.strftime('%H%M%S.%f')+'.png')
                    plt.savefig(SavedFileName)
                    '''
                    continue                
                        
                else:  ###-----Check Packet loss----              
                    PacketLossFlag=False
                    CandidatePVC_QRS=np.array(ecg[int(Ridx[qrs_index])-20:int(Ridx[qrs_index])+20])
                    for m in range(5,len(CandidatePVC_QRS)):
                        FivePointSegment=CandidatePVC_QRS[m-5:m]
                        if(sum(abs(np.diff(FivePointSegment)))==0):
                            PacketLossFlag=True
                            break                                
                                
                    if(PacketLossFlag):  ###漏封包，這拍不計算
                        continue  
                                      
                    ''''           
                    ax.text(2.0, -75, "QualtiyScore:"+str(QualtiyScore),fontsize=15)
                    ax.text(2.0, -110, "QRS width:"+str(QRSArray[qrs_index]*1000),fontsize=15)
                    ax.text(2.0,-145, "medianRRI:"+str(medianRRI),fontsize=15)
                    ax.text(2.0, -180, "RRI_Previous:"+str(RRI_Previous),fontsize=15)
                    ax.text(2.0, -215, "RRI_Next:"+str(RRI_Next),fontsize=15)
                    ax.text(2.0, -250, "Ratio:"+str(RRI_Next/RRI_Previous),fontsize=15)  
                    '''              
                    
                    if((RRI_Previous<=0.88*medianRRI) and (RRI_Next>=1.12*medianRRI) and (RRI_Next/RRI_Previous)>=1.20):
                        TotalPVCCount=TotalPVCCount+1
                        ##OccuringTime=dt+timedelta(seconds=Ridx[qrs_index]/250) 
                        ecg_sec30=ecg_pre ###前後多抓10秒最後輸出ecg 30 secs片段
                        ecg_sec30.extend(RawEcg)
                        ecg_sec30.extend(ecg_next) ###前後多抓10秒最後輸出ecg 30 secs片段
                        ecg_sec30_debasedline= BaselineRemove_Obj.BaselineRemove(ecg_sec30) 
                        rpeak_indexarray=np.where((Ridx>=500) & (Ridx<3000))
                        rpeak_output=Ridx[rpeak_indexarray] -500               
                        rpeak_output=rpeak_output.astype(int)
                        newItem=pd.DataFrame([{'user_id':UserId,'Measured_date':dt.strftime('%Y%m%d'),'Measured_time':dt.strftime('%H%M%S.%f') ,'HR':avgHR,'avgPR':avgPR,'avgQRS':avgQRS,'avgQT':avgQT,'avgQTc':avgQTc,'Label':'PVC','Location' : Ridx[qrs_index]-500, 'ab-QRSWidth':QRSArray[qrs_index]*1000,'Ecg sec10' : ecg[500:3000].tolist(), 'Ecg sec30': ecg_sec30_debasedline.tolist(),'RPeaks': rpeak_output.tolist()}])
                        PVCInformation=PVCInformation.append(newItem,ignore_index=True)
                        '''
                        outputFolder2 = os.path.join(export_path,'PositivePattern_Figure')
                        if not os.path.exists(outputFolder2):
                            os.makedirs(outputFolder2)
                            print('Create directory:'+outputFolder2)
                        
                        SavedFileName=os.path.join(outputFolder2,dt.strftime('%Y%m%d')+'_'+dt.strftime('%H%M%S.%f')+'_'+str(TotalPVCCount)+'.png')
                        plt.savefig(SavedFileName)
                        
                        for hour_index in range(24):
                            if(OccuringTime>=nowDay+timedelta(hours=hour_index) and OccuringTime<nowDay+timedelta(hours=hour_index+1)):
                                hourStr=str(hour_index)
                                nowCount=PVCStatisticData.at[dayIndex,hourStr]                        
                                PVCStatisticData.at[dayIndex,hourStr]=nowCount+1       
                    
                    else:  ###Negative
                        outputFolder2 = os.path.join(export_path,'NegativePattern_Figure')
                        if not os.path.exists(outputFolder2):
                            os.makedirs(outputFolder2)
                            print('Create directory:'+outputFolder2)
                                                        
                        ax.text(2.0,-285, "The rythm of  pre- and next-RRI is not irregular enough!",fontsize=15)
                        SavedFileName=os.path.join(outputFolder2,dt.strftime('%Y%m%d')+'_'+dt.strftime('%H%M%S.%f')+'.png')
                        plt.savefig(SavedFileName)  
                    '''           
        
        return PVCInformation 

    ####====================RRI calculate and heart rate analysis===================
    def RRIHeartRateAnalysis(self,EcgData_Debasedline,OriginalTimeArray): 
        
        Ridx_global = np.array([],dtype="int32")    
        Ridx_globaltime = np.array([], dtype='datetime64[s]') 
        SegmentCount=0    
         
        for index in range(2500,len(EcgData_Debasedline),2500):  ###每10秒一個片段，偵測R peak後整合成一個global r peak array
            SegmentCount=SegmentCount+1 
            nowEcg=EcgData_Debasedline[index-2500:index]
            EcgMaxValue=max(nowEcg)
            if(EcgMaxValue<=50):
                nowECG=nowEcg*4                
            elif(EcgMaxValue<=100):
                nowECG=nowEcg*3              
            
            Ridx=Rpeak_Obj.RPeakDetection(nowEcg)
            if(len(Ridx)>=2): ####有找到R Peak(陣列元素1是R peak個數，2之後才是R peak 位置)                
                Ridx_global = np.append(Ridx_global,np.array(Ridx[1:]+(index-2500),dtype="int32"))
               
        if(len(Ridx_global)>=15):
            RRIBuffers=[]
            RRIArray=np.diff(Ridx_global)*4
            ##RRIs = self.RRIFilter(RRIArray,medianFlag=False) ###for poincare plot
            ##allRRIs.extend(RRIs)       ###for poincare plot
            HRArray=np.full(len(RRIArray),np.nan)
            
            RRI_start = 0
            
            for i in range(len(RRIArray)):
                if ((RRIArray[i]>=285) and (RRIArray[i]<=1300)): ###hr=46~210   for exercise         
                    RRI_start = RRIArray[i]    
                    break   
            
            RRIBuffers.append(RRI_start)
            HRArray[0]=60000/RRI_start
            
            print(HRArray[0])
            
            for k in range(1,15): ##前10個設定RRI 750與HR 80
                RRIFilteredArray=self.RRIFilter(RRIArray[:k])
                if(RRIFilteredArray[-1]==RRIArray[k]):###本次RRI沒有被過濾過
                    RRIBuffers.append(RRIArray[k])
                    HRArray[k]=60000/np.mean(RRIBuffers[:len(RRIBuffers)]) 
                else:
                    HRArray[k]=HRArray[k-1]  ###使用前一個HR數值
                
                print(HRArray[k])
           
            for i in range(15,len(RRIArray)): ###每次考慮15個RRI做過濾計算
                RRIFilteredArray=self.RRIFilter(RRIArray[i-15:i])
                if(RRIFilteredArray[-1]==RRIArray[i]):###本次RRI沒有被過濾過
                    RRIBuffers.append(RRIArray[i])
                    HRArray[i]=60000/np.mean(RRIBuffers[len(RRIBuffers)-10:len(RRIBuffers)]) 
                else:
                    HRArray[i]=HRArray[i-1]  ###使用前一個HR數值
                
        else:            
            HRArray=np.array([],dtype="int32")   

        for k in range(len(Ridx_global)):
            Ridx_globaltime=np.append(Ridx_globaltime,OriginalTimeArray[0]+timedelta(seconds=(Ridx_global[k]/250)))        
       
        Ridx_globaltime=Ridx_globaltime.astype('datetime64[s]')
        delta=OriginalTimeArray[-1]-OriginalTimeArray[0]
        secondsArray= [OriginalTimeArray[0]+timedelta(seconds=i) for i in range(delta.seconds + 1)]
        Length_HRArray=len(secondsArray)
        HRArray_persecond=np.full(Length_HRArray,0,dtype="int32")
        for k in range(1,Length_HRArray): ##針對每一個秒數，但第一秒不要看
            secondindex=np.argwhere(Ridx_globaltime==secondsArray[k]) 
            if(len(secondindex)>0): ###不為空，表示此秒有R波 
                nowHR=np.nanmean(HRArray[secondindex-1])  
                if(np.isnan(nowHR)):
                    HRArray_persecond[k]=0  
                else:
                    HRArray_persecond[k]= int(nowHR)                 
            else:
                HRArray_persecond[k]=HRArray_persecond[k-1]  ###放入前一個心率數值
  
        HRArray_persecond_smoothed=np.full(Length_HRArray,0,dtype="int32")
        offset=7  ###前後7秒的HR(共15個)做平均，將HR平滑化
        for k in range(Length_HRArray): ##HR smoothing
                startindex=k-offset                
                if(startindex<0):
                    startindex=0

                endindex=k+offset
                if(endindex>Length_HRArray):
                    endindex=Length_HRArray

                HRArray_persecond_smoothed[k]=np.nanmean(HRArray_persecond[startindex:endindex])        
      
        return HRArray_persecond_smoothed 

    ####=============================心臟分析==========================
    def CardioHistoryExtractor(self,UUID):    
        cardiovascularReportList=[]
        cardiovascularReportList.append({'name': 'Report 1','date':(date.today()).strftime('%Y/%m/%d'),'score':0})  ### Report 1先設定為空白
        ReportList=[]
        ExtractingPath= os.path.join(self.BasePath,'SevenDaysReportOutput',UUID) 
        isdirFlag = os.path.isdir(ExtractingPath) 
        if(isdirFlag): ##此UUID過去分析過            
            directory=os.listdir(ExtractingPath)           
            filenameArray=[]
            
            for d in directory: ###搜尋不同日期的資料夾
                bottomdir=os.path.join(ExtractingPath,d)
                files=os.listdir(bottomdir)
                for file in files:
                    if file.endswith(".json"):                       
                        filenameArray.append(os.path.join(bottomdir,file))            
        
            if(len(filenameArray)>0): ##資料夾內有過去json檔案
                filenameArray.sort(reverse=True)                
                JsonFilePath=os.path.join(ExtractingPath,filenameArray[0])               
                with open(JsonFilePath,'r',encoding='utf-8') as f:
                    s = f.read()
                    json_object = json.loads(json.dumps(eval(s)))                   
                    
                scoreRecord=json_object['cardiovascularExamEvaluation']['scoreRecord']
                ReportList=scoreRecord['records']   
           
            if(len(ReportList)>4): ####超過4筆資料，只取前4個
                ReportLen=4
            else:
                ReportLen=len(ReportList)
            
            for i in range(ReportLen):
                ReportIndexText="Report "+str(i+2) ###編號自Report 2開始
                NowReport=ReportList[i]
                cardiovascularReportList.append({'name': ReportIndexText,'date':NowReport['date'],'score':NowReport['score']})
        
        return cardiovascularReportList

    def CardiovascularAnalysis(self,EcgData_Debasedline,OriginalTimeArray,MotionData,Age):     
        ####-----1. 心臟指標分析---------
        MotionSampleRate=2
        EcgSampleRate=250
        SecondsThr_5min=60*5  ###5分鐘
        SecondsThr_3min=60*3  ###3分鐘       
        staticScore=heartfuncScore=-1       
        MinHR=self.IntMaxValue 
        Min_RRSpreadValueFilteredArray=[]
        Min_RRSpreadValue=self.IntMaxValue    
        RRI_Milliseconds=[]    
        MaxDecreaseTime=-1 ###OriginalTimeArray[0]   ###最大HR降幅，初始時間設定為一開始
        if(len(MotionData)>0):
            StaticLabel = self.StaticAnalysis(MotionData, SampleRate=2)
        else:  ###舊版的沒有motion            
            return [-1,-1,-1]  ### Error code for no motion    
        
        DiffArr=np.diff(StaticLabel)
        StaticStartIndexArr=np.array(np.where(DiffArr == 1))   ### 1->0(靜態變成動態)
        StaticEndIndexArr=np.array(np.where(DiffArr == -1))    ### 0->1(動態變成靜態)    
        StaticEndIndexArr=StaticEndIndexArr[0][:] ##有多個結束
        StaticStartIndexArr=StaticStartIndexArr[0][:]  ##有多個開始  
        AllStaticFlag=False
        if(len(StaticEndIndexArr)==0 or len(StaticStartIndexArr)==0): ##沒有靜態轉動態，一直都是靜態，直接給整個量測範圍
            StaticStartIndexArr=[0]
            StaticEndIndexArr=[len(StaticLabel)]           
            AllStaticFlag=True    
        
        '''
        針對每個超過5分鐘靜態的時間段，計算每3分鐘的RRspread，
        取得最小 RR spread的片段，計算平靜心率並對應年齡後給予評分
        '''
        StaticStateIndexArray=[]  
        for i in range(len(StaticEndIndexArr)):
            CurrentStaticEndIndex=StaticEndIndexArr[i]
            if(AllStaticFlag): ###都是靜態的資料            
                CurrentStaticStartIndex=StaticStartIndexArr
            else: ###有動有靜的資料
                StaticStartIndex = np.where(StaticStartIndexArr <= CurrentStaticEndIndex)  ###向前找此次開始進入靜態狀態的index)
                CurrentStaticStartIndex=StaticStartIndex[0][:]             
         
            if(len(CurrentStaticStartIndex)==0 or AllStaticFlag==True):  ###都是靜態，或是找不到開始，表示是第一次進入靜態狀態，起始自index=0開始
                StaticStateIndexArray.append([0,CurrentStaticEndIndex])           
            else:
                StaticStateIndexArray.append([StaticStartIndexArr[CurrentStaticStartIndex[-1]],CurrentStaticEndIndex])  
        
        StaticStateTimeArray=[]
        for pair in StaticStateIndexArray:
            Duration=pair[1]-pair[0]      
            if(Duration>MotionSampleRate*SecondsThr_5min): ###找出超過5分鐘以上的片段
                StaticStateTimeArray.append([pair[0]/MotionSampleRate,pair[1]/MotionSampleRate]) 
     
        Static_Ridx_global = np.array([],dtype="int32") 
        for index in range(len(StaticStateTimeArray)):  ###針對每個超過5分鐘靜態的時間段，計算每3分鐘的RRspread，取得最小 RR spread的片段
            Count=0
            StartStaticsIndex=int(StaticStateTimeArray[index][0]*EcgSampleRate)+2500 ###靜態起
            EndStaticsIndex=min([int(StaticStateTimeArray[index][1]*EcgSampleRate),len(EcgData_Debasedline)]) ###靜態迄(ECG資料可能遺漏而較短，故去兩者最小)        
            for i in range(StartStaticsIndex,EndStaticsIndex, 2500): ###每10秒一個片段處理，串成global R peak index
                Count=Count+1
                nowECG=EcgData_Debasedline[i-2500+1:i]           
                EcgMaxValue=max(nowECG)
                if(EcgMaxValue<=50):
                    nowECG=nowECG*4                
                elif(EcgMaxValue<=100):
                    nowECG=nowECG*3               
                                
                Ridx=Rpeak_Obj.RPeakDetection(nowECG)
                if(len(Ridx)>=2): ####有找到R Peak(陣列元素1是R peak個數，2之後才是R peak 位置)                
                    Static_Ridx_global = np.append(Static_Ridx_global,np.array(Ridx[1:]+(Count-1)*2500+StartStaticsIndex-2500,dtype="int32"))
            
            RRI_Milliseconds=np.diff(Static_Ridx_global)*4 
            FullFlag=False
            for EndRindex in range(len(Static_Ridx_global)):  ###針對每個R peak,找到第一個與起始位置相距滿3分鐘的R peak所在位置
                if(FullFlag==False):
                    SecondsDuration=(Static_Ridx_global[EndRindex]-(StartStaticsIndex-2500+1))/EcgSampleRate               
                    if(SecondsDuration>=SecondsThr_3min): ###三分鐘
                        FullFlag=True
                    
                if(FullFlag): ###滿3分鐘後開始計算每個片段的RRspread
                    for StartRindex in range(EndRindex,0,-1): ###當下這個R peak往前計算三分鐘的片段
                        TotalRRI_Milliseconds=np.sum(RRI_Milliseconds[StartRindex:EndRindex]) 
                        if(TotalRRI_Milliseconds>=SecondsThr_3min*1000):  ###滿3分鐘，計算此片段的 RRSpread，並跳出3分鐘片段搜尋                        
                            FilteredRRI=self.RRIFilter(RRI_Milliseconds[StartRindex:EndRindex])                        
                            if(len(FilteredRRI)>=3): ###RRI至少三個才能算
                                RRSpreadValue=self.RRSpreadCalculate(FilteredRRI)                           
                                if(RRSpreadValue<Min_RRSpreadValue):
                                    Min_RRSpreadValue=RRSpreadValue
                                    Min_RRSpreadValueArray=RRI_Milliseconds[StartRindex:EndRindex]                      
                                    Min_RRSpreadValueFilteredArray=FilteredRRI  ####最小RRSpread的RRI片段                                                                                
                                break
                            ##else:
                                ##print('FilteredRRI len is less than 3!')
                                
            MinRRIDiff=self.IntMaxValue
            ##MinRRIDiffArray=[]
            MinIndex=HR=-1      
            if(len(Min_RRSpreadValueFilteredArray)>=11):
                ##print('Min_RRSpreadValueFilteredArray:',Min_RRSpreadValueFilteredArray)
                for i in range(10,len(Min_RRSpreadValueFilteredArray)): ####RRI變化量最小的10個RRI
                    RRIDiff=max(Min_RRSpreadValueFilteredArray[i-10:i])-min(Min_RRSpreadValueFilteredArray[i-10:i])
                    if(RRIDiff<MinRRIDiff):
                        MinRRIDiff=RRIDiff
                        MinIndex=i
                        
                HR=60000/np.mean(Min_RRSpreadValueFilteredArray[MinIndex-10:MinIndex])       
                ##print('HR: ',HR)
            if(HR>-1):
                if(Age>15 and Age<65):
                    if(HR<=60):
                        staticScore=95
                    elif(HR>=61 and HR<=75):
                        staticScore=85
                    elif(HR>=76 and HR<=90):
                        staticScore=75
                    elif(HR>=91 and HR<=105):
                        staticScore=65
                    elif(HR>=106):
                        staticScore=55            
                else:
                    if(HR<=55):
                        staticScore=95
                    elif(HR>=56 and HR<=70):
                        staticScore=85
                    elif(HR>=71 and HR<=85):
                        staticScore=75
                    elif(HR>=86 and HR<=100):
                        staticScore=65
                    elif(HR>=101):
                        staticScore=55
            else:
                staticScore=-1               
        ####----------------------2. 心臟效率指標-------------------------------
        '''
        找出動態5分鐘後轉靜態3分鐘的訊號片段，計算心律最高
        與最低之差，觀察差值大小與對應年齡，給於心臟效率之評分
        '''
        Dynamic2StaticIndexArray=[]
        for pair in StaticStateIndexArray:
            Duration=pair[1]-pair[0]  ##此次靜待時間起迄歷經時間長度           
            if(Duration>=MotionSampleRate*SecondsThr_5min): ###針對每個超過5分鐘靜態的時間段，找到前面動態時間超過3分鐘的片段
                NowEndDynamicIndex=pair[0]-1
                NowStartDynamicIndex=NowEndDynamicIndex-SecondsThr_3min*2
                if(NowStartDynamicIndex>0):  ###靜態的時間是在起始時間之後超過五分鐘之後發生
                    NowStaticIndexArray= [x for x in StaticLabel if x == 1]  ###找看看前面五分鐘是否存在靜態狀態
                    if(len(NowStaticIndexArray)>0):  ###前面五分鐘沒有靜態狀態，符合要抓取的動態五分鐘時段
                        NowStartStaticIndex=pair[0]
                        NowEndStaticIndex=pair[0]+SecondsThr_3min*2
                        Dynamic2StaticIndexArray.append([NowStartDynamicIndex,NowEndDynamicIndex,NowStartStaticIndex,NowEndStaticIndex])            
    
        if(len(Dynamic2StaticIndexArray)>0): 
            DiffHRArray=[]
            maxHR=-self.IntMaxValue
            minHR=self.IntMaxValue        
            for k in range(len(Dynamic2StaticIndexArray)): ####針對每個符合的動靜態片段，將其自Motion位置對應到ECG訊號位置上
                DynamicStartIndex_ECG=(Dynamic2StaticIndexArray[k][0]/2)*EcgSampleRate ### motion位置轉到ECG位置
                DynamicEndIndex_ECG=(Dynamic2StaticIndexArray[k][1]/2)*EcgSampleRate
                DynamicCount=0
                RPeak_Dynamic=np.array([],dtype="int32") 
                for m in range(int(DynamicStartIndex_ECG+2500),int(DynamicEndIndex_ECG),2500):  ###動態片段偵測R Peak              
                    DynamicCount=DynamicCount+1
                    nowECG=EcgData_Debasedline[m-2500:m-1]                   
                    EcgMaxValue=max(nowECG)
                    if(EcgMaxValue<=50):
                        nowECG=nowECG*4                
                    elif(EcgMaxValue<=100):
                        nowECG=nowECG*3   
                                    
                    nowRidx=Rpeak_Obj.RPeakDetection(nowECG)
                    if(len(nowRidx)>=2): ####有找到R Peak(陣列元素1是R peak個數，2之後才是R peak 位置)                
                        RPeak_Dynamic = np.append(RPeak_Dynamic,np.array(nowRidx[1:]+(DynamicCount-1)*2500+DynamicStartIndex_ECG-2500,dtype="int32"))                    
                              
                StaticStartIndex_ECG=(Dynamic2StaticIndexArray[k][2]/2)*EcgSampleRate
                StaticEndIndex_ECG=(Dynamic2StaticIndexArray[k][3]/2)*EcgSampleRate  
                RPeak_Static=[SR for SR in Static_Ridx_global if SR>=StaticStartIndex_ECG and SR<=StaticEndIndex_ECG]  
                RRISeq_Dynamic=np.diff(RPeak_Dynamic)*4
                RRISeq_Static=np.diff(RPeak_Static)*4 
                for d in range(0,len(RRISeq_Dynamic)-10+1,1):  ###找到10個RRI算出動態時的HR值
                    RRIFilteredSeq_Dynamic=self.RRIFilter(RRISeq_Dynamic[d:d+10-1])
                    nowDynamicHR=60000/np.mean(RRIFilteredSeq_Dynamic)               
                    if(nowDynamicHR>maxHR):
                        maxHR=nowDynamicHR                    
            
                for s in range(0,len(RRISeq_Static)-10+1,1):  ###找到10個RRI算出靜態時的HR值
                    RRIFilteredSeq_Static=self.RRIFilter(RRISeq_Static[s:s+10-1])
                    nowStaticHR=60000/np.mean(RRIFilteredSeq_Static)               
                    if(nowStaticHR<minHR):
                        minHR=nowStaticHR                        
                      
                DiffHR=maxHR-minHR              
                DiffHRArray.append(DiffHR)
                
            HR=np.max(DiffHRArray)       
            MaxDecreaseIndex=np.argmax(DiffHRArray)
            IndexinECG=(Dynamic2StaticIndexArray[MaxDecreaseIndex][0]/2)*EcgSampleRate ##motion位置轉到ECG位置
            MaxDecreaseTime=OriginalTimeArray[0]+timedelta(microseconds=(IndexinECG*4))
            ##print('DiffHRArray:',DiffHRArray,' MaxDiffHR:',HR,' MaxDecreaseIndex:',MaxDecreaseIndex,' DiffHRArray[MaxDecreaseIndex]:',DiffHRArray[MaxDecreaseIndex],'MaxDecreaseTime:',MaxDecreaseTime)
            
            if(Age>15 and Age<65):
                if(HR>40):
                    heartfuncScore=95
                elif(HR>=31 and HR<=40):
                    heartfuncScore=85
                elif(HR>=21 and HR<=30):
                    heartfuncScore=75
                elif(HR>=11 and HR<=20):
                    heartfuncScore=65
                elif(HR<=10):
                    heartfuncScore=55            
            else:
                if(HR>=33):
                    heartfuncScore=95
                elif(HR>=24 and HR<=33):
                    heartfuncScore=85
                elif(HR>=15 and HR<=23):
                    heartfuncScore=75
                elif(HR>=6 and HR<=14):
                    heartfuncScore=65
                elif(HR<=5):
                    heartfuncScore=55    
        else: ####沒有找到動態5分鐘轉靜態5分鐘的狀況，分數不加減
            heartfuncScore=-1      
        
        return [staticScore,heartfuncScore,MaxDecreaseTime]

    ####===============最大心律事件解析===========================
    def MaxHREventLoad(self,report):                       
        
        max_hr_physio_event=report['max_hr_physio']
        
        reason=(max_hr_physio_event['reason']).split(',')
        HR=((max_hr_physio_event['hr']).split(' '))[0]
        PR=((max_hr_physio_event['pr']).split(' '))[0]
        QRS=((max_hr_physio_event['qrs']).split(' '))[0]
        QT=((max_hr_physio_event['qt']).split(' '))[0]
        QTc=((max_hr_physio_event['qtc']).split(' '))[0]             
        maxHRStatistics={'date': datetime.fromtimestamp(float(max_hr_physio_event['timestamp'])/1000).strftime('%Y/%m/%d'),
                'time': datetime.fromtimestamp(float(max_hr_physio_event['timestamp'])/1000).strftime('%H:%M:%S'), ###只取到秒數
                'unit': reason[0],
                'HR': HR, 
                'PR': PR,
                'QRS': QRS,
                'QT': QT,                      
                'QTc': QTc, 
                'Irrequlars': [],
                'PVCs': [],
                'RPeaks': (max_hr_physio_event['ridx']).tolist(), 
                'sec10': max_hr_physio_event['ecgs'],
                'sec30': max_hr_physio_event['ecgs sec30']
                }
        
        return maxHRStatistics       

    ####===============心律不整事件解析===========================
    def ArrhythmiaEventLoad(self,report):    
        ir_statistics=report['ir_statistics']
        ir_statistics_perHour=report['ir_statistics_perHour']
        ir_events=report['ir_events'] 
        EcgDict=[]
        for i in range(len(ir_events)):
            RowData={}
            reason=(ir_events[i]['reason']).split(',')
            HR=((ir_events[i]['hr']).split(' '))[0]
            PR=((ir_events[i]['pr']).split(' '))[0]
            QRS=((ir_events[i]['qrs']).split(' '))[0]
            QT=((ir_events[i]['qt']).split(' '))[0]
            QTc=((ir_events[i]['qtc']).split(' '))[0]
                
            RowData={'date': datetime.fromtimestamp(float(ir_events[i]['timestamp'])/1000).strftime('%Y/%m/%d'),
                    'time': datetime.fromtimestamp(float(ir_events[i]['timestamp'])/1000).strftime('%H:%M:%S'), ###只取到秒數
                    'unit': reason[0],
                    'HR': HR, 
                    'PR': PR,
                    'QRS': QRS,
                    'QT': QT,                      
                    'QTc': QTc, 
                    'Irrequlars': ir_events[i]['eventloc'],
                    'PVCs': [],
                    'RPeaks': (ir_events[i]['ridx']).tolist(), 
                    'sec10': ir_events[i]['ecgs'],
                    'sec30': ir_events[i]['ecgs sec30']
                    }
                    
            EcgDict.append(RowData)         
        
        return EcgDict,ir_statistics,ir_statistics_perHour
        
    ####================PVC事件解析================================
    def PVCEventLoad(self,PVCInformation,ecgDict):       
        for i in range(len(PVCInformation)):
            RowData={}
            Measured_date=PVCInformation.at[i, 'Measured_date']
            date=Measured_date[0:4]+"/"+Measured_date[4:6]+"/"+Measured_date[6:8]       
            Measured_time=PVCInformation.at[i, 'Measured_time']
            time=Measured_time[0:2]+":"+Measured_time[2:4]+":"+Measured_time[4:6]
            RowData={'date': date,
                    'time': time, ###只取到秒數
                    'unit': "10mm/mV",
                    'HR': round(PVCInformation.at[i, 'HR']),
                    'PR': PVCInformation.at[i, 'avgPR'],
                    'QRS': PVCInformation.at[i, 'avgQRS'],
                    'QT': PVCInformation.at[i, 'avgQT'],                         
                    'QTc': PVCInformation.at[i, 'avgQTc'],
                    'Irrequlars': [],
                    'PVCs': [int(PVCInformation.at[i, 'Location'])],
                    'RPeaks': PVCInformation.at[i, 'RPeaks'],
                    'sec10': PVCInformation.at[i, 'Ecg sec10'],
                    'sec30': PVCInformation.at[i, 'Ecg sec30']
                    }                    
         
            ecgDict.append(RowData)       

        return ecgDict

    ####========================心律不整分析=========================
    def arrhythmia_analysis(self,user_info,data_path,start,end,export_path=""):  
        
        startTime = datetime.strptime(start,'%Y%m%d %H%M%S')
        endTime = datetime.strptime(end,'%Y%m%d %H%M%S')   

        # Parse Data
        srjFiles = [f for f in os.listdir(data_path) if f.endswith('.srj')]
        Datas = self.load_data(data_path,srjFiles,startTime,endTime)  
        if(len(Datas)==0): ##當天沒有資料
            report=[]
            return report
        
        # Analyze Data
        AD = ArrhythmiaDetection(data=Datas,userInfo=user_info)
        SavedFileName='ArrhythmiaReport_'+start.split(" ")[0]+'.xls'        
        report = AD.genReport(Mode="Arrhythmia",gpu=0,multi_proc=False,savetoxlsFlag=False,savedPath=os.path.join(export_path,SavedFileName))         
            
        """
        startDate = datetime.strptime(start,'%Y%m%d')
        endDate = datetime.strptime(end,'%Y%m%d')
        ##Dates = [(startDate+timedelta(days=i)).strftime("%Y%m%d") for i in range((endDate-startDate).days+1)] ##Paul
        Dates = [startDate]

        # Parse Data
        srjFiles = [f for f in os.listdir(data_path) if f.endswith('.srj')]
        Datas = self.load_data(data_path,srjFiles,startDate,endDate)  
        if(len(Datas)==0): ##當天沒有資料
            report=[]
            return report
        
        # Analyze Data
        AD = ArrhythmiaDetection(data=Datas,userInfo=user_info)
        SavedFileName='ArrhythmiaReport_'+start+'.xls'        
        report = AD.genReport(Mode="Arrhythmia",gpu=0,multi_proc=False,savetoxlsFlag=False,savedPath=os.path.join(export_path,SavedFileName))         
            
        return report
        """
        
        return report
    
    def arrhythmia_analysis_ori(self,user_info,data_path,start,end,export_path=""): ###原本以天為單位
        startDate = datetime.strptime(start,'%Y%m%d')
        endDate = datetime.strptime(end,'%Y%m%d')
        ##Dates = [(startDate+timedelta(days=i)).strftime("%Y%m%d") for i in range((endDate-startDate).days+1)] ##Paul
        Dates = [startDate]

        # Parse Data
        srjFiles = [f for f in os.listdir(data_path) if f.endswith('.srj')]
        Datas = self.load_data(data_path,srjFiles,startDate,endDate)  
        if(len(Datas)==0): ##當天沒有資料
            report=[]
            return report
        
        # Analyze Data
        AD = ArrhythmiaDetection(data=Datas,userInfo=user_info)
        SavedFileName='ArrhythmiaReport_'+start+'.xls'        
        report = AD.genReport(Mode="Arrhythmia",gpu=0,multi_proc=False,savetoxlsFlag=False,savedPath=os.path.join(export_path,SavedFileName))         
            
        return report
    
    ###======================三分鐘登階分析========================
    def AssessAnalysis(self,HRArray_persecond,Gender,Age):
        AssessScore=-1
        AssessIndex=-1
        HRDecreaseValue=-1 ##HRDecreaseScore=-1
        AssessScoreText=AssessEvaluationText=AssessSuggestionText=HRDecreaseText=""
        PercentageVale=-1
        Stage1Array=Stage2Array=Stage3Array=[]
        
        # [270s,180s-270s] 
        
        Stage1Value = round(np.nanmean(HRArray_persecond[240-1:270]))
        Stage2Value = round(np.nanmean(HRArray_persecond[300-1:330]))
        Stage3Value = round(np.nanmean(HRArray_persecond[360-1:390]))
                     
        Stage1Array=[Stage1Value,HRArray_persecond[179-1]-Stage1Value]
        Stage2Array=[Stage2Value,Stage1Value-Stage2Value]        
        Stage3Array=[Stage3Value,Stage2Value-Stage3Value]
        
        AssessIndex=(180*100)/(Stage1Value+Stage2Value+Stage3Value)  ##取六分半
        AssessIndex=round(AssessIndex,2)

        '''
        if(len(HRArray_persecond)>=390): ##檢查資料長度，若不足六分半，取資料最後一個點計算，若足夠六分半，取六分半的點計算
            Stage3Array=[HRArray_persecond[390],HRArray_persecond[330]-HRArray_persecond[390]]
            AssessIndex=(180*100)/((HRArray_persecond[270]+HRArray_persecond[330]+HRArray_persecond[390])*2)  ##取六分半
        else:
            Stage3Array=[HRArray_persecond[331],HRArray_persecond[331]-HRArray_persecond[-1]]
            AssessIndex=(len(HRArray_persecond)*100)/((HRArray_persecond[270]+HRArray_persecond[330]+HRArray_persecond[-1])*2)  ##取六分半
        '''
        
        HRArray_persecond_3 = (HRArray_persecond[179:-1]).tolist()
        
        HRMaxIndex = len(HRArray_persecond_3) - HRArray_persecond_3[::-1].index(max(HRArray_persecond_3)) - 1
        
        HRMaxIndex=HRMaxIndex+179
        HR_Max=HRArray_persecond[HRMaxIndex-1]
        MaxHRIndex_After=HRMaxIndex+60   ###找到三分鐘之後的最大值HR值所在位置，此位置往後再抓60秒所在的HR值
        if(MaxHRIndex_After>=len(HRArray_persecond)): ###如果超過資料長度，去最後資料點的數值
            MaxHRIndex_After=len(HRArray_persecond)-1

        HR_After=HRArray_persecond[MaxHRIndex_After-1]    
        RecoveryHRLoc=[HRMaxIndex,MaxHRIndex_After]
        
        HRDecreaseValue=int(round(HR_Max)-round(HR_After))
        
        if Age < 0: Age = 0
        if Age > 999: Age = 999
        
        if((Age>=15 and Age<65 and HRDecreaseValue>40) or (Age>=65 and HRDecreaseValue>=33)):
            HRDecreaseText="優"
            HRDecreaseScore=10
        elif((Age>=15 and Age<65 and HRDecreaseValue>=31 and HRDecreaseValue<=40) or (Age>=65 and HRDecreaseValue>=24 and HRDecreaseValue>=32)):
            HRDecreaseText="佳"
            HRDecreaseScore=5
        elif((Age>=15 and Age<65 and HRDecreaseValue>=21 and HRDecreaseValue<=30) or (Age>=65 and HRDecreaseValue>=15 and HRDecreaseValue<=23)):
            HRDecreaseText="普"
            HRDecreaseScore=0
        elif((Age>=15 and Age<65 and HRDecreaseValue>=11 and HRDecreaseValue<=20) or (Age>=65 and HRDecreaseValue>=6 and HRDecreaseValue<=14)):
            HRDecreaseText="不佳"
            HRDecreaseScore=-5
        elif((Age>=15 and Age<65 and HRDecreaseValue<=10) or (Age>=65 and HRDecreaseValue<=5)):
            HRDecreaseText="異常"
            HRDecreaseScore=-10    
        
        Age_list = [0, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5, 25.5, 30.5, 35.5, 40.5, 45.5, 50.5, 55.5, 60.5, 1000]
        
        M_Bad_list = [47.7, 50.2, 51.1 ,52.7, 52.2, 52.4, 51.1, 54.2, 55.0, 52.4, 51.9, 51.9, 50.3, 50.6, 50.6, 49.1, 48.7, 49.0, 49.9, 50.5, 50.6, 49.5, 47.6]
        M_Normal_list = [54.8, 56.5, 55.7, 57.8, 55.3, 56.9, 58.0, 59.0, 59.6, 57.8, 56.4, 56.9, 54.3, 54.8, 55.8, 53.0, 53.2, 53.8, 54.1, 55.0, 55.7, 55.7, 53.5]
        M_Good_list = [58.6, 59.9, 59.7, 63.4, 59.6, 61.5, 62.7, 64.1, 63.8, 60.3, 60.3, 60.3, 59.0, 59.7, 59.9, 56.4, 57.0, 58.9, 59.7, 59.3, 60.7, 60.9, 60.1]
        M_Great_list = [65.1, 68.6, 66.0, 68.8, 66.0, 66.5, 70.6, 69.8, 68.5, 69.6, 65.1, 68.1, 66.5, 64.7, 67.4, 62.2, 63.6, 66.0, 66.6, 66.2, 67.7, 69.6, 66.2]
        
        M_Worst_list = [ Bad - 10 for Bad in M_Bad_list ]
        M_Best_list = [ Great + 10 for Great in M_Great_list ]
        
        F_Bad_list = [45.1, 49.9, 50.2, 47.5, 47.9, 51.3, 48.7, 48.4, 48.1, 46.2, 45.8, 46.3, 47.7, 47.8, 47.9, 49.0, 49.1, 48.4, 49.5, 47.2, 44.7, 42.8, 34.9]
        F_Normal_list = [51.2, 53.5, 53.7, 52.7, 51.3, 54.3, 53.2, 53.2, 51.8, 49.7, 49.5, 50.4, 50.3, 51.8, 51.5, 52.6, 53.6, 52.7, 54.3, 54.6, 53.5, 53.4, 50.4]
        F_Good_list = [56.3, 58.6, 57.4, 56.4, 55.4, 58.3, 56.0, 57.6, 55.7, 53.3, 53.3, 54.3, 55.0, 56.7, 56.5, 56.5, 58.2, 56.6, 58.8, 58.9, 60.1, 60.5, 57.1]
        F_Great_list = [62.8, 63.5, 63.5, 63.3, 60.5, 64.8, 61.5, 64.5, 63.5, 61.5, 58.6, 60.5, 61.2, 61.6, 63.9, 61.4, 63.7, 63.1, 63.4, 65.6, 67.9, 65.9, 68.5]
        
        F_Worst_list = [ Bad - 10 for Bad in F_Bad_list ]
        F_Best_list = [ Great + 10 for Great in F_Great_list ]
        
        if Gender == "男":
            
            for i_age, p_age in enumerate(Age_list[:-1]):
                
                n_age = Age_list[i_age + 1]
                
                if p_age <= Age < n_age:
                    
                    m_worst = M_Worst_list[i_age]
                    m_bad = M_Bad_list[i_age]
                    m_normal = M_Normal_list[i_age]
                    m_good = M_Good_list[i_age]
                    m_great = M_Great_list[i_age]
                    m_best = M_Best_list[i_age]
                    
                    if AssessIndex < m_worst: AssessIndex = m_worst
                    if AssessIndex > m_best: AssessIndex = m_best
                    
                    if AssessIndex <= m_bad:
                        AssessScore = -10
                        PercentageVale = 3 + 10*(AssessIndex - m_worst)/(m_bad - m_worst)
                        
                    elif m_bad < AssessIndex <= m_normal:
                        AssessScore = -5
                        PercentageVale = 13 + 18*(AssessIndex - m_bad)/(m_normal - m_bad)
                        
                    elif m_normal < AssessIndex <= m_good:
                        AssessScore = 0
                        PercentageVale = 31 + 38*(AssessIndex - m_normal)/(m_good - m_normal)
                        
                    elif m_good < AssessIndex <= m_great:
                        AssessScore = 5
                        PercentageVale = 69 + 18*(AssessIndex - m_good)/(m_great - m_good)
                        
                    else :
                        AssessScore = 10
                        PercentageVale = 87 + 11*(AssessIndex - m_great)/(m_best - m_great)
                
                    break
        
        else :
            
            for i_age, p_age in enumerate(Age_list[:-1]):
                
                n_age = Age_list[i_age + 1]
                
                if p_age <= Age < n_age:
                    
                    f_worst = F_Worst_list[i_age]
                    f_bad = F_Bad_list[i_age]
                    f_normal = F_Normal_list[i_age]
                    f_good = F_Good_list[i_age]
                    f_great = F_Great_list[i_age]
                    f_best = F_Best_list[i_age]
                    
                    if AssessIndex < f_worst: AssessIndex = f_worst
                    if AssessIndex > f_best: AssessIndex = f_best
                    
                    if AssessIndex <= f_bad:
                        AssessScore = -10
                        PercentageVale = 3 + 10*(AssessIndex - f_worst)/(f_bad - f_worst)
                        
                    elif f_bad < AssessIndex <= f_normal:
                        AssessScore = -5
                        PercentageVale = 13 + 18*(AssessIndex - f_bad)/(f_normal - f_bad)
                        
                    elif f_normal < AssessIndex <= f_good:
                        AssessScore = 0
                        PercentageVale = 31 + 38*(AssessIndex - f_normal)/(f_good - f_normal)
                        
                    elif f_good < AssessIndex <= f_great:
                        AssessScore = 5
                        PercentageVale = 69 + 18*(AssessIndex - f_good)/(f_great - f_good)
                        
                    else :
                        AssessScore = 10
                        PercentageVale = 87 + 11*(AssessIndex - f_great)/(f_best - f_great)
                
                    break
        
        PercentageVale = round(PercentageVale)
        
        if(AssessScore==10):
            AssessScoreText="優"
            AssessEvaluationText="瞬間高強度指標屬於中上等級，心肺循環效率高，可供應大部分狀況下全身足夠的血氧需求。且回歸靜態後，因心臟效率優秀，可以快速降回平穩心率。"
            AssessSuggestionText="可持續透過瞬間高強度訓練，持續維持爆發力，如跳繩、高強度間歇訓練(HIIT)、TABATA...等。訓練時透過調整訓練強度，維持最大心率大於85%以上。"
        elif(AssessScore==5):
            AssessScoreText="佳"
            AssessEvaluationText="瞬間高強度指標屬於中上等級，心肺循環效率佳，可供應大部分狀況下全身足夠的血氧需求。且回歸靜態後，因心臟效率佳，降回平穩心率的速度較一般人好。"
            AssessSuggestionText="可透過增加高強度訓練課程，提升爆發力，如跳繩、高強度間歇訓練(HIIT)、TABATA...等。訓練時透過調整訓練強度，維持最大心率大於85%以上。"
        elif(AssessScore==0):
            AssessScoreText="普通"
            AssessEvaluationText="瞬間高強度指標屬於一般等級，心肺循環效率正常，可供應一般狀況下全身足夠的血氧需求。回歸靜態後，心臟降回平穩的速度符合該年齡層的一般水準。"
            AssessSuggestionText="建議平常可增加高強度的運動量，如跳繩、爬樓梯三層樓以上、中高強度TABATA運動、開合跳...等。訓練時確保最大心率需大於75%以上"
        elif(AssessScore==-5):
            AssessScoreText="不佳"
            AssessEvaluationText="瞬間高強度指標低於一般同齡人，心肺循環效率較差，一般狀況下瞬間高強度活動可能會出現喘的狀況。回歸靜態後，心跳速率降回平穩所花費的時間較該年齡層長。"
            AssessSuggestionText="建議平常需培養高強度的活動量，如跳繩、爬樓梯三層樓以上。透過日常活動中增加高強度活動後，再搭配中強度的間歇訓練、TABATA課程...等。訓練時最大心率須確保大於70%以上。"
        elif(AssessScore==-10 and HRDecreaseText != "異常"):
            AssessScoreText="差"
            AssessEvaluationText="瞬間高強度指標嚴重低於一般同齡人，心肺功能較差，當出現瞬間高強度活動時，可能會出現上氣不接下氣的問題。待坐下後，心跳速率會花比大部分人還久的時間才能緩和。"
            AssessSuggestionText="建議諮詢專業醫師或健身教練，循序漸進鍛鍊心肺適能"
        else :
            AssessScoreText="異常"
            AssessEvaluationText="瞬間高強度指標量測結果異常。"
            AssessSuggestionText="建議重新進行測試。"
        
        return AssessScore,AssessIndex,AssessScoreText,PercentageVale,Stage1Array,Stage2Array,Stage3Array,HRDecreaseValue,HRDecreaseText,RecoveryHRLoc,AssessEvaluationText,AssessSuggestionText,HRDecreaseScore
   

    def ExerciseAnalysis(self,HRArray_persecond_exercise,Age):
        HR_Maximum=220-Age
        ExerciseScore=0
        ExerciseScoreText=ExerciseEvaluationText=ExerciseSuggestionText=""
        duration_80=sum(np.argwhere(HRArray_persecond_exercise>=HR_Maximum*0.8))
        HR_Max=np.max(HRArray_persecond_exercise)       
        
        if(duration_80>15*60 and duration_80<10*60):
            ExerciseScore=-5
            ExerciseScoreText="不佳"
            ExerciseEvaluationText="心臟效率較同齡人差，心肺耐力僅能勉強提供身體完成一個緊急狀況的處置，若時間拉長或強度提升，身體可能會不堪負荷。"
            ExerciseSuggestionText="建議諮詢專業教練，依據身體素質進行課程規劃，循序漸進提升心肺耐力，避免貿然提高訓練強度造成風險。"
        elif((HR_Max>=HR_Maximum*0.9 and HR_Max<=HR_Maximum*0.95 and duration_80>=5*60 and duration_80<=10*60) or
             (HR_Max>=HR_Maximum*0.85 and HR_Max<=HR_Maximum*0.9 and duration_80>=5*60) or
             (HR_Max>=HR_Maximum*0.8 and HR_Max<=HR_Maximum*0.85 and duration_80>=10*60)):
            ExerciseScore=0
            ExerciseScoreText="普通"
            ExerciseEvaluationText="心臟效率屬於一般等級，心肺耐力與同齡人相仿，心血管對於應付身體的活動強度變化時，養分供給速度一般，可能不耐長時間活動。"
            ExerciseSuggestionText="培養適合的有氧運動習慣，並持續維持，以增加心肺循環能力。並適時增加中高強度運動訓練，提升中高強度心臟耐受力。"           
        elif((HR_Max>=HR_Maximum*0.95 and duration_80>=5*60 and duration_80<=10*60) or
             (HR_Max>=HR_Maximum*0.9 and HR_Max<=HR_Maximum*0.95 and duration_80>=10*60 and duration_80<=15*60)):
            ExerciseScore=5
            ExerciseScoreText="佳"
            ExerciseEvaluationText="心肺耐力屬於中上等級，代表心血管調適能力足以應付一般狀況下身體活動強度的變化。持續高強度的耐受度較一般人好，對於持續的高強度負荷，全身的養分供給及時。"
            ExerciseSuggestionText="培養適合的有氧運動習慣，並持續維持。適合運動：30分鐘以上快走。或可維持心率於70~80%最大心率且持續30分鐘以上的運動。"
        elif((HR_Max>=HR_Maximum*0.95 and duration_80>=10*60) or (HR_Max>=HR_Maximum*0.9 and HR_Max<=HR_Maximum*0.95 and duration_80>=15*60)):
            ExerciseScore=10
            ExerciseScoreText="優"
            ExerciseEvaluationText="心肺耐力屬於優良等級，代表心血管調適能力足以應付身體活動強度的變化。且對於持續高強度的耐受度強，對於持續的高強度負荷，全身的養分供給快速。"
            ExerciseSuggestionText="培養適合的中高強度運動習慣，並持續維持。適合運動：30分鐘間歇衝刺、7分速跑步30分鐘。"
        else :
            ExerciseScore=-10
            ExerciseScoreText="異常"
            ExerciseEvaluationText="高強度耐力指標量測結果異常。"
            ExerciseSuggestionText="建議重新進行測試。"

        HR_Distribution=[int(HR_Maximum*1.1),int(HR_Maximum),int(HR_Maximum*0.9),int(HR_Maximum*0.8),int(HR_Maximum*0.7),int(HR_Maximum*0.6),int(HR_Maximum*0.5),int(HR_Maximum*0.4),int(HR_Maximum*0.3)]

        return ExerciseScore,ExerciseScoreText,ExerciseEvaluationText,ExerciseSuggestionText,HR_Distribution

    ####=====================主要呼叫函式====================================
    def ExerciseAnalysisReport(self,assessStartTime,assessEndTime,exerciseStartTime,exerciseEndTime,userInfo):   
        UUID=userInfo['id']    
        ##產生報告輸出資料夾
        outputFolder0 = os.path.join(self.BasePath,'ExerciseReportOutput',UUID) 
        if not os.path.exists(outputFolder0):
            os.makedirs(outputFolder0)
        
        reportdate_str=(date.today()).strftime('%Y%m%d')  
        outputFolder1 = os.path.join(outputFolder0,reportdate_str)
        if not os.path.exists(outputFolder1):
            os.makedirs(outputFolder1) 
            
        UUID_tempPath = os.path.join(self.DB, UUID)
        
        if not os.path.exists(UUID_tempPath):
            os.makedirs(UUID_tempPath) 
      
        jsontempletePath=os.path.join(self.BasePath,'exercise_jsonformat_v01.json')
        
        with open(jsontempletePath,'r',encoding="utf-8") as readfile:  ## Reading from json file
            jsontemplatefile = json.load(readfile)      
        
        jsontemplatefile["irregularHeartRateEcgs"]=[]
        
        assessStartTime_datetime = datetime.strptime(assessStartTime,'%Y%m%d %H%M%S')
        assessEndTime_datetime = datetime.strptime(assessEndTime,'%Y%m%d %H%M%S')
        exerciseStartTime_datetime = datetime.strptime(exerciseStartTime,'%Y%m%d %H%M%S')
        exerciseEndTime_datetime = datetime.strptime(exerciseEndTime,'%Y%m%d %H%M%S')
        
        RealStartTime = assessStartTime
        
        if exerciseStartTime_datetime < assessStartTime_datetime:
            RealStartTime = exerciseStartTime
        
        RealEndTime = assessEndTime
        
        if exerciseEndTime_datetime > assessEndTime_datetime:
            RealEndTime = exerciseEndTime
        
        testingPeriod=RealStartTime[0:4]+"/"+RealStartTime[4:6]+"/"+RealStartTime[6:8]+" "+RealStartTime[9:11]+":"+RealStartTime[11:13]+":"+RealStartTime[13:15]+"~"+RealEndTime[0:4]+"/"+RealEndTime[4:6]+"/"+RealEndTime[6:8]+" "+RealEndTime[9:11]+":"+RealEndTime[11:13]+":"+RealEndTime[13:15]
        Age=int(float(userInfo['age'])) 
        Gender=userInfo['gender']  
        IrrCountAssess=IrrCountExercise=MaxHRLoc_exercise=ExerciseAvgScore=AssessScore=ExerciseScore=PercentageVale=-1
        ExerciseAvgScoreText=AssessScoreText=ExerciseScoreText=AssessEvaluationText=AssessSuggestionText=""
        Stage1Array=Stage2Array=Stage3Array=[]  
        
        ##---------三分鐘登階分析----------       
        startDate=assessStartTime[0:8] 
        endDate=assessEndTime[0:8]     
        UnzipFileNameList_assess=self.search_upzip(db_path=self.DB,target=UUID,start=startDate,end=endDate,export_path=UUID_tempPath)
        document_process_(UUID_tempPath, UUID_tempPath)   
        arrhythmia_report_assess=self.arrhythmia_analysis(user_info=userInfo,data_path=UUID_tempPath,start=assessStartTime,end=assessEndTime) ###三分鐘登階心律不整偵測
        if(len(arrhythmia_report_assess)==0):
            ecgDict_assess=ir_statistics_assess=ir_statistics_perHour_assess=[]
            IrrCountAssess=0
        else:
            ecgDict_assess,ir_statistics_assess,ir_statistics_perHour_assess=self.ArrhythmiaEventLoad(arrhythmia_report_assess)
            IrrCountAssess=sum(ir_statistics_assess)

        if(IrrCountAssess==0):
            IrrAssessScore=10
        elif(IrrCountAssess<=2):
            IrrAssessScore=5            
        elif(IrrCountAssess<=6):
            IrrAssessScore=0            
        elif(IrrCountAssess<=12):
            IrrAssessScore=-5
        else:
            IrrAssessScore=-10                         
          
        '''
        PVCInformation=self.PVC_Report(user_info=userInfo,data_path=UUID_tempPath,start=startTime,end=endTime)
        if(len(PVCInformation)>0):
            ecgDict=self.PVCEventLoad(PVCInformation,ecgDict)  
        '''
                                      
        OriginalTimeArray_assess,ConcateEcgArray_assess=self.DataConcate(UnzipFileNameList_assess,assessStartTime,assessEndTime,userInfo["id"]) 
        
        if(len(ConcateEcgArray_assess)>0): ####有量測資料  
        
            EcgData_Debasedline_assess=BaselineRemove_Obj.BaselineRemove(ConcateEcgArray_assess)    
            HRArray_persecond_assess=self.RRIHeartRateAnalysis(EcgData_Debasedline_assess,OriginalTimeArray_assess)
            Length_HRArray_Assess=len(HRArray_persecond_assess)
            if(Length_HRArray_Assess>390):    ###資料太長
                HRArray_persecond_assess=HRArray_persecond_assess[0:390]
            elif(Length_HRArray_Assess<390):  ###資料太短
                HRArray_persecond_assess=np.append(HRArray_persecond_assess,np.full([1,390-Length_HRArray_Assess],HRArray_persecond_assess[-1]))

            AssessScore,AssessIndex,AssessScoreText,PercentageVale,Stage1Array,Stage2Array,Stage3Array,HRDecreaseValue,HRDecreaseText,RecoveryHRLoc,AssessEvaluationText,AssessSuggestionText,HRDecreaseScore=self.AssessAnalysis(HRArray_persecond_assess,Gender,Age)
        
        else :
            print("Failed. No Assess ECG Data.")
            return {'status':False, 'message':'No Assess ECG Data.'}
                       
        ##jsontemplatefile["irregularHeartRateEcgs"]=ecgDict_assess            
       
        ###-------運動分析-------------
        startDate=exerciseStartTime[0:8] 
        endDate=exerciseEndTime[0:8]    
        UnzipFileNameList_exercise=self.search_upzip(db_path=self.DB,target=UUID,start=startDate,end=endDate,export_path=UUID_tempPath)            
        document_process_(UUID_tempPath, UUID_tempPath)   
        arrhythmia_report_exercise=self.arrhythmia_analysis(user_info=userInfo,data_path=UUID_tempPath,start=exerciseStartTime,end=exerciseEndTime)
        
        ###運動心律不整偵測
        if(len(arrhythmia_report_exercise)==0):
            ecgDict_exercise=ir_statistics_exercise=ir_statistics_perHour_exercise=[]
            IrrCountExercise=0
        else:
            
            ecgDict_exercise,ir_statistics_exercise,ir_statistics_perHour_exercise=self.ArrhythmiaEventLoad(arrhythmia_report_exercise)
            IrrCountExercise=sum(ir_statistics_exercise)
            
            arrhythmia_report_exercise=self.arrhythmia_analysis(user_info=userInfo,data_path=UUID_tempPath,start=exerciseStartTime,end=exerciseEndTime)
            
            if len(arrhythmia_report_exercise['max_hr_physio']) >= 10:
                maxHRStatistics_exercise=self.MaxHREventLoad(arrhythmia_report_exercise)
                
            else :
                print("Failed. Too Many Bad Signals.")
                return {'status':False, 'message':'Too Many Bad Signals.'}
                
        if(IrrCountExercise==0):
            IrrExerciseScore=10
            
        elif(IrrCountExercise<=5):
            IrrExerciseScore=5       
            
        elif(IrrCountExercise<=10):
            IrrExerciseScore=0        
            
        elif(IrrCountExercise<=20):
            IrrExerciseScore=-5
            
        else:
            IrrExerciseScore=-10    
        
        if len(arrhythmia_report_exercise['max_hr_physio']) == 0:
            IrrExerciseScore=-10
            IrrAssessScore=-10
        
        OriginalTimeArray_exercise,ConcateEcgArray_exercise=self.DataConcate(UnzipFileNameList_exercise,exerciseStartTime,exerciseEndTime,userInfo["id"]) 
        
        if(len(ConcateEcgArray_exercise)>0): ####有量測資料  
            EcgData_Debasedline_exercise=BaselineRemove_Obj.BaselineRemove(ConcateEcgArray_exercise) 
            HRArray_persecond_exercise=self.RRIHeartRateAnalysis(EcgData_Debasedline_exercise,OriginalTimeArray_exercise) 
            Length_HRArray_Exercise=len(HRArray_persecond_exercise)
            
            if(Length_HRArray_Exercise>1800):    ###資料太長
                HRArray_persecond_exercise=HRArray_persecond_exercise[0:1800]
                
            elif(Length_HRArray_Exercise<1800):  ###資料太短
                HRArray_persecond_exercise=np.append(HRArray_persecond_exercise,np.full([1,1800-Length_HRArray_Exercise],HRArray_persecond_exercise[-1]))

            MaxHRLoc_exercise=np.argmax(HRArray_persecond_exercise)
            ExerciseScore,ExerciseScoreText,ExerciseEvaluationText,ExerciseSuggestionText,HR_Distribution=self.ExerciseAnalysis(HRArray_persecond_exercise,Age)               

        ecgDict=[]
        ecgDict.extend(ecgDict_exercise)
        ecgDict.extend(ecgDict_assess)
        jsontemplatefile["irregularHeartRateEcgs"]=ecgDict   
        ExerciseAvgScore=60+AssessScore+IrrAssessScore+ExerciseScore+IrrExerciseScore+HRDecreaseScore
        
        if ExerciseAvgScore < 55:
            ExerciseAvgScore = 55
        
        if ExerciseAvgScore > 95:
            ExerciseAvgScore = 95
        
        if(ExerciseAvgScore<=67):
            ExerciseAvgScoreText="不佳"
        elif(ExerciseAvgScore<83):
            ExerciseAvgScoreText="佳"
        else:
            ExerciseAvgScoreText="優秀"
        
        ####--------------write json Template File----------------------------------------
        jsontemplatefile['header']={
        "report": "S001V1",
        "reportName": "BEATINFO HEALTH REPORT",
        "testingPeriod": testingPeriod,
        "reportDate": (date.today()).strftime('%Y/%m/%d'), 
        "alternativeName": "Alternative Name",
        "secondRow": "Second Row"
        }
    
        jsontemplatefile['userInfo']={
        "name": userInfo['name'],
        "birthday": userInfo['birthday'],  
        "gender": userInfo['gender'], 
        "age": Age,    
        "height": userInfo['height']+" cm",  
        "weight": userInfo['weight']+" kg"   
        }        
       
        jsontemplatefile["ExerciseReport"]={
        "score" : ExerciseAvgScore, 
        "scoreText": ExerciseAvgScoreText, 
        "AssessIndex": {
            "score": AssessIndex, ##AssessScore,  
            "scoreText": AssessScoreText, 
            "description" : "透過瞬間⾼負荷運動進⾏⾝體質量評估，瞬間⾼強度運動如三分鐘登階，能於短時間內讓⼼率提⾄相對高點，且測試後須⽴刻坐下靜⽌，查看過程中⼼臟是否能夠隨⾝體養分供應需求進⾏快速調節。",
            "evaluation": AssessEvaluationText,
            "suggestion": AssessSuggestionText
        },
        "ExerciseIndex": {
            "score": ExerciseScore, 
            "scoreText": ExerciseScoreText,   
            "description" : "透過30分鐘以上的運動，並且過程中讓⼼率維持在80%以上連續5分鐘。透過持續⾼強度運動，可藉此發現當⼼臟是否因運動時需氧量增加⽽造成失衡。",
            "evaluation": ExerciseEvaluationText,    
            "suggestion": ExerciseSuggestionText,   
            "hr_distribution": HR_Distribution
        },
        "IrregularStatistic":{
            "IrrinAssess": IrrCountAssess,
            "IrrinExercise": IrrCountExercise
        }, 
    
        "notes": ""
       }
                
        jsontemplatefile["AssessIndexReport"]={
        "score": AssessIndex, ###AssessScore, 
        "scoreText": AssessScoreText,
        "Stage1": Stage1Array, 
	    "Stage2": Stage2Array, 
	    "Stage3": Stage3Array, 
        "Percentage": PercentageVale, 
        "HRperSec":HRArray_persecond_assess.tolist(),
        "RecoveryHRLoc":RecoveryHRLoc,
        "RecoveryHRValue":{
            "HRDecrese":HRDecreaseValue,
            "Text": HRDecreaseText
            }
       }

        jsontemplatefile['ExerciseIndexReport']={
       "HRperSec": HRArray_persecond_exercise.tolist(),
       "MaxHRLoc":MaxHRLoc_exercise,
       "maxHRStatistics": maxHRStatistics_exercise
        }       

        JsonSavedName = "Report_%s.json" %(datetime.now().strftime("%Y%m%d%H")+"("+userInfo["id"]+")")
        JsonSavedPath=os.path.join(outputFolder1,JsonSavedName)
        with open(JsonSavedPath,'w',encoding='utf-8') as f:
            f.write((str)(jsontemplatefile))
        
        if(os.path.exists(JsonSavedPath)):
            print('Finished! jsonfilepath:',JsonSavedPath)
            return {'status':True, 'message':JsonSavedPath}            
        else:
            return {'status':False, 'message':'No Document'}
    
    
if __name__ == '__main__':
   
    exportPath = os.path.abspath("G:/共用雲端硬碟/奇翼醫電_執行專案/智慧防疫好幫手/報告產生器")
    workSheetPath = os.path.join(exportPath,"防疫好幫手_分析報告清單-Dennis.xlsx")
    workSheet = pd.read_excel(workSheetPath)
    toDo = workSheet[workSheet['分析進度']=='待分析']
    print(toDo)   
    
    DBPath="C:\\Users\\User\\Desktop\\DataDB"   
    ExerciseReport_Obj=ExerciseReportGenerator(DBPath)   
    for index in toDo.index:
        '''
        assessStartTime = str(int(toDo.loc[index,"登階開始"]))
        assessEndTime = str(int(toDo.loc[index,"登階結束"]))
        exerciseStartTime =str(int(toDo.loc[index,"運動開始"]))
        exerciseEndTime = str(int(toDo.loc[index,"運動結束"]))
        '''        
        assessStartTime='20220803 103107'  
        assessEndTime='20220803 104208' 
        exerciseStartTime='20220723 082000'
        exerciseEndTime='20220723 085000'

        UUID = toDo.loc[index,'UUID']
        print('UUID Index:',index, ' UUID:',UUID)
       
        if not isinstance(UUID, str):
            UUID = str(int(UUID))
        if '\n' in UUID:
            UUID = UUID.replace('\n','')
        print("\n********* UUID: %s, Date:%s~%s *********" %(UUID,assessStartTime,assessEndTime,exerciseStartTime,exerciseEndTime))
        
        userInfo = {
            "id":UUID,
            "name":toDo.loc[index,'用戶姓名'],
            "email":toDo.loc[index,'信箱'],
            "gender":toDo.loc[index,'性別'],
            "height":str(toDo.loc[index,'身高']),
            "weight":str(toDo.loc[index,'體重']),
            "birthday":toDo.loc[index,'生日'].strftime("%Y/%m/%d"),
            "age":str(toDo.loc[index,'年齡'])
        }
        
        jsonfile_outputpath=ExerciseReport_Obj.ExerciseAnalysisReport(assessStartTime,assessEndTime,exerciseStartTime,exerciseEndTime,userInfo) ##call function
           
            


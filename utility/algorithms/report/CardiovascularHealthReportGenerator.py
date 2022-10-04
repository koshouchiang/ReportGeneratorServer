import os
import sys
import tqdm

import numpy as np
import pandas as pd
import ujson as json
import hrvanalysis as hrv
import matplotlib.pyplot as plt

from zipfile import ZipFile
from scipy import interpolate
from matplotlib.patches import Ellipse
from datetime import date, datetime, timedelta

if os.path.dirname(__file__) not in sys.path: sys.path.append(os.path.dirname(__file__))
for path in sys.path: print(path)

from . import ahrs
from .Beatinfo_Srj_Time_Parse import document_process_
from .Arrhythmia_Pack.ecg import baseline as BaselineRemove_Obj
from .Arrhythmia_Pack.ecg import Fiducial_v5 as Fiducial_Obj
from .Arrhythmia_Pack.ecg import Rpeak as Rpeak_Obj
from .Arrhythmia_Pack.ecg import score as Score_Obj
from .Arrhythmia_Pack.arrhythmia.analysis_v2 import ArrhythmiaDetection

class CardiovascularHealthReportGenerator:
    
    def __init__(self,DBPath): 
        self.BasePath=os.path.dirname(__file__)
        self.DB=self.tempDB=DBPath
        self.IntMaxValue=1000000           
    ####=========================檔案解壓縮===============================
    def search_upzip(self,db_path,target,start,end,export_path):
        startDT = datetime.strptime(start,'%Y%m%d')
        endDT = datetime.strptime(end,'%Y%m%d')
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
                ###print('Folder:',Folder)
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
                                UnzipFileNameList.append(filename[0:len(filename)]+'.srj')  ### Dennis 新增
                                ##print("Filename:",filename[0:len(filename)]+'.srj')
        ##t2 = time()
        ##print("  Elapsed time: %.2fs" %(t2-t1))
        return UnzipFileNameList

    ####=================================Data concate============================
    def DataConcate(self,FileList,NowDay,UUID):   
        OriginalTimeArray=[]
        ConcateEcgArray=[] 
        MotionDataArray=[]
        
        FileList = sorted(FileList)
        
        NowDayEnd=NowDay+timedelta(days = 1)    
        for index in range(len(FileList)):
            ##NowFilePath=os.path.join(self.BasePath,'RawData暫存',UUID,FileList[index])
            NowFilePath=os.path.join(self.DB,UUID,FileList[index])
            
            with open(NowFilePath,'r') as srj:
                line = srj.readline()
                while line:
                    data = json.loads(line)
                    motions = data['rows']['motions']
                    ecgs=data['rows']['ecgs']
                    tt=data['tt']
                    tt=int(tt/1000)
                    nowday=datetime.fromtimestamp(tt)
                    if(nowday>=NowDay and nowday<=NowDayEnd): ###針對當天的時段Concate Data
                        OriginalTimeArray.append(nowday)                
                        for m in motions:
                            MotionDataArray.append(m)
                    
                        for n in ecgs:
                            ConcateEcgArray.append(n) 
                
                    line = srj.readline()          
                
        return OriginalTimeArray,ConcateEcgArray,MotionDataArray    

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
        endDT = endDT + timedelta(hours=24)
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
    
     ####===============報告筆數篩選=================================
    def report_filter( self, ecgDict, ir_statistics, ir_statistics_perHour ):
        
        noflat_ecgDict = []
        new_ecgDict = []
        ecgDict_filter = []
        ir_statistics = [0]
        ir_statistics_perHour = [ 0 for i in range(24)]
        
        for ecg_info in ecgDict:
            
            ecgs = ecg_info['sec10']
            
            p_ecg = ecgs[0]
            
            same_count = 1
            max_count = 1
            
            for n_ecg in ecgs[1:]:
                
                if p_ecg == n_ecg:
                    same_count += 1
                else :
                    if same_count > max_count:
                        max_count = same_count
                    same_count = 1
                
                p_ecg = n_ecg
                    
            if max_count < 40:
                noflat_ecgDict.append(ecg_info)
        
        if len(noflat_ecgDict) > 1:
        
            Ir_num = 0
            PVC_num = 0
            
            for ecg_i, p_info in enumerate(noflat_ecgDict[:-1]): 
                
                duplicated_count = 0
                
                for ecg_j, n_info in enumerate(noflat_ecgDict[ecg_i+1:]):
                    
                    if p_info['date'] == n_info['date'] and p_info['time'] == n_info['time']: 
                        duplicated_count += 1
                    
                if duplicated_count == 0:
                    
                    if len(p_info['PVCs']) != 0: 
                        PVC_num += 1
                    
                    new_ecgDict.append(p_info)
            
            if len(noflat_ecgDict[-1]['PVCs']) != 0: 
                PVC_num += 1
            
            new_ecgDict.append(noflat_ecgDict[-1])
            
            for ecg_info in new_ecgDict:
                ir_statistics_perHour[int(ecg_info['time'][0:2])] += 1
            
            New_num = len(new_ecgDict)
            
            ir_statistics.append(New_num)
            
            Ir_num = New_num - PVC_num
            
            ir_ratio_num = 0
            pvc_ratio_num = 0
            
            if Ir_num + PVC_num > 10:
                
                ir_ratio_num = round(10*Ir_num/New_num)
                pvc_ratio_num = round(10*PVC_num/New_num)
                
            else :
                
                ir_ratio_num = Ir_num
                pvc_ratio_num = PVC_num
            
            if ir_ratio_num != 0:
                ecgDict_filter.extend(new_ecgDict[:ir_ratio_num])
            
            if pvc_ratio_num != 0:
                ecgDict_filter.extend(new_ecgDict[-pvc_ratio_num:])
        
        elif len(noflat_ecgDict) == 1:
            
            ir_statistics_perHour[int(noflat_ecgDict[0]['time'][0:2])] += 1
            ir_statistics.append(1)
            
            ecgDict_filter.append(noflat_ecgDict[0])
        
        ecgDict_string = ['HR', 'PR', 'QRS', 'QT', 'QTc']
        
        for i, ecg_info in enumerate(ecgDict_filter):
            if ecg_info['PVCs'] != 0:
                for i_string in ecgDict_string:
                    if pd.isnull(ecg_info[i_string]):
                        ecgDict_filter[i][i_string] = '--'
                    else : 
                        ecgDict_filter[i][i_string] = str(ecg_info[i_string])
        
        return ecgDict_filter, ir_statistics, ir_statistics_perHour
    
    ####===================================RRIFilter============================
    def RRIFilter(self,RRIArray,medianFlag=True):
        FilteredRRIArray=[]
        FinalFilteredRRIArray=[]
        for i in range(len(RRIArray)):  
            if((RRIArray[i]>=245) and (RRIArray[i]<=2100)):            
                FilteredRRIArray.append(RRIArray[i])
        
        if(medianFlag): ##另外加上中值濾波   
            if(len(FilteredRRIArray)>0):
                RRIMedian=np.median(FilteredRRIArray)
                for i in range(len(FilteredRRIArray)):
                    if((FilteredRRIArray[i]>=(RRIMedian-0.55*RRIMedian)) and (FilteredRRIArray[i]<=RRIMedian+0.62*RRIMedian)):
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
        
    ####========================潘凱圖分析==============================
    def poincare_figure(self,ReportTime,allRRIs,save_path,sd_feature=True):
        fig = plt.figure(figsize=(12,12))
        plt.ioff()
        ax = fig.add_subplot(1,1,1)
        if len(allRRIs) > 1:
            RRI = np.array(allRRIs)
            minRRI, maxRRI = min(RRI), max(RRI)
            X, Y = RRI[:-1], RRI[1:] # unit: second
            ax.scatter(X, Y, c='b', s=2)
            ax.set_xlabel("RR_n (ms)", fontsize=15)
            ax.set_ylabel("RR_n+1 (ms)", fontsize=15)
            ax.set_xlim(minRRI, maxRRI)
            ax.set_ylim(minRRI, maxRRI)

            if sd_feature:
                # Calculate SD1 and SD2
                dict_sd1_sd2 = hrv.get_poincare_plot_features(RRI.tolist())
                sd1 = dict_sd1_sd2["sd1"]
                sd2 = dict_sd1_sd2["sd2"]
                mean_nni = np.mean(RRI)

            # Plot ellipse contour
                ells = Ellipse(xy=(mean_nni, mean_nni), width=2 * sd2 + 1,
                    height=2 * sd1 + 1, angle=45, linewidth=2,
                    fill=False)
                ax.add_patch(ells)

                # Plot background color of ellipse
                ells = Ellipse(xy=(mean_nni, mean_nni), width=2 * sd2,
                    height=2 * sd1, angle=45)
                ells.set_alpha(0.2)
                ells.set_facecolor("blue")
                ax.add_patch(ells)

                # Plot axis of ellipse by SD1 and SD2
                arrow_style = {'length_includes_head':True,'head_width':15,'head_length':15,'linewidth':3}
                sd1_arrow = ax.arrow(mean_nni,mean_nni,-sd1*np.sqrt(2)/2,sd1*np.sqrt(2)/2,
                            ec='r',fc="r",label="SD1",**arrow_style)
                sd2_arrow = ax.arrow(mean_nni,mean_nni,sd2*np.sqrt(2)/2,sd2*np.sqrt(2)/2,
                            ec='g',fc="g",label="SD2",**arrow_style)
                ax.legend(handles=[sd1_arrow, sd2_arrow], fontsize=12, loc="lower right")

                # Plot auxiliary lines
                line_style = {'linestyle':'--','color':'k','linewidth':1,'alpha':0.75}
                text_style = {'ha':'left','va':'bottom','alpha':0.75}
                for per in [1,1.1,1.2,1.3]:
                    if per > 1:
                        ax.plot([0,maxRRI],[0,maxRRI*per],**line_style)
                        ax.plot([0,maxRRI],[0,maxRRI/per],**line_style)
                        per_str = "%d%%"%(per*100-100)
                        ax.text(maxRRI/per,maxRRI,per_str,**text_style)
                        ax.text(maxRRI,maxRRI/per,per_str,**text_style)
                    else:
                        ax.plot([0,maxRRI],[0,maxRRI],**line_style)
                        ax.text(maxRRI,maxRRI,'0%',**text_style)

        # Save figure
        fig.tight_layout()
        save_name = "Poincare_%s.jpg" %(ReportTime.strftime("%Y%m%d%H"))
        poincareimagepath=os.path.join(save_path,save_name)
        kargs = {'dpi':300,'facecolor':'white','bbox_inches':'tight'}
        fig.savefig(poincareimagepath,**kargs)
        plt.close(fig)       
        
        return poincareimagepath

    ####======================PVC 偵測===============================
    def PVC_Report(self,user_info,data_path,start,end,export_path=""):
        UserId=user_info['id']
        startDate = datetime.strptime(start,'%Y%m%d')
        endDate = datetime.strptime(end,'%Y%m%d')
        Dates = [(startDate+timedelta(days=i)).strftime("%Y%m%d") for i in range((endDate-startDate).days+1)]    
        ##PVCStatisticData = pd.DataFrame({'Date':Dates})
        PVCInformation = pd.DataFrame()    
        '''
        for hour_index in range(24):
            HourStr=str(hour_index)
            PVCStatisticData[HourStr] = 0        
        '''

        #### Parse Data
        srjFiles = [f for f in os.listdir(data_path) if f.endswith('.srj')]
        data = self.load_data(data_path,srjFiles,startDate,endDate)   
        fs=250  ##ECG Sampling Rate
        TotalPVCCount=0
        ##OccuringCountArray=np.zeros(24)  ###計算每個小時發生幾次的陣列
        
        score_list = []
        
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
            
            MinValue=np.min(ecg)
            MaxValue=np.max(ecg)
            
            if(MinValue==MaxValue):
                continue
            
            RpeakArray=Rpeak_Obj.RPeakDetection(ecg,DetectionMode=1)
            Ridx=RpeakArray[1:len(RpeakArray)]   
            
            if len(Ridx) < 10 or len(Ridx) > 35 or Ridx[1] > 2*fs or Ridx[-1] < 3500-2*fs:
                continue            
           
            RRIArray = np.diff(Ridx)*1000/250
            RRIArray.astype('int32')
            
            score0 = Score_Obj.PatternClustering(ecg,Ridx)
            score1 = Score_Obj.AreaRatio(ecg, Ridx)
            QualtiyScore = score0 * score1
            
            if(QualtiyScore < 85): ##訊號品質不好不分析
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
                        newItem=pd.DataFrame([{'user_id':UserId,'Measured_date':dt.strftime('%Y%m%d'),'Measured_time':dt.strftime('%H%M%S.%f') ,'HR':avgHR,'avgPR':avgPR,'avgQRS':avgQRS,'avgQT':avgQT,'avgQTc':avgQTc,'Label':'PVC','Location' : Ridx[qrs_index]-500, 'ab-QRSWidth':QRSArray[qrs_index]*1000,'Ecg sec10' : ecg[500:3000].tolist(), 'Ecg sec30': ecg_sec30_debasedline.tolist(), 'Score':QualtiyScore, 'RPeaks': rpeak_output.tolist()}])
                        
                        
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
                    
        if PVCInformation.shape[0] > 0:
            PVCInformation = PVCInformation.sort_values(by='Score', ascending=True)    
            PVCInformation = PVCInformation.drop(columns='Score')
            PVCInformation = PVCInformation.reset_index(drop=True)    
        
        return PVCInformation 

    ####====================RRI calculate and heart rate analysis===================
    def RRIHeartRateAnalysis(self,EcgData_Debasedline,OriginalTimeArray,allRRIs): 
        HR_Min=HR_Max=HR_Mean=-1
        Ridx_global = np.array([],dtype="int32")    
        Ridx_hourtime_global = np.array([],dtype="int32")  
        Ridx_minutetime_global = np.array([],dtype="int32")   
        SegmentCount=0
        HR_Min_perHour=np.full(24,-1,dtype="float32")
        HR_Max_perHour=np.full(24,-1,dtype="float32") 
        HR_Mean_perHour=np.full(24,-1,dtype="float32") 
        evaluationTime_MinuteperHour=np.full(24,0,dtype="float32")
        
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
                Ridx_hourtime=np.full(len(Ridx[1:]),OriginalTimeArray[SegmentCount].hour) 
                Ridx_hourtime_global=np.append(Ridx_hourtime_global,Ridx_hourtime)
                Ridx_minutetime=np.full(len(Ridx[1:]),OriginalTimeArray[SegmentCount].minute) 
                Ridx_minutetime_global=np.append(Ridx_minutetime_global,Ridx_minutetime)         
        
        if(len(Ridx_global)>=11):
            RRIArray=np.diff(Ridx_global)*4
            RRIs = self.RRIFilter(RRIArray,medianFlag=False) ###for poincare plot
            allRRIs.extend(RRIs)       ###for poincare plot
            HRArray=np.full(len(RRIArray),np.nan)         
            ###Ridx_hourtime_global[0:11]=-1  ###前十個設定為-1,不被之後的計算考慮
            for i in range(10,len(RRIArray)): ###每次考慮10個RRI，離群值過濾後剩下的RRI計算心律
                RRIFilteredArray=self.RRIFilter(RRIArray[i-10:i])
                if(len(RRIFilteredArray)>=5): ###超過一半以上被保留                
                    HRArray[i]=60000/np.mean(RRIFilteredArray)              
            
            HR_Min=round(np.nanmin(HRArray)) ####一整天的Min
            HR_Max=round(np.nanmax(HRArray)) ####一整天的Max  
            HR_Mean=round(np.nanmean(HRArray)) ####一整天的Mean
            for hour in range(24): ###針對每一個小時
                hourindexArray=np.argwhere(Ridx_hourtime_global == hour)-1  ###找出此小時的RRI index, RRI和Ridex index差一個           
                if(np.any(hourindexArray)):
                    evaluationTime_MinuteperHour[hour]=len(np.unique(Ridx_minutetime_global[hourindexArray[:]+1]))
                    ###print('evaluationTime_MinuteperHour[',str(hour),']:',evaluationTime_MinuteperHour[hour])
                    hr_min=np.nanmin(HRArray[hourindexArray])
                    hr_max=np.nanmax(HRArray[hourindexArray])
                    hr_mean=np.nanmean(HRArray[hourindexArray])
                    if(not np.isnan(hr_min)):
                        HR_Min_perHour[hour]=round(hr_min) 
                    
                    if(not np.isnan(hr_max)):
                        HR_Max_perHour[hour]=round(hr_max) 
                        
                    if(not np.isnan(hr_mean)):    
                        HR_Mean_perHour[hour]=round(hr_mean)       
        else:
            HR_Min=-1
            HR_Max=-1   
            HR_Mean=-1
            
        return [HR_Min,HR_Max,HR_Mean,HR_Min_perHour,HR_Max_perHour,HR_Mean_perHour,evaluationTime_MinuteperHour] 

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

    ####===============心律不整事件解析===========================
    def ArrhythmiaEventLoad(self,report, ecgDict):    
        ir_statistics=report['ir_statistics']
        ir_statistics_perHour=report['ir_statistics_perHour']
        ir_events=report['ir_events'] 
        
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
                    
            ecgDict.append(RowData)         
        
        return ecgDict,ir_statistics,ir_statistics_perHour
        
    ####================PVC事件解析================================
    def PVCEventLoad(self,PVCInformation,ecgDict): 
        pvc_statistics=pvc_statistics_perHour=[]        
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
        ##report = AD.genReport(Mode="Arrhythmia",gpu=1,multi_proc=True,savetoxlsFlag=False,savedPath=os.path.join(export_path,SavedFileName))
        report = AD.genReport(Mode="Arrhythmia",gpu=0,multi_proc=False,savetoxlsFlag=False,savedPath=os.path.join(export_path,SavedFileName))         
            
        return report

    ####=====================主要呼叫函式====================================
    def HealthReportGenerator(self,startTime, endTime, userInfo, version, CardioHistoricalList=[]):
        
        startDate = startTime.split(" ")[0]
        endDate = endTime.split(" ")[0]
        
        UUID=userInfo['id']
        
        ### 產生七日報告資料夾
        outputFolder1 = os.path.join(self.BasePath,'SevenDaysReportOutput',UUID, (date.today()).strftime('%Y%m%d')) 
        if not os.path.exists(outputFolder1): os.makedirs(outputFolder1) 
        
        ### 讀取資料庫位置並於未有對應資料時以產生空資料夾給予空值形式避免中斷
        UUID_tempPath = os.path.join(self.DB, UUID)
        if not os.path.exists(UUID_tempPath): os.makedirs(UUID_tempPath)     

        ### 讀取報告結果基礎格式
        jsontempletePath=os.path.join(self.BasePath,'7days_health_jsonformat_v01.json')
        with open(jsontempletePath,'r',encoding="utf-8") as readfile: jsontemplatefile = json.load(readfile)      
        jsontemplatefile["irregularHeartRateStatistics"] = []
        
        ### !!! 是否後移
        testingPeriod=startDate+"~"+endDate
        
        ### 產生以日期為間隔的列表
        CheckInDate_datatime = datetime.strptime(startDate, '%Y%m%d')
        CheckOutDate_datatime = datetime.strptime(endDate, '%Y%m%d')
        DayTimeArray = [CheckInDate_datatime + timedelta(days=x) for x in range((CheckOutDate_datatime - CheckInDate_datatime).days + 1)]
        
        Age=int(float(userInfo['age']))       
        Whole_HRMin=self.IntMaxValue
        Whole_HRMax=-self.IntMaxValue
        Whole_HRMean=0
        Whole_HRMeanCount=0
        heartRate7DaysDict=[]
        Whole_staticScore=Whole_heartfuncScore=-1
        Whole_MaxDecreaseTime=MaxDecreaseTimeIndex=HRMinTimeIndex=DayCount=-1 
        allRRIs=[] ####for poincare plot
        UnzipFileNameList=self.search_upzip(db_path=self.DB,target=UUID,start=startDate,end=endDate,export_path=UUID_tempPath)        
        
        document_process_(UUID_tempPath, UUID_tempPath)
        
        day_count = 0
        
        for NowDay in DayTimeArray:
            MaxDecreaseTimeIndex=MaxDecreaseTime=-1

            arrhythmia_report=self.arrhythmia_analysis(user_info=userInfo,data_path=UUID_tempPath,start=NowDay.strftime("%Y%m%d"),end=(NowDay+timedelta(days=0)).strftime("%Y%m%d")) ###心律不整偵測
            
            PVCInformation=self.PVC_Report(user_info=userInfo,data_path=UUID_tempPath,start=NowDay.strftime("%Y%m%d"),end=(NowDay+timedelta(days=0)).strftime("%Y%m%d"))
            
            ecgDict=[]
            ir_statistics=[]
            ir_statistics_perHour=[]
            
            if(len(arrhythmia_report)!=0):
                ecgDict,ir_statistics,ir_statistics_perHour=self.ArrhythmiaEventLoad(arrhythmia_report,ecgDict)
                
            ##PVCInformation=self.PVC_Report(user_info=userInfo,data_path=self.DB,start=NowDay.strftime("%Y%m%d"),end=(NowDay+timedelta(days=0)).strftime("%Y%m%d"))
            if(len(PVCInformation)>0):
                ecgDict=self.PVCEventLoad(PVCInformation,ecgDict)  
            
            ### 將心律不整個數與心室早期收縮個數按比例篩選成10筆
            ecgDict_filter, ir_statistics, ir_statistics_perHour = self.report_filter( ecgDict, ir_statistics, ir_statistics_perHour )
            
            HR_Mean_perHour=np.full(24,-1,dtype="float32")
            HR_Min_perHour=np.full(24,-1,dtype="float32")
            HR_Max_perHour=np.full(24,-1,dtype="float32")
            evaluationTime_MinuteperHour=np.full(24,0,dtype="float32")        
            HR_Max_WholeDay=HR_Min_WholeDay=HR_Mean_WholeDay=-1 
            
            OriginalTimeArray,ConcateEcgArray,MotionDataArray=self.DataConcate(UnzipFileNameList,NowDay,userInfo["id"]) 
            
            if len(OriginalTimeArray) < 720:
                continue
            else :
                day_count += 1
            
            if(len(ConcateEcgArray)>0): ####有量測資料               
                DayCount=DayCount+1
                EcgData_Debasedline=BaselineRemove_Obj.BaselineRemove(ConcateEcgArray)  ####ECG基線拉直               
                [staticScore,heartfuncScore,MaxDecreaseTime]=self.CardiovascularAnalysis(EcgData_Debasedline,OriginalTimeArray,MotionDataArray,Age) 
                    
                if(staticScore!=-1 and staticScore>Whole_staticScore):
                    Whole_staticScore=staticScore
                        
                if(heartfuncScore!=-1 and heartfuncScore>Whole_heartfuncScore):
                    Whole_heartfuncScore=heartfuncScore
                    Whole_MaxDecreaseTime=MaxDecreaseTime ###取成績最好的那天所在最大HR降幅時間
                    MaxDecreaseTimeIndex=DayCount
                        
                [HR_Min,HR_Max,HR_average,HR_Min_perHour,HR_Max_perHour,HR_Mean_perHour,evaluationTime_MinuteperHour]=self.RRIHeartRateAnalysis(EcgData_Debasedline,OriginalTimeArray,allRRIs)
                    
                if(HR_Max>Whole_HRMax):
                    Whole_HRMax=HR_Max

                if(HR_Min!=-1 and HR_Min<Whole_HRMin):
                    Whole_HRMin=HR_Min
                    HRMinTimeIndex=DayCount

                if(HR_average!=-1):
                    Whole_HRMeanCount=Whole_HRMeanCount+1
                    Whole_HRMean=Whole_HRMean+HR_average
                        
                Positive_HR_Min_Array = np.array([ num for num in HR_Min_perHour if num > -1 ])              
                Positive_HR_Mean_Array= np.array([ num for num in HR_Mean_perHour if num > -1 ])
                HR_Max_WholeDay=np.nanmax(HR_Max_perHour) ##當天最大心率
                
                if(len(Positive_HR_Min_Array))>0:
                    HR_Min_WholeDay=np.nanmin(Positive_HR_Min_Array)   ###(HR_Min_perHour) ##當天最小心率
                    
                if(len(Positive_HR_Mean_Array)>0):
                    HR_Mean_WholeDay=float("{:.2f}".format(np.mean(Positive_HR_Mean_Array)))   ###(HR_Mean_perHour) ##當天平均心率                
                
                ratio=0.0
                
                if(np.nansum(evaluationTime_MinuteperHour)/60>0):
                    ratio=float("{:.2f}".format(sum(ir_statistics)/(np.nansum(evaluationTime_MinuteperHour)/60)))   
                
                evaluationTime=float("{:.2f}".format((np.nansum(evaluationTime_MinuteperHour)/60))) 
                if(evaluationTime>0): ###有量測的那一天才紀錄
                    heartRate7DaysDict.append({
                    "date":NowDay.strftime('%m/%d'),
                    "evaluationTime": evaluationTime, ###分鐘轉換為小時，取小數後一位
                    "average":HR_average,
                    "min":HR_Min,
                    "max":HR_Max,
                    "maxDecrease":False,
                    "minHR":False,
                    "irregular":{"number":int(sum(ir_statistics)),"rate":ratio}}) 
                else:
                    DayCount=DayCount-1

            ###else:               
                ##heartRate7DaysDict.append({"date":NowDay.strftime('%m/%d'),"evaluationTime":0.0,"average":-1,"min":-1,"max":-1,"maxDecrease":False,"minHR":False,"irregular":{"number":0,"rate":0}})
                
            heartRate24HoursDict=[]
            MinHRValue_perHour=self.IntMaxValue
            HRMinTimeIndex_perHour=-1
            for hourindex in range(24): ##針對每一天計算每個小時心率最大、最小等，以及每一小時量測多少分鐘
                if(HR_Min_perHour[hourindex]!=-1 and HR_Min_perHour[hourindex]<MinHRValue_perHour):##找出每天在哪一個小時有最小HR
                    MinHRValue_perHour=HR_Min_perHour[hourindex]
                    HRMinTimeIndex_perHour=hourindex
                
                if(evaluationTime_MinuteperHour[hourindex]==0):
                    ratio_perHour=0.0
                else:
                    ratio_perHour=float("{:.2f}".format(ir_statistics_perHour[hourindex]/evaluationTime_MinuteperHour[hourindex]))                
                    
                if(len(ir_statistics_perHour)==0):
                    number_perHour=0
                else:
                    number_perHour=ir_statistics_perHour[hourindex]
                            
                heartRate24HoursDict.append({
                        "hour": str(hourindex+1).zfill(2),
                        "evaluationTime": float(str(evaluationTime_MinuteperHour[hourindex]).zfill(2)),
                        "average": HR_Mean_perHour[hourindex],
                        "max": HR_Max_perHour[hourindex],
                        "min": HR_Min_perHour[hourindex],
                        "maxDecrease": False, ##先設定為Fasle
                        "minHR": False,       ##先設定為Fasle
                        "irregular": {
                            "number": number_perHour,
                            "rate": ratio_perHour
                    }
                    })                
            
            if(HRMinTimeIndex_perHour!=-1):
                heartRate24HoursDict[HRMinTimeIndex_perHour]["minHR"]=True
            
            ##if(Whole_MaxDecreaseTime!=-1): ##找出最大HR降幅發生時間
            if(MaxDecreaseTime!=-1):
                MaxDecreaseTimeIndex_hour=int(MaxDecreaseTime.hour)    ##int(Whole_MaxDecreaseTime.hour)    
                print('MaxDecreaseTimeIndex_hour:',MaxDecreaseTimeIndex_hour)      
                heartRate24HoursDict[MaxDecreaseTimeIndex_hour]["maxDecrease"]=True        
            
            if(HR_Mean_WholeDay>-1): ##當天有量測才會記錄
                jsontemplatefile['irregularHeartRateStatistics'].append({
                    "date": NowDay.strftime('%m/%d'),
                    "maxHR": HR_Max_WholeDay,
                    "minHR": HR_Min_WholeDay,
                    "averageHR": HR_Mean_WholeDay,
                    "heartRate24Hours": heartRate24HoursDict,
                    "ecgs":ecgDict_filter})
        
        if day_count < 7:
            
            """
            if version == "A002V2":
                return {'status':False, 'message':'The Number of the Day is Not Enough'}
            """
            
            if version == "A002V2":
                return {'status':False, 'message':'The Number of the Day is Not Enough', 'record':[]}
        
        if(MaxDecreaseTimeIndex!=-1):        
            heartRate7DaysDict[MaxDecreaseTimeIndex]["maxDecrease"]=True
        
        if(HRMinTimeIndex!=-1):
            heartRate7DaysDict[HRMinTimeIndex]["minHR"]=True
            
        if(Whole_HRMeanCount>0):
            Whole_HRMean=int(Whole_HRMean/Whole_HRMeanCount) ###七天平均HR值的平均數        
        ####-----------------------總分計算--------------------------
        cardiovascularScoreLevel=staticScoreLevel=heartfuncScoreLevel=""
        if(Whole_staticScore==-1 and Whole_heartfuncScore==-1):    
            cardiovascularScore=-1
        elif(Whole_staticScore!=-1 and Whole_heartfuncScore!=-1):          
            cardiovascularScore=(Whole_staticScore+Whole_heartfuncScore)/2
        else:
            cardiovascularScore=np.max([Whole_staticScore,Whole_heartfuncScore])
        
        if(cardiovascularScore<67):
            cardiovascularScoreLevel="不佳"
    
        elif(cardiovascularScore>=67 and cardiovascularScore<83):
            cardiovascularScoreLevel="佳"
        elif(cardiovascularScore>=83):
            cardiovascularScoreLevel="優秀"        
            
        if(Whole_staticScore<60):
            staticScoreLevel="異常"
            staticEvaluationTxt = "靜態心率嚴重偏高，需要進一步尋求專業醫療協助。"
            staticSuggestionTxt = "需盡快前往尋求專業醫療協助，並且在沒有專業醫療評估之前，避免進行強度過高的運動。"
        elif(Whole_staticScore>=60 and Whole_staticScore<70):
            staticScoreLevel="不佳"
            staticEvaluationTxt = "靜態心率偏高，身體可能處於發炎或疲憊狀態。若長期皆屬於偏高狀態，則代表心肺循環系統不足以供應全身養分需求。需先排除是否有咖啡因攝取過量，或是心血管疾病之問題。"
            staticSuggestionTxt = "尋求專業醫療協助，確認是否有血壓過高、動脈硬化、心臟瓣膜、發燒....等有可能造成長期心肺循環效率不佳的問題。改善睡眠時間與效率，並於睡眠前增加放鬆冥想或泡熱水澡幫助放鬆。運動方面則需培養適合的有氧運動習慣，並持續維持。適合運動：30分鐘以上快走。或可維持心率於60~70%最大心率且持續30分鐘以上的運動。"
        elif(Whole_staticScore>=70 and Whole_staticScore<80):
            staticScoreLevel="普"
            staticEvaluationTxt = "靜態心率輕微偏高，身體可能處於發炎或疲憊狀態。若長期皆屬於偏高狀態，則代表心肺循環系統不足以供應全身養分需求。"
            staticSuggestionTxt = "改善睡眠時間與效率，並於睡眠前增加放鬆冥想或泡熱水澡幫助放鬆。運動方面則需培養適合的有氧運動習慣，並持續維持。適合運動：30分鐘以上快走。或可維持心率於60~70%最大心率且持續30分鐘以上的運動。"
        elif(Whole_staticScore>=80 and Whole_staticScore<90):
            staticScoreLevel="佳"
            staticEvaluationTxt = "靜態心臟指標屬於中上等級，心肺循環效率高，可供應大部分狀況下全身足夠的血氧需求。"
            staticSuggestionTxt = "培養適合的有氧運動習慣，並持續維持。適合運動：30分鐘以上快走。或可維持心率於60~70%最大心率且持續30分鐘以上的運動。"
        elif(Whole_staticScore>=90):
            staticScoreLevel="優"        
            staticEvaluationTxt = "靜態心臟指標屬於優良等級，代表靜態時心肺循環系統效率高，能以更少的跳動次數即可達成全身的血氧供應。"
            staticSuggestionTxt = "繼續維持既有健康生活習慣，並隨身體狀況調整適合的運動，以維持優良的攝氧與代謝效率。"
            
        if(Whole_heartfuncScore<60):
            heartfuncScoreLevel="異常"
            funcEvaluationTxt = "心臟效率嚴重偏低，需進一步尋求專業醫師協助。"
            funcSuggestionTxt = "需盡快前往尋求專業醫療協助，並且在沒有專業醫療評估之前，避免進行強度過高的運動。"
        elif(Whole_heartfuncScore>=60 and Whole_heartfuncScore<70):
            heartfuncScoreLevel="不佳"
            funcEvaluationTxt = "心臟效率偏低，需先確認日常生活中是否偏靜態活動，缺少如爬樓梯、搬重物、快走...等的活動而造成心臟負荷需求偏低。若活動狀態非偏靜態，但出現心臟反應效率偏低的狀況，則表示心血管調適能力無法負荷生活中強度較高的活動，有可能造成活動後會喘的狀況。"
            funcSuggestionTxt = "需尋求專業醫療協助，檢測心跳恢復率，進階確認是否有恢復異常的現象。若有異常則建議繼續進行相關心血管檢測，確認發生之根本原因。若非因生活型態造成，則需培養適合的有氧運動習慣，並持續維持，以增加心肺循環能力。"
        elif(Whole_heartfuncScore>=70 and Whole_heartfuncScore<80):
            heartfuncScoreLevel="普"
            funcEvaluationTxt = "心臟反應效率輕微偏低，需先確認生活中是否缺少如爬樓梯、搬重物、快走...等的活動而造成心臟負荷需求偏低。若活動狀態並非偏靜態，但出現反應效率輕微偏低，則代表心血管調適彈性較差或心肺循環能力較差，當活動轉靜態後，仍需持續供應大量養分以供代謝。"
            funcSuggestionTxt = "若平時活動偏靜態，可於日常生活中增加爬樓梯、快走等中低強度活動。若非因生活型態造成，則需培養適合的有氧運動習慣，並持續維持，以增加心肺循環能力。"
        elif(Whole_heartfuncScore>=80 and Whole_heartfuncScore<90):
            heartfuncScoreLevel="佳"
            funcEvaluationTxt = "心臟效率屬於中上等級，心血管調適能力良好，可因應一般活動變化所需的養分供給進行快速的調整。"
            funcSuggestionTxt = "培養適合的有氧運動習慣，並持續維持，以增加心肺循環能力。並適時增加中高強度運動訓練，提升中高強度心臟耐受力。"
        elif(Whole_heartfuncScore>=90):
            heartfuncScoreLevel="優"
            funcEvaluationTxt = "心臟效率屬於優良等級，代表心血管調適能力足以應付身體的活動強度變化，當身體活動量降低時，心肺循環即可及時降低供給。"
            funcSuggestionTxt = "繼續維持既有健康生活習慣，並隨身體狀況調整適合的運動，以確保心血管系統維持優良的彈性調適空間。"
        
        """
        if version == "A002V2":
            CardioHistoricalList=self.CardioHistoryExtractor(userInfo["id"])
            CardioHistoricalList[0]['score']=cardiovascularScore
        """
            
        if version == "A002V2":
        
            CardioHistoricalList.insert(0, {'date': startDate[0:4] + '/' + startDate[4:6] + '/' + startDate[6:8], 'score': cardiovascularScore})
            
            for i, CardioHistorical in enumerate(CardioHistoricalList):
                CardioHistoricalList[i].update({'name': 'Report ' + str(i+1)})
        
        poincareimagepath=self.poincare_figure(datetime.now(),allRRIs=allRRIs,save_path=outputFolder1) ##poincare
        
        ####--------------write json Template File----------------------------------------
        jsontemplatefile['header']={
        "report": "A002V2",
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
        
        jsontemplatefile['notes']=""

        jsontemplatefile['cardiovascularHealthReport']={
            "score" : cardiovascularScore,
            "scoreText": cardiovascularScoreLevel,
            "staticHeartIndex": {
            "score": Whole_staticScore,  
            "scoreText": staticScoreLevel,
            "description" : "評估使用者靜態狀況下安靜心率值可得知其心肺適能狀態，心肺適能愈好，攝氧能力愈佳、靜態心率會愈慢。當靜態心率偏高時，可分長期與短期；短期偏高則屬於當下身體狀態較差，長期靜態心率偏高則屬於心肺適能較差。",
            "evaluation": staticEvaluationTxt,
            "suggestion": staticSuggestionTxt
            },
            "heartFunctionIndex": {
            "score": Whole_heartfuncScore,
            "scoreText": heartfuncScoreLevel,
            "description" : "評估使用者心臟的減速速率是指當心率速度從高速降低時間愈短，代表其心血管循環系統效率愈高。愈高的效率表示當身體因活動變化，而需要心血管系統供給更多或減少養分、氧氣時，心血管系統有優秀的調整彈性進行配合。",
            "evaluation": funcEvaluationTxt,
            "suggestion": funcSuggestionTxt
            }
        }
            
        jsontemplatefile['cardiovascularExamEvaluation']={
            "scoreRecord": {
            "description": "",
            "records": CardioHistoricalList           
            },        
            "abnormalHeartRateStatistic":{
            "reportDate": (date.today()).strftime('%Y/%m/%d'),   
            "startDate": startDate, 
            "endDate": endDate,    
            "maxHR": Whole_HRMax,
            "minHR": Whole_HRMin, 
            "averageHR": Whole_HRMean,
            "heartRate7Days": heartRate7DaysDict
            } 
        }      
        
       
        imagePath=os.path.join(outputFolder1,poincareimagepath)
        jsontemplatefile['poincare']={
        "description": "",
        "suggestion": "",
        "imagePath": imagePath            
        }     
        
        JsonSavedName = "Report_%s.json" %(datetime.now().strftime("%Y%m%d%H")+"("+userInfo["id"]+")")
        JsonSavedPath=os.path.join(outputFolder1,JsonSavedName)
        with open(JsonSavedPath,'w',encoding='utf-8') as f:
            f.write((str)(jsontemplatefile))
        
        """
        if version == "A002V2":
            
            if(os.path.exists(JsonSavedPath)):
                return {'status':True, 'message':JsonSavedPath}            
            else:
                return {'status':False, 'message':'No Document'}
        """
        
        if version == "A002V2":
        
            for i, CardioHistorical in enumerate(CardioHistoricalList):
                CardioHistoricalList[i].pop('name')
            
            if len(CardioHistoricalList) > 6:
                history_length = 6
            else :
                history_length = len(CardioHistoricalList)
        
            if(os.path.exists(JsonSavedPath)):
                return {'status':True, 'message':JsonSavedPath, 'record':CardioHistoricalList[:history_length]}            
            else:
                return {'status':False, 'message':'No Document', 'record':[]}
        
if __name__ == '__main__':
    
    exportPath = os.path.abspath("G:/共用雲端硬碟/奇翼醫電_執行專案/智慧防疫好幫手/報告產生器")
    workSheetPath = os.path.join(exportPath,"防疫好幫手_分析報告清單_展元.xlsx")
    workSheet = pd.read_excel(workSheetPath)
    toDo = workSheet[workSheet['分析進度']=='待分析']
    print(toDo)   
    
    DBPath="C:\\Users\\SWM-Jared\\Desktop\\DataDB"   
    HealthReport_Obj=CardiovascularHealthReportGenerator(DBPath)   
    for index in toDo.index:
        startDate = str(int(toDo.loc[index,'入住']))
        endDate = str(int(toDo.loc[index,'退房']))
        UUID = toDo.loc[index,'UUID']
        print('UUID Index:',index, ' UUID:',UUID)
       
        if not isinstance(UUID, str):
            UUID = str(int(UUID))
        if '\n' in UUID:
            UUID = UUID.replace('\n','')
        print("\n********* UUID: %s, Date:%s~%s *********" %(UUID,startDate,endDate))

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
        
        jsonfile_outputpath=HealthReport_Obj.HealthReportGenerator(startDate,endDate,userInfo) ##call function
        print('Finished! jsonfilepath:', jsonfile_outputpath)
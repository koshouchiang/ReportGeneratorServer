import pandas as pd
import shutil
from datetime import date, datetime, timedelta
from zipfile import ZipFile
from torch import int32
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

from . import ahrs
from .Beatinfo_Srj_Time_Parse import document_process_
from .Arrhythmia_Pack.ecg import baseline as BaselineRemove_Obj
from .Arrhythmia_Pack.ecg import Fiducial_v5 as Fiducial_Obj
from .Arrhythmia_Pack.ecg import Rpeak as Rpeak_Obj
from .Arrhythmia_Pack.ecg import score as Score_Obj
from .Arrhythmia_Pack.arrhythmia.analysis_v2 import ArrhythmiaDetection
###=====sleep analysis of simple Medel========
from .Arrhythmia_Pack.ecg.baseline import BaselineRemove
from .ahrs.filters.madgwick import Madgwick
from .ahrs.common.orientation import acc2q, q2R
##=======sleep analysis of AI Model==========
from .Sleep_Strap import sleep_v2 as sleep
from multiprocessing import Pool

class multi_process:
    def __init__(self, timeTable, fileNames, data_path, export_path):
        self._initialize()
        self._load_schedule(timeTable, fileNames, data_path, export_path)

    def _initialize(self):
        self.timeTable = []
        self.fileNames = []
        self.dataPath = ""
        self.exportPath = ""
        self.Output = []

    def _load_schedule(self,timeTable,fileNames,data_path,export_path):
        self.timeTable = timeTable
        self.fileNames = fileNames
        self.dataPath = data_path
        self.exportPath = export_path

    def _read_srj_file(self,file_path):
        lines = []
        with open(file_path,'r') as srj:
            row = srj.readline()
            while row:
                lines.append(row)
                row = srj.readline()

        # Check if there any repeated json strings
        output = set(lines)
        return output

    ##======================????????????====================
    def sleepdata_concate(self,Data):
        prevtt = 0
        startTT = 0
        ECG = []
        Motion = []
        MotionFs = 0
        for i,data in enumerate(Data):
            tt = data['tt']/1000
            ecgs = data['rows']['ecgs']
            motions = data['rows']['motions']
            if i == 0:
                startTT = tt
                prevtt = tt
                ECG = ecgs
                Motion = motions
                MotionFs = 2 if len(motions)/10 < 10 else 20
            else:
                diff_tt = tt - prevtt - 10
                if diff_tt > 5:
                    zero_ecg = np.zeros(int(diff_tt*250)).tolist()
                    ECG.extend(zero_ecg)
                    zero_motion = np.zeros((int(diff_tt*2),10)).tolist()
                    Motion.extend(zero_motion)
                ECG.extend(ecgs)
                if len(motions)<20:
                    motions.append([0,0,0,0,0,0,0,0,0,0])
                Motion.extend(motions)
                prevtt = tt

        return startTT, ECG, Motion, MotionFs    

    def detect_ridx(self,ecg):
        # Remove Baseline and Pulse
        
        ecg_filt = BaselineRemove(ecg)
        
        # Rescale signal for R peak detection
        scale = 1
        if 300 >= max(ecg_filt) > 150:
            scale = 2
        elif 150 >= max(ecg_filt):
            scale = 4
        else:
            scale = 1
        ecg_filt = ecg_filt * scale
        
        Rpeaks = Rpeak_Obj.RPeakDetection(ecg_filt)
        
        if len(Rpeaks) == 0:
            num = 0
            locs = []
        else :
            num = Rpeaks[0]
            locs = Rpeaks[1:]
            
        return num, locs

    def nni_filter(self,Ridxs, Fs):
        RRI = np.diff(Ridxs)*1000/Fs
        RRIs = [int(rri) for rri in RRI if rri>300 and rri<2000]
        NNIs = []
        if len(RRIs) > 0:
            for i in range(1,len(RRIs)):
                rr_spread = abs((RRIs[i-1]-RRIs[i])/RRIs[i-1])
                if rr_spread < 0.3:
                    NNIs.append(RRIs[i])
        return NNIs

    def motion_energy(self,Motions, SampleRate):
        ##### Preprocessing #####
        SampleNum = len(Motions)
        
        # ???Motion raw data ?????????????????????(dps, g, ...)
        F = np.concatenate((np.ones(3)/114.28,np.ones(3)*0.000061,np.ones(3)*1.5, 1),axis=None)
        Values = Motions * F

        # ??????ACC and GYR 
        GYR = Values[:,0:3] * np.pi/180
        ACC = Values[:,3:6] * 9.80665

        FUSE = Madgwick(frequency=SampleRate)
        Q = np.zeros((SampleNum,4))
        Q[0] = acc2q(ACC[0])
        for i in range(1,SampleNum):
            if Motions[i] == [0,0,0,0,0,0,0,0,0,0]:
                Q[i] = Q[i-1]
            else:
                Q[i] = FUSE.updateIMU(Q[i-1],gyr=GYR[i],acc=ACC[i])
        C = q2R(Q)

        # ??? ACC ?????? global ?????????, ?????? gravity ????????????????????????????????????
        linACC = np.zeros(ACC.shape)
        for i in range(0, SampleNum):
            ACCglob = np.dot(ACC[i], C[i].T)
            linACC[i] = ACCglob - [0,0,1] # notice: C in matlab is the transpose of C in here
        linACC = linACC * 9.81 # g to m/s^2
    
        # ????????????????????? 2 ??????????????????
        w_size = 2 * SampleRate
        STD = np.zeros(linACC.shape)
        STD[0] = np.nan
        w_size = 2 * SampleRate
        for i in range(1, SampleNum):
            if(i > 0):
                if(i < w_size):
                    window = linACC[:i+1]
                else:
                    window = linACC[i-w_size+1:i+1]
                # ???xyz????????????????????????    
                STD[i] = np.std(window, axis=0)
            
        # return np.linalg.norm(STD,axis=1)
        return np.amax(STD, axis=1)
    
    
    def sleep_simplemodel_statistic(self,StartTT,EndTT,Stage):        
        REM,Light,Deep = 0,0,0
        for stage in Stage:
            if(stage==-1):
                REM +=1
            elif(stage==-2):
                Light +=1
            elif(stage==-3):
                Deep +=1
                
        Total = REM+Light+Deep

        result = {
            'asleep':StartTT.strftime("%Y/%m/%d %H:%M:%S"), ##dennis modified
            'wakeup':EndTT.strftime("%Y/%m/%d %H:%M:%S"),  ##dennis modifiied
            'sleephours': (EndTT-StartTT).total_seconds()/(60*60),
            'rem':100*REM/Total if Total>0 else 0,
            'light':100*Light/Total if Total>0 else 0,
            'deep':100*Deep/Total if Total>0 else 0
        }
        return result
    
    def sleep_analysis_simplemodel(self,startDT,endDT,uuid):
        ##SleepReportTime=date.today()        
        data_path=self.dataPath
        startTT = startDT.timestamp() * 1000
        endTT = endDT.timestamp() * 1000
        
        # Parse evt file
        Files = [os.path.join(data_path,f) for f in os.listdir(data_path) if f.endswith('evt')]       
        initACCs = []
        srjFiles = []
        for ff in Files:
            with open(ff,'r') as evt:
                line = evt.readline()
                data = json.loads(line)
                init = data["motionInitArgs"]       ##for health app
                iniACC = [init['x'], init['y'], init['z']]
                ##iniACC = data['extra']['motionMeanAccXYZ']  ##for inhouse app
                initACCs.append(iniACC)
                if data['startTT']<endTT and data['endTT']>startTT:
                    srj = ff.replace('evt','srj')
                    srjFiles.append(srj)
        
        # Seperate each srj files into blocks
        Blocks = []
        for ff in srjFiles:
            Lines = []
            with open(ff,'r') as srj:
                line = srj.readline()
                while line:
                    data = json.loads(line)
                    if startTT < data['tt'] < endTT:
                        Lines.append(line)
                    line = srj.readline()
            Lines = set(Lines)

            Data = []
            for line in Lines:
                data = json.loads(line)
                Data.append(data)
            Data.sort(key=lambda i:i['tt'])
            Blocks.append(Data)
        
        if(len(Blocks)==0):
            ##print('No data in sleeping time!')
            return []              
        ##------------------
        window = 60*5
        step = 60*1
        Ratios = []
        Ratio_DT = []
        Moves = []
        Moves_DT = []
        STDs = []
        STD_DT = []
        Stages = []
        for Data in Blocks:
            
            ratios = []
            ratio_tt = []
            startTT, ecgs, motions, fs = self.sleepdata_concate(Data)
            startDT = datetime.fromtimestamp(startTT)   
            loc = window*250
            
            loc_start = step*250
            
            for i in range(4):
                
                ecg_seg = ecgs[:loc_start*(i+1)]
                
                # ??????R???
                Rnum, Ridxs = self.detect_ridx(ecg_seg)
                
                if Rnum < 5*30: # < 30bpm
                    lfhf = float('nan')
                else:
                    # RRI Filter --> NNI
                    NNIs = self.nni_filter(Ridxs,250)
                    # HRV analysis
            
                    features = hrv.get_frequency_domain_features(NNIs)
                    lfhf = features['lf_hf_ratio']
                    
                ratios.append(lfhf)
                ratio_tt.append(startDT+timedelta(seconds=loc_start*i/250))
                
            while loc <= len(ecgs):
                # ??????ecg??????
                
                ecg_seg = ecgs[loc-window*250:loc]
                
                # ??????R???
                Rnum, Ridxs = self.detect_ridx(ecg_seg)
                
                if Rnum < 5*30: # < 30bpm
                    lfhf = float('nan')
                else:
                    # RRI Filter --> NNI
                    NNIs = self.nni_filter(Ridxs,250)
                    # HRV analysis
            
                    features = hrv.get_frequency_domain_features(NNIs)
                    lfhf = features['lf_hf_ratio']
                    
                ratios.append(lfhf)
                ratio_tt.append(startDT+timedelta(seconds=loc/250))

                loc += step*250
            
            if len(ratios) > 1:
                Ratios.extend(ratios)
                Ratio_DT.extend(ratio_tt)
            
            moving = []
            moving_tt = []    
            stds = []
            
            if len(motions) > 0:
                
                stds = self.motion_energy(motions,fs)
                
                loc = window*fs
                
                while loc <= len(stds):
                    std_seg = stds[loc-window*fs:loc] 
                    thr = 0.1
                    if sum(std_seg>thr) > 0.25*window*fs:
                        moving.append(1)
                    else:
                        moving.append(0)
                    moving_tt.append(startDT+timedelta(seconds=loc/fs))
                    loc += step*fs
            
            Moves.extend(moving)
            Moves_DT.extend(moving_tt)

            STDs.append(stds)
            STD_DT.append(startDT)
        
        if len(Ratios) > 1:
        
            ##------------
            filtRatios = np.zeros(len(Ratios))
            width = 11 # need to be odd number
            side = int((width-1)/2)
            for i in range(len(Ratios)):
                if i < side:
                    window = Ratios[:i+side+1]
                elif i+side >= len(Ratios):
                    window = Ratios[i-side:]
                else:
                    window = Ratios[i-side:i+side+1]
                
                filtRatios[i] = np.nanmean(window)        
            
            q1,q3 = np.nanquantile(Ratios,[0.25,0.8])
            
            for value in filtRatios:
                if value > q3:
                    Stages.append(-1) #REM
                elif value < q1:
                    Stages.append(-3) #Deep
                else:
                    Stages.append(-2) #Light
        
        '''
        fig = plt.figure(figsize=(15,15))
        ax1 = fig.add_subplot(311)
        ax1.plot(Ratio_DT,Ratios,'ko-',label='1 min sliding')
        ax1.plot(Ratio_DT,filtRatios,'r-',label='Filtered(10 mins)',linewidth=2)
        ax1.plot([Ratio_DT[0],Ratio_DT[-1]],[q1,q1],'g--')
        ax1.plot([Ratio_DT[0],Ratio_DT[-1]],[q3,q3],'b--')
        ax1.grid(alpha=0.5)      
        ax1.legend()
        ax1.set_ylabel('lf / hf')

        df = pd.DataFrame({'Time':Ratio_DT,'Stage':Stages})
        ax2 = fig.add_subplot(312)
        ax2.step(Ratio_DT,Stages,where='pre')
        ax2.set_yticks(range(0,-4,-1))
        ax2.set_yticklabels(['Awake','REM','Light','Deep'])
        ax2.grid(alpha=0.5)
        ax2.set_title('Sleep Stages')

        ax3 = fig.add_subplot(313)
        for i, std in enumerate(STDs):
            std_tt = [STD_DT[i]+timedelta(seconds=p/fs) for p in range(len(std))]
            ax3.plot(std_tt,std,color='black',linewidth=0.3)
        ax3.grid(alpha=0.5)
        ax3.set_title('Motion Energy')
        
        save_name = "SleepStageResult%s.png" %(SleepReportTime.strftime("%Y%m%d%H"))
        sleepanalysisimagepath=os.path.join(sleep_save_path,save_name)
        kargs = {'dpi':300,'facecolor':'white','bbox_inches':'tight'}
        fig.savefig(sleepanalysisimagepath,**kargs)
        '''
        return Ratio_DT, Stages
    
    def _analyze_multi_night_MP(self):
        with Pool(processes=8) as pool:
            for result in pool.map(self._analyze_one_night, range(len(self.timeTable)-1)):
                if result is not None:
                    self.Output.append(result)
        return self.Output

    def analyze_multi_night(self,modeltype,uuid):  
        
        for idx in range(len(self.timeTable)-1):
            ##result = self._analyze_one_night(idx)
            
            result,Stage,Posture = self._analyze_one_night(idx,uuid,modeltype)
            
            if result is not None:
                self.Output.append(result)
            
        return self.Output,Stage,Posture

    def _analyze_one_night(self,idx,uuid,modeltype):
        
        # set start time and end time based on given table
        startTT = self.timeTable.loc[idx,'StartDetect']
        endTT = self.timeTable.loc[idx,'EndDetect']        
        Datas = []
        
        # Select files to open base on start time and end time
        for files in self.fileNames:
            # Get timestamp of start time and end time in .evt file
            evtFile = files + ".evt"
            
            with open(os.path.join(self.dataPath,evtFile),'r') as evt:
                event = json.loads(evt.readline())
                evtStartTT = datetime.fromtimestamp(event["startTT"]/1000)
                evtEndTT = datetime.fromtimestamp(event["endTT"]/1000)
                iniACC = [event["motionInitArgs"]["x"],event["motionInitArgs"]["y"],event["motionInitArgs"]["z"]]
            # If timestamp of file matched, open the corresponding .srj file
            srjFile = files + ".srj"
            if startTT<evtEndTT<endTT or startTT<evtStartTT<endTT:
                lines = self._read_srj_file(os.path.join(self.dataPath,srjFile))
            elif evtStartTT<startTT and endTT<evtEndTT:
                lines = self._read_srj_file(os.path.join(self.dataPath,srjFile))
            else:
                continue

            # Only get strings in file before end time
            for line in lines:
                string = json.loads(line)
                stringTT = datetime.fromtimestamp(string['tt']/1000)
                if startTT<=stringTT and stringTT<=endTT:
                    Datas.append(string)
        
        if len(Datas) == 0:
            return {}, [], []
        
        Datas.sort(key = lambda i:i['tt'])
        model = sleep.Device(Datas,duration=[startTT,endTT],iniACC=iniACC)
        Posture=model.State ##model.posture_figure(save_path=self.exportPath)
        
        postureResult = model.posture_analysis()      
        
        if(modeltype=="ai"):
            Stage=model.State   ###stage_figure(save_path=self.exportPath)
            stageResult = model.stage_analysis()
        else: ##simple model
            
            post_list = []
            post_dt_list = []
        
            for i_posture in Posture:
                post_list.extend(i_posture['State'].tolist())
                post_dt_list.extend(i_posture['DT'].tolist())
            
            Stage_DT, Stage = self.sleep_analysis_simplemodel( startTT, endTT, uuid )
            
            New_Stage = []
            
            ### ????????????REM?????????Awake
            
            first_rem = 1
            
            for st in Stage:
                if first_rem == 1 and st != -1: first_rem = 0
                if st == -1 and first_rem == 1: st = 0
            
            ### ???????????????REM????????????Awake
            
            last = 1
            
            while Stage[-last] == -1:
                last += 1
            
            for l in range(1,last):
                Stage[-l] = 0
            
            
            ### ????????????Up-right????????????Awake ??? ???????????????????????????????????????????????????1
            
            for post_dt, post in zip(post_dt_list, post_list):
                
                same_time = 0
                
                for st_i, st_dt in enumerate(Stage_DT):
                    
                    if post_dt == st_dt:
                        
                        same_time += 1
                        
                        if post == 1:
                            New_Stage.append(0)
                        else :
                            New_Stage.append(Stage[st_i])
                
                if same_time == 0:
                    New_Stage.append(1)
            
            ### ??????5???????????????????????? ???????????????Awake ???????????????Awake
            
            New_Stage[0] = 0
            New_Stage[1] = 0
            New_Stage[2] = 0
            New_Stage[3] = 0
            New_Stage[4] = 0
            New_Stage[-1] = 0
            
            stageResult = self.sleep_simplemodel_statistic( startTT, endTT, New_Stage )
        
        ##model.poincare_figure(save_path=self.exportPath)
        ##model.output_stages(save_path=self.exportPath) #??????CSV??????        
        ##hrvResult = model.hrv_analysis()
        datas = {}
        datas.update(postureResult)
        datas.update(stageResult)
        ##datas.update(hrvResult)
        output = {str(idx):datas}
        
        return output,New_Stage,Posture

class SleepQualityReportGenerator:    
    def __init__(self,DBPath):
        self.BasePath=os.path.dirname(__file__)
        self.DB=self.tempDB=DBPath
        self.IntMaxValue=1000000 
       
    ####=========================???????????????===============================
    def search_upzip(self,db_path,target,start,end,export_path):
        startDT = datetime.strptime(start,'%Y%m%d')
        endDT = datetime.strptime(end,'%Y%m%d')
        existFiles = [f.split('.')[0] for f in os.listdir(export_path) if f.endswith('.srj')]
        UnzipFileNameList=[] 
        print("[Progress] Downloading Datas")
        ##t1 = time()
        # ?????????????????????
        for D in os.listdir(db_path):
            if(len(D)<8): ##uuid?????????????????????parsing??????
                continue
                
            Folder = os.path.join(db_path,D)
            # ????????????????????????
            if os.path.isdir(Folder):
                date = datetime.strptime(D,'%Y%m%d')
                if date >= startDT and date <= endDT:
                    # ?????????????????????????????????
                    for files in os.listdir(Folder):
                        fileparts = files.split("_")
                        uuid = fileparts[0]
                        # ?????????????????????????????????
                        filename = files.split('.')[0]
                        ##if filename in existFiles:
                        ##    continue
                        if "(" in filename or ")" in filename: ###???????????????????????????????????????????????????
                            continue
                        # ????????????UUID??????zip???
                        if uuid == target and files.endswith('.zip'):
                            filePath = os.path.join(Folder,files)
                            print('     %s' %filename)
                            # ????????????????????????
                            with ZipFile(filePath,'r') as zip:
                                zip.extractall(export_path)
                                UnzipFileNameList.append(filename[0:len(filename)]+'.srj')  ### Dennis ??????
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
        ##NowDayEnd=NowDay+timedelta(days = 1)    
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
                    ##if(nowday>=NowDay and nowday<=NowDayEnd): ###?????????????????????Concate Data
                    if(nowtime>=startTime and nowtime<=endTime): ###?????????????????????Concate Data
                        OriginalTimeArray.append(nowtime)                
                        for m in motions:
                            MotionDataArray.append(m)
                    
                        for n in ecgs:
                            ConcateEcgArray.append(n) 
                
                    line = srj.readline()          
                
        return OriginalTimeArray,ConcateEcgArray,MotionDataArray    

    ####===============?????????????????????=================================
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
        endTT = endDT.timestamp()*1000
        with tqdm.tqdm(total=len(lines),desc='  [??????]',file=sys.stdout) as pbar:
            for line in lines:
                string = json.loads(line)
                if startTT <= string['tt'] <= endTT:
                    Datas.append(string)
                pbar.update()
        Datas.sort(key=lambda i:i['tt'])

        ##t2 = time()
        ##print("  Elapsed time: %.2fs" %(t2-t1))
        return Datas
    
   ####===============??????????????????=================================
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
        
        if(medianFlag): ##????????????????????????   
            if(len(FilteredRRIArray)>0):
                RRIMedian=np.median(FilteredRRIArray)
                for i in range(len(FilteredRRIArray)):
                    if((FilteredRRIArray[i]>=(RRIMedian-0.55*RRIMedian)) and (FilteredRRIArray[i]<=RRIMedian+0.62*RRIMedian)):
                        FinalFilteredRRIArray.append(FilteredRRIArray[i])
            
            return FinalFilteredRRIArray
        else:
            return FilteredRRIArray
        
    ####=================??????PVC?????????RRI??????==============================
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

    ####================???????????????=============================
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

        # ???Motion raw data ?????? numpy array
        SampleNum = len(Motions)
        Motions = np.array(Motions)

        # ???Motion raw data ?????????????????????(dps, g, ...)
        F = np.concatenate((np.ones(3)/114.28, np.ones(3)*0.000061, np.ones(3)*1.5, 1), axis = None)
        Values = Motions * F

        # ??????ACC and GYR 
        ACC = Values[:,3:6]
        GYR = Values[:,0:3]
        
        # ?????? global & body ????????????????????????: C
        orientation = ahrs.filters.Madgwick(acc=ACC*9.80665, gyr=GYR*np.pi/180, frequency=SampleRate)
        C = ahrs.common.orientation.q2R(orientation.Q)
        
        # ??? ACC ?????? global ?????????, ?????? gravity ????????????????????????????????????
        linACC = np.zeros(ACC.shape)
        for i in range(0, SampleNum):
            ACCglob = np.dot(ACC[i], C[i].T)
            linACC[i] = ACCglob - [0,0,1] # notice: C in matlab is the transpose of C in here
        linACC = linACC * 9.81 # g to m/s^2
        
        # ????????????????????? 2 ??????????????????
        STD = np.zeros(linACC.shape)
        w_size = 2 * SampleRate
        for i in range(0, SampleNum):
            if i < w_size:
                window = linACC[:i+1]
            else:
                window = linACC[i-w_size+1:i+1]

            if window.shape[0] > 1:
                STD[i] = np.std(window, axis=0)
                
        # ???????????????????????????????????????????????????
        movingTH = 0.5
        Static_label = np.ones(SampleNum,dtype=int)
        for i in range(w_size, SampleNum):
            s = STD[i]

            # ?????????????????????????????????????????????????????????
            flag = np.sum(s > movingTH)
            if flag == 0:
                Static_label[i] = 1 # Static
            else:
                Static_label[i] = 0 # Dynamic

    
        return Static_label,STD  

    ####=============================Calculate RRSpread==============================
    def RRSpreadCalculate(self,RRIArray):    
        MaxRRI=np.max(RRIArray)
        MinRRI=np.min(RRIArray)
        RRSpreadValue=(MaxRRI-MinRRI)/(MaxRRI+MinRRI)
        return RRSpreadValue
        
    ####======================PVC ??????===============================
    def PVC_Report(self,user_info,data_path,start,end,export_path=""):
        
        startTime = datetime.strptime(start,'%Y%m%d %H%M%S')
        endTime = datetime.strptime(end,'%Y%m%d %H%M%S')
        
        startDate = datetime.strptime(start.split(" ")[0], "%Y%m%d")
        endDate = datetime.strptime(end.split(" ")[0], "%Y%m%d")
        
        UserId=user_info['id']
        
        Dates = [(startDate+timedelta(days=i)).strftime("%Y%m%d") for i in range((endDate-startDate).days+1)]    
        ##PVCStatisticData = pd.DataFrame({'Date':Dates})
        PVCInformation = pd.DataFrame() 
        #### Parse Data
        srjFiles = [f for f in os.listdir(data_path) if f.endswith('.srj')]
        data = self.load_data(data_path,srjFiles,startTime,endTime)   
        fs=250  ##ECG Sampling Rate
        TotalPVCCount=0
        OccuringCountArray=np.zeros(24)  ###???????????????????????????????????????    
        for i in range(1,len(data)-1):
            ecg_pre = data[i-1]['rows']['ecgs'] 
            ecg = data[i]['rows']['ecgs']
            ecg_next = data[i+1]['rows']['ecgs'] 
            tt = data[i]['tt']
            dt = datetime.fromtimestamp(int(tt)/1000)
            nowDay = dt.replace(hour=0, minute=0,second=0,microsecond=0)
            dayIndex=(nowDay-startDate).days        
            RawEcg=ecg
            ecgtemp=ecg_pre[2500-2*fs:2500] ###????????????2???(??????PCV??????????????????????????????)
            ecgtemp.extend(ecg)
            ecgtemp.extend(ecg_next[0:2*fs]) ###????????????2???(??????PCV??????????????????????????????)
            ecg=ecgtemp
            ecg=np.array(ecg)
            ecg=BaselineRemove_Obj.BaselineRemove(ecg)   
            
            MinValue=np.min(ecg)
            MaxValue=np.max(ecg)
            
            if(MinValue==MaxValue):
                continue
            
            RpeakArray=Rpeak_Obj.RPeakDetection(ecg,DetectionMode=1)
            Ridx=RpeakArray[1:len(RpeakArray)]       
            ##PatternClusteringScore=Score_Obj.PatternClustering(ecg,Ridx)
            
            if len(Ridx) < 10 or len(Ridx) > 35 or Ridx[1] > 2*fs or Ridx[-1] < 3500-2*fs:
                continue            
           
            score0 = Score_Obj.PatternClustering(ecg,Ridx)
            score1 = Score_Obj.AreaRatio(ecg, Ridx)
            QualtiyScore = score0 * score1
            
            if(QualtiyScore<85): ##???????????????????????????
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
                    if(nowWidth>=0.114 and nowWidth<=0.185):  ###???????????????QRS????????????
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
                if(abs(meanLocRRI-medianRRI)>=0.3*medianRRI): ###??????????????????RRI???????????????                
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
                                
                    if(PacketLossFlag):  ###???????????????????????????
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
                        OccuringTime=dt+timedelta(seconds=Ridx[qrs_index]/250) 

                        ecg_sec30=ecg_pre ###????????????10???????????????ecg 30 secs??????
                        ecg_sec30.extend(RawEcg)
                        ecg_sec30.extend(ecg_next) ###????????????10???????????????ecg 30 secs??????
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
        for index in range(2500,len(EcgData_Debasedline),2500):  ###???10????????????????????????R peak??????????????????global r peak array
            SegmentCount=SegmentCount+1 
            nowEcg=EcgData_Debasedline[index-2500:index]
            EcgMaxValue=max(nowEcg)
            if(EcgMaxValue<=50):
                nowECG=nowEcg*4                
            elif(EcgMaxValue<=100):
                nowECG=nowEcg*3              
            
            Ridx=Rpeak_Obj.RPeakDetection(nowEcg)
            if(len(Ridx)>=2): ####?????????R Peak(????????????1???R peak?????????2????????????R peak ??????)                
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
            for i in range(10,len(RRIArray)): ###????????????10???RRI??????????????????????????????RRI????????????
                RRIFilteredArray=self.RRIFilter(RRIArray[i-10:i])
                if(len(RRIFilteredArray)>=5): ###???????????????????????????                
                    HRArray[i]=60000/np.mean(RRIFilteredArray)              
            
            HR_Min=round(np.nanmin(HRArray)) ####????????????Min
            HR_Max=round(np.nanmax(HRArray)) ####????????????Max  
            HR_Mean=round(np.nanmean(HRArray)) ####????????????Mean
            for hour in range(24): ###?????????????????????
                hourindexArray=np.argwhere(Ridx_hourtime_global == hour)-1  ###??????????????????RRI index, RRI???Ridex index?????????           
                if(np.any(hourindexArray)):
                    evaluationTime_MinuteperHour[hour]=len(np.unique(Ridx_minutetime_global[hourindexArray[:]+1]))                   
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
            HRArray=np.array([],dtype="int32")       
        
        Ridx_minutetime_global_diff=np.diff(Ridx_minutetime_global)
        
        startindex=10 ###???10??????NAN????????????
        HRArray_perminutes=np.array([],dtype="int32")
        
        for k in range(11,len(Ridx_minutetime_global_diff)): ###???10??????NAN????????????
            if(Ridx_minutetime_global_diff[k]!=0): ##??????????????????
                
                endindex=k
                HR_minute=np.nanmean(HRArray[startindex:endindex])
                if np.isnan(HR_minute) == False:
                    HRArray_perminutes=np.append(HRArray_perminutes,round(HR_minute))
                else :
                    HRArray_perminutes=np.append(HRArray_perminutes,-1)
                startindex=k
                
                nan_time = int((Ridx_hourtime_global[k+1] - Ridx_hourtime_global[k]) * 60 + Ridx_minutetime_global[k+1] -Ridx_minutetime_global[k]-1)
                
                for m in range(nan_time):
                    HRArray_perminutes=np.append(HRArray_perminutes,-1)
        
        return [HR_Min,HR_Max,HR_Mean,HR_Min_perHour,HR_Max_perHour,HR_Mean_perHour,evaluationTime_MinuteperHour,HRArray_perminutes] 

    ####=============================????????????==========================
    def SleepingQualityHistoryExtractor(self,UUID):    
        SleepingQualityReportList=[]
        ReportList=[]
        SleepingQualityReportList.append({'name': 'Report 1','date':(date.today()).strftime('%Y/%m/%d'),'score':0})  ### Report 1??????????????????
        ExtractingPath=os.path.join(self.BasePath,"SleepingReportOutput",UUID)        
        isdirFlag = os.path.isdir(ExtractingPath) 
        if(isdirFlag): ##???UUID???????????????            
            directory=os.listdir(ExtractingPath)           
            filenameArray=[]
            
            for d in directory: ###??????????????????????????????
                bottomdir=os.path.join(ExtractingPath,d)               
                files=os.listdir(bottomdir)
                for file in files:
                    if file.endswith(".json"):                       
                        filenameArray.append(os.path.join(bottomdir,file))            
        
            if(len(filenameArray)>0): ##?????????????????????json??????
                filenameArray.sort(reverse=True)                
                JsonFilePath=os.path.join(ExtractingPath,filenameArray[0]) 
                with open(JsonFilePath,'r',encoding='utf-8') as f:
                    s = f.read()
                    json_object = json.loads(json.dumps(eval(s)))                   
                    
                scoreRecord=json_object['SleepingQualityExamEvaluation']['scoreRecord']
                ReportList=scoreRecord['records']  

            if(len(ReportList)>5): ####??????5?????????????????????5???
                ReportLen=5
            else:
                ReportLen=len(ReportList)

            for i in range(ReportLen):
                ReportIndexText="Report "+str(i+2) ###?????????Report 2??????
                NowReport=ReportList[i]
                SleepingQualityReportList.append({'name': ReportIndexText,'date':NowReport['date'],'score':NowReport['score']})
        
        return SleepingQualityReportList

    def CardiovascularAnalysis(self,EcgData_Debasedline,OriginalTimeArray,MotionData,Age):     
        ####-----1. ??????????????????---------
        MotionSampleRate=2
        EcgSampleRate=250
        SecondsThr_5min=60*5  ###5??????
        SecondsThr_3min=60*3  ###3??????       
        staticScore=heartfuncScore=-1       
        MinHR=self.IntMaxValue
        Min_RRSpreadValueArray=Min_RRSpreadValueFilteredArray=[]
        Min_RRSpreadValue=self.IntMaxValue    
        RRI_Milliseconds=[]    
        MaxDecreaseTime=-1 ###OriginalTimeArray[0]   ###??????HR???????????????????????????????????????
        if(len(MotionData)>0):
            StaticLabel,STD = self.StaticAnalysis(MotionData, SampleRate=2)
        else:  ###???????????????motion            
            return [-1,-1,-1]  ### Error code for no motion    
        
        DiffArr=np.diff(StaticLabel)
        StaticStartIndexArr=np.array(np.where(DiffArr == 1))   ### 1->0(??????????????????)
        StaticEndIndexArr=np.array(np.where(DiffArr == -1))    ### 0->1(??????????????????)    
        StaticEndIndexArr=StaticEndIndexArr[0][:] ##???????????????
        StaticStartIndexArr=StaticStartIndexArr[0][:]  ##???????????????  
        AllStaticFlag=False
        if(len(StaticEndIndexArr)==0 or len(StaticStartIndexArr)==0): ##????????????????????????????????????????????????????????????????????????
            StaticStartIndexArr=[0]
            StaticEndIndexArr=[len(StaticLabel)]           
            AllStaticFlag=True    
        
        '''
        ??????????????????5????????????????????????????????????3?????????RRspread???
        ???????????? RR spread????????????????????????????????????????????????????????????
        '''
        StaticStateIndexArray=[]  
        for i in range(len(StaticEndIndexArr)):
            CurrentStaticEndIndex=StaticEndIndexArr[i]
            if(AllStaticFlag): ###?????????????????????            
                CurrentStaticStartIndex=StaticStartIndexArr
            else: ###?????????????????????
                StaticStartIndex = np.where(StaticStartIndexArr <= CurrentStaticEndIndex)  ###??????????????????????????????????????????index)
                CurrentStaticStartIndex=StaticStartIndex[0][:] 
            
         
            if(len(CurrentStaticStartIndex)==0 or AllStaticFlag==True):  ###???????????????????????????????????????????????????????????????????????????????????????index=0??????
                StaticStateIndexArray.append([0,CurrentStaticEndIndex])           
            else:
                StaticStateIndexArray.append([StaticStartIndexArr[CurrentStaticStartIndex[-1]],CurrentStaticEndIndex])  
        
        StaticStateTimeArray=[]
        for pair in StaticStateIndexArray:
            Duration=pair[1]-pair[0]      
            if(Duration>MotionSampleRate*SecondsThr_5min): ###????????????5?????????????????????
                StaticStateTimeArray.append([pair[0]/MotionSampleRate,pair[1]/MotionSampleRate])  
        
     
        Static_Ridx_global = np.array([],dtype="int32") 
        for index in range(len(StaticStateTimeArray)):  ###??????????????????5????????????????????????????????????3?????????RRspread??????????????? RR spread?????????
            Count=0
            StartStaticsIndex=int(StaticStateTimeArray[index][0]*EcgSampleRate)+2500 ###?????????
            EndStaticsIndex=min([int(StaticStateTimeArray[index][1]*EcgSampleRate),len(EcgData_Debasedline)]) ###?????????(ECG????????????????????????????????????????????????)        
            for i in range(StartStaticsIndex,EndStaticsIndex, 2500): ###???10??????????????????????????????global R peak index
                Count=Count+1
                nowECG=EcgData_Debasedline[i-2500+1:i]           
                EcgMaxValue=max(nowECG)
                if(EcgMaxValue<=50):
                    nowECG=nowECG*4                
                elif(EcgMaxValue<=100):
                    nowECG=nowECG*3               
                                
                Ridx=Rpeak_Obj.RPeakDetection(nowECG)
                if(len(Ridx)>=2): ####?????????R Peak(????????????1???R peak?????????2????????????R peak ??????)                
                    Static_Ridx_global = np.append(Static_Ridx_global,np.array(Ridx[1:]+(Count-1)*2500+StartStaticsIndex-2500,dtype="int32"))
            
            RRI_Milliseconds=np.diff(Static_Ridx_global)*4 
            FullFlag=False
            for EndRindex in range(len(Static_Ridx_global)):  ###????????????R peak,???????????????????????????????????????3?????????R peak????????????
                if(FullFlag==False):
                    SecondsDuration=(Static_Ridx_global[EndRindex]-(StartStaticsIndex-2500+1))/EcgSampleRate               
                    if(SecondsDuration>=SecondsThr_3min): ###?????????
                        FullFlag=True
                    
                if(FullFlag): ###???3????????????????????????????????????RRspread
                    for StartRindex in range(EndRindex,0,-1): ###????????????R peak??????????????????????????????
                        TotalRRI_Milliseconds=np.sum(RRI_Milliseconds[StartRindex:EndRindex]) 
                        if(TotalRRI_Milliseconds>=SecondsThr_3min*1000):  ###???3??????????????????????????? RRSpread????????????3??????????????????                        
                            FilteredRRI=self.RRIFilter(RRI_Milliseconds[StartRindex:EndRindex])                        
                            if(len(FilteredRRI)>=3): ###RRI?????????????????????
                                RRSpreadValue=self.RRSpreadCalculate(FilteredRRI)                           
                                if(RRSpreadValue<Min_RRSpreadValue):
                                    Min_RRSpreadValue=RRSpreadValue
                                    Min_RRSpreadValueArray=RRI_Milliseconds[StartRindex:EndRindex]                      
                                    Min_RRSpreadValueFilteredArray=FilteredRRI  ####??????RRSpread???RRI??????                                                                                
                                break
                            ##else:
                                ##print('FilteredRRI len is less than 3!')
                                
            MinRRIDiff=self.IntMaxValue
            MinRRIDiffArray=[]
            MinIndex=HR=-1      
            if(len(Min_RRSpreadValueFilteredArray)>=11):             
                for i in range(10,len(Min_RRSpreadValueFilteredArray)): ####RRI??????????????????10???RRI
                    RRIDiff=max(Min_RRSpreadValueFilteredArray[i-10:i])-min(Min_RRSpreadValueFilteredArray[i-10:i])
                    if(RRIDiff<MinRRIDiff):
                        MinRRIDiff=RRIDiff
                        MinIndex=i
                        
                HR=60000/np.mean(Min_RRSpreadValueFilteredArray[MinIndex-10:MinIndex])      
               
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
        ####----------------------2. ??????????????????-------------------------------
        '''
        ????????????5??????????????????3??????????????????????????????????????????
        ?????????????????????????????????????????????????????????????????????????????????
        '''
        Dynamic2StaticIndexArray=[]

        for pair in StaticStateIndexArray:
            Duration=pair[1]-pair[0]  ##??????????????????????????????????????????           
            if(Duration>=MotionSampleRate*SecondsThr_5min): ###??????????????????5?????????????????????????????????????????????????????????3???????????????
                NowEndDynamicIndex=pair[0]-1
                NowStartDynamicIndex=NowEndDynamicIndex-SecondsThr_3min*2
                if(NowStartDynamicIndex>0):  ###??????????????????????????????????????????????????????????????????
                    NowStaticIndexArray= [x for x in StaticLabel if x == 1]  ###????????????????????????????????????????????????
                    if(len(NowStaticIndexArray)>0):  ###???????????????????????????????????????????????????????????????????????????
                        NowStartStaticIndex=pair[0]
                        NowEndStaticIndex=pair[0]+SecondsThr_3min*2
                        Dynamic2StaticIndexArray.append([NowStartDynamicIndex,NowEndDynamicIndex,NowStartStaticIndex,NowEndStaticIndex])            
    
        if(len(Dynamic2StaticIndexArray)>0): 
            DiffHRArray=[]
            maxHR=-self.IntMaxValue
            minHR=self.IntMaxValue  
            for k in range(len(Dynamic2StaticIndexArray)): ####????????????????????????????????????????????????Motion???????????????ECG???????????????               
                DynamicStartIndex_ECG=(Dynamic2StaticIndexArray[k][0]/2)*EcgSampleRate ### motion????????????ECG??????
                DynamicEndIndex_ECG=(Dynamic2StaticIndexArray[k][1]/2)*EcgSampleRate
                DynamicCount=0
                RPeak_Dynamic=np.array([],dtype="int32") 
                for m in range(int(DynamicStartIndex_ECG+2500),int(DynamicEndIndex_ECG),2500):  ###??????????????????R Peak              
                    DynamicCount=DynamicCount+1
                    nowECG=EcgData_Debasedline[m-2500:m-1]
                    EcgMaxValue=max(nowECG)
                    if(EcgMaxValue<=50):
                        nowECG=nowECG*4                
                    elif(EcgMaxValue<=100):
                        nowECG=nowECG*3   
                                    
                    nowRidx=Rpeak_Obj.RPeakDetection(nowECG)
                    if(len(nowRidx)>=2): ####?????????R Peak(????????????1???R peak?????????2????????????R peak ??????)                
                        RPeak_Dynamic = np.append(RPeak_Dynamic,np.array(nowRidx[1:]+(DynamicCount-1)*2500+DynamicStartIndex_ECG-2500,dtype="int32"))                    
                              
                StaticStartIndex_ECG=(Dynamic2StaticIndexArray[k][2]/2)*EcgSampleRate
                StaticEndIndex_ECG=(Dynamic2StaticIndexArray[k][3]/2)*EcgSampleRate  
                RPeak_Static=[SR for SR in Static_Ridx_global if SR>=StaticStartIndex_ECG and SR<=StaticEndIndex_ECG]  
                RRISeq_Dynamic=np.diff(RPeak_Dynamic)*4
                RRISeq_Static=np.diff(RPeak_Static)*4                  
              
                for d in range(0,len(RRISeq_Dynamic)-10+1,1):  ###??????10???RRI??????????????????HR???
                    RRIFilteredSeq_Dynamic=self.RRIFilter(RRISeq_Dynamic[d:d+10-1])
                    nowDynamicHR=60000/np.mean(RRIFilteredSeq_Dynamic)               
                    if(nowDynamicHR>maxHR):
                        maxHR=nowDynamicHR                    
            
                for s in range(0,len(RRISeq_Static)-10+1,1):  ###??????10???RRI??????????????????HR???
                    RRIFilteredSeq_Static=self.RRIFilter(RRISeq_Static[s:s+10-1])
                    nowStaticHR=60000/np.mean(RRIFilteredSeq_Static)               
                    if(nowStaticHR<minHR):
                        minHR=nowStaticHR                        
                      
                DiffHR=maxHR-minHR              
                DiffHRArray.append(DiffHR)
                
            HR=np.max(DiffHRArray)       
            MaxDecreaseIndex=np.argmax(DiffHRArray)
            IndexinECG=(Dynamic2StaticIndexArray[MaxDecreaseIndex][0]/2)*EcgSampleRate ##motion????????????ECG??????
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
        else: ####??????????????????5???????????????5?????????????????????????????????
            ##print('??????????????????5???????????????5???????????????!')
            heartfuncScore=-1      
        
        return [staticScore,heartfuncScore,MaxDecreaseTime]

    ####===============??????????????????????????????===========================
    def MaxMinHREventLoad(self,report): 
        min_hr_physio_event=report['min_hr_physio'] 
        ##RowData={}
        reason=(min_hr_physio_event['reason']).split(',')
        HR=((min_hr_physio_event['hr']).split(' '))[0]
        PR=((min_hr_physio_event['pr']).split(' '))[0]
        QRS=((min_hr_physio_event['qrs']).split(' '))[0]
        QT=((min_hr_physio_event['qt']).split(' '))[0]
        QTc=((min_hr_physio_event['qtc']).split(' '))[0]      
        minHRStatistics={'date': datetime.fromtimestamp(float(min_hr_physio_event['timestamp'])/1000).strftime('%Y/%m/%d'),
                'time': datetime.fromtimestamp(float(min_hr_physio_event['timestamp'])/1000).strftime('%H:%M:%S'), ###???????????????
                'unit': reason[0],
                'HR': HR, 
                'PR': PR,
                'QRS': QRS,
                'QT': QT,                      
                'QTc': QTc, 
                'Irrequlars': [],
                'PVCs': [],
                'RPeaks': (min_hr_physio_event['ridx']).tolist(), 
                'sec10': min_hr_physio_event['ecgs'],
                'sec30': min_hr_physio_event['ecgs sec30']
                }                    
               
        max_hr_physio_event=report['max_hr_physio']       
        reason=(max_hr_physio_event['reason']).split(',')
        HR=((max_hr_physio_event['hr']).split(' '))[0]
        PR=((max_hr_physio_event['pr']).split(' '))[0]
        QRS=((max_hr_physio_event['qrs']).split(' '))[0]
        QT=((max_hr_physio_event['qt']).split(' '))[0]
        QTc=((max_hr_physio_event['qtc']).split(' '))[0]             
        maxHRStatistics={'date': datetime.fromtimestamp(float(max_hr_physio_event['timestamp'])/1000).strftime('%Y/%m/%d'),
                'time': datetime.fromtimestamp(float(max_hr_physio_event['timestamp'])/1000).strftime('%H:%M:%S'), ###???????????????
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
           
        
        return minHRStatistics,maxHRStatistics       
        
    ####===============????????????????????????===========================
    def ArrhythmiaEventLoad(self,report,ecgDict):    
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
                    'time': datetime.fromtimestamp(float(ir_events[i]['timestamp'])/1000).strftime('%H:%M:%S'), ###???????????????
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
        
    ####================PVC????????????================================
    def PVCEventLoad(self,PVCInformation,ecgDict): 
        ###pvc_statistics=pvc_statistics_perHour=[]        
        for i in range(len(PVCInformation)):
            RowData={}
            Measured_date=PVCInformation.at[i, 'Measured_date']
            date=Measured_date[0:4]+"/"+Measured_date[4:6]+"/"+Measured_date[6:8]       
            Measured_time=PVCInformation.at[i, 'Measured_time']
            time=Measured_time[0:2]+":"+Measured_time[2:4]+":"+Measured_time[4:6]
            RowData={'date': date,
                    'time': time, ###???????????????
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

        return ecgDict ###,pvc_statistics,pvc_statistics_perHour

    ####========================??????????????????=========================
    def arrhythmia_analysis(self,user_info,data_path,start,end,export_path=""):
        
        startTime = datetime.strptime(start,'%Y%m%d %H%M%S')
        endTime = datetime.strptime(end,'%Y%m%d %H%M%S')
        
        ##Dates = [(startDate+timedelta(days=i)).strftime("%Y%m%d") for i in range((endDate-startDate).days+1)] ##Paul
        ##Dates = [startDate]

        # Parse Data
        srjFiles = [f for f in os.listdir(data_path) if f.endswith('.srj')]
        Datas = self.load_data(data_path,srjFiles,startTime,endTime)  
        if(len(Datas)==0): ##??????????????????
            report=[]
            return report
        
        # Analyze Data
        AD = ArrhythmiaDetection(data=Datas,userInfo=user_info)
        SavedFileName='ArrhythmiaReport_'+start.split(" ")[0]+'.xls'        
        report = AD.genReport(Mode="Arrhythmia",gpu=0,multi_proc=False,savetoxlsFlag=False,savedPath=os.path.join(export_path,SavedFileName))         
            
        return report

    
    def sleep_analysis(self,start,end,UUID,modeltype,multi_proc=False):
        
        startTime = datetime.strptime(start,'%Y%m%d %H%M%S')
        endTime = datetime.strptime(end,'%Y%m%d %H%M%S')
        
        ##???????????????????????????       
        outputFolder0 = os.path.join(self.BasePath,'SleepingReportOutput',UUID)       
        reportdate_str=(date.today()).strftime('%Y%m%d')  
        export_path = os.path.join(outputFolder0,reportdate_str)
        ##????????????????????????????????????U???????????????UUID????????????
        UUID_tempPath = os.path.join(self.tempDB, UUID)        
        UUID_tempPath = os.path.join(self.tempDB, UUID)
        data_path=UUID_tempPath
        fileNames = [ff[:-4] for ff in os.listdir(UUID_tempPath) if ff.endswith('srj')]       
        ## Set sleep duration in table
        startDate = datetime.strptime(start.split(" ")[0], '%Y%m%d')
        endDate = startDate + timedelta(days=1)
        Dates = [startDate+timedelta(days=i) for i in range((endDate-startDate).days+1)]
        timeTable = pd.DataFrame({'Date':Dates})
        ## Add empty columns in table
        timeTable[['StartDetect','EndDetect']] = ""
        timeTable[['OnBed','OffBed']] = ""
        timeTable[['Right','Prone','Left','Supine']] = 0
        timeTable[['Asleep','WakeUp']] = ""
        timeTable[['SleepHours','REM','Light','Deep']] = 0
        ##timeTable[['min_hr','lf','hf','lf/hf','lf%','stage']] = 0
        
        for i in range(len(timeTable)-1):
            
            timeTable.loc[i,'StartDetect'] = startTime
            timeTable.loc[i,'EndDetect'] = endTime
        
        ## Analyze datas in each night
        MP = multi_process(timeTable,fileNames,data_path,export_path)
        if multi_proc:
            Output = MP._analyze_multi_night_MP()
        else:
            ##Output = MP.analyze_multi_night()
            Output,Stage,Posture = MP.analyze_multi_night(modeltype,UUID)
        
        for output in Output:
            for key, value in output.items():
                timeTable.iloc[int(key),3:] = value.values()
        
        wake_count = [i for i,x in enumerate(Stage) if x == 0]
        
        timeTable.loc[0,'SleepHours'] = round((timeTable.loc[0,'EndDetect'] - timeTable.loc[0,'StartDetect']).total_seconds() / 3600 - len(wake_count)/60, 1)
        
        #### Export result of analysis to files
        '''
        ##timeTable.to_csv(os.path.join(export_path,"Analysis_Result.csv"),index=False) ###?????????excel
        kargs = {'dpi':300,'facecolor':'white'}
        fig0 = plt.figure(figsize=(12,2))
        plt.ioff()
        ax0 = fig0.add_subplot(1,1,1)
        data = timeTable.loc[:,['Supine','Right','Left','Prone']]
        data.plot(ax=ax0, kind="bar",stacked=True)
        ax0.legend(bbox_to_anchor=(1.12,1.0))
        ax0.grid(alpha=0.3)
        xlabel = [index.strftime("%m/%d") for index in timeTable.Date]
        ax0.set_xticklabels(xlabel, rotation=0)
        ax0.set_ylabel("Proportion (%)")
        plt.savefig(os.path.join(export_path,"Posture_Proportion.png"),**kargs)
        plt.close(fig0)

        fig1 = plt.figure(figsize=(12,2))
        plt.ioff()
        ax1 = fig1.add_subplot(1,1,1)
        data = timeTable.loc[:,['Deep','Light','REM']]
        data.plot(ax=ax1, kind="bar",stacked=True)
        ax1.legend(bbox_to_anchor=(1.12,1.0))
        ax1.grid(alpha=0.3)
        xlabel = [index.strftime("%m/%d") for index in timeTable.Date]
        ax1.set_xticklabels(xlabel, rotation=0)
        ax1.set_ylabel("Proportion (%)")
        
        
        ax12 = ax1.twinx()
        data = timeTable.loc[:,"lf/hf"]
        y = data[data>0]
        x = timeTable.index[data>0]
        ax12.plot(x,1/y,marker='s',color='k')
        ax12.set_yticks([0,1,2])
        ax12.set_yticklabels(['Bad','Normal','Good'])
        plt.savefig(os.path.join(export_path,"Stage_Proportion.png"),**kargs)
        

        fig2 = plt.figure(figsize=(12,2))
        plt.ioff()
        ax2 = fig2.add_subplot(1,1,1)
        data = timeTable.loc[:,'SleepHours']
        data.plot(ax=ax2, kind="bar")
        ax2.grid(alpha=0.3)
        xlabel = [index.strftime("%m/%d") for index in timeTable.Date]
        ax2.set_xticklabels(xlabel, rotation=0)
        ax2.set_ylabel("Hours")
        fig2.savefig(os.path.join(export_path,"Sleep_Hours.png"),**kargs)
        plt.close(fig2)
        '''
        return timeTable,Stage,Posture
    
    def StagePosutureConcate(self,Stage,Posture,modeltype):
        
        post_list = []
        post_dt_list = []
        
        New_Stage = []
        New_Posture = []
        
        if len(Stage) > 0:
        
            for i_posture in range(len(Posture)):
                post_list.append((Posture.iloc[i_posture]['State']).astype(int))
                post_dt_list.append(Posture.iloc[i_posture]['DT'])
            
            New_Posture_DT = []            
            set_dt = post_dt_list[0].replace(second=0, microsecond=0)     
            post_dt_p = 0            
            sorted_list = np.array([post_dt_list, post_list, Stage]).T.tolist()
            sorted_list = sorted(sorted_list, key=lambda l:l[0])
            sorted_list = np.array(sorted_list).T.tolist()
            
            post_dt_list = sorted_list[0]
            post_list = sorted_list[1]
            Stage = sorted_list[2]
            
            for post, post_dt, stg in zip(post_list, post_dt_list, Stage): 
                
                post_dt_0 = post_dt.replace(second=0, microsecond=0)
                
                if post_dt_p != post_dt_0:
                    
                    while post_dt_0 != set_dt:
                        New_Posture_DT.append(set_dt)
                        New_Posture.append(-1)
                        New_Stage.append(-1)
                        set_dt = set_dt + timedelta(minutes=1)
                    
                    New_Posture_DT.append(post_dt)
                    New_Posture.append(post)
                    New_Stage.append(-1*stg)
                    set_dt = set_dt + timedelta(minutes=1)
                
                else :
                    
                    New_Posture_DT.append(post_dt)
                    New_Posture.append(post)
                    New_Stage.append(-1*stg)
                
                post_dt_p = post_dt_0
            
                       
            """
            Stage_list=[]
            Posture_list=[]
            if(len(Posture)>0):  ###??????Posture
                Posture_list.append((Posture.iloc[0]['State']).astype(int)) ##??????????????????
                for sindex in range(1,len(Posture)): ##????????????????????????????????????????????????????????????append????????????(-4)
                    t1=Posture.iloc[sindex-1]['DT']   
                    t2=Posture.iloc[sindex]['DT']
                    timediff=round(pd.Timedelta(t2-t1).seconds/60.0)
                    if(timediff>1): ##??????????????????????????????
                        for k in range(timediff-1):
                            Posture_list.append(-1) ##?????????????????????-1
                    else: ###????????????????????????
                        nowPosture=(Posture.iloc[sindex]['State']).astype(int)                
                        if(nowPosture<-1):
                            nowPosture=-1
                        Posture_list.append(nowPosture)                 
            
            ####-----??????Stage----
            if(modeltype=='simple'):
                for s in Stage:
                    Stage_list.append(-1*s) ##????????????            
            else:
                if(len(Stage)>0):
                    Stage_list.append((Stage.iloc[0]['Stage']).astype(int)) ##??????????????????             
                    for sindex in range(1,len(Stage)): ##????????????????????????????????????????????????????????????append????????????(-4)
                        t1=Stage.iloc[sindex-1]['DT']   
                        t2=Stage.iloc[sindex]['DT']
                        timediff=round(pd.Timedelta(t2-t1).seconds/60.0)
                        if(timediff>1): ##??????????????????????????????
                            for k in range(timediff-1):
                                Stage_list.append(-1) ##?????????????????????-1                          
                        else: ###????????????????????????
                            nowStage=(Stage.iloc[sindex]['Stage']).astype(int)                
                            if(nowStage<=-4): ##<=-4??????????????????0(wake),-1(rem),-2(light),-3(deep)
                                nowStage=-1            
                                Stage_list.append(nowStage)
                            else: ##??????Stage????????????
                                Stage_list.append(-1*nowStage) ##????????????             
            """
        
        return New_Stage,New_Posture    

####=====================??????????????????====================================
    def SleepAnalysisReport(self,startTime,endTime,userInfo,modeltype='simple'):
        
        startDate = startTime.split(" ")[0]
        endDate = endTime.split(" ")[0]
        
        ## modeltype='ai' for using ai model 
        UUID=userInfo['id']    
        ##???????????????????????????
        outputFolder0 = os.path.join(self.BasePath,'SleepingReportOutput',UUID) 
        if not os.path.exists(outputFolder0):
            os.makedirs(outputFolder0)
        
        reportdate_str=(date.today()).strftime('%Y%m%d')  
        outputFolder1 = os.path.join(outputFolder0,reportdate_str)
        if not os.path.exists(outputFolder1):
            os.makedirs(outputFolder1)        
        
        ##????????????????????????????????????U???????????????UUID????????????
        UUID_tempPath = os.path.join(self.tempDB, UUID)
        if not os.path.exists(UUID_tempPath):
            os.makedirs(UUID_tempPath)                
        
        ###NowTime=datetime.now()       
        jsontempletePath=os.path.join(self.BasePath,'sleeping_jsonformat_v01.json')
        jsonfile=''
        with open(jsontempletePath,'r',encoding="utf-8") as readfile:  ## Reading from json file
            jsontemplatefile = json.load(readfile)      
        
        jsontemplatefile["irregularHeartRateStatistics"]=[] 
        testingPeriod=startTime+"~"+endTime
        CheckInDate_datatime=datetime(int(startTime[0:4]),int(startTime[4:6]),int(startTime[6:8]),int(startTime[9:11]),int(startTime[11:13]),int(startTime[13:15]))        
        CheckOutDate_datatime=datetime(int(endTime[0:4]),int(endTime[4:6]),int(endTime[6:8]),int(endTime[9:11]),int(endTime[11:13]),int(endTime[13:15]))
        delta = CheckOutDate_datatime-CheckInDate_datatime
        
        limitDate = CheckInDate_datatime + timedelta(hours=10)
        
        if CheckOutDate_datatime > limitDate:
            return {'status':False, 'message':'Too Many Hours.'}
        
        setDate = (CheckOutDate_datatime - timedelta(days=1)).strftime('%Y%m%d')
        
        numdays=delta.days+1
        DayTimeArray = pd.date_range(CheckInDate_datatime, periods=numdays).tolist() 
        Age=int(float(userInfo['age']))       
        Whole_HRMin=self.IntMaxValue
        Whole_HRMax=-self.IntMaxValue
        Whole_HRMean=0
        Whole_HRMeanCount=0
        heartRate7DaysDict=[]
        Whole_staticScore=Whole_heartfuncScore=-1
        Whole_MaxDecreaseTime=MaxDecreaseTimeIndex=HRMinTimeIndex=DayCount=-1 
        allRRIs=[] ####for poincare plot
        UnzipFileNameList=self.search_upzip(db_path=self.DB,target=UUID,start=setDate,end=endDate,export_path=UUID_tempPath)
        
        document_process_(UUID_tempPath, UUID_tempPath)
        
        ####----???????????????????????????-------
        timeTable,Stage,Posture=self.sleep_analysis(start=startTime,end=endTime,UUID=UUID,modeltype=modeltype,multi_proc=False)
        
        if len(Posture) == 0:
            print("No Data in this time period.")
            return {'status':False, 'message':'No Data in This Time Period.'}
        
        ##---------------------------
        
        for NowDay in DayTimeArray: ##?????????????????????CardiovascularScore
            ##arrhythmia_report=arrhythmia_analysis(user_info=userInfo,data_path=UUID_tempPath,start=NowDay.strftime("%Y%m%d"),end=(NowDay+timedelta(days=0)).strftime("%Y%m%d"),export_path=outputFolder2) ###??????????????????
            
            arrhythmia_report=self.arrhythmia_analysis(user_info=userInfo,data_path=UUID_tempPath,start=startTime,end=endTime) ###??????????????????
            
            PVCInformation=self.PVC_Report(user_info=userInfo,data_path=UUID_tempPath,start=startTime,end=endTime)
            
            ecgDict=[]
            ir_statistics=[]
            ir_statistics_perHour=[]
            
            if(len(arrhythmia_report)!=0):
                ecgDict,ir_statistics,ir_statistics_perHour=self.ArrhythmiaEventLoad(arrhythmia_report,ecgDict) 
                minHRStatistics,maxHRStatistics=self.MaxMinHREventLoad(arrhythmia_report)        
            
            if(len(PVCInformation)>0):
                ecgDict = self.PVCEventLoad(PVCInformation,ecgDict)                      
            
            ### ??????????????????????????????????????????????????????????????????10???
            ecgDict_filter, ir_statistics, ir_statistics_perHour = self.report_filter( ecgDict, ir_statistics, ir_statistics_perHour )
            
            HR_Mean_perHour=np.full(24,-1,dtype="float32")
            HR_Min_perHour=np.full(24,-1,dtype="float32")
            HR_Max_perHour=np.full(24,-1,dtype="float32")
            evaluationTime_MinuteperHour=np.full(24,0,dtype="float32")        
            HR_Max_WholeDay=HR_Min_WholeDay=HR_Mean_WholeDay=-1  
            
            OriginalTimeArray,ConcateEcgArray,MotionDataArray = self.DataConcate(UnzipFileNameList,startTime,endTime,userInfo["id"])    
            
            if(len(ConcateEcgArray)>0): ####???????????????
            
                DayCount=DayCount+1
                EcgData_Debasedline=BaselineRemove_Obj.BaselineRemove(ConcateEcgArray)  ####ECG????????????
                [staticScore,heartfuncScore,MaxDecreaseTime]=self.CardiovascularAnalysis(EcgData_Debasedline,OriginalTimeArray,MotionDataArray,Age) ###?????????????????????(???????????????)
              
                if(staticScore!=-1 and staticScore>Whole_staticScore):
                    Whole_staticScore=staticScore
                        
                if(heartfuncScore!=-1 and heartfuncScore>Whole_heartfuncScore):
                    Whole_heartfuncScore=heartfuncScore
                    Whole_MaxDecreaseTime=MaxDecreaseTime ###????????????????????????????????????HR????????????
                    MaxDecreaseTimeIndex=DayCount
                        
                [HR_Min,HR_Max,HR_average,HR_Min_perHour,HR_Max_perHour,HR_Mean_perHour,evaluationTime_MinuteperHour,HRArray_perminute]=self.RRIHeartRateAnalysis(EcgData_Debasedline,OriginalTimeArray,allRRIs)
                
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
                HR_Max_WholeDay=np.nanmax(HR_Max_perHour) ##??????????????????
                if(len(Positive_HR_Min_Array))>0:
                    HR_Min_WholeDay=np.nanmin(Positive_HR_Min_Array)   ###(HR_Min_perHour) ##??????????????????
                    
                if(len(Positive_HR_Mean_Array)>0):
                    HR_Mean_WholeDay=np.mean(Positive_HR_Mean_Array)   ###(HR_Mean_perHour) ##??????????????????                
                
                ratio=0.0
                
                if(np.nansum(evaluationTime_MinuteperHour)/60>0):
                    ratio=float("{:.2f}".format(sum(ir_statistics)/(np.nansum(evaluationTime_MinuteperHour)/60)))   
                
                evaluationTime=float("{:.2f}".format((np.nansum(evaluationTime_MinuteperHour)/60))) 
                if(evaluationTime>0): ###??????????????????????????????
                    heartRate7DaysDict.append({
                        "date":NowDay.strftime('%m/%d'),
                        "evaluationTime": evaluationTime, ###??????????????????????????????????????????
                        "average":HR_average,
                        "min":HR_Min,
                        "max":HR_Max,
                        "maxDecrease":False,
                        "minHR":False,
                        "irregular":{"number":int(sum(ir_statistics)),"rate":ratio}}) 
                else:
                    DayCount=DayCount-1
            else:
                HRArray_perminute = np.array([],dtype="int32")
                ##print('Currently Processing Day:',NowDay,' ConcateEcgArray contains no data!')
                ##heartRate7DaysDict.append({"date":NowDay.strftime('%m/%d'),"evaluationTime":0.0,"average":-1,"min":-1,"max":-1,"maxDecrease":False,"minHR":False,"irregular":{"number":0,"rate":0}})
            
            #fig = plt.figure(figsize=(15,12))
            #ax1 = fig.add_subplot(111)
            #ax1.plot(HRArray_perminute,'ko-')

            heartRate24HoursDict=[]
            MinHRValue_perHour=self.IntMaxValue
            HRMinTimeIndex_perHour=-1
            for hourindex in range(24): ##????????????????????????????????????????????????????????????????????????????????????????????????
                if(HR_Min_perHour[hourindex]!=-1 and HR_Min_perHour[hourindex]<MinHRValue_perHour):##???????????????????????????????????????HR
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
                        "evaluationTime": str(evaluationTime_MinuteperHour[hourindex]).zfill(2),
                        "average": HR_Mean_perHour[hourindex],
                        "max": HR_Max_perHour[hourindex],
                        "min": HR_Min_perHour[hourindex],
                        "maxDecrease": False, ##????????????Fasle
                        "minHR": False,       ##????????????Fasle
                        "irregular": {
                            "number": number_perHour,
                            "rate": ratio_perHour
                    }
                    })                
            
            if(HRMinTimeIndex_perHour!=-1):
                heartRate24HoursDict[HRMinTimeIndex_perHour]["minHR"]=True
            
            if(Whole_MaxDecreaseTime!=-1): ##????????????HR??????????????????
                MaxDecreaseTimeIndex_hour=int(Whole_MaxDecreaseTime.hour)          
                heartRate24HoursDict[MaxDecreaseTimeIndex_hour]["maxDecrease"]=True        
            
            if(HR_Mean_WholeDay>-1): ##???????????????????????????
                jsontemplatefile['irregularHeartRateStatistics'].append({
                    "date": NowDay.strftime('%m/%d'),
                    "maxHR": HR_Max_WholeDay,
                    "minHR": HR_Min_WholeDay,
                    "averageHR": HR_Mean_WholeDay,
                    "heartRate24Hours": heartRate24HoursDict,
                    "ecgs":ecgDict_filter})
        
        if(MaxDecreaseTimeIndex!=-1):        
            heartRate7DaysDict[MaxDecreaseTimeIndex]["maxDecrease"]=True
        
        if(HRMinTimeIndex!=-1):
            heartRate7DaysDict[HRMinTimeIndex]["minHR"]=True
            
        if(Whole_HRMeanCount>0):
            Whole_HRMean=int(Whole_HRMean/Whole_HRMeanCount) ###????????????HR???????????????        
        
        ## Calculate sleeping qualtiy score       
        PostureAll=pd.DataFrame()
        for p in Posture:
            PostureAll = pd.concat([PostureAll,p])            
        Posture=PostureAll          
        
        if(modeltype=='ai'):
            StageAll=pd.DataFrame()
            for s in Stage: ####???????????????????????????concate??????
                StageAll = pd.concat([StageAll,s])            
            Stage=StageAll    
        
        Stage_list,Posture_list=self.StagePosutureConcate(Stage,Posture,modeltype)
        DeepScore=LightScore=REMScore=SleepHoursScore=AsleepScore=TurnOverScore=0      
        
        SleepStartTime = len(Stage_list)
        UpRightEndTime = 0
        
        for i, (i_posture, i_stage) in enumerate(zip( Posture_list, Stage_list )):
            
            if i_stage == 2 or i_stage == 3:
                SleepStartTime = i
                break
            
            if i_posture == 1:
                UpRightEndTime = i
        
        SleepStartTime = SleepStartTime - UpRightEndTime ##????????????
        
        if(SleepStartTime>5 and SleepStartTime<=10):
            AsleepTimeText='???'
            AsleepScore=10
        elif(SleepStartTime>10 and SleepStartTime<=25):    
            AsleepScore=5
            AsleepTimeText='???'
        elif(SleepStartTime>25 and SleepStartTime<=40):    
            AsleepScore=0
            AsleepTimeText='???'
        elif((SleepStartTime>40 and SleepStartTime<=60) or SleepStartTime<=5):    
            AsleepScore=-5   
            AsleepTimeText='??????'    
        else :
            AsleepScore=-10           
            AsleepTimeText='??????'
        
        wake_turn = 0
        WakeCount = 0
        
        for post in Posture_list:
            
            if post == 1 and wake_turn == 0:
                wake_turn = 1
                WakeCount += 1
            elif post != 1 and wake_turn == 1:
                wake_turn = 0
        
        if Posture_list[0] == 1:
            WakeCount -= 1
        
        if Posture_list[-1] == 1:
            WakeCount -= 1
            
        """
        WakeLoc=np.argwhere((Posture_list[4:len(Posture_list)-5])==1) ###upright
        
        if(len(WakeLoc)>0): ##????????????????????????
            WakeCount=len(WakeLoc) ##???????????????5??????????????????5?????????????????????
        else:
            WakeCount=0           
        """
        
        Turnover_list=(Posture.loc[:,'Roll Over'].values).tolist()
        TurnOverCount=sum(Turnover_list)
        
        if(TurnOverCount>=11 and TurnOverCount<15):
            TurnOverScore=10
            TurnOverTimesText='???'
        elif(TurnOverCount>=6 and TurnOverCount<=10):
            TurnOverScore=5
            TurnOverTimesText='???'
        elif((TurnOverCount>=3 and TurnOverCount<=5) or (TurnOverCount>=16 and TurnOverCount<=20)):
            TurnOverScore=0
            TurnOverTimesText='??????'
        elif(TurnOverCount<3 or (TurnOverCount>=21 and TurnOverCount<=30)):
            TurnOverScore=-5
            TurnOverTimesText='??????'
        else :
            TurnOverScore=-10
            TurnOverTimesText='??????'            
            
        if(WakeCount==0):    
            WakeTimesText='???'
        elif(WakeCount>=1 and WakeCount<=2):    
            WakeTimesText='???'
        elif(WakeCount>2 and WakeCount<=5):    
            WakeTimesText='???'
        else :
            WakeTimesText='??????'            
        
        SleepMinutes = 0
        
        for i_stage in Stage_list:
            if i_stage != 0 and i_stage != -1:
                SleepMinutes += 1
        
        SleepHours = round(SleepMinutes/60,1)
        
        REMRatio=float("{:.2f}".format(timeTable.loc[0,'REM']))
        LightRatio=float("{:.2f}".format(timeTable.loc[0,'Light']))
        DeepRatio=float("{:.2f}".format(timeTable.loc[0,'Deep']))       
        
        if(Age>18 and Age<65):#????????????????????????
            if(SleepHours>=7 and SleepHours<=9): 
                SleepHoursScore=10   
                SleepHoursText='???'        
            elif((SleepHours>=6 and SleepHours<7) or (SleepHours>=9 and SleepHours<10)):
                SleepHoursScore=5  
                SleepHoursText='???'         
            elif((SleepHours>=5 and SleepHours<6) or (SleepHours>=10 and SleepHours<11)):
                SleepHoursScore=0  
                SleepHoursText='??????'          
            elif((SleepHours>=4 and SleepHours<5) or (SleepHours>=11 and SleepHours<12)):
                SleepHoursScore=-5   
                SleepHoursText='??????'        
            else :   
                SleepHoursScore=-10
                SleepHoursText='??????'
        else: ##65?????????
            if(SleepHours>=6 and SleepHours<=8): 
                SleepHoursScore=10   
                SleepHoursText='???'         
            elif((SleepHours>=5 and SleepHours<6) or (SleepHours>8 and SleepHours<10)):
                SleepHoursScore=5 
                SleepHoursText='???'            
            elif((SleepHours>=10 and SleepHours<11)): 
                SleepHoursScore=0
                SleepHoursText='??????'              
            elif((SleepHours>=4 and SleepHours<5) or (SleepHours>=11 and SleepHours<12)):
                SleepHoursScore=-5   
                SleepHoursText='??????'          
            else :
                SleepHoursScore=-10
                SleepHoursText='??????' 


        if(DeepRatio>45): #????????????????????????
            DeepScore=10
            DeepRatioText='???'
        elif(DeepRatio>=25):
            DeepScore=5
            DeepRatioText='???'
        elif(DeepRatio>15):
            DeepScore=0
            DeepRatioText='???'
        elif(DeepRatio>5):
            DeepScore=-5
            DeepRatioText='??????'
        else:   
            DeepScore=-10
            DeepRatioText='??????'
        
        if(LightRatio<=20): #????????????????????????
            LightScore=10
            LightRatioText='???'
        elif(LightRatio>20 and LightRatio<=35):
            LightScore=-5
            LightRatioText='???'
        elif(LightRatio>35 and LightRatio<=45):
            LightScore=0
            LightRatioText='???'
        elif(LightRatio>45 and LightRatio<=55):
            LightScore=5
            LightRatioText='??????'
        else:   
            LightScore=-10
            LightRatioText='??????'    

        
        if(REMRatio>15 and REMRatio<=25): ##REM
            REMScore=10
            REMRatioText='???'
        elif((REMRatio>10 and REMRatio<=15) or (REMRatio>25 and REMRatio<=30)):
            REMScore=5
            REMRatioText='???'
        elif((REMRatio>5 and REMRatio<=10) or (REMRatio>30 and REMRatio<=35)):
            REMScore=0
            REMRatioText='???'
        elif(REMRatio>35 or REMRatio<=45):
            REMScore=-5
            REMRatioText='??????'
        else :
            REMScore=-10    
            REMRatioText='??????'               

        SleepingQualityScore=70+(SleepHoursScore+AsleepScore+REMScore+DeepScore+LightScore+TurnOverScore)
        
        if SleepingQualityScore > 95:
            SleepingQualityScore = 95
        elif SleepingQualityScore < 55:
            SleepingQualityScore = 55
        
        if SleepingQualityScore >= 83: ###??????????????????????????????
            SleepingQualityText='???'
        elif 83 > SleepingQualityScore >= 67:
            SleepingQualityText='???'
        else:
            SleepingQualityText='??????'
            
        SleepingQualtiyHistoricalList=self.SleepingQualityHistoryExtractor(userInfo["id"])
        SleepingQualtiyHistoricalList[0]['score']=SleepingQualityScore        
        ####--------------write json Template File----------------------------------------
        jsontemplatefile['header']={
        "report": "E001V1",
        "reportName": "BEATINFO SLEEPING ANALYSIS REPORT",
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
        
        jsontemplatefile['sleepingState']={
        "date": Posture.iloc[0]['Date'],
        "time": (Posture.iloc[0]['DT']).strftime("%H:%M:%S"),
        "Stage": Stage_list,
        "Posture": Posture_list,
        "HeartRate": HRArray_perminute.tolist()  
        }
            
        jsontemplatefile['sleepingQualityReport']={
            "score" : SleepingQualityScore,  
            "scoreText": SleepingQualityText,  
            "sleepingTimeIndex": {
            "score": SleepHours,   
            "scoreText": SleepHoursText,  
            "description" : "??????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????7~9?????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????7~9???????????????????????????????????????11?????????????????????11????????????1????????????(??????)???????????????????????????????????????????????????????????????????????????5??????7????????????????????????????????????????????????????????????????????????????????????????????????"
            },
            "timeCostIndex":  {
            "cost": SleepStartTime, 
            "scoreText": AsleepTimeText,  
            "description" : "?????????????????????????????????????????????????????????????????????????????????AI????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????10~20??????????????????????????????????????????5?????????????????????????????????????????????????????????????????????????????????????????????????????????30?????????????????????????????????????????????????????????????????????????????????????????????????????????"
            },
            "deepRatioIndex": {
            "ratio": DeepRatio,
            "scoreText": DeepRatioText,
            "description" : "???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????15%???25%?????????????????????????????????72???120???????????????"
            },
            "lightRatioIndex": {
            "ratio": LightRatio,
            "scoreText": LightRatioText,
            "description" : "??????????????????????????????5???6??????????????????????????????????????????????????????60???90?????????????????????????????????????????????????????????55%????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????"           
            },
            "remRatioIndex": {
            "ratio": REMRatio,
            "scoreText": REMRatioText,
            "description" : "??????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????REM??????????????????REM????????????????????????????????????20%????????????REM????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????"            
            },
            "wakeIndex": {
            "time": WakeCount,
            "scoreText": WakeTimesText,
            "description" : "65??????????????????????????????????????? (???5??????)????????????1????????????65???????????????????????????????????????2???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????20?????????????????????????????????????????????????????????20????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????3C????????????????????????????????????????????????????????????"           
            },
            "turnoverIndex": {
            "times": TurnOverCount,
            "scoreText": TurnOverTimesText,
            "description" : "???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????80??????????????????????????????????????????60????????????????????????45?????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????20~40???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????"           
            }

       }
            
        jsontemplatefile['SleepingQualityExamEvaluation']={
            "scoreRecord": {
                "description": "????????????????????????",
                "records": SleepingQualtiyHistoricalList           
            },
            "maxHRStatistics":maxHRStatistics,
            "minHRStatistics":minHRStatistics
        }          
             
        JsonSavedName = "SleepingQualityReport_%s.json" %(datetime.now().strftime("%Y%m%d%H")+"("+userInfo["id"]+")")
        JsonSavedPath=os.path.join(outputFolder1,JsonSavedName)
        with open(JsonSavedPath,'w',encoding='utf-8') as f:
            f.write((str)(jsontemplatefile))
        
        if(os.path.exists(JsonSavedPath)):
            return {'status':True, 'message':JsonSavedPath}            
        else:
            return {'status':False, 'message':'No Document'}
        
###--------------------------------
if __name__ == '__main__':
    
    userInfo = {
        "id":"7",
        "name":"test",
        "email":"test",
        "gender":"male",
        "height":"175",
        "weight":"65",
        "birthday":"1990/01/01",
        "age":"30"
    }

    startTime = "20220804 220000"
    endTime = "20220805 230000"
    DBPath="C:\\Users\\User\\Desktop\\DataDB"   
    SleepQualityReport_Obj=SleepQualityReportGenerator(DBPath)
    JsonSavedPath=SleepQualityReport_Obj.SleepAnalysisReport(startTime,endTime,userInfo,modeltype='simple')
    print('Finished!')
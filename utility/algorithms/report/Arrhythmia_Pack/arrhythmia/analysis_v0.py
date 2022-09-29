import numpy as np
import os, time, sys, json
#os.environ["OMP_NUM_THREADS"] = "1"
from datetime import datetime
from ecg.abnormal.DatasetV2 import AbnormalDetector
from ecg.baseline import BaselineRemove
from ecg.Rpeak import RPeakDetection
from ecg import Fiducial_v5 as Fiducial
from multiprocessing import Pool
import tqdm, sys

class ArrhythmiaDetection:
    def __init__(self, srjPath, evtPath, userInfo):
        self._initialize()
        self.srjPath = srjPath
        self.evtPath = evtPath
        self.Report["user_info"] = userInfo
        
    def genReport(self, Mode="Arrhythmia", gpu=0, multi_proc=False):
        self._ParseEvtFile()
        self._ParseSrjFile()
        self._QualityCheckModel(GPU=gpu)
        if multi_proc:
            self._AnalyzeArrhythmia_MP(os.cpu_count()/2)
        else:
            self._AnalyzeArrhythmia()
        self._OutputEvents(mode=Mode)
        self.Report["report_datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.Report.update(self.Output)
        return self.Report
        
    def _initialize(self):
        # File Path
        self.evtPath = ""
        self.srjPath = ""
        # Measure Time Info
        self.startDT = []
        self.endDT = []
        # Raw Datas
        self.ecgArrays = []
        self.timeArrays = []
        # AI result
        self.passIdxs = []
        # Arrhythmia Thresholds
        self.std_thr = 0.1
        self.RRI_thr = 0.2
        # Fiducial Features
        self.Features = []
        # Output
        self.Output = {}
        self.Output["ir_statistics"] = np.zeros(31,dtype='int32').tolist()
        self.Output["ir_events"] = []
        self.Output["max_hr_physio"] = []
        self.Output["min_hr_physio"] = []
        self.Output["note"] = ""
        # Report Content
        self.Report = {}
        self.Report["type"] = "P001"
        self.Report["version"] = "v1.0"
        self.Report["report_datetime"] = ""
        self.Report["measure_start_datetime"] = ""
        self.Report["measure_end_datetime"] = ""
        self.Report["user_info"] = []

    def _ParseEvtFile(self):
        f = open(self.evtPath, "r")
        line = f.readline()
        f.close()
        evt = json.loads(line)
        self.startDT = datetime.fromtimestamp(evt["startTT"]/1000)
        self.endDT = datetime.fromtimestamp(evt["endTT"]/1000)
        self.Report["measure_start_datetime"] = self.startDT.strftime("%Y-%m-%d %H:%M:%S")
        self.Report["measure_end_datetime"] = self.endDT.strftime("%Y-%m-%d %H:%M:%S")  

    def _ParseSrjFile(self):    
        print("[Progress] Parse Data")
        t1 = time.time()
        ecgArray = []   
        f = open(self.srjPath, "r")
        line = f.readline()
        srj = json.loads(line)
        dt = datetime.fromtimestamp(srj["tt"]/1000)
        self.timeArrays.append(dt)
        ecgs = self._ecgSegmentProcess(srj["rows"]["ecgs"])
        ecgArray.append(ecgs)
        line = f.readline()
        while line:
            srj = json.loads(line)
            dt = datetime.fromtimestamp(srj["tt"]/1000)
            self.timeArrays.append(dt)
            ecgs = self._ecgSegmentProcess(srj["rows"]["ecgs"])
            ecgArray.append(ecgs)
            line = f.readline()
        self.ecgArrays = np.array(ecgArray)
        t2 = time.time()
        print("  Elapsed time: %.2fs" %(t2-t1))
        
    @staticmethod
    def _ecgSegmentProcess(ecg):
        # Remove Baseline and Pulse
        ecg_filt = BaselineRemove(ecg)
        # Check Output Length
        if len(ecg_filt) < 2500:
            output = np.zeros(2500)
            output[:len(ecg_filt)] = ecg_filt
        else:
            output = ecg_filt[:2500]
        return output.tolist()

    def _QualityCheckModel(self, GPU=0):
        print("[Progress] Quality Check")
        t1 = time.time()
        score = []
        totalSegment = len(self.ecgArrays)
        print("  Progress of Quality Check: 0/%d." %(totalSegment), end="")
        if totalSegment > 0:
            AI_model = AbnormalDetector(use_gpu=GPU)
            if GPU:
                segNum = 1000 ##設定每1000筆計算一次
            else:
                segNum = 10
            if totalSegment > segNum:
                ##資料分多次處理
                looptime = int(totalSegment/segNum)
                for k in range(looptime):
                    t3 = time.time()
                    ## 分類訊號品質好壞
                    dataset = self.ecgArrays[k*segNum:(k+1)*segNum]
                    NowScore = AI_model.detect_abnormal(dataset)
                    t4 = time.time()
                    print("\r  Progress of Quality Check: %d/%d. (%d data/%.2fs)" 
                            %((k+1)*segNum, totalSegment, segNum, t4-t3), end="")
                    score.extend(NowScore)
                ##計算非整除的剩餘片段               
                if totalSegment%segNum > 0:  
                    dataset = self.ecgArrays[looptime*segNum:]
                    NowScore = AI_model.detect_abnormal(dataset)
                    score.extend(NowScore)
            else: ##資料不滿1000筆
                ## 分類訊號品質好壞 
                score = AI_model.detect_abnormal(self.ecgArrays)   
            print("\r  Progress of Quality Check: %d/%d." 
                    %(totalSegment, totalSegment), end="")  

            score = np.array(score, dtype=np.float32)
            self.passIdxs = np.argwhere(score <= 0.5).flatten()
        else:
            print("  No data founded. --> End process.")
        t2 = time.time()
        print("  Elapsed time: %.2fs" %(t2-t1))
    
    def _AnalyzeArrhythmia(self):
        print("[Progress] Arrhythmia Analysis")
        t1 = time.time()
        count = 1
        for idx in self.passIdxs:
            print("\r  Progress of Arrhythmia Analysis: %d/%d"
                %(count,len(self.passIdxs)), end="")
            features = self._EcgAnalysis(idx)
            if features is not None:
                self.Features.append(self._EcgAnalysis(idx))
            count += 1
        t2 = time.time()
        print("  Elapsed time: %.2fs" %(t2-t1))

    def _AnalyzeArrhythmia_MP(self, procNum):
        print("[Progress] Arrhythmia Analysis")
        t1 = time.time()
        with Pool(processes=int(procNum)) as pool:
            with tqdm.tqdm(total=len(self.passIdxs),desc='  [進度]',file=sys.stdout) as pbar:
                for feature in pool.imap(self._EcgAnalysis, self.passIdxs):
                    if feature is not None:
                        self.Features.append(feature)
                    pbar.update()
        t2 = time.time()
        print("  Elapsed time: %.2fs" %(t2-t1))

    def _OutputEvents(self, mode):
        ## Output irregular events
        if mode == "Arrhythmia":
            ir_events = self._EventSummerize("Arrhythmia",50)
            if len(ir_events) > 0:
                self.Output["ir_events"] = ir_events
                self.Output["note"] = "建議前往醫院進行更進一步之檢測"
        else:
            ir_events = self._EventSummerize("All",[])
            self.Output["ir_events"] = ir_events

        ## Output max and min HR event
        max_hr_physio = self._EventSummerize("Maximum Heart Rate",10)
        self.Output["max_hr_physio"] = max_hr_physio[0]
        min_hr_physio = self._EventSummerize("Minimum Heart Rate",10)
        self.Output["min_hr_physio"] = min_hr_physio[0]

    def _EventSummerize(self, reason, num):
        if reason == "All":
            events = self.Features
            num = len(events)
        if reason == "Arrhythmia":
            events = [evt for evt in self.Features if evt['ResultFlag'] > 0] 
            events.sort(key=lambda s:s['STD'], reverse=True)
        if reason == "Maximum Heart Rate":
            events = sorted(self.Features, key=lambda s:s['maxHR'], reverse=True)
        if reason == "Minimum Heart Rate":
            events = sorted(self.Features, key=lambda s:s['minHR'], reverse=False)

        CheckNumFunc = lambda x : num if len(x)>=num else len(x)
        OutputNum = CheckNumFunc(events)
        events = events[:OutputNum]
        output = []
        for evt in events:
            dt = self.timeArrays[evt['Index']]
            ecg = self.ecgArrays[evt['Index']]
            if reason=="All":
                if evt['ResultFlag'] > 0:
                    title = "Arrhythmia"
                else:
                    title = ""
            else:
                title = reason
            output.append(self._eventsConverter(evt, title, dt, ecg))
        return output
        
    def _eventsConverter(self, evt, reason, dt, ecg):
        output = {}
        output["timestamp"] = dt.timestamp() * 1000
        output["reason"] = reason

        if np.isnan(evt["avgHR"]):
            output["hr"] = "--"
        else:
            output["hr"] = str(int(evt["avgHR"])) + " bpm"
        
        quality = evt["good_quality"]
        output["pr"] = self._msConvert(evt["avgPR"],quality)
        output["qrs"] = self._msConvert(evt["avgQRS"],quality)
        output["qt"] = self._msConvert(evt["avgQT"],quality)
        output["qtc"] = self._msConvert(evt["avgQTc"],quality)
        output["ecgs"] = ecg.tolist()
        return output

    @staticmethod
    def _msConvert(x, quality):
        pass
        if np.isnan(x):
            return "--"
        else:
            output = str(int(x))+" ms"
            if not quality:
                output = output + "*"
            return output

    def _EcgAnalysis(self, idx):
        ## detect R peaks
        sig = self.ecgArrays[idx]
        RPeaks = RPeakDetection(sig)
        if RPeaks.size > 1:        
            RPeakArray = RPeaks[1:]           
            # ECG normalization
            ecg = np.interp(sig,(sig.min(),sig.max()),(0,1)).reshape(2500,1)
            # Calculate fiducial features of ecg
            Features = Fiducial.feature_gen(ecg,250,RPeakArray)
            Features['ecg'] = sig.tolist()
            Ridx = Features["Ridx"]
            if len(Ridx) >= 2:         
                ## calculate RRI 
                RRIArray = np.diff(Ridx)*1000/250
                RRIArray.astype('int32')

                if len(RRIArray) >= 2:
                    nowMaxRRI = max(RRIArray)
                    nowMinRRI = min(RRIArray)

                    ## detect irreqular heart beats
                    ResultFlag = 0
                    stdValue = np.std(RRIArray)/np.mean(RRIArray)
                    if stdValue >= self.std_thr:                                
                        ResultFlag = 1

                    Var_Count = 0
                    for k in range(1,len(RRIArray)):
                        delta_RRI = (RRIArray[k]-RRIArray[k-1])/RRIArray[k-1]
                        if abs(delta_RRI) >= self.RRI_thr:
                            Var_Count += 1
                            if Var_Count >= 2:
                                ResultFlag = 2 if ResultFlag==0 else 12
                                break
                    
                    Dict = {'Index':idx,
                            'ResultFlag':ResultFlag,
                            'STD':stdValue,
                            'minHR':60000/nowMaxRRI,
                            'maxHR':60000/nowMinRRI,
                            'Ridx':Ridx,
                            }
                    Dict.update(Features)
                    return Dict
    

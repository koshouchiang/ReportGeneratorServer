from Arrhythmia_Pack import ecg
import numpy as np
import os, time, sys, json
#os.environ["OMP_NUM_THREADS"] = "1"
from datetime import datetime, timedelta
from ..ecg.abnormal.DatasetV2 import AbnormalDetector
from ..ecg.baseline import BaselineRemove
from ..ecg.Rpeak import RPeakDetection
from ..ecg.Rpeak import RRI_filter
from ..ecg import Fiducial_v5 as Fiducial
from multiprocessing import Pool, RawArray
import tqdm, sys
from . import multi_preprocess as mp
from ..ecg.score import AreaRatio, PatternClustering

class ArrhythmiaDetection:
    def __init__(self, data, userInfo):
        self._initialize()
        self._load_data_multi(data)
        self.Report["user_info"] = userInfo
        
    def genReport(self, Mode="Arrhythmia", gpu=0, multi_proc=False):
        self._QualityCheckModel(GPU=gpu)
        if multi_proc:
            self._AnalyzeArrhythmia_MP(8)
        else:
            self._AnalyzeArrhythmia()
        self._Arrhythmia_Count()
        self._OutputEvents(mode=Mode)
        self.Report["report_datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.Report.update(self.Output)
        return self.Report
        
    def _initialize(self):
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
        # Arrhythmia Counts
        self.ArrhythmiaCounts = {}
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
        
    def _load_data(self, data):
        print("[Progress] Processing Datas")
        t1 = time.time()
        data.sort(key = lambda i:i['tt'])
        ecgArray = []
        with tqdm.tqdm(total=len(data),desc='  [進度]',file=sys.stdout) as pbar:
            for line in data:
                dt = datetime.fromtimestamp(line["tt"]/1000)
                self.timeArrays.append(dt)
                ecgs = self._ecgSegmentProcess(line["rows"]["ecgs"])
                ecgArray.append(ecgs)
                pbar.update()
        self.ecgArrays = np.array(ecgArray)

        self.startDT = self.timeArrays[0]
        self.endDT = self.timeArrays[-1] + timedelta(seconds=10)
        self.Report["measure_start_datetime"] = self.startDT.strftime("%Y-%m-%d %H:%M:%S")
        self.Report["measure_end_datetime"] = self.endDT.strftime("%Y-%m-%d %H:%M:%S")  
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

    def _load_data_multi(self, data):
        print("[Progress] Processing Datas")
        t1 = time.time()
        data.sort(key = lambda i:i['tt'])

        self.timeArrays = [datetime.fromtimestamp(line["tt"]/1000) for line in data]
        self.startDT = self.timeArrays[0]
        self.endDT = self.timeArrays[-1] + timedelta(seconds=10)
        self.Report["measure_start_datetime"] = self.startDT.strftime("%Y-%m-%d %H:%M:%S")
        self.Report["measure_end_datetime"] = self.endDT.strftime("%Y-%m-%d %H:%M:%S")  

        X_shape = (len(data),2500)
        ecgDatas = np.zeros(X_shape)
        for i in range(len(data)):
            ecg = data[i]['rows']['ecgs']
            if len(ecg) < 2500:
                ecgDatas[i,:len(ecg)] = ecg
            else:
                ecgDatas[i,:] = ecg[:2500]
        # Create array in shared memory
        X = RawArray('d',X_shape[0]*X_shape[1])
        # Wrap X as an numpy array so we can easily manipulates its data.
        X_np = np.frombuffer(X).reshape(X_shape)
        # Copy data to our shared array.
        np.copyto(X_np,ecgDatas)
        # Multi processing in shared memory
        with Pool(processes=8,initializer=mp.init_worker,initargs=(X,X_shape)) as pool:
            with tqdm.tqdm(total=len(data),desc='  [進度]',file=sys.stdout) as pbar:
                for result in pool.imap(mp.segment_preprocess,range(len(data))):
                    self.ecgArrays.append(result)
                    pbar.update()
        self.ecgArrays = np.array(self.ecgArrays)
        t2 = time.time()
        print("  Elapsed time: %.2fs" %(t2-t1))

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
                    print("\r  Progress of Quality Check: %d/%d. (%.2fit/s)" 
                            %((k+1)*segNum, totalSegment, segNum/(t4-t3)), end="")
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
            result = self._EcgAnalysis(idx)
            if result is not None:
                self.Features.append(self._EcgAnalysis(idx))
            count += 1
        t2 = time.time()
        print("  Elapsed time: %.2fs" %(t2-t1))

    def _AnalyzeArrhythmia_MP(self, procNum):
        print("[Progress] Arrhythmia Analysis")
        t1 = time.time()
        # with Pool(processes=int(procNum)) as pool:
        #     with tqdm.tqdm(total=len(self.passIdxs),desc='  [進度]',file=sys.stdout) as pbar:
        #         #for result in pool.imap(self._EcgAnalysis, self.passIdxs):
        #         for result in pool.map(self._EcgAnalysis, self.passIdxs):
        #             if result is not None:
        #                 self.Features.append(result)
        #             pbar.update()

        X_shape = self.ecgArrays.shape
        X = RawArray('d',X_shape[0]*X_shape[1])
        # Wrap X as an numpy array so we can easily manipulates its data.
        X_np = np.frombuffer(X).reshape(X_shape)
        # Copy data to our shared array.
        np.copyto(X_np,self.ecgArrays)
        with Pool(processes=procNum,initializer=mp.init_worker,initargs=(X,X_shape)) as pool:
            with tqdm.tqdm(total=len(self.passIdxs),desc='  [進度]',file=sys.stdout) as pbar:
                for result in pool.map(mp.EcgAnalysis, self.passIdxs):
                    if result is not None:
                        self.Features.append(result)
                    pbar.update()
        self.Features.sort(key=lambda s:s['Index'], reverse=False)
        t2 = time.time()
        print("  Elapsed time: %.2fs" %(t2-t1))

    def _Arrhythmia_Count(self):
        startDate = self.startDT.date()
        endDate = self.endDT.date()
        DateList = []
        for i in range(0,(endDate-startDate).days+1):
            DateList.append(startDate+timedelta(days=i))

        arrhythmia = [evt for evt in self.Features if evt['ResultFlag'] > 0] 
        dateArray = [self.timeArrays[arr['Index']].strftime("%Y%m%d") for arr in arrhythmia]
        dateArray = np.array(dateArray)
        
        for Date in DateList:
            Dday = Date.day
            Dstr = Date.strftime("%Y%m%d")
            Count = sum(dateArray==Dstr)
            self.Output["ir_statistics"][Dday-1] = Count
            self.ArrhythmiaCounts[Dstr] = Count

    def _OutputEvents(self, mode):
        ## Output irregular events
        print("[Progress] Output Features")
        t1 = time.time()
        if mode == "Arrhythmia":
            # ir_events = self._EventSummerize("Arrhythmia",50)
            ir_events = self._EventSummerize("Arrhythmia",100)
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
        t2 = time.time()
        print("  Elapsed time: %.2fs" %(t2-t1))

    def _EventSummerize(self, reason, num):
        if reason == "All":
            events = self.Features
            num = len(events)
        if reason == "Arrhythmia":
            # events = [evt for evt in self.Features if evt['ResultFlag'] > 0] 
            # events.sort(key=lambda s:s['STD'], reverse=True)
            events = [evt for evt in self.Features if evt['ResultFlag']>0 and evt['score']>0.6] 
            events.sort(key=lambda s:(-s['ResultFlag'],-s['score']))
        if reason == "Maximum Heart Rate":
            events = sorted(self.Features, key=lambda s:s['avgHR'], reverse=True)
        if reason == "Minimum Heart Rate":
            events = sorted(self.Features, key=lambda s:s['avgHR'], reverse=False)

        CheckNumFunc = lambda x : num if len(x)>=num else len(x)
        OutputNum = CheckNumFunc(events)
        events = events[:OutputNum]
        output = []
        # for evt in events:
        #     dt = self.timeArrays[evt['Index']]
        #     ecg = self.ecgArrays[evt['Index']]
        #     if reason=="All":
        #         if evt['ResultFlag'] > 0:
        #             title = "Arrhythmia"
        #         else:
        #             title = ""
        #     else:
        #         title = reason
        #     output.append(self._eventsConverter(evt, title, dt, ecg))
        for evt in events:
            dt = self.timeArrays[evt['Index']]
            ecg = self.ecgArrays[evt['Index']]

            if reason=="All":
                if evt['ResultFlag'] > 0:
                    title = "Arrhythmia"
                else:
                    title = ""
            else:
                scale = evt['scale']
                ecg = ecg * scale
                # title = "%dmm/mV" %(10*scale)
                title = "%dmm/mV, score:%.2f, flag:%d" %(10*scale,evt['score'],evt['ResultFlag'])
            output.append(self._eventsConverter(evt, title, dt, ecg))
        return output
        
    def _eventsConverter(self, evt, reason, dt, ecg):
        output = {}
        output["timestamp"] = dt.timestamp() * 1000
        output["reason"] = reason
        output['hr'] = str(int(evt["avgHR"])) + " bpm"

        ecg_norm = np.interp(ecg,(ecg.min(),ecg.max()),(0,1)).reshape(2500,1)
        feature = Fiducial.feature_gen(ecg_norm,250,evt['Ridx'])
        # if np.isnan(feature["avgHR"]):
        #     output["hr"] = "--"
        # else:
        #     output["hr"] = str(int(feature["avgHR"])) + " bpm"
        
        quality = feature["good_quality"]
        output["pr"] = self._msConvert(feature["avgPR"],quality)
        output["qrs"] = self._msConvert(feature["avgQRS"],quality)
        output["qt"] = self._msConvert(feature["avgQT"],quality)
        output["qtc"] = self._msConvert(feature["avgQTc"],quality)
        output["ecgs"] = ecg.tolist()
        return output
        
        # if np.isnan(evt["avgHR"]):
        #     output["hr"] = "--"
        # else:
        #     output["hr"] = str(int(evt["avgHR"])) + " bpm"
        
        # quality = evt["good_quality"]
        # output["pr"] = self._msConvert(evt["avgPR"],quality)
        # output["qrs"] = self._msConvert(evt["avgQRS"],quality)
        # output["qt"] = self._msConvert(evt["avgQT"],quality)
        # output["qtc"] = self._msConvert(evt["avgQTc"],quality)
        # output["ecgs"] = ecg.tolist()
        # return output
        
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

        if RPeaks.size > 1:        
            RPeakArray = RPeaks[1:]           
            Ridx = RPeakArray
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
    
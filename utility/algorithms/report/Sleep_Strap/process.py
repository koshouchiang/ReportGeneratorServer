import os, json
from zipfile import ZipFile
from datetime import datetime, timedelta
import pandas as pd
import sleep_v2 as sleep
import matplotlib.pyplot as plt
from multiprocessing import Pool
from time import time
import platform

if __name__ == "__main__":
    import process

    if platform.system() == 'Darwin':
        exportPath = "/Volumes/GoogleDrive/共用雲端硬碟/奇翼醫電_執行專案/智慧防疫好幫手/報告產生器"
        DB = "/Volumes/GoogleDrive/.shortcut-targets-by-id/1Mc_sTYrGzDau1JPki2AQDpV4FeX5tKu3/SWM_DataCenter/Health_Server"
        tempDB = "/Users/swm-paul/Downloads/防疫專案暫存"
    else:
        exportPath = os.path.abspath("G:/共用雲端硬碟/奇翼醫電_執行專案/智慧防疫好幫手/報告產生器")
        DB = os.path.abspath("G:/.shortcut-targets-by-id/1Mc_sTYrGzDau1JPki2AQDpV4FeX5tKu3/SWM_DataCenter/Health_Server")
        tempDB = os.path.abspath("D:/防疫專案暫存")
    
    workSheetPath = os.path.join(exportPath,"防疫好幫手_分析報告清單.xlsx")
    workSheet = pd.read_excel(workSheetPath)
    toDo = workSheet[workSheet['分析進度']=='待分析']
    
    for index in toDo.index:
        startDate = str(int(toDo.loc[index,'入住']))
        endDate = str(int(toDo.loc[index,'退房']))
        UUID = toDo.loc[index,'UUID']
        if not isinstance(UUID, str):
            UUID = str(int(UUID))
        if '\n' in UUID:
            UUID = UUID.replace('\n','')
        print("\nUUID: %s, Date:%s~%s" %(UUID,startDate,endDate))
        
        # 將符合日期的資料解壓縮至暫存資料區
        tempPath = os.path.join(tempDB, UUID)
        if not os.path.exists(tempPath):
            os.makedirs(tempPath)
        process.search_upzip(db_path=DB,target=UUID,start=startDate,end=endDate,export_path=tempPath)

        # 產生報告輸出資料夾
        outputFolder0 = os.path.join(exportPath,'報告原始資料',str(toDo.loc[index,'報告資料夾']))
        if not os.path.exists(outputFolder0):
            os.makedirs(outputFolder0)
        outputFolder1 = os.path.join(outputFolder0,UUID)
        if not os.path.exists(outputFolder1):
            os.makedirs(outputFolder1)
        outputFolder2 = os.path.join(outputFolder1,'睡眠分析圖')
        if not os.path.exists(outputFolder2):
            os.makedirs(outputFolder2)
        else:
            print("Report is already exist.")
            ##continue

        # 分析結果
        t1 = time()
        process.sleep_analysis(data_path=tempPath,
                               start=startDate,end=endDate,
                               export_path=outputFolder2,
                               multi_proc=False)
        t2 = time()
        print(' Elapsed Time: %.2fs' %(t2-t1))

def search_upzip(db_path,target,start,end,export_path):
    startDT = datetime.strptime(start,'%Y%m%d')
    endDT = datetime.strptime(end,'%Y%m%d')
    existFiles = [f.split('.')[0] for f in os.listdir(export_path) if f.endswith('.srj')]

    print("[Progress] Downloading Datas")
    t1 = time()
    # 遍蒞所有資料夾
    for D in os.listdir(db_path):
        Folder = os.path.join(db_path,D)
        # 符合日期的資料夾
        if os.path.isdir(Folder):
            date = datetime.strptime(D,'%Y%m%d')
            if date >= startDT and date <= endDT:
                # 遍歷該日期資料夾的檔案
                for files in os.listdir(Folder):
                    fileparts = files.split("_")
                    uuid = fileparts[0]
                    # 檢查檔案是否已解壓縮過
                    filename = files.split('.')[0]
                    if filename in existFiles:
                        continue
                    if "(" in filename or ")" in filename:
                        continue
                    # 檢查符合UUID且為zip檔
                    if uuid == target and files.endswith('.zip'):
                        filePath = os.path.join(Folder,files)
                        print('     %s' %filename)
                        # 解壓縮至指定路徑
                        with ZipFile(filePath,'r') as zip:
                            zip.extractall(export_path)
    t2 = time()
    print("  Elapsed time: %.2fs" %(t2-t1))

def sleep_analysis(data_path,start,end,export_path,multi_proc=False):
    fileNames = [ff[:-4] for ff in os.listdir(data_path) if ff.endswith('srj')]

    # Set sleep duration in table
    startDate = datetime.strptime(start,'%Y%m%d')
    endDate = datetime.strptime(end,'%Y%m%d')
    Dates = [startDate+timedelta(days=i) for i in range((endDate-startDate).days+1)]
    timeTable = pd.DataFrame({'Date':Dates})

    # Add empty columns in table
    timeTable[['StartDetect','EndDetect']] = ""
    timeTable[['OnBed','OffBed']] = ""
    timeTable[['Right','Prone','Left','Supine']] = 0
    timeTable[['Asleep','WakeUp']] = ""
    timeTable[['SleepHours','REM','Light','Deep']] = 0
    timeTable[['min_hr','lf','hf','lf/hf','lf%','stage']] = 0

    on_bed_time = 22 # start time in hour
    sleep_hours = 12 # hours
    for i in range(len(timeTable)-1):
        timeTable.loc[i,'StartDetect'] = timeTable.loc[i,'Date']+timedelta(hours=on_bed_time)
        timeTable.loc[i,'EndDetect'] = timeTable.loc[i,'StartDetect']+timedelta(hours=sleep_hours)

    # Analyze datas in each night
    MP = multi_process(timeTable,fileNames,data_path,export_path)
    if multi_proc:
        Output = MP._analyze_multi_night_MP()
    else:
        Output = MP.analyze_multi_night()
    for output in Output:
        for key, value in output.items():
            timeTable.iloc[int(key),3:] = value.values()
    
    # Export result of analysis to files
    timeTable.to_csv(os.path.join(export_path,"Analysis_Result.csv"),index=False)

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
    plt.close(fig1)

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

    def _analyze_multi_night_MP(self):
        with Pool(processes=8) as pool:
            for result in pool.map(self._analyze_one_night, range(len(self.timeTable)-1)):
                if result is not None:
                    self.Output.append(result)
        return self.Output

    def analyze_multi_night(self):
        for idx in range(len(self.timeTable)-1):
            result = self._analyze_one_night(idx)
            if result is not None:
                self.Output.append(result)
        return self.Output

    def _analyze_one_night(self,idx):
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
            return
        Datas.sort(key = lambda i:i['tt'])
        
        model = sleep.Device(Datas,duration=[startTT,endTT])
        model.posture_figure(save_path=self.exportPath)
        model.stage_figure(save_path=self.exportPath)
        model.poincare_figure(save_path=self.exportPath)
        model.output_stages(save_path=self.exportPath)
        postureResult = model.posture_analysis()
        stageResult = model.stage_analysis()
        hrvResult = model.hrv_analysis()

        datas = {}
        datas.update(postureResult)
        datas.update(stageResult)
        datas.update(hrvResult)
        output = {str(idx):datas}
        return output
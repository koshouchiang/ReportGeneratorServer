from pydoc import TextDoc
from warnings import filterwarnings
import plotly.graph_objects as go
from fpdf import FPDF
import os
from datetime import datetime
from numpy import irr

#####
## Use this function need the following extra packages
## plotly
## kaleido
#####

class PDF_E001V1(FPDF):

    # Page header
    def header(self):
        pass

    # Page footer
    def footer(self):
        pass

    def sColors(self, txtColor=[0, 0, 0], drawColor=[0, 0, 0], fillColor=[255, 255, 255]):
        self.set_text_color(txtColor[0], txtColor[1], txtColor[2])
        self.set_draw_color(drawColor[0], drawColor[1], drawColor[2])
        self.set_fill_color(fillColor[0], fillColor[1], fillColor[2])

    def dText(self, x, y, txt, family, size:int=7):
        self.set_font(family, size = size)
        self.text(x, y, txt=txt)

    def dMultiText(self, x, y, w, h, txt, family, size:int=7):
        self.set_font(family, size = size)
        self.set_xy(x, y)
        self.multi_cell(w, h, txt=txt)

    def dLine(self, x0, y0, x1, y1, lwidth:float=0.1):
        self.set_line_width(lwidth)
        self.line(x0, y0, x1, y1)

    def dDashLine(self, x0, y0, x1, y1, lwidth:float=0.1):
        self.set_line_width(lwidth)
        self.dashed_line(x0, y0, x1, y1)

    def dRect(self, x, y, w, h, lwidth:float=0.1, style:str="D"):
        self.set_line_width(lwidth)
        self.rect(x, y, w, h, style=style)

    def dCircle(self, x, y, r, lwidth:float=0.1, style:str="D"):
        self.set_line_width(lwidth)
        self.ellipse(x, y, r, r, style=style)

    def dImage(self, x, y, imagePath, w=0, h=0):
        self.set_xy(x, y)
        self.image(imagePath, w=w, h=h)

class E001V1():
    def __init__(self) -> None:
        self.pageNo = 0             # 頁數
        self.pageWidth = 210        # 頁寬
        self.pageHeight = 297       # 頁高
        self.cellW = 2
        self.rowNo = 12
        self.rowWidth = 16 # (210-12)/12=16
        self.pageWidth_mx = 9       # 頁寬 margin left & right
        self.pageHeight_mt = 6      # 頁高 margin top & bottom


        # 檔案相關
        pypath = os.path.dirname(__file__)
        self.fontFamily = 'TaipeiSans'                              # 字型
        self.fontSungFamily = 'TW-Sung'
        self.fontPath = os.path.join(pypath,"doc","TaipeiSansTCBeta-Regular.ttf")  # 字型檔案位置
        self.fontSungPath = os.path.join(pypath,"doc","TW-Sung-98_1.ttf")  # 字型檔案位置
        self.logoPath = os.path.join(pypath,"doc","SW-Logo.png")                   # logo 檔案位置
        self.maxHRDecPath = os.path.join(pypath,"doc","hr_decrease.png")
        self.minHRPath = os.path.join(pypath,"doc","hr_min.png") 
        self.pvcPath = os.path.join(pypath,"doc","Poincare_PVC.png")
        self.persistAFPath = os.path.join(pypath,"doc","Poincare_Persist_AF.png")
        self.paroxysmalAFPath = os.path.join(pypath,"doc","Poincare_Paroxysmal_AF.png")
        self.flagPath = os.path.join(pypath,"doc","flag.png")

        # 色彩
        self.black = [0, 0, 0]
        self.white = [255, 255, 255]
        self.lightGrey = [230, 230, 230]
        self.grey = [190, 190, 190]
        self.darkGrey = [64, 64, 64]
        pass

    def genReport(self, json, file_name, pngFloder):
        piePath = os.path.join(pngFloder, 'sleepPie.png')
        sleepingQR = json['sleepingQualityReport']
        self.__drawPie([ 'Light','Deep', 'REM'], [sleepingQR['lightRatioIndex']['ratio'], sleepingQR['deepRatioIndex']['ratio'], sleepingQR['remRatioIndex']['ratio']], piePath)
        self.generateReport(json['header'], json['userInfo'], json['sleepingState'], sleepingQR, json['notes'], json['SleepingQualityExamEvaluation'], json['irregularHeartRateStatistics'], file_name, piePath)
        pass

    def generateReport(self, header, userInfo, sleepingState, qualityReport, notes, examEval, irregularHRStat, file_name, piePath) -> None:
        print('in generate Report')
        # A4 (w:210 mm and h:297 mm)
        filterwarnings("ignore")

        # 繪製PDF
        self.report = PDF_E001V1(format='A4')
        self.report.add_font(self.fontFamily, '', self.fontPath, uni=True)
        self.report.add_font(self.fontSungFamily, '', self.fontSungPath, uni=True)
        self.header = header
        self.userInfo = userInfo
        self.__addSleepReport(sleepingState, qualityReport)
        self.__addNote(notes)
        self.__addQualityEval(qualityReport, piePath)
        self.__addECGs(examEval, irregularHRStat)
        # self.__addIrregular(irregulars)
        
        # 匯出PDF
        pypath = os.path.join(os.path.dirname(__file__), '..', '..', 'user_pdf', 'E001V1')
        if not os.path.exists(pypath):
            os.makedirs(pypath)

        file = os.path.join(pypath, file_name)
        self.report.output(file, 'F')
        pass

    def __drawPie(self, labels, values, file_path):
        # set the colors ['Light','Deep', 'REM']
        pie_colors = ['rgb(220, 220, 220)', 'rgb(105, 105, 105)', 'rgb(169, 169, 169)' ]
        # pull is given as a fraction of the pie radius
        # let Deep be the pulled part and set sort as False to maintain the order.
        fig = go.Figure(data=[go.Pie(direction='clockwise', labels=labels, values=values, textinfo='label+percent', insidetextorientation='horizontal', marker_colors=pie_colors, sort=False, pull=[0, 0.2, 0, 0])])
        fig.write_image(file_path, engine="kaleido", format="png", width=600, height=600)
        # return fig.to_image(format="png", width=600, height=600)

    def __addPage(self) -> None:
        ## y軸
        self.y = 0 + self.pageHeight_mt
        self.report.add_page()
        self.report.alias_nb_pages()
        if (self.report.page_no()==1):
            self.__gen1PageHeader()
        else:
            self.__genHeader()
        self.__genFooter()
        pass

    def __gen1PageHeader(self) -> None:
        # 報告名稱、logo
        startHeight = self.pageHeight_mt
        cellHeightNo = 4
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*1.5), self.header['reportName'], self.fontFamily, 8)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*1.5), "測試期間", self.fontFamily, 8)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*3), self.header['testingPeriod'], self.fontFamily, 7)
        self.report.dImage(self.pageWidth_mx+(self.rowWidth*9), startHeight-self.cellW, self.logoPath, h=7.5)
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+(self.rowWidth*9)-(self.cellW*2), startHeight+(self.cellW*4))
        self.__addDriven(self.pageWidth_mx+(self.rowWidth*9), self.pageWidth_mx+(self.rowWidth*12), startHeight+(self.cellW*4))

        # 使用者和公司資訊
        startHeight = self.pageHeight_mt+(self.cellW*4)
        cellHeightNo = 16
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*3), '姓名:', self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*5), self.userInfo['name'], self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*9), '生日:', self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*11), self.userInfo['birthday'], self.fontFamily, 7)        
        self.report.dText(self.pageWidth_mx+(self.rowWidth*2), startHeight+(self.cellW*3), '年齡:', self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*2), startHeight+(self.cellW*5), str(self.userInfo['age']), self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*2), startHeight+(self.cellW*9), '性別:', self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*2), startHeight+(self.cellW*11), self.userInfo['gender'], self.fontFamily, 7)        
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4), startHeight+(self.cellW*3), '高度:', self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4), startHeight+(self.cellW*5), self.userInfo['height'], self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4), startHeight+(self.cellW*9), '重量:', self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4), startHeight+(self.cellW*11), self.userInfo['weight'], self.fontFamily, 7)        
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+(self.rowWidth*9)-(self.cellW*2), startHeight+(self.cellW*13))
        self.report.dText(self.pageWidth_mx+(self.rowWidth*9), startHeight+(self.cellW*3), '奇翼醫電股份有限公司', self.fontFamily, 8)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*9), startHeight+(self.cellW*5), 'Singular Wings Medical', self.fontFamily,8)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*9), startHeight+(self.cellW*9), 'service@singularwings.com', self.fontFamily, 8)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*9), startHeight+(self.cellW*11), 'www.singularwings.com', self.fontFamily, 8)        
        self.__addDriven(self.pageWidth_mx+(self.rowWidth*9), self.pageWidth_mx+(self.rowWidth*12), startHeight+(self.cellW*13))
        pass

    def __genHeader(self) -> None:
        startHeight = self.pageHeight_mt
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*2))
        self.report.set_font(self.fontFamily, size = 7)
        self.report.text(self.pageWidth_mx, startHeight+self.cellW, txt='睡眠品質評估報告')
        self.report.text(self.pageWidth_mx+(self.rowWidth*4), startHeight+self.cellW, txt='報告日期: '+self.header['reportDate'])
        self.report.text(self.pageWidth_mx+(self.rowWidth*8), startHeight+self.cellW, txt='測試期間: '+self.header['testingPeriod'])
        pass

    def __genFooter(self) -> None:
        startHeight = self.pageHeight_mt+(self.cellW*140)
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight)
        self.report.set_font(self.fontFamily, size = 7)
        self.report.text(self.pageWidth_mx, startHeight+self.cellW*2, txt='使用者: '+self.userInfo['name'])
        self.report.text(self.pageWidth_mx+(self.rowWidth*3), startHeight+self.cellW*2, txt='報告類別: E001V1')
        self.report.text(self.pageWidth_mx+(self.rowWidth*6), startHeight+self.cellW*2, txt='報告日期: '+self.header['reportDate'])
        self.report.text(self.pageWidth_mx+(self.rowWidth*10), startHeight+self.cellW*2, txt='頁數: '+str(self.report.page_no()))
        pass

    def __addSleepReport(self, sleepingState, qualityReport) -> None:
        self.__addPage()
        startHeight = self.pageHeight_mt+(self.cellW*20)
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+self.cellW, '睡眠品質評估', self.fontFamily, 12)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*6), startHeight+self.cellW, str(qualityReport['score'])+" / 100", self.fontFamily, 12)
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*4), 'SLEEPING ANALYSIS REPORT', self.fontFamily, 12)

        self.report.dText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*4), "|", self.fontFamily, 7)
        strWidth = self.report.get_string_width("不佳")
        self.report.dText(self.pageWidth_mx+(self.rowWidth*7)-(strWidth/2), startHeight+(self.cellW*4), "不佳", self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*8), startHeight+(self.cellW*4), "|", self.fontFamily, 7)
        strWidth = self.report.get_string_width("佳")
        self.report.dText(self.pageWidth_mx+(self.rowWidth*9)-(strWidth/2), startHeight+(self.cellW*4), "佳", self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*10), startHeight+(self.cellW*4), "|", self.fontFamily, 7)
        strWidth = self.report.get_string_width("優秀")
        self.report.dText(self.pageWidth_mx+(self.rowWidth*11)-(strWidth/2), startHeight+(self.cellW*4), "優秀", self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*12), startHeight+(self.cellW*4), "|", self.fontFamily, 7)

        self.report.sColors(drawColor=self.lightGrey, fillColor=self.lightGrey)
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*5.5), self.rowWidth*6+0.5, self.cellW*4, 0.2, 'F')
        # scoreWidth = (self.rowWidth*6+0.5)*(qualityReport['score']/100.0)
        scoreWidth = (self.rowWidth*6+0.5)*((qualityReport['score']-50)/50.0)
        self.report.sColors(drawColor=self.black, fillColor=self.black)
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*5.5), scoreWidth, self.cellW*4, 0.2, 'F')
        stlen = len(qualityReport['scoreText'])
        if stlen>0:
            self.report.sColors(txtColor=self.white)
            scoreTextWidth = self.report.get_string_width(qualityReport['scoreText'])
            self.report.dText(self.pageWidth_mx+(self.rowWidth*6)+scoreWidth-scoreTextWidth-4, startHeight+(self.cellW*8), qualityReport['scoreText'], self.fontFamily, 7)
            self.report.sColors()

        stage = sleepingState['Stage']
        levels = ['Awake', 'REM', 'Light Sleep', 'Deep Sleep']
        self.__addStage(startHeight+(self.cellW*12), 24, levels, sleepingState['date'], sleepingState['time'], stage)
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*36))
        posture = sleepingState['Posture']
        levels = ['Supine', 'Left', 'Prone', 'Right', 'Upright']
        self.__addPosture(startHeight+(self.cellW*36), 24, levels, sleepingState['date'], sleepingState['time'], posture)
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*63))
        hr = sleepingState['HeartRate']
        levels = ['100', '80', '60', '40']
        self.__addHR(startHeight+(self.cellW*63), 24, levels, sleepingState['date'], sleepingState['time'], hr)
        pass

    def __addStage(self, startHeight, cellNoHeight, levels, date, time, values):
        dt = datetime.strptime(date+' '+time, "%Y/%m/%d %H:%M:%S")
        tt = dt.timestamp()

        # 8H values
        vNo = len(values)
        eHUnitNo = len(levels)
        uspace = 0.366
        fyNo = 480
        uWidth = uspace*480 # 8H = 8*60m
        xUnitNo = 16
        title = '總睡眠時間 (8H SLEEP)'
        if (vNo > 480):
            if (vNo > 600):
                uspace = 0.244
                fyNo = 720
                uWidth = uspace*720
                xUnitNo = 24
                title = '總睡眠時間 (12H SLEEP)'
            uspace = 0.293
            fyNo = 600
            uWidth = uspace*600
            xUnitNo = 20
            title = '總睡眠時間 (10H SLEEP)'
        eHUnit = self.cellW*3.5
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*3.5), title, self.fontFamily, 10)

        for i in range(0, eHUnitNo):
            self.report.sColors()
            self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*7)+(i*eHUnit), levels[i], self.fontFamily, 5)
            self.report.sColors(drawColor=self.lightGrey)
            self.report.dLine(self.pageWidth_mx+self.rowWidth, startHeight+(self.cellW*7)+(i*eHUnit), self.pageWidth_mx+self.rowWidth+uWidth, startHeight+(self.cellW*7)+(i*eHUnit), 0.15)
        for i in range(0, xUnitNo+1):
            self.report.sColors(drawColor=self.lightGrey)
            self.report.dLine(self.pageWidth_mx+self.rowWidth+(i*30*uspace), startHeight+(self.cellW*7), self.pageWidth_mx+self.rowWidth+(i*30*uspace), startHeight+(self.cellW*7)+((eHUnitNo-1)*eHUnit), 0.15)
        self.report.set_font(self.fontFamily, size = 5)
        for i in range(0, xUnitNo+1):
            self.report.rotate(45, self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(i*uspace*30), startHeight+(self.cellW*11)+((eHUnitNo-1)*eHUnit))
            tstr = datetime.fromtimestamp(tt+(i*1800)).strftime('%H:%M')
            self.report.dText(self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(i*uspace*30), startHeight+(self.cellW*11)+((eHUnitNo-1)*eHUnit), tstr, self.fontFamily, 5)
            self.report.rotate(0, self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(i*uspace*30), startHeight+(self.cellW*11)+((eHUnitNo-1)*eHUnit))

        if (vNo>fyNo):
            vNo = fyNo
        preV = -1
        for i in range(0, vNo):
            if (values[i]>-1 and preV>-1):
                pv = preV
                cv = values[i]
                # if (pv==3):
                #     pv = 0
                # elif (pv==0):
                #     pv = 3
                # if (cv==3):
                #     cv = 0
                # elif (cv==0):
                #     cv = 3
                # prey = startHeight+(self.cellW*7)+(3-pv)*eHUnit
                # cury = startHeight+(self.cellW*7)+(3-cv)*eHUnit
                prey = startHeight+(self.cellW*7)+(pv)*eHUnit
                cury = startHeight+(self.cellW*7)+(cv)*eHUnit
                self.report.sColors()
                self.report.dLine(self.pageWidth_mx+self.rowWidth+((i-1)*uspace), prey, self.pageWidth_mx+self.rowWidth+((i)*uspace), cury, 0.3)
            preV = values[i]

    def __addPosture(self, startHeight, cellNoHeight, levels, date, time, values):
        dt = datetime.strptime(date+' '+time, "%Y/%m/%d %H:%M:%S")
        tt = dt.timestamp()

        # 8H values
        vNo = len(values)
        eHUnitNo = len(levels)
        uspace = 0.366
        fyNo = 480
        uWidth = uspace*480 # 8H = 8*60m
        xUnitNo = 16
        title = '睡姿分析圖 (8H POSITION)'
        if (vNo > 480):
            if (vNo > 600):
                uspace = 0.244
                fyNo = 720
                uWidth = uspace*720
                xUnitNo = 24
                title = '睡姿分析圖 (12H POSITION)'
            uspace = 0.293
            fyNo = 600
            uWidth = uspace*600
            xUnitNo = 20
            title = '睡姿分析圖 (10H POSITION)'
        eHUnit = self.cellW*3
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*3.5), title, self.fontFamily, 10)

        for i in range(0, eHUnitNo):
            self.report.sColors()
            self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*7)+(i*eHUnit), levels[i], self.fontFamily, 5)
            self.report.sColors(drawColor=self.lightGrey)
            self.report.dLine(self.pageWidth_mx+self.rowWidth, startHeight+(self.cellW*7)+(i*eHUnit), self.pageWidth_mx+self.rowWidth+uWidth, startHeight+(self.cellW*7)+(i*eHUnit), 0.15)
        for i in range(0, xUnitNo+1):
            self.report.sColors(drawColor=self.lightGrey)
            self.report.dLine(self.pageWidth_mx+self.rowWidth+(i*30*uspace), startHeight+(self.cellW*7), self.pageWidth_mx+self.rowWidth+(i*30*uspace), startHeight+(self.cellW*7)+((eHUnitNo-1)*eHUnit), 0.15)
        self.report.set_font(self.fontFamily, size = 5)
        for i in range(0, xUnitNo+1):
            self.report.rotate(45, self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(i*uspace*30), startHeight+(self.cellW*11)+((eHUnitNo-1)*eHUnit))
            tstr = datetime.fromtimestamp(tt+(i*1800)).strftime('%H:%M')
            self.report.dText(self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(i*uspace*30), startHeight+(self.cellW*11)+((eHUnitNo-1)*eHUnit), tstr, self.fontFamily, 5)
            self.report.rotate(0, self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(i*uspace*30), startHeight+(self.cellW*11)+((eHUnitNo-1)*eHUnit))

        if (vNo>fyNo):
            vNo = fyNo
        preV = -1
        for i in range(0, vNo):
            if (values[i]>-1 and preV>-1):
                prey = startHeight+(self.cellW*7)+(5-preV)*eHUnit
                cury = startHeight+(self.cellW*7)+(5-values[i])*eHUnit
                self.report.sColors()
                self.report.dLine(self.pageWidth_mx+self.rowWidth+((i-1)*uspace), prey, self.pageWidth_mx+self.rowWidth+((i)*uspace), cury, 0.3)
            preV = values[i]

    def __addHR(self, startHeight, cellNoHeight, levels, date, time, values):
        dt = datetime.strptime(date+' '+time, "%Y/%m/%d %H:%M:%S")
        tt = dt.timestamp()

        # 8H values
        vNo = len(values)
        eHUnitNo = len(levels)
        uspace = 0.366
        fyNo = 480
        uWidth = uspace*480 # 8H = 8*60m
        xUnitNo = 16
        title = '心率變化圖 (8H SLEEP)'
        if (vNo > 480):
            if (vNo > 600):
                uspace = 0.244
                fyNo = 720
                uWidth = uspace*720
                xUnitNo = 24
                title = '心率變化圖 (12H SLEEP)'
            uspace = 0.293
            fyNo = 600
            uWidth = uspace*600
            xUnitNo = 20
            title = '心率變化圖 (10H SLEEP)'
        eHUnit = self.cellW*3.5
        hspace = eHUnit*(eHUnitNo-1)/60
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*3.5), title, self.fontFamily, 10)

        for i in range(0, eHUnitNo):
            self.report.sColors()
            self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*7)+(i*eHUnit), levels[i], self.fontFamily, 5)
            self.report.sColors(drawColor=self.lightGrey)
            self.report.dLine(self.pageWidth_mx+self.rowWidth, startHeight+(self.cellW*7)+(i*eHUnit), self.pageWidth_mx+self.rowWidth+uWidth, startHeight+(self.cellW*7)+(i*eHUnit), 0.15)
        for i in range(0, xUnitNo+1):
            self.report.sColors(drawColor=self.lightGrey)
            self.report.dLine(self.pageWidth_mx+self.rowWidth+(i*30*uspace), startHeight+(self.cellW*7), self.pageWidth_mx+self.rowWidth+(i*30*uspace), startHeight+(self.cellW*7)+((eHUnitNo-1)*eHUnit), 0.15)
        self.report.set_font(self.fontFamily, size = 5)
        for i in range(0, xUnitNo+1):
            self.report.rotate(45, self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(i*uspace*30), startHeight+(self.cellW*11)+((eHUnitNo-1)*eHUnit))
            tstr = datetime.fromtimestamp(tt+(i*1800)).strftime('%H:%M')
            self.report.dText(self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(i*uspace*30), startHeight+(self.cellW*11)+((eHUnitNo-1)*eHUnit), tstr, self.fontFamily, 5)
            self.report.rotate(0, self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(i*uspace*30), startHeight+(self.cellW*11)+((eHUnitNo-1)*eHUnit))

        if (vNo>fyNo):
            vNo = fyNo
        preV = -1
        for i in range(0, vNo):
            if (values[i]>-1 and preV>-1):
                prey = startHeight+(self.cellW*7)+(100-preV)*hspace
                cury = startHeight+(self.cellW*7)+(100-values[i])*hspace
                self.report.sColors()
                self.report.dLine(self.pageWidth_mx+self.rowWidth+((i-1)*uspace), prey, self.pageWidth_mx+self.rowWidth+((i)*uspace), cury, 0.3)
            preV = values[i]

    def __addNote(self, note) -> None:
        startHeight = self.pageHeight_mt+(self.cellW*114)
        cellHeightNo = 24
        self.report.set_draw_color(0, 0, 0)
        self.report.set_fill_color(255, 255, 255)
        self.report.set_text_color(0, 0, 0)
        self.report.rect(self.pageWidth_mx, startHeight, self.rowWidth*self.rowNo, self.cellW*(cellHeightNo-2), '')
        self.report.text(self.pageWidth_mx+self.cellW, startHeight+(self.cellW*1.5), "NOTES")
        if len(note)>0:
            self.report.set_xy(self.pageWidth_mx+self.cellW, startHeight+(self.cellW*2))
            self.report.multi_cell(w=(self.rowWidth*12)-(4*self.cellW), h=self.cellW*2, txt=note, align='L')
        pass

    def __addQualityEval(self, qualityEval, piePath) -> None:
        self.__addPage()
        startHeight = self.pageHeight_mt+(self.cellW*2)
        cellHeightNo = 6
        self.report.set_draw_color(0, 0, 0)
        self.report.set_fill_color(255, 255, 255)
        self.report.set_text_color(0, 0, 0)
        self.report.set_font(self.fontFamily, size = 12)
        self.report.text(self.pageWidth_mx, startHeight+(self.cellW*4), "睡眠品質評估指標")
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*cellHeightNo))
        self.report.dImage(self.pageWidth_mx+(self.rowWidth*3), startHeight+(self.cellW*7), piePath, h=self.rowWidth*6)
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*8)+(self.rowWidth*6))
        self.__addSleepTimeIndex(startHeight+(self.cellW*10)+(self.rowWidth*6), 18, qualityEval['sleepingTimeIndex'])
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*28)+(self.rowWidth*6))
        self.__addSleepCostIndex(startHeight+(self.cellW*30)+(self.rowWidth*6), 18 , qualityEval['timeCostIndex'])
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*48)+(self.rowWidth*6))
        self.__addSleepDeepIndex(startHeight+(self.cellW*50)+(self.rowWidth*6), 18 , qualityEval['deepRatioIndex'])
        self.__addPage()
        self.__addSleepLightIndex(self.pageHeight_mt+(self.cellW*4), 18, qualityEval['lightRatioIndex'])
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*20))
        self.__addSleepRemIndex(self.pageHeight_mt+(self.cellW*24), 18, qualityEval['remRatioIndex'])
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*40))
        self.__addSleepWakeIndex(self.pageHeight_mt+(self.cellW*44), 18, qualityEval['wakeIndex'])
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*60))
        self.__addSleepTurnIndex(self.pageHeight_mt+(self.cellW*64), 18, qualityEval['turnoverIndex'])
        pass

    def __addSleepTimeIndex(self, startHeight, cellNoHeight, timeIndex):
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*1), "睡眠時間指標", self.fontFamily, 10)
        self.report.dMultiText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW), self.rowWidth*5.8, self.cellW*2, timeIndex['description'], self.fontSungFamily, 7)
        tWidth = self.rowWidth*5.8
        self.report.sColors(drawColor=self.lightGrey)
        self.report.dLine(self.pageWidth_mx, startHeight+(self.cellW*3), self.pageWidth_mx+tWidth, startHeight+(self.cellW*3), 0.15)
        tindexStr = str(timeIndex['score'])+" 小時"
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*6), tindexStr, self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*3), startHeight+(self.cellW*6), timeIndex['scoreText'], self.fontFamily, 10)
        self.report.sColors(fillColor=self.lightGrey)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth, self.cellW*4, 0.1, 'F')
        self.report.sColors(fillColor=self.black)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth*timeIndex['score']/12, self.cellW*4, 0.1, 'F')
        self.report.sColors(drawColor=self.grey)
        self.report.dLine(self.pageWidth_mx+(tWidth*7/12), startHeight+(self.cellW*10), self.pageWidth_mx+(tWidth*7/12), startHeight+(self.cellW*14), 0.3)
        self.report.dLine(self.pageWidth_mx+(tWidth*9/12), startHeight+(self.cellW*10), self.pageWidth_mx+(tWidth*9/12), startHeight+(self.cellW*14), 0.3)
        self.report.set_font(self.fontFamily, size=8)
        tisLen = self.report.get_string_width(tindexStr)
        self.report.dText(self.pageWidth_mx+(tWidth*timeIndex['score']/12)-tisLen, startHeight+(self.cellW*9.5), tindexStr, self.fontFamily, 8)
        self.report.sColors(txtColor=self.darkGrey)
        self.report.set_font(self.fontFamily, size=5)
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*15.3), '睡眠開始', self.fontFamily, 5)
        slen = self.report.get_string_width('7小時')
        self.report.dText(self.pageWidth_mx+(tWidth*7/12)-slen, startHeight+(self.cellW*15.3), '7小時', self.fontFamily, 5)
        slen = self.report.get_string_width('9小時')
        self.report.dText(self.pageWidth_mx+(tWidth*9/12)-slen, startHeight+(self.cellW*15.3), '9小時', self.fontFamily, 5)
        pass
    
    def __addSleepCostIndex(self, startHeight, cellNoHeight, costIndex):
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*1), "入睡品質指標", self.fontFamily, 10)
        self.report.dMultiText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW), self.rowWidth*5.8, self.cellW*2, costIndex['description'], self.fontSungFamily, 7)
        tWidth = self.rowWidth*5.8
        self.report.sColors(drawColor=self.lightGrey)
        self.report.dLine(self.pageWidth_mx, startHeight+(self.cellW*3), self.pageWidth_mx+tWidth, startHeight+(self.cellW*3), 0.15)
        tindexStr = str(costIndex['cost'])+" 分鐘"
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*6), tindexStr, self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*3), startHeight+(self.cellW*6), costIndex['scoreText'], self.fontFamily, 10)
        self.report.sColors(fillColor=self.lightGrey)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth, self.cellW*4, 0.1, 'F')
        self.report.sColors(fillColor=self.black)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth*costIndex['cost']/60, self.cellW*4, 0.1, 'F')
        self.report.sColors(drawColor=self.grey)
        self.report.dLine(self.pageWidth_mx+(tWidth*20/60), startHeight+(self.cellW*10), self.pageWidth_mx+(tWidth*20/60), startHeight+(self.cellW*14), 0.3)
        self.report.dLine(self.pageWidth_mx+(tWidth*30/60), startHeight+(self.cellW*10), self.pageWidth_mx+(tWidth*30/60), startHeight+(self.cellW*14), 0.3)
        self.report.set_font(self.fontFamily, size=8)
        tisLen = self.report.get_string_width(tindexStr)
        self.report.dText(self.pageWidth_mx+(tWidth*costIndex['cost']/60)-tisLen, startHeight+(self.cellW*9.5), tindexStr, self.fontFamily, 8)
        self.report.sColors(txtColor=self.darkGrey)
        self.report.set_font(self.fontFamily, size=5)
        slen = self.report.get_string_width('60分鐘')
        self.report.dText(self.pageWidth_mx+tWidth-slen, startHeight+(self.cellW*15.3), '60分鐘', self.fontFamily, 5)
        slen = self.report.get_string_width('20分鐘')
        self.report.dText(self.pageWidth_mx+(tWidth*20/60)-slen, startHeight+(self.cellW*15.3), '20分鐘', self.fontFamily, 5)
        slen = self.report.get_string_width('30分鐘')
        self.report.dText(self.pageWidth_mx+(tWidth*30/60)-slen, startHeight+(self.cellW*15.3), '30分鐘', self.fontFamily, 5)
        pass

    def __addSleepDeepIndex(self, startHeight, cellNoHeight, deepIndex):
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*1), "深眠比例指標", self.fontFamily, 10)
        self.report.dMultiText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW), self.rowWidth*5.8, self.cellW*2, deepIndex['description'], self.fontSungFamily, 7)
        tWidth = self.rowWidth*5.8
        self.report.sColors(drawColor=self.lightGrey)
        self.report.dLine(self.pageWidth_mx, startHeight+(self.cellW*3), self.pageWidth_mx+tWidth, startHeight+(self.cellW*3), 0.15)
        tindexStr = str(deepIndex['ratio'])+"%"
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*6), tindexStr, self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*3), startHeight+(self.cellW*6), deepIndex['scoreText'], self.fontFamily, 10)
        self.report.sColors(fillColor=self.lightGrey)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth, self.cellW*4, 0.1, 'F')
        self.report.sColors(fillColor=self.black)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth*deepIndex['ratio']/100, self.cellW*4, 0.1, 'F')
        self.report.sColors(drawColor=self.grey)
        self.report.dLine(self.pageWidth_mx+(tWidth*15/100), startHeight+(self.cellW*10), self.pageWidth_mx+(tWidth*15/100), startHeight+(self.cellW*14), 0.3)
        self.report.dLine(self.pageWidth_mx+(tWidth*25/100), startHeight+(self.cellW*10), self.pageWidth_mx+(tWidth*25/100), startHeight+(self.cellW*14), 0.3)
        self.report.set_font(self.fontFamily, size=8)
        tisLen = self.report.get_string_width(tindexStr)
        self.report.dText(self.pageWidth_mx+(tWidth*deepIndex['ratio']/100)-tisLen, startHeight+(self.cellW*9.5), tindexStr, self.fontFamily, 8)
        self.report.sColors(txtColor=self.darkGrey)
        self.report.set_font(self.fontFamily, size=5)
        slen = self.report.get_string_width('全部睡眠時間')
        self.report.dText(self.pageWidth_mx+tWidth-slen, startHeight+(self.cellW*15.3), '全部睡眠時間', self.fontFamily, 5)
        slen = self.report.get_string_width('15%')
        self.report.dText(self.pageWidth_mx+(tWidth*15/100)-slen, startHeight+(self.cellW*15.3), '15%', self.fontFamily, 5)
        slen = self.report.get_string_width('25%')
        self.report.dText(self.pageWidth_mx+(tWidth*25/100)-slen, startHeight+(self.cellW*15.3), '25%', self.fontFamily, 5)
        pass

    def __addSleepLightIndex(self, startHeight, cellNoHeight, lightIndex):
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*1), "淺眠比例指標", self.fontFamily, 10)
        self.report.dMultiText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW), self.rowWidth*5.8, self.cellW*2, lightIndex['description'], self.fontSungFamily, 7)
        tWidth = self.rowWidth*5.8
        self.report.sColors(drawColor=self.lightGrey)
        self.report.dLine(self.pageWidth_mx, startHeight+(self.cellW*3), self.pageWidth_mx+tWidth, startHeight+(self.cellW*3), 0.15)
        tindexStr = str(lightIndex['ratio'])+"%"
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*6), tindexStr, self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*3), startHeight+(self.cellW*6), lightIndex['scoreText'], self.fontFamily, 10)
        self.report.sColors(fillColor=self.lightGrey)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth, self.cellW*4, 0.1, 'F')
        self.report.sColors(fillColor=self.black)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth*lightIndex['ratio']/100, self.cellW*4, 0.1, 'F')
        self.report.sColors(drawColor=self.grey)
        self.report.dLine(self.pageWidth_mx+(tWidth*55/100), startHeight+(self.cellW*10), self.pageWidth_mx+(tWidth*55/100), startHeight+(self.cellW*14), 0.3)
        self.report.set_font(self.fontFamily, size=8)
        tisLen = self.report.get_string_width(tindexStr)
        self.report.dText(self.pageWidth_mx+(tWidth*lightIndex['ratio']/100)-tisLen, startHeight+(self.cellW*9.5), tindexStr, self.fontFamily, 8)
        self.report.sColors(txtColor=self.darkGrey)
        self.report.set_font(self.fontFamily, size=5)
        slen = self.report.get_string_width('全部睡眠時間')
        self.report.dText(self.pageWidth_mx+tWidth-slen, startHeight+(self.cellW*15.3), '全部睡眠時間', self.fontFamily, 5)
        slen = self.report.get_string_width('55%')
        self.report.dText(self.pageWidth_mx+(tWidth*55/100)-slen, startHeight+(self.cellW*15.3), '55%', self.fontFamily, 5)
        pass

    def __addSleepRemIndex(self, startHeight, cellNoHeight, remIndex):
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*1), "REM比例指標", self.fontFamily, 10)
        self.report.dMultiText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW), self.rowWidth*5.8, self.cellW*2, remIndex['description'], self.fontSungFamily, 7)
        tWidth = self.rowWidth*5.8
        self.report.sColors(drawColor=self.lightGrey)
        self.report.dLine(self.pageWidth_mx, startHeight+(self.cellW*3), self.pageWidth_mx+tWidth, startHeight+(self.cellW*3), 0.15)
        tindexStr = str(remIndex['ratio'])+"%"
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*6), tindexStr, self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*3), startHeight+(self.cellW*6), remIndex['scoreText'], self.fontFamily, 10)
        self.report.sColors(fillColor=self.lightGrey)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth, self.cellW*4, 0.1, 'F')
        self.report.sColors(fillColor=self.black)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth*remIndex['ratio']/100, self.cellW*4, 0.1, 'F')
        self.report.sColors(drawColor=self.grey)
        self.report.dLine(self.pageWidth_mx+(tWidth*20/100), startHeight+(self.cellW*10), self.pageWidth_mx+(tWidth*20/100), startHeight+(self.cellW*14), 0.3)
        self.report.set_font(self.fontFamily, size=8)
        tisLen = self.report.get_string_width(tindexStr)
        self.report.dText(self.pageWidth_mx+(tWidth*remIndex['ratio']/100)-tisLen, startHeight+(self.cellW*9.5), tindexStr, self.fontFamily, 8)
        self.report.sColors(txtColor=self.darkGrey)
        self.report.set_font(self.fontFamily, size=5)
        slen = self.report.get_string_width('全部睡眠時間')
        self.report.dText(self.pageWidth_mx+tWidth-slen, startHeight+(self.cellW*15.3), '全部睡眠時間', self.fontFamily, 5)
        slen = self.report.get_string_width('20%')
        self.report.dText(self.pageWidth_mx+(tWidth*20/100)-slen, startHeight+(self.cellW*15.3), '20%', self.fontFamily, 5)
        pass

    def __addSleepWakeIndex(self, startHeight, cellNoHeight, wakeIndex):
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*1), "睡眠甦醒指標", self.fontFamily, 10)
        self.report.dMultiText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW), self.rowWidth*5.8, self.cellW*2, wakeIndex['description'], self.fontSungFamily, 7)
        tWidth = self.rowWidth*5.8
        self.report.sColors(drawColor=self.lightGrey)
        self.report.dLine(self.pageWidth_mx, startHeight+(self.cellW*3), self.pageWidth_mx+tWidth, startHeight+(self.cellW*3), 0.15)
        wTimes = wakeIndex['time']
        if wTimes > 10:
            wTimes = 10
        tindexStr = str(wTimes)+"次"
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*6), tindexStr, self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*3), startHeight+(self.cellW*6), wakeIndex['scoreText'], self.fontFamily, 10)
        self.report.sColors(fillColor=self.lightGrey)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth, self.cellW*4, 0.1, 'F')
        self.report.sColors(fillColor=self.black)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth*wTimes/10, self.cellW*4, 0.1, 'F')
        self.report.sColors(drawColor=self.grey)
        self.report.dLine(self.pageWidth_mx+(tWidth*2/10), startHeight+(self.cellW*10), self.pageWidth_mx+(tWidth*2/10), startHeight+(self.cellW*14), 0.3)
        self.report.set_font(self.fontFamily, size=8)
        tisLen = self.report.get_string_width(tindexStr)
        if (wTimes<1):
            tisLen = 0
        self.report.dText(self.pageWidth_mx+(tWidth*wTimes/10)-tisLen, startHeight+(self.cellW*9.5), tindexStr, self.fontFamily, 8)
        self.report.sColors(txtColor=self.darkGrey)
        self.report.set_font(self.fontFamily, size=5)
        slen = self.report.get_string_width('10次+')
        self.report.dText(self.pageWidth_mx+tWidth-slen, startHeight+(self.cellW*15.3), '10次+', self.fontFamily, 5)
        slen = self.report.get_string_width('2次')
        self.report.dText(self.pageWidth_mx+(tWidth*2/10)-slen, startHeight+(self.cellW*15.3), '2次', self.fontFamily, 5)
        pass

    def __addSleepTurnIndex(self, startHeight, cellNoHeight, turnIndex):
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*1), "睡眠翻身指標", self.fontFamily, 10)
        self.report.dMultiText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW), self.rowWidth*5.8, self.cellW*2, turnIndex['description'], self.fontSungFamily, 7)
        tWidth = self.rowWidth*5.8
        self.report.sColors(drawColor=self.lightGrey)
        self.report.dLine(self.pageWidth_mx, startHeight+(self.cellW*3), self.pageWidth_mx+tWidth, startHeight+(self.cellW*3), 0.15)
        wTimes = turnIndex['times']
        if wTimes > 50:
            wTimes = 50
        tindexStr = str(wTimes)+"次"
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*6), tindexStr, self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*3), startHeight+(self.cellW*6), turnIndex['scoreText'], self.fontFamily, 10)
        self.report.sColors(fillColor=self.lightGrey)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth, self.cellW*4, 0.1, 'F')
        self.report.sColors(fillColor=self.black)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*10), tWidth*wTimes/50, self.cellW*4, 0.1, 'F')
        self.report.sColors(drawColor=self.grey)
        self.report.dLine(self.pageWidth_mx+(tWidth*20/50), startHeight+(self.cellW*10), self.pageWidth_mx+(tWidth*20/50), startHeight+(self.cellW*14), 0.3)
        self.report.dLine(self.pageWidth_mx+(tWidth*40/50), startHeight+(self.cellW*10), self.pageWidth_mx+(tWidth*40/50), startHeight+(self.cellW*14), 0.3)
        self.report.set_font(self.fontFamily, size=8)
        tisLen = self.report.get_string_width(tindexStr)
        if (wTimes<8):
            tisLen = 0
        self.report.dText(self.pageWidth_mx+(tWidth*wTimes/50)-tisLen, startHeight+(self.cellW*9.5), tindexStr, self.fontFamily, 8)
        self.report.sColors(txtColor=self.darkGrey)
        self.report.set_font(self.fontFamily, size=5)
        slen = self.report.get_string_width('50次+')
        self.report.dText(self.pageWidth_mx+tWidth-slen, startHeight+(self.cellW*15.3), '50次+', self.fontFamily, 5)
        slen = self.report.get_string_width('20次')
        self.report.dText(self.pageWidth_mx+(tWidth*20/50)-slen, startHeight+(self.cellW*15.3), '20次', self.fontFamily, 5)
        slen = self.report.get_string_width('40次')
        self.report.dText(self.pageWidth_mx+(tWidth*40/50)-slen, startHeight+(self.cellW*15.3), '40次', self.fontFamily, 5)
        pass

    def __addECGs(self, examEval, irregulars) -> None:
        self.__addPage()
        startHeight = self.pageHeight_mt+(self.cellW*2)
        cellHeightNo = 6
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*4), "心電圖", self.fontFamily, 12)
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*6))
        self.__addEcg(self.pageWidth_mx+(self.cellW*10), 35, examEval['maxHRStatistics'], '最大心率心電圖')
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*41))
        self.__addEcg(self.pageWidth_mx+(self.cellW*45), 35, examEval['minHRStatistics'], '最小心率電圖')

        ecgs = []
        for i in range(0, len(irregulars)):
            if (len(irregulars[i]['ecgs'])>0):
                for j in range(0, len(irregulars[i]['ecgs'])):
                    ecgs.append(irregulars[i]['ecgs'][j])
        ecgsNo = len(ecgs)
        if (ecgsNo>0):
            self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*76))
            self.__addEcg(self.pageWidth_mx+(self.cellW*80), 35, ecgs[0], '異常心電圖')
        ecgHeight = 32
        if (ecgsNo>1):
            extraPgNo = int((ecgsNo-1)/4)
            if ((ecgsNo-1)%4>0):
                extraPgNo = extraPgNo+1
            for p in range(0, extraPgNo):
                self.__addPage()
                startHeight = self.pageHeight_mt+(self.cellW*2)
                self.report.sColors()
                self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*4), "異常心電圖", self.fontFamily, 12)
                self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*6))
                startHeight = self.pageHeight_mt+(self.cellW*8)
                ecgIdx = 1 + (p*4)
                for ei in range(0, 4):
                    ceIdx = ecgIdx+ei
                    if (ceIdx<ecgsNo):
                        if (ei>0):
                            self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(ei*self.cellW*ecgHeight))
                        self.__addEcg(startHeight+(self.cellW*ecgHeight*ei), ecgHeight, ecgs[ceIdx])
        pass

    def __addEcg(self, startHeight, cellNoHeight, ecg, title=''):
        dt = datetime.strptime(ecg['date']+' '+ecg['time'], "%Y/%m/%d %H:%M:%S")
        tt = dt.timestamp()

        self.report.sColors()
        titleHeight = self.cellW
        if (len(title)==0):
            titleHeight = 0
        else:
            self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*0.5), title, self.fontFamily, 10)
            startHeight = startHeight + titleHeight

        # ECG資料
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*3.5), ecg['date'], self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*5.5), ecg['time'], self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*2), startHeight+(self.cellW*3.5), ecg['unit'], self.fontFamily, 7) 
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4), startHeight+(self.cellW*3.5), "心率: "+str(ecg['HR'])+' bpm', self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*3.5), "PR: "+str(ecg['PR'])+' ms', self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*5.5), "QRS: "+str(ecg['QRS'])+' ms', self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*8), startHeight+(self.cellW*3.5), "QT: "+str(ecg['QT'])+' ms', self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*8), startHeight+(self.cellW*5.5), "QTc: "+str(ecg['QTc'])+' ms', self.fontFamily, 7)

        self.report.sColors(fillColor=self.black)
        self.report.dCircle(self.pageWidth_mx+(self.rowWidth*10)+1, startHeight+(self.cellW*2)+1, 2, 0.1, 'F')
        self.report.dText(self.pageWidth_mx+(self.rowWidth*10.3), startHeight+(self.cellW*3.5), "Irreqular", self.fontFamily, 7)
        self.report.dImage(self.pageWidth_mx+(self.rowWidth*10), startHeight+(self.cellW*4.0), self.flagPath, w=4, h=4)
        self.report.sColors()
        self.report.dText(self.pageWidth_mx+(self.rowWidth*10.3), startHeight+(self.cellW*5.5), "PVC", self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*11), "ECG", self.fontFamily, 7) 
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*13), "10 SEC", self.fontFamily, 7)
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*26), "ECG", self.fontFamily, 7) 
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*28), "30 SEC", self.fontFamily, 7)

        # 10秒 ECG
        espace = 0.07
        eWidth = 0.07*2499
        eHeight= eWidth/50*6
        eUnit = eHeight/6
        self.report.sColors()
        self.report.dRect(self.pageWidth_mx+(self.rowWidth)-(self.cellW), startHeight+(self.cellW*10), eWidth, eHeight, 0.15, 'D')
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*17), eUnit, eUnit, 0.15, 'D')
        self.report.dText(self.pageWidth_mx+eUnit+1, startHeight+(self.cellW*17)+(eUnit/2)+1, "0.5mV", self.fontFamily, 5)
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*17)+eUnit+3, "200ms", self.fontFamily, 5)
        self.report.sColors(drawColor=self.lightGrey)
        for i in range(1, 6):
            self.report.dLine(self.pageWidth_mx+(self.rowWidth)-(self.cellW), startHeight+(self.cellW*10)+(i*eUnit), self.pageWidth_mx+(self.rowWidth)-(self.cellW)+eWidth, startHeight+(self.cellW*10)+(i*eUnit), 0.09)
        for i in range(1, 50):
            self.report.dLine(self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(i*eUnit), startHeight+(self.cellW*10), self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(i*eUnit), startHeight+(self.cellW*10)+eHeight, 0.09)
        self.report.set_font(self.fontFamily, size = 5)
        for i in range(0, 11):
            tstr = datetime.fromtimestamp(tt+i).strftime('%H:%M:%S')
            tstrLen = self.report.get_string_width(tstr)
            self.report.dText(self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(i*eUnit*5)-(tstrLen/2), startHeight+(self.cellW*22), tstr, self.fontFamily, 5)
        # Irrequlars
        irrs = ecg['Irrequlars']
        irrLen = len(irrs)
        self.report.sColors(fillColor=self.black)
        for i in range(0, irrLen):
            irrPos = irrs[i]
            self.report.dCircle(self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(irrPos*espace)-1, startHeight+(self.cellW*9)-1, 2, style='F')
        # PVCs
        pvcs = ecg['PVCs']
        pvcLen = len(pvcs)
        self.report.sColors()
        for i in range(0, pvcLen):
            pos = pvcs[i]
            self.report.dImage(self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(pos*espace)-1.5, startHeight+(self.cellW*7), self.flagPath, 3, 3)
            self.report.dLine(self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(pos*espace), startHeight+(self.cellW*8), self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(pos*espace), startHeight+(self.cellW*10), 0.15)
        # ECGs
        yspace = eHeight/25
        sec10 = ecg['sec10']
        sec10Len = len(sec10)
        ecgY0 = startHeight+(self.cellW*10)+(yspace*15)
        ecgYStep = (yspace*10)/650
        self.report.sColors()
        preX = 0
        preY = 0
        for i in range(0,2500):
            if (i<sec10Len):
                curX = self.pageWidth_mx+(self.rowWidth)-(self.cellW)+(espace*i)
                curY = ecgY0 - (sec10[i]*ecgYStep)
                if (i>0):
                    self.report.dLine(preX, preY, curX, curY, 0.15)
                preX = curX
                preY = curY

        # 30秒 ECG圖形
        lastEWidth = eWidth
        espace = 0.0229
        eWidth = espace*7499
        eHeight= eWidth/150*6
        eUnit = eHeight/6
        # 外框
        self.report.sColors()
        self.report.dRect(self.pageWidth_mx+(self.rowWidth)-(self.cellW), startHeight+(self.cellW*25), lastEWidth, eHeight, 0.15)
        # 陰影
        dummySpace = (lastEWidth-eWidth)/2
        self.report.sColors(fillColor=self.lightGrey)
        self.report.dRect(self.pageWidth_mx+(self.rowWidth)-(self.cellW), startHeight+(self.cellW*25), dummySpace, eHeight, style='F')
        self.report.dRect(self.pageWidth_mx+(self.rowWidth)-(self.cellW)+lastEWidth-dummySpace, startHeight+(self.cellW*25), dummySpace, eHeight, style='F')
        self.report.dRect(self.pageWidth_mx+(self.rowWidth)-(self.cellW)+dummySpace+(espace*2500), startHeight+(self.cellW*25), espace*2500, eHeight, style='F')
        # ECGs
        yspace = eHeight/25
        sec30 = ecg['sec30']
        sec30Len = len(sec30)
        ecgY0 = startHeight+(self.cellW*25)+(yspace*15)
        ecgYStep = (yspace*10)/650
        preX = 0
        preY = 0
        self.report.sColors()
        for i in range(0,7500):
            if (i<sec30Len):
                curX = self.pageWidth_mx+(self.rowWidth)-(self.cellW)+dummySpace+(espace*i)
                curY = ecgY0 - (sec30[i]*ecgYStep)
                if (i>0):
                    self.report.dLine(preX, preY, curX, curY, 0.15)
                preX = curX
                preY = curY
        pass

    def __addDriven(self, startGridX, endGridX, y='') -> None:
        # 分割線
        if(y==''):
            y = self.y
        self.report.sColors()
        self.report.dLine(startGridX, y, endGridX, y, 0.3)
        pass    
from pydoc import TextDoc
from warnings import filterwarnings
from fpdf import FPDF
import os, logging
from datetime import datetime
from numpy import irr

class PDF_S001V1(FPDF):

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

    def gTextLen(self, txt, family, size:int=7):
        self.set_font(family, size = size)
        return self.get_string_width(txt)

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

class S001V1():
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
        self.distribe = [1.0, 1.3, 1.6, 2.0, 2.4, 3.0, 3.6, 4.4, 5.4, 6.5, 7.7, 9.2, 11.0, 13.0, 15.3, 17.9, 20.9, 24.3, 28.0, 32.3, 37.0, 42.2, 47.9, 54.1, 60.9, 68.2, 76.0, 84.4, 93.2, 102.6, 112.3, 122.4, 132.8, 143.5, 154.3, 165.1, 175.9, 186.6, 197.1, 207.1, 216.7, 225.8, 234.1, 241.7, 248.3, 254.0, 258.7, 262.2, 264.6, 265.8, 265.8, 264.6, 262.2, 258.7, 254.0, 248.3, 241.7, 234.1, 225.8, 216.7, 207.1, 197.1, 186.6, 175.9, 165.1, 154.3, 143.5, 132.8, 122.4, 112.3, 102.6, 93.2, 84.4, 76.0, 68.2, 60.9, 54.1, 47.9, 42.2, 37.0, 32.3, 28.0, 24.3, 20.9, 17.9, 15.3, 13.0, 11.0, 9.2, 7.7, 6.5, 5.4, 4.4, 3.6, 3.0, 2.4, 2.0, 1.6, 1.3, 1.0]

        pass

    def genReport(self, json, filePath, pngFloder):
        self.generateReport(json['header'], json['userInfo'], json['ExerciseReport'], json['AssessIndexReport'], json['ExerciseIndexReport'], json['irregularHeartRateEcgs'], filePath)
        pass

    def generateReport(self, header, userInfo, exerciseReport, accessIndex, exerciseIndex, irregularEcgs, filePath) -> None:
        # A4 (w:210 mm and h:297 mm)
        filterwarnings("ignore")
        print('self.fontPath :', self.fontPath)
        # 繪製PDF
        self.report = PDF_S001V1(format='A4')
        self.report.add_font(self.fontFamily, '', self.fontPath, uni=True)
        self.report.add_font(self.fontSungFamily, '', self.fontSungPath, uni=True)
        self.header = header
        self.userInfo = userInfo
        self.__addExerciseReport(exerciseReport)
        self.__addNote(exerciseReport['notes'])
        self.__addAccessIndex(accessIndex, exerciseReport['ExerciseIndex']['hr_distribution'])
        self.__addExerciseIndex(exerciseIndex, exerciseReport['ExerciseIndex']['hr_distribution'])
        self.__addIrregular(irregularEcgs)
        
        # 匯出PDF
        pypath = os.path.join(os.path.dirname(__file__), '..', '..', 'user_pdf', 'S001V1')
        if not os.path.exists(pypath):
            os.makedirs(pypath)
        print('pypath :', pypath)
        file = os.path.join(pypath, filePath)
        print('file :', file)
        self.report.output(file)
        pass

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
        self.report.text(self.pageWidth_mx, startHeight+self.cellW, txt='運動健康評估報告')
        self.report.text(self.pageWidth_mx+(self.rowWidth*4), startHeight+self.cellW, txt='報告日期: '+self.header['reportDate'])
        self.report.text(self.pageWidth_mx+(self.rowWidth*8), startHeight+self.cellW, txt='測試期間: '+self.header['testingPeriod'])
        pass

    def __genFooter(self) -> None:
        startHeight = self.pageHeight_mt+(self.cellW*140)
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight)
        self.report.set_font(self.fontFamily, size = 7)
        self.report.text(self.pageWidth_mx, startHeight+self.cellW*2, txt='使用者: '+self.userInfo['name'])
        self.report.text(self.pageWidth_mx+(self.rowWidth*3), startHeight+self.cellW*2, txt='報告類別: S001V1')
        self.report.text(self.pageWidth_mx+(self.rowWidth*6), startHeight+self.cellW*2, txt='報告日期: '+self.header['reportDate'])
        self.report.text(self.pageWidth_mx+(self.rowWidth*10), startHeight+self.cellW*2, txt='頁數: '+str(self.report.page_no()))
        pass

    def __addExerciseReport(self, exerciseReport) -> None:
        self.__addPage()
        startHeight = self.pageHeight_mt+(self.cellW*20)
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+self.cellW, '運動健康評估', self.fontFamily, 12)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*6), startHeight+self.cellW, str(exerciseReport['score'])+" / 100", self.fontFamily, 12)
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*5), 'EXERCISE CARDIOVASCULAR', self.fontFamily, 12)
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*8), 'HEALTH REPORT', self.fontFamily, 12)

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
        # scoreWidth = (self.rowWidth*6+0.5)*(exerciseReport['score']/100.0)
        scoreWidth = (self.rowWidth*6+0.5)*((exerciseReport['score']-40)/60.0)
        self.report.sColors(drawColor=self.black, fillColor=self.black)
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*5.5), scoreWidth, self.cellW*4, 0.2, 'F')
        stlen = len(exerciseReport['scoreText'])
        if stlen>0:
            self.report.sColors(txtColor=self.white)
            scoreTextWidth = self.report.get_string_width(exerciseReport['scoreText'])
            self.report.dText(self.pageWidth_mx+(self.rowWidth*6)+scoreWidth-scoreTextWidth-4, startHeight+(self.cellW*8), exerciseReport['scoreText'], self.fontFamily, 7)
            self.report.sColors()
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*13))

        # assess
        assesssIndex = exerciseReport['AssessIndex']
        startHeight = self.pageHeight_mt+(self.cellW*35)
        cellHeightNo = 22
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*2), "瞬間高強度指標", self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*2), assesssIndex['scoreText'], self.fontFamily, 10)
        descStr = assesssIndex['description']
        self.report.dMultiText(self.pageWidth_mx, startHeight+(self.cellW*4), self.rowWidth*5.5, self.cellW*2, descStr, self.fontSungFamily, 7)
        suggStr = assesssIndex['suggestion']
        self.report.dMultiText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*4), self.rowWidth*5.5, self.cellW*2, suggStr, self.fontSungFamily, 7)
        evalStr = assesssIndex['evaluation']
        self.report.dMultiText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*12), self.rowWidth*5.5, self.cellW*2, evalStr, self.fontSungFamily, 7)
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*cellHeightNo))
        # exercise
        exerciseIndex = exerciseReport['ExerciseIndex']
        startHeight = self.pageHeight_mt+(self.cellW*59)
        cellHeightNo = 22
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*3), "高強度耐力指標", self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*3), exerciseIndex['scoreText'], self.fontFamily, 10)
        descStr = exerciseIndex['description']
        self.report.dMultiText(self.pageWidth_mx, startHeight+(self.cellW*4), self.rowWidth*5.5, self.cellW*2, descStr, self.fontSungFamily, 7)
        suggStr = exerciseIndex['suggestion']
        self.report.dMultiText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*4), self.rowWidth*5.5, self.cellW*2, suggStr, self.fontSungFamily, 7)
        evalStr = exerciseIndex['evaluation']
        self.report.dMultiText(self.pageWidth_mx+(self.rowWidth*6), startHeight+(self.cellW*12), self.rowWidth*5.5, self.cellW*2, evalStr, self.fontSungFamily, 7)
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*cellHeightNo))
        # irregular
        irregularStat = exerciseReport['IrregularStatistic']
        startHeight = self.pageHeight_mt+(self.cellW*83)
        cellHeightNo = 20
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*3), "異常心率統計", self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4), startHeight+(self.cellW*3), '異常統計', self.fontFamily, 10)
        self.report.sColors(fillColor=self.lightGrey)
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*4), startHeight+(self.cellW*5), self.rowWidth*4-0.2, self.cellW*6-0.2, 0.1, "F")
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*8)+0.2, startHeight+(self.cellW*5), self.rowWidth*4-0.2, self.cellW*6-0.2, 0.1, "F")
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*4), startHeight+(self.cellW*11)+0.2, self.rowWidth*4-0.2, self.cellW*6-0.2, 0.1, "F")
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*8)+0.2, startHeight+(self.cellW*11)+0.2, self.rowWidth*4-0.2, self.cellW*6-0.2, 0.1, "F")
        self.report.sColors()
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4)+1, startHeight+(self.cellW*6.5), '項目', self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*8)+1.2, startHeight+(self.cellW*6.5), '異常次數', self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4)+1, startHeight+(self.cellW*12.5)+0.2, '項目', self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*8)+1.2, startHeight+(self.cellW*12.5)+0.2, '異常次數', self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4)+1, startHeight+(self.cellW*9.5), '三分鐘登階', self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*8)+1.2, startHeight+(self.cellW*9.5), str(irregularStat['IrrinAssess'])+'次', self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4)+1, startHeight+(self.cellW*15.5)+0.2, '高強度耐力運動', self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*8)+1.2, startHeight+(self.cellW*15.5)+0.2, str(irregularStat['IrrinExercise'])+'次', self.fontFamily, 10)
        pass

    def __addNote(self, note) -> None:
        startHeight = self.pageHeight_mt+(self.cellW*114)
        cellHeightNo = 24
        self.report.set_draw_color(0, 0, 0)
        self.report.set_fill_color(255, 255, 255)
        self.report.set_text_color(0, 0, 0)
        self.report.sColors()
        self.report.dRect(self.pageWidth_mx, startHeight, self.rowWidth*self.rowNo, self.cellW*(cellHeightNo-2), 0.2, 'D')
        self.report.dText(self.pageWidth_mx+self.cellW, startHeight+(self.cellW*1.5), "NOTES", self.fontFamily, 8)
        if len(note)>0:
            self.report.set_xy(self.pageWidth_mx+self.cellW, startHeight+(self.cellW*2))
            self.report.dMultiText(self.pageWidth_mx+self.cellW, startHeight+(self.cellW*2), (self.rowWidth*12)-(4*self.cellW), self.cellW*2, note, self.fontSungFamily, 7)
        pass

    def __addAccessIndex(self, accessIndex, hrDist) -> None:
        self.__addPage()
        startHeight = self.pageHeight_mt+(self.cellW*2)
        cellHeightNo = 6
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*4), "瞬間高強度指標", self.fontFamily, 12)
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*cellHeightNo))

        startHeight = self.pageHeight_mt+(self.cellW*7)
        cellHeightNo = 25
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*4), "三分鐘登階測試", self.fontFamily, 10)
        self.report.sColors(fillColor=self.lightGrey)
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*3), startHeight+(self.cellW*3), self.rowWidth*4.5, self.cellW*6-0.2, 0.1, "F")
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*3), startHeight+(self.cellW*9), self.rowWidth*1.5, self.cellW*6-0.2, 0.1, "F")
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*4.5)+0.2, startHeight+(self.cellW*9), self.rowWidth*1.5-0.2, self.cellW*6-0.2, 0.1, "F")
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*6)+0.2, startHeight+(self.cellW*9), self.rowWidth*1.5-0.2, self.cellW*6-0.2, 0.1, "F")
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*3), startHeight+(self.cellW*15), self.rowWidth*1.5, self.cellW*6-0.2, 0.1, "F")
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*4.5)+0.2, startHeight+(self.cellW*15), self.rowWidth*1.5-0.2, self.cellW*6-0.2, 0.1, "F")
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*6)+0.2, startHeight+(self.cellW*15), self.rowWidth*1.5-0.2, self.cellW*6-0.2, 0.1, "F")
        self.report.sColors()
        self.report.dText(self.pageWidth_mx+(self.rowWidth*3)+1, startHeight+(self.cellW*4.5), '心肺耐力指數', self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*3)+1, startHeight+(self.cellW*10.5), '第一階段心率值', self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4.5)+1.2, startHeight+(self.cellW*10.5), '第二階段心率值', self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*6)+1.2, startHeight+(self.cellW*10.5), '第三階段心率值', self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*3)+1, startHeight+(self.cellW*16.5), '第一階段心率降幅', self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4.5)+1.2, startHeight+(self.cellW*16.5), '第二階段心率降幅', self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*6)+1.2, startHeight+(self.cellW*16.5), '第三階段心率降幅', self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*3)+1.2, startHeight+(self.cellW*7.5), str(accessIndex['score'])+', '+accessIndex['scoreText'], self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*3)+1.2, startHeight+(self.cellW*13.5), str(accessIndex['Stage1'][0])+' BPM', self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*3)+1.2, startHeight+(self.cellW*19.5), str(accessIndex['Stage1'][1])+' BPM', self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4.5)+1.2, startHeight+(self.cellW*13.5), str(accessIndex['Stage2'][0])+' BPM', self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*4.5)+1.2, startHeight+(self.cellW*19.5), str(accessIndex['Stage2'][1])+' BPM', self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*6)+1.2, startHeight+(self.cellW*13.5), str(accessIndex['Stage3'][0])+' BPM', self.fontFamily, 10)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*6)+1.2, startHeight+(self.cellW*19.5), str(accessIndex['Stage3'][1])+' BPM', self.fontFamily, 10)
        percent = int(accessIndex['Percentage'])
        descStr = '比 '+str(percent)+'% 的人健康'
        descLen = self.report.gTextLen(descStr, self.fontFamily, 9)
        self.report.dText(self.pageWidth_mx+(self.rowWidth*10)-(descLen/2), startHeight+(self.cellW*6), descStr, self.fontFamily, 9)
        self.report.sColors(drawColor=self.lightGrey)
        self.report.dRect(self.pageWidth_mx+(self.rowWidth*8), startHeight+(self.cellW*8), self.rowWidth*4, self.cellW*13, 0.2, "D")
        yspace = self.cellW*13/600
        xspace = ((self.rowWidth*4)-0.2)/99
        y0 = startHeight+(self.cellW*8)
        preX = 0
        preY = 0
        self.report.sColors()
        for i in range(1, 101):
                curX = self.pageWidth_mx+(self.rowWidth*8)+0.1+(xspace*(i-1))
                curY = y0+((600-self.distribe[i-1])*yspace)
                if (i>1):
                    self.report.dLine(preX, preY, curX, curY, 0.3)

                if (i==percent):
                    self.report.dLine(curX, curY, curX, y0+(self.cellW*3), 0.1)
                    pstr = str(percent)+'%'
                    pstrlen = self.report.gTextLen(pstr, self.fontFamily, 7)
                    self.report.dText(curX-(pstrlen/2), y0+(self.cellW*2.5), pstr, self.fontFamily, 7)
                preX = curX
                preY = curY
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*cellHeightNo))
        self.__addAssessHR(startHeight+(self.cellW*cellHeightNo+2), 44, accessIndex['HRperSec'], hrDist)
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*72))
        self.__addAssessRecovery(startHeight+(self.cellW*74), 44, accessIndex['RecoveryHRValue'], accessIndex['RecoveryHRLoc'], accessIndex['HRperSec'], hrDist)
        pass

    def __addAssessHR(self, startHeight, cellNoHeight, hrs, hrDist):
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*2), "三分鐘登階心率變化圖", self.fontFamily, 10)
        (bw, bh, bx, by, ybu, yu, xbu, xu) = self.__addHRBg(self.pageWidth_mx+(self.rowWidth*2), startHeight+(self.cellW*4), self.rowWidth*10, self.cellW*(cellNoHeight-5), hrDist)
        preX = 0
        preY = -1
        self.report.sColors()
        hrLen = len(hrs)
        if hrLen>390:
            hrLen = 390
        for i in range(1, hrLen+1):
            curX = bx+(xu*(i))
            curY = by+((hrDist[0]-hrs[i-1])*yu)
            if (curY>(by+bh)):
                curY = -1
            if (preY!=-1 and curY!=-1):
                self.report.dLine(preX, preY, curX, curY, 0.3)
            if (i==180 or i==255 or i==315 or i==375):
                lY = curY
                if (lY==-1):
                    lY = by+bh
                hY = lY - (self.cellW*3)
                self.report.dLine(curX, lY, curX, hY, 0.2)
                self.report.sColors(txtColor=self.white, fillColor=self.black)
                txt = str(int(hrs[i-1]))+' BPM'
                txtLen = self.report.gTextLen(txt, self.fontFamily, 8)
                self.report.dRect(curX-((txtLen+2)/2), hY-(self.cellW*2+2), (txtLen+2), (self.cellW*2+2), 0.1, 'F')
                self.report.dText(curX-(txtLen/2), hY-(self.cellW), txt, self.fontFamily, 8)
                self.report.sColors()
            preX = curX
            preY = curY
        pass

    def __addAssessRecovery(self, startHeight, cellNoHeight, recoveryValues, recoveryLog, hrs, hrDist):
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*2), "心跳恢復率", self.fontFamily, 10)
        self.report.sColors(fillColor=self.lightGrey)
        self.report.dRect(self.pageWidth_mx, startHeight+(self.cellW*4), self.rowWidth*1.8, self.cellW*8, 0.1, "F")
        self.report.sColors()
        self.report.dText(self.pageWidth_mx+1, startHeight+(self.cellW*5.5), '心跳恢復率評比', self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+1, startHeight+(self.cellW*8.5), recoveryValues['Text'], self.fontFamily, 11)
        self.report.dText(self.pageWidth_mx+1, startHeight+(self.cellW*11), str(recoveryValues['HRDecrese'])+' BPM', self.fontFamily, 11)

        (bw, bh, bx, by, ybu, yu, xbu, xu) = self.__addHRBg(self.pageWidth_mx+(self.rowWidth*2), startHeight+(self.cellW*4), self.rowWidth*10, self.cellW*(cellNoHeight-5), hrDist)
        preX = 0
        preY = -1
        self.report.sColors()
        hrLen = len(hrs)
        if hrLen>390:
            hrLen = 390
        for i in range(1, hrLen+1):
            curX = bx+(xu*(i))
            curY = by+((hrDist[0]-hrs[i-1])*yu)
            if (curY>(by+bh)):
                curY = -1
            if (preY!=-1 and curY!=-1):
                self.report.dLine(preX, preY, curX, curY, 0.3)
            if (i==recoveryLog[0] or i==recoveryLog[1]):
                lY = curY
                if (lY==-1):
                    lY = by+bh
                hY = lY - (self.cellW*3)
                self.report.dLine(curX, lY, curX, hY, 0.2)
                self.report.sColors(txtColor=self.white, fillColor=self.black)
                txt = str(int(hrs[i-1]))+' BPM'
                txtLen = self.report.gTextLen(txt, self.fontFamily, 8)
                self.report.dRect(curX-((txtLen+2)/2), hY-(self.cellW*2+2), (txtLen+2), (self.cellW*2+2), 0.1, 'F')
                self.report.dText(curX-(txtLen/2), hY-(self.cellW), txt, self.fontFamily, 8)
                self.report.sColors()
            preX = curX
            preY = curY
        pass    
  
    def __addHRBg(self, x, y, w, h, hrDist):
        rLabel = ['110%', '100%', '90%', '80%', '70%', '60%', '50%', '40%', '30%']
        bw = w-(self.rowWidth)
        bh = h-(self.cellW*4)
        bx = x+(self.rowWidth/2)
        by = y+(self.cellW*2)
        ybu = bh/8
        yu = bh/(hrDist[0]-hrDist[8])
        xbu = bw/14
        xu = bw/420
        self.report.sColors(drawColor=self.darkGrey)
        self.report.dRect(bx, by, bw, bh, 0.1, "D")
        for i in range(0, 9):
            self.report.sColors(txtColor=self.darkGrey, drawColor=self.darkGrey)
            txt = str(hrDist[i])
            txtLen = self.report.gTextLen(txt, self.fontFamily, 6)
            self.report.dText(bx-self.cellW-txtLen, by+(i*ybu)+0.5, txt, self.fontFamily, 6)
            self.report.dText(bx+bw+self.cellW, by+(i*ybu)+0.5, rLabel[i], self.fontFamily, 6)
            self.report.dLine(bx, by+(i*ybu), bx+bw, by+(i*ybu), 0.1)
        for i in range(1, 14):
            self.report.sColors(txtColor=self.darkGrey, drawColor=self.darkGrey)
            if (i!=13 and i%2!=0):
                self.report.dDashLine(bx+(i*xbu), by, bx+(i*xbu), by+bh, 0.1)
            else:
                self.report.dLine(bx+(i*xbu), by, bx+(i*xbu), by+bh, 0.1)
                ts = "0"+str(int(i/2))+":00"
                if (i==13):
                    ts = "06:30"
                tsl = self.report.gTextLen(ts, self.fontFamily, 6)
                self.report.dText(bx+(i*xbu)-(tsl/2), by+bh+(self.cellW*2.5), ts, self.fontFamily, 6)
        self.report.sColors()
        txt = 'START'
        txtLen = self.report.gTextLen(txt, self.fontFamily, 7)
        self.report.dText(bx-(txtLen/2), y+(self.cellW*0.5), txt, self.fontFamily, 7)
        txt = 'REST'
        txtLen = self.report.gTextLen(txt, self.fontFamily, 7)
        self.report.dText(bx+(6*xbu)-(txtLen/2), y+(self.cellW*0.5), txt, self.fontFamily, 7)
        txt = 'END'
        txtLen = self.report.gTextLen(txt, self.fontFamily, 7)
        self.report.dText(bx+(13*xbu)-(txtLen/2), y+(self.cellW*0.5), txt, self.fontFamily, 7)
        return (bw, bh, bx, by, ybu, yu, xbu, xu)

    def __addExerciseIndex(self, exerciseIndex, hrDist) -> None:
        self.__addPage()
        startHeight = self.pageHeight_mt+(self.cellW*2)
        cellHeightNo = 6
        self.report.sColors()
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*4), "高強度耐力指標", self.fontFamily, 12)
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*cellHeightNo))

        startHeight = self.pageHeight_mt+(self.cellW*7)
        cellHeightNo = 44
        self.report.dText(self.pageWidth_mx, startHeight+(self.cellW*4), "運動心率變化圖", self.fontFamily, 10)

        x = self.pageWidth_mx+(self.rowWidth*2)
        y = startHeight+(self.cellW*6)
        w = self.rowWidth*10
        h = self.cellW*(cellHeightNo-5)

        rLabel = ['110%', '100%', '90%', '80%', '70%', '60%', '50%', '40%', '30%']
        bw = w-(self.rowWidth)
        bh = h-(self.cellW*4)
        bx = x+(self.rowWidth/2)
        by = y+(self.cellW*2)
        ybu = bh/8
        yu = bh/(hrDist[0]-hrDist[8])
        xbu = bw/30
        xu = bw/1800
        self.report.sColors(drawColor=self.darkGrey)
        self.report.dRect(bx, by, bw, bh, 0.1, "D")
        for i in range(0, 9):
            self.report.sColors(txtColor=self.darkGrey, drawColor=self.darkGrey)
            txt = str(hrDist[i])
            txtLen = self.report.gTextLen(txt, self.fontFamily, 6)
            self.report.dText(bx-self.cellW-txtLen, by+(i*ybu)+0.5, txt, self.fontFamily, 6)
            self.report.dText(bx+bw+self.cellW, by+(i*ybu)+0.5, rLabel[i], self.fontFamily, 6)
            self.report.dLine(bx, by+(i*ybu), bx+bw, by+(i*ybu), 0.1)
        for i in range(0, 30):
            self.report.sColors(txtColor=self.darkGrey, drawColor=self.darkGrey)
            if (i%5!=0):
                self.report.dDashLine(bx+(i*xbu), by, bx+(i*xbu), by+bh, 0.1)
            else:
                if (i>0):
                    self.report.dLine(bx+(i*xbu), by, bx+(i*xbu), by+bh, 0.1)
                tsf = "{i:02d}:00"
                ts = tsf.format(i=i)
                tsl = self.report.gTextLen(ts, self.fontFamily, 6)
                self.report.dText(bx+(i*xbu)-(tsl/2), by+bh+(self.cellW*2.5), ts, self.fontFamily, 6)
        self.report.sColors(txtColor=self.darkGrey, drawColor=self.darkGrey)
        ts = tsf.format(i=30)
        tsl = self.report.gTextLen(ts, self.fontFamily, 6)
        self.report.dText(bx+(30*xbu)-(tsl/2), by+bh+(self.cellW*2.5), ts, self.fontFamily, 6)
        self.report.sColors()
        txt = 'START'
        txtLen = self.report.gTextLen(txt, self.fontFamily, 7)
        self.report.dText(bx-(txtLen/2), y+(self.cellW*0.5), txt, self.fontFamily, 7)
        txt = 'END'
        txtLen = self.report.gTextLen(txt, self.fontFamily, 7)
        self.report.dText(bx+(30*xbu)-(txtLen/2), y+(self.cellW*0.5), txt, self.fontFamily, 7)
        self.report.sColors()
        self.report.dLine(self.pageWidth_mx, by, self.pageWidth_mx, by+bh, 0.2)
        for i in range(0, 9):
            if (i!=1 and i!=7):
                self.report.dLine(self.pageWidth_mx, by+(i*ybu), self.pageWidth_mx+2.5, by+(i*ybu), 0.2) 
                self.report.dDashLine(self.pageWidth_mx+5, by+(i*ybu), self.pageWidth_mx+(self.rowWidth*1.9), by+(i*ybu), 0.2)
        self.report.dText(self.pageWidth_mx+5, by+(1*ybu)-1, "速度與爆發力運動", self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+5, by+(1*ybu)+2, "極限鍛鍊 / 提升最大攝氧量", self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+5, by+(2.5*ybu)-0.5, "高強度運動", self.fontFamily, 6) 
        self.report.dText(self.pageWidth_mx+5, by+(2.5*ybu)+2.5, "無氧運動訓練 / 肌力鍛鍊", self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+5, by+(3.5*ybu)-0.5, "中強度運動", self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+5, by+(3.5*ybu)+2.5, "有氧運動 / 減脂瘦身", self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+5, by+(4.5*ybu)-0.5, "低強度運動", self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+5, by+(4.5*ybu)+2.5, "暖身 / 鍛鍊後恢復", self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+5, by+(5.5*ybu)+1, "暖身運動 / 鍛鍊後恢復", self.fontFamily, 6)
        self.report.dText(self.pageWidth_mx+5, by+(7.*ybu)+1, "靜態活動", self.fontFamily, 6)
        hrs = exerciseIndex['HRperSec']
        preX = 0
        preY = -1
        self.report.sColors()
        hrLen = len(hrs)
        if hrLen>1800:
            hrLen = 1800
        for i in range(1, hrLen+1):
            curX = bx+(xu*(i))
            curY = by+((hrDist[0]-hrs[i-1])*yu)
            if (curY>(by+bh)):
                curY = -1
            if (preY!=-1 and curY!=-1):
                self.report.dLine(preX, preY, curX, curY, 0.3)
            if (i==exerciseIndex['MaxHRLoc']):
                lY = curY
                if (lY==-1):
                    lY = by+bh
                hY = lY - (self.cellW*3)
                self.report.dLine(curX, lY, curX, hY, 0.2)
                self.report.sColors(txtColor=self.white, fillColor=self.black)
                txt = str(int(hrs[i-1]))+' BPM'
                txtLen = self.report.gTextLen(txt, self.fontFamily, 8)
                self.report.dRect(curX-((txtLen+2)/2), hY-(self.cellW*2+2), (txtLen+2), (self.cellW*2+2), 0.1, 'F')
                self.report.dText(curX-(txtLen/2), hY-(self.cellW), txt, self.fontFamily, 8)
                self.report.sColors()
            preX = curX
            preY = curY
        self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight+(self.cellW*50))
        self.__addEcg(startHeight+(self.cellW*54), 35, exerciseIndex['maxHRStatistics'], '運動心電圖', drawPVC=False)
        pass
    
    def __addIrregular(self, ecgs) -> None:
        startHeight = self.pageHeight_mt+(self.cellW*96)
        ecgsNo = len(ecgs)
        if (ecgsNo>0):
            self.__addDriven(self.pageWidth_mx, self.pageWidth_mx+self.rowWidth*12, startHeight)
            self.__addEcg(self.pageWidth_mx+(self.cellW*98), 35, ecgs[0], '異常心電圖')
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

    def __addEcg(self, startHeight, cellNoHeight, ecg, title='', drawPVC=True):
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

        if (drawPVC==True):
            self.report.sColors(fillColor=self.black)
            self.report.dCircle(self.pageWidth_mx+(self.rowWidth*10)+1, startHeight+(self.cellW*2)+1, 2, 0.1, 'F')
            self.report.dText(self.pageWidth_mx+(self.rowWidth*10.3), startHeight+(self.cellW*3.5), "Irreqular", self.fontFamily, 7)
            self.report.dImage(self.pageWidth_mx+(self.rowWidth*10), startHeight+(self.cellW*4.0), self.flagPath, w=4, h=4)
            self.report.sColors()
            self.report.dText(self.pageWidth_mx+(self.rowWidth*10.3), startHeight+(self.cellW*5.5), "PVC", self.fontFamily, 7)
        else:
            self.report.sColors()

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
        preY = -1
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
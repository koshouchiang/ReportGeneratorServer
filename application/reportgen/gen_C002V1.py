from warnings import filterwarnings
from fpdf import FPDF
import os
from datetime import datetime


class Report_C002V1(FPDF):

    # Page header
    def header(self):
        if(self.page_no() > 1):
            self.set_font('TaipeiSans', size = 8)
            headerY = 8
            self.set_xy(6, headerY)
            self.cell(5, txt="兩分鐘心電圖")
            self.set_xy(66, headerY)
            # self.cell(5, txt='測量時間: 2022/04/07 10:33:21')
        pass

    # Page footer
    def footer(self):
        self.set_line_width(0.3)
        self.set_draw_color(0, 0, 0)
        self.line(6, 280, 204, 280)

        self.set_font('TaipeiSans', size = 8)
        footerY = -13
        # self.set_xy(6, footerY)
        # self.cell(5, txt='姓名: xxx')

        # self.set_xy(66, footerY)
        # self.cell(5, txt='報告: 兩分鐘心電圖')

        self.set_xy(188, footerY)
        self.cell(5, txt='頁碼: %s' % self.page_no() + '/{nb}')
    
        pass


class Gen_Report_C002V1():

    def __init__(self) -> None:
        self.pageNo = 0             # 頁數
        self.pageWidth = 210        # 頁寬
        self.pageHeight = 297       # 頁高
        self.pageWidth_mx = 6       # 頁寬 margin left & right
        self.pageHeight_mt = 6      # 頁高 margin top & bottom

        # grid 1~12 x軸位置
        self.grid_pr = 3                                                 # grid padding right
        self.gridWidth = (self.pageWidth - (self.pageWidth_mx*2)) / 12   # grid 每隔寬度
        self.grid1X = self.pageWidth_mx
        self.grid2X = self.grid1X + self.gridWidth
        self.grid3X = self.grid2X + self.gridWidth
        self.grid4X = self.grid3X + self.gridWidth
        self.grid5X = self.grid4X + self.gridWidth
        self.grid6X = self.grid5X + self.gridWidth
        self.grid7X = self.grid6X + self.gridWidth
        self.grid8X = self.grid7X + self.gridWidth
        self.grid9X = self.grid8X + self.gridWidth
        self.grid10X = self.grid9X + self.gridWidth
        self.grid11X = self.grid10X + self.gridWidth
        self.grid12X = self.grid11X + self.gridWidth

        # column
        ## 高 (一頁八欄)
        self.colHeight = (self.pageHeight - self.pageHeight_mt*2) / 8

        # 文字行高
        self.lineHeight = 4.5

        # 檔案相關
        pypath = os.path.dirname(__file__)
        self.fontPath = os.path.join(pypath,"doc","TaipeiSansTCBeta-Regular.ttf")  # 字型檔案位置
        self.logoPath = os.path.join(pypath,"doc","SW-Logo.png")                   # logo 檔案位置
        self.fontFamily = 'TaipeiSans'                              # 字型

        pass

    def generateReport(self, report_info, user_info, events, note, file_name) -> None:
        # A4 (w:210 mm and h:297 mm)
        self.report = Report_C002V1(format='A4')
        self.report.add_font(self.fontFamily, '', self.fontPath, uni=True)
        self.__addPage()
        self.__addInfo(report_info, user_info)
        self.y = 58
        self.__addEcgs(events)
        self.__addNote(note)
        filterwarnings("ignore")
        
        pypath = os.path.join(os.path.dirname(__file__), '..', '..', 'user_pdf', 'C002V1')
        if not os.path.exists(pypath):
            os.makedirs(pypath)

        file = os.path.join(pypath, file_name)
        self.report.output(file, 'F')
        pass

    def __addPage(self) -> None:
        ## y軸
        self.y = 0 + self.pageHeight_mt
        self.report.add_page()
        self.report.alias_nb_pages()
        pass

    def __addInfo(self, report_info, user_info) -> None:
        __InfoStartY = self.y + 3
        self.__addUserProfile(__InfoStartY, report_info=report_info, user_info=user_info)
        self.__addComponyInfo(__InfoStartY)
        __InfoStartY += 25 + self.lineHeight*4
        self.__addEcgTitle(__InfoStartY, report_info=report_info)
        pass

    def __addComponyInfo(self, __InfoStartY) -> None:

        self.report.set_font(self.fontFamily, size = 8)
        self.report.set_xy(self.grid9X, __InfoStartY - 1)
        self.report.image(self.logoPath, h=7.5)
        __InfoStartY += 9
        self.__addDriven(self.grid9X, self.grid12X + self.gridWidth, __InfoStartY)

        __InfoStartY += 5
        row1 = __InfoStartY
        row2 = row1 + self.lineHeight
        row3 = row2 + self.lineHeight + 5
        row4 = row3 + self.lineHeight
        # 公司名稱
        self.report.set_xy(self.grid9X, row1)
        self.report.cell(self.lineHeight, txt='奇翼醫電股份有限公司')
        self.report.set_xy(self.grid9X, row2)
        self.report.cell(self.lineHeight, txt='Singular Wings Medical')
        # email
        self.report.set_xy(self.grid9X, row3)
        self.report.cell(self.lineHeight, txt='service@singularwings.com')
        # Web
        self.report.set_xy(self.grid9X, row4)
        self.report.cell(self.lineHeight, txt='www.singularwings.com')

        __InfoStartY += self.lineHeight*4 + 4
        self.__addDriven(self.grid9X, self.grid12X + self.gridWidth, __InfoStartY)
        
        pass

    def __addUserProfile(self, __InfoStartY, report_info, user_info) -> None:

        ReportHeaderName = report_info['ReportHeaderName']
        TestingPeriod = report_info['TestingPeriod']
        UserName = user_info['Name']
        UserBirthday = user_info['Birthday']
        UserAge = user_info['Age']
        UserGender = user_info['Gender']
        UserHeight = user_info['Height']
        UserWeight = user_info['Weight']

        self.report.set_font(self.fontFamily, size = 8)
        self.report.set_xy(self.grid1X, __InfoStartY)
        self.report.cell(self.lineHeight, txt=ReportHeaderName)

        self.report.set_xy(self.grid7X, __InfoStartY)
        self.report.cell(self.lineHeight, txt='測量時間:')
        __InfoStartY += self.lineHeight
        self.report.set_xy(self.grid7X, __InfoStartY)
        self.report.cell(self.lineHeight, txt=TestingPeriod)
        __InfoStartY += self.lineHeight

        self.__addDriven(self.grid1X, self.grid8X + self.gridWidth - self.grid_pr, __InfoStartY)

        __InfoStartY += 5
        row1 = __InfoStartY
        row2 = row1 + self.lineHeight
        row3 = row2 + self.lineHeight + 5
        row4 = row3 + self.lineHeight
        # 姓名
        self.report.set_xy(self.grid1X, row1)
        self.report.cell(self.lineHeight, txt='姓名:')
        self.report.set_xy(self.grid1X, row2)
        self.report.cell(self.lineHeight, txt=UserName)
        # 年齡
        self.report.set_xy(self.grid3X, row1)
        self.report.cell(self.lineHeight, txt='年齡:')
        self.report.set_xy(self.grid3X, row2)
        self.report.cell(self.lineHeight, txt=UserAge)
        # 身高
        self.report.set_xy(self.grid5X, row1)
        self.report.cell(self.lineHeight, txt='身高:')
        self.report.set_xy(self.grid5X, row2)
        self.report.cell(self.lineHeight, txt=UserHeight)
        # 生日
        self.report.set_xy(self.grid1X, row3)
        self.report.cell(self.lineHeight, txt='生日:')
        self.report.set_xy(self.grid1X, row4)
        self.report.cell(self.lineHeight, txt=UserBirthday)
        # 性別
        self.report.set_xy(self.grid3X, row3)
        self.report.cell(self.lineHeight, txt='性別:')
        self.report.set_xy(self.grid3X, row4)
        self.report.cell(self.lineHeight, txt=UserGender)
        # 體重
        self.report.set_xy(self.grid5X, row3)
        self.report.cell(self.lineHeight, txt='體重:')
        self.report.set_xy(self.grid5X, row4)
        self.report.cell(self.lineHeight, txt=UserWeight)

        __InfoStartY += self.lineHeight*4 + 4
        self.__addDriven(self.grid1X, self.grid8X + self.gridWidth - self.grid_pr, __InfoStartY)

        pass

    def __addEcgTitle(self, __InfoStartY, report_info) -> None:

        ReportName = report_info['ReportName']

        self.report.set_font(self.fontFamily, size = 16)
        self.report.set_xy(self.grid1X, __InfoStartY)
        self.report.cell(self.lineHeight, txt=ReportName)
        pass

    def __addEcgs(self, events) -> None:
        for i in range(0, len(events)):
            if (i < 12):
                if (self.pageHeight-self.y < self.colHeight):
                    self.__addPage()
                    self.y += self.lineHeight
                
                self.__addEcg(events[i], self.y)
        pass

    def __addEcg(self, event, __EcgStartY) -> None:
        
        self.__addDriven(self.grid1X, self.grid12X + self.gridWidth)

        ecgWidth = 170
        ecgHeight = ecgWidth/10

        self.report.set_font(self.fontFamily, size = 8)
        self.report.set_text_color(0, 0, 0)
        self.report.set_xy(self.grid1X, __EcgStartY + 6)
        self.report.cell(self.lineHeight, txt='ECG')
        self.report.set_xy(self.grid1X, __EcgStartY + 6 + self.lineHeight)
        self.report.cell(self.lineHeight, txt='10 SEC')
        # 0.5mV / 200 ms
        self.report.set_line_width(0.15)
        self.report.rect(self.grid1X + 1, __EcgStartY + self.colHeight/2 + 5, ecgWidth/50, ecgHeight/5)
        self.report.set_font(self.fontFamily, size = 6)
        self.report.set_xy(self.grid1X + ecgWidth/50 + 1.5, __EcgStartY + self.colHeight/2 + 7)
        self.report.cell(self.lineHeight, txt='0.5mV')
        self.report.set_xy(self.grid1X, __EcgStartY + self.colHeight/2 + 11)
        self.report.cell(self.lineHeight, txt='200 ms')
        
        # ECG 格子
        ecgChartStartX = self.grid1X + 20
        ecgChartStartY = __EcgStartY + 9

        self.report.set_line_width(0.3)
        self.report.set_draw_color(190, 190, 190)
        self.report.rect(ecgChartStartX, ecgChartStartY, ecgWidth, ecgHeight)

        ## Y 線
        ecgYStep = ecgHeight/25
        for i in range(1, 25):
            if (i%5 == 0):
                self.report.set_line_width(0.15)
                self.report.line(ecgChartStartX, ecgChartStartY+(ecgYStep*i), ecgChartStartX+ecgWidth, ecgChartStartY+(ecgYStep*i))

        ## X 線
        ecgXStep = ecgWidth/250
        for i in range(1, 250):
            if (i%25 == 0):
                self.report.set_line_width(0.3)
                self.report.line(ecgChartStartX+(ecgXStep*i), ecgChartStartY, ecgChartStartX+(ecgXStep*i), ecgChartStartY+ecgHeight)
            elif (i%5==0):
                self.report.set_line_width(0.15)
                self.report.line(ecgChartStartX+(ecgXStep*i), ecgChartStartY, ecgChartStartX+(ecgXStep*i), ecgChartStartY+ecgHeight)

        # ECG 線 & rpeak
        ecgLineXStep = ecgWidth/2500
        ecgLineYStep = (ecgYStep*10)/650
        ecgLineY0 = ecgChartStartY+(ecgYStep*15)    ## 第一個點(0,Y)位置
        preX = 0
        preY = 0

        # Rpeak 打點直徑
        rpeakEllipseDiameter = 1

        tt = event['Timestamp']
        rpeak = event['Rpeak']
        ecgs = event['ECGs']

        self.report.set_line_width(0.15)
        self.report.set_draw_color(0, 0, 0)

        for i in range(0,len(ecgs)):
            curX = ecgChartStartX+(ecgLineXStep*i)
            curY = ecgLineY0 - (ecgs[i]*ecgLineYStep)
            # ECG
            if (i>0):
                self.report.line(preX, preY, curX, curY)
            # Rpeak
            if(i in rpeak):
                self.report.ellipse(curX - rpeakEllipseDiameter/2, ecgChartStartY - 2, rpeakEllipseDiameter, rpeakEllipseDiameter, 'F')
                pass
            preX = curX
            preY = curY

        for i in range(0, 11):
            dt = datetime.fromtimestamp((tt+(1000*i))/1000)
            dtstr = dt.strftime("%H:%M:%S")
            self.report.set_font(self.fontFamily, size=6)
            self.report.set_xy(ecgChartStartX+(ecgXStep*i*25)-5, ecgChartStartY+ecgHeight+0.5)
            self.report.cell(w=10, h=3.0, align='C', txt=dtstr, border=0)


        self.y += self.colHeight
        pass

    def __addNote(self, note) -> None:

        if (self.pageHeight-self.y < self.colHeight):
            self.__addPage()
            self.y += 5

        self.__addDriven(self.grid1X, self.grid12X + self.gridWidth)
        self.y += 3

        # 外線
        noteStartY = self.y
        noteEndY = noteStartY + 37
        self.report.set_line_width(0.1)
        # 左
        self.report.line(self.grid1X, noteStartY, self.grid1X, noteEndY)
        # 上
        self.report.line(self.grid1X, noteStartY, self.grid12X + self.gridWidth, noteStartY)
        # 右
        self.report.line(self.grid12X + self.gridWidth, noteStartY, self.grid12X + self.gridWidth, noteEndY)
        # 下
        self.report.line(self.grid1X, noteEndY, self.grid12X + self.gridWidth, noteEndY)

        # 內線
        noteInitStartX = self.grid1X + 3
        noteInitEndX = self.grid12X + self.gridWidth - 3
        self.report.set_draw_color(230, 230, 230)
        for noteLine in range(0, 5):
            startY = noteStartY + 8 + noteLine * 6
            self.report.line(noteInitStartX, startY, noteInitEndX, startY)

        self.report.set_font(self.fontFamily, size = 8)
        self.report.set_xy(noteInitStartX, noteStartY + 4)
        # note
        self.report.multi_cell(190, self.lineHeight+1.1, txt=note)

        pass

    def __addDriven(self, startGridX, endGridX, y='') -> None:
        """分割線"""
        if(y==''):
            y = self.y
        self.report.set_draw_color(0, 0, 0)
        self.report.set_line_width(0.3)
        self.report.line(startGridX, y, endGridX, y)

        pass



from typing import List
from utility.request_mapper import base_json_content

from .gen_C002V1 import Gen_Report_C002V1


class ReportC002V1InfoContent(base_json_content):
    ReportId: str = None
    ReportHeaderName: str = None
    ReportName: str = None
    TestingPeriod: str = None
    ReportDate: str = None

class ReportC002V1UserInfoContent(base_json_content):
    Name: str = None
    Birthday: str = None
    Age: str = None
    Gender: str = None
    Height: str = None
    Weight: str = None

class ReportC002V1EventsContent(base_json_content):
    Timestamp: int = 0
    Rpeak: List[int] = []
    ECGs: List[int] = []

class ReportC002V1Content(base_json_content):
    ReportInfo: ReportC002V1InfoContent = None
    UserInfo: ReportC002V1UserInfoContent = None
    Events: List[ReportC002V1EventsContent] = []
    Note: str = None
    FileName: str = None

    def Generate(self) -> bool:
        gen_C002V1 = Gen_Report_C002V1()
        gen_C002V1.generateReport(report_info=self.ReportInfo, user_info=self.UserInfo, events=self.Events, note=self.Note, file_name=self.FileName)
        return True
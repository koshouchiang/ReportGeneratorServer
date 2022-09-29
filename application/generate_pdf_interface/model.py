from application.reportgen.gen_A002V2 import A002V2
from application.reportgen.gen_E001V1 import E001V1
from application.reportgen.gen_S001v1 import S001V1


def fake_choose_generate_pdf_version(report_code : str) -> object:
    report_code_generate_pdf_version_map = {
        'A002V2' : A002V2(),
        'E001V1' : E001V1(),
        'S001V1' : S001V1()
    }
    return report_code_generate_pdf_version_map[report_code]

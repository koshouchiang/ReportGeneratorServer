import re
from utility.algorithms.report.ExerciseReportGenerator import ExerciseReportGenerator
from utility.algorithms.report.SleepQualityReportGenerator import SleepQualityReportGenerator
from utility.algorithms.report.CardiovascularHealthReportGenerator import CardiovascularHealthReportGenerator
from application.setting import ZIP_FILE_PATH_HEALTH_SERVER, E001V1_FILES_PATH, PDF_A002V2_PATH, PDF_S001V1_PATH, PDF_E001V1_PATH




def choose_algorithm_type(report_code : str, zip_path : str) :
    '''
    this function will let algo choose version
    '''
    card_instanse = CardiovascularHealthReportGenerator(zip_path)
    sleep_instanse = SleepQualityReportGenerator(zip_path)
    exercise_instanse = ExerciseReportGenerator(zip_path)
    report_code_algo_version_map = {
        'A\d*V\d*' : card_instanse.HealthReportGenerator,
        'E\d*V\d*' : sleep_instanse.SleepAnalysisReport,
        'S\d*V\d*' : exercise_instanse.ExerciseAnalysisReport
    }
    for key in report_code_algo_version_map.keys():
        match_result = re.match(key,report_code)
        # must only match one key in report_code_algo_version_map
        if match_result:
            print(match_result.group())
            return report_code_algo_version_map[key]
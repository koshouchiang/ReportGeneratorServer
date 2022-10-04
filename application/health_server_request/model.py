import time, os, json, re, zipfile
from datetime import datetime
from utility.algorithms.report.ExerciseReportGenerator import ExerciseReportGenerator
from utility.algorithms.report.SleepQualityReportGenerator import SleepQualityReportGenerator
from utility.algorithms.report.CardiovascularHealthReportGenerator import CardiovascularHealthReportGenerator
from application.setting import q, ZIP_FILE_PATH_HEALTH_SERVER, E001V1_FILES_PATH, PDF_A002V2_PATH, PDF_A002V3_PATH, PDF_S001V1_PATH, PDF_E001V1_PATH
import application.setting as setting
from application.mysql_.model import ReportTable
from application.algorithm_interface.model import choose_algorithm_type
from application.generate_pdf_interface.model import fake_choose_generate_pdf_version
from ..model import RequestTemplate
import application
from application.logger.model import logger_message



class HealthServerRequestAction(RequestTemplate):


    def __init__(self):
        self.report_generating = False
        self.report_generate_progress = {
            "in_create" : {"flag" : 0, "time":None},
            "in_create_done" : {"flag" : 0, "time":None},
            "in_send" : {"flag" : 0, "time":None},
            "in_send_done" : {"flag" : 0, "time":None},
            "in_algorithm" : {"flag" : 0, "time":None},
            "in_algorithm_done" : {"flag" : 0, "time":None},
            "in_generate_pdf" : {"flag" : 0, "time":None},
            "in_generate_pdf_done" : {"flag" : 0, "time":None}
        }
        self.algorithm_setting_map = {
            'S001V1' : {'time_format' : '%Y%m%d %H%M%S'},
            'E001V1' : {'time_format' : '%Y%m%d %H%M%S'},
            'A002V2' : {'time_format' : '%Y%m%d'},
            'A002V3' : {'time_format' : '%Y%m%d'}
        }

        self.data_completed_map = {
            'create' : ["report_code", "user_id" ,"health_server_got_generate_request_time" ,"health_server_post_create_time" ,"user_info", "algorithm_input"],
            'send' : ["report_table_index", "end_flag"]

        }

    def check_data_completed(self, data : dict, post_api_mode : str):
        for key in data.keys():
            if key not in self.data_completed_map[post_api_mode]:
                return False, "unknow data : {}".format(key)
        for key in self.data_completed_map[post_api_mode]:
            if key not in list(data.keys()):
                return False, "missing data : {}".format(key)
        return True, 200

    def start_process_entrance(self, content):
        self.report_generating = True
        algorithm_result, report_code, user_info = self.start_algorithm_part(self.prepare_algorithm_input(content), content)
        print(algorithm_result, report_code, user_info)
        if algorithm_result['status']:
            if self.manual_review:
                self.start_generate_pdf_part(content, algorithm_result['message'], report_code, user_info)
        self.report_generating = False

    def check_qsize_fulled(self) -> bool:
        return q.qsize() >= setting.QUEUE_SIZE
    
    def make_dir(self, path):
        if not os.path.exists(path):
            os.mkdir(path)

    def prepare_algorithm_input(self, content) -> tuple:
        algorithm_input, report_code = application.mysql_manage.query_data_algorithm_input(content)
        algorithm_input = self.transfer_timestamp(algorithm_input, self.algorithm_setting_map[report_code]['time_format'])
        if report_code == 'S001V1':
            return (report_code), (algorithm_input['step_test_start_tt'], algorithm_input['step_test_end_tt'], algorithm_input['exercise_start_tt'], algorithm_input['exercise_end_tt'], algorithm_input['user_info'])
        elif report_code == 'E001V1':
            return (report_code), (algorithm_input['report_start_tt'], algorithm_input['report_end_tt'], algorithm_input['user_info'])
        elif report_code == 'A002V2' or report_code == 'A002V3':
            return (report_code), (algorithm_input['report_start_tt'], algorithm_input['report_end_tt'], algorithm_input['user_info'])
        

    def transfer_timestamp(self, algorithm_input : dict, time_format : str):
        for key in algorithm_input.keys():
            if key.endswith('_tt'):
                algorithm_input[key] = datetime.fromtimestamp(algorithm_input[key]/1000).strftime(time_format)
        return algorithm_input

    def start_algorithm_part(self, report_code_and_algorithm_input, content):
        report_code = report_code_and_algorithm_input[0]
        algorithm_input = report_code_and_algorithm_input[1]
        user_info = algorithm_input[-1]
        application.mysql_manage.update_data_generate_status(ReportTable, content['primary_key'], 'in_algorithm')
        if report_code == 'S001V1':
            algorithm_result = choose_algorithm_type(report_code, content['zip_path'])(algorithm_input[0], algorithm_input[1], algorithm_input[2], algorithm_input[3], user_info)
        elif report_code == 'E001V1':
            algorithm_result = choose_algorithm_type(report_code, content['zip_path'])(algorithm_input[0], algorithm_input[1], user_info)
        elif report_code == 'A002V2' or report_code == 'A002V3':
            history_list = application.mongodb_manage.query_data_id(user_info['id'])
            # algorithm_result = choose_algorithm_type(report_code, content['zip_path'])(algorithm_input[0], algorithm_input[1], user_info)
            algorithm_result = choose_algorithm_type(report_code, content['zip_path'])(algorithm_input[0], algorithm_input[1], user_info, report_code, history_list)
            if algorithm_result['status'] is True:
                history_result = {"history" : algorithm_result['record'][0]}
                history_result["history"]['score'] = int(history_result["history"]['score'])
                history_result['id'] = user_info['id']
                application.mongodb_manage.create_data(history_result)
        application.mysql_manage.update_generate_result_message(algorithm_result, ReportTable, content['primary_key'])
        application.mysql_manage.update_data_generate_status(ReportTable, content['primary_key'], 'in_algorithm_done')
        return algorithm_result, report_code, user_info

    def start_generate_pdf_part(self, content : dict, json_output_path : str, report_code : str, user_info : dict):
        self.filename = '{0}_{1:05d}_{2}.pdf'.format(report_code, int(user_info['id']), str(int(time.time())))
        application.mysql_manage.update_data_generate_status(ReportTable, content['primary_key'], 'in_generate_pdf')
        logger_message('json_output_path: {}'.format(json_output_path))
        print('json_output_path: {}'.format(json_output_path))
        logger_message('Start {} PDF'.format(report_code))
        print('Start {} PDF'.format(report_code))
        
        with open(json_output_path, 'r', encoding='utf-8') as f:
            report_json_string = f.read()
        report_json = json.loads(json.dumps(eval(report_json_string)))
        generate_pdf_version_instanse = fake_choose_generate_pdf_version(report_code)
        if report_code == 'S001V1':
            generate_pdf_version_instanse.genReport(report_json, self.filename, '')
            application.mysql_manage.update_generate_pdf_path(os.path.join(PDF_S001V1_PATH, self.filename), ReportTable, content['primary_key'])
        elif report_code == 'E001V1':
            self.temp_png_path = os.path.join(E001V1_FILES_PATH, str(user_info['id']))
            if not os.path.exists(self.temp_png_path):
                os.mkdir(self.temp_png_path)
            generate_pdf_version_instanse.genReport(report_json, self.filename, self.temp_png_path)
            application.mysql_manage.update_generate_pdf_path(os.path.join(PDF_E001V1_PATH, self.filename), ReportTable, content['primary_key'])

        elif report_code == 'A002V2':
            generate_pdf_version_instanse.genReport(report_json, self.filename)
            application.mysql_manage.update_generate_pdf_path(os.path.join(PDF_A002V2_PATH, self.filename), ReportTable, content['primary_key'])
        elif report_code == 'A002V3':
            generate_pdf_version_instanse.genReport(report_json, self.filename)
            application.mysql_manage.update_generate_pdf_path(os.path.join(PDF_A002V3_PATH, self.filename), ReportTable, content['primary_key'])

        application.mysql_manage.update_data_generate_status(ReportTable, content['primary_key'], 'in_generate_pdf_done')
        print('End {} PDF.'.format(report_code))
        logger_message('End {} PDF.'.format(report_code))

    def check_file_endswith(self, file : str, kind : str) -> bool:
            return file.endswith(kind)

    def explode_zip_file(self, file_list : list, zip_path : str):
        for file in file_list:
            with zipfile.ZipFile(file, 'r') as zf:
                for name in zf.namelist():
                    zf.extract(name, path = zip_path)

    def report_generate_progress_reset(self):
        self.report_generate_progress = {
            "in_create" : {"flag" : 1, "time":int(time.time())},
            "in_create_done" : {"flag" : 0, "time":None},
            "in_send" : {"flag" : 0, "time":None},
            "in_send_done" : {"flag" : 0, "time":None},
            "in_algorithm" : {"flag" : 0, "time":None},
            "in_algorithm_done" : {"flag" : 0, "time":None},
            "in_generate_pdf" : {"flag" : 0, "time":None},
            "in_generate_pdf_done" : {"flag" : 0, "time":None}
        }

    def query_generate_status(self, primary_key : str) -> dict:
        generate_status = application.mysql_manage.query_data_generate_status(ReportTable, primary_key)
        result_message = application.mysql_manage.query_data_result_message(ReportTable, primary_key)
        if not result_message:
            if generate_status["in_algorithm"]["flag"] == 0:
                return {"error_message" : "algorithm didn't start"}, 403
            if generate_status["in_algorithm"]["flag"] == 1 and generate_status["in_algorithm_done"]["flag"] == 0:
                return {"error_message" : "algorithm running"}, 403
            return {"error_message" : "algorithm didn't have result"}, 403
        if not result_message['status']:
            return {"error_message" : result_message["message"]}, 405
        return {'time_record':generate_status, 'result_message':result_message}


    def query_pdf_path(self, primary_key : str) -> dict:
        return application.mysql_manage.query_data_pdf_path(ReportTable, primary_key)

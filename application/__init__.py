
from .contorller import main as application_root
from application.mysql_.model import UserTable, FileTable, ReportTable, TokenPermissionTable
import time, threading, json, os
from flask import Flask
from application.setting import q, FOLDER_CONTROLLER_LIST
from flasgger import Swagger
from application.queue_.manage import multithread_run
from config_controller import config_map
from application.setting import LOG_PATH
import logging
from application.logger.model import Logger
from application.health_server_request.model import HealthServerRequestAction

def check_folder_path():
    for path in FOLDER_CONTROLLER_LIST:
        if not os.path.exists(path):
            os.mkdir(path)

def make_fake_data_for_unit_test(mode):
    if mode == 'test':
        health_server_request = HealthServerRequestAction()
        data = {
            "token" : "711565b38b1c85510998e256e74b7cc73d558b7cbe77ad52ba0f1b3da276a597",
            "server_name" : "KoshouDevelop",
            "create_time" : int(time.time()),
            "permission" : "normal"
        }
        mysql_manage.create_data(data, TokenPermissionTable, 1)
        data = { "report_code" : "S001V1", "user_id" : 7, "health_server_got_generate_request_time": 1660094681353, "health_server_post_create_time": 1664265075021, "user_info": { "id": "7", "name": "koshou", "email": "koshou@singularwings.com", "gender": "男", "height": "176", "weight": "90", "birthday": "1996/10/10", "age": "25" }, "algorithm_input": { "step_test_start_tt" : 1662111836963, "step_test_end_tt" : 1662112234177, "exercise_start_tt" : 1662112291507, "exercise_end_tt" : 1662114091512, "user_info": { "id": "7", "name": "koshou", "email": "koshou@singularwings.com", "gender": "男", "height": "176", "weight": "90", "birthday": "1996/10/10", "age": "25" } } }
        data['report_server_got_post_create_time'] = int(time.time())
        data['generate_status'] = health_server_request.report_generate_progress
        current_record_id = mysql_manage.create_data(data, ReportTable)
        result_message = {"status": True, "message": "C:\\projects\\ReportGeneratorServer\\utility\\algorithms\\report\\ExerciseReportOutput\\7\\20221004\\Report_2022100411(7).json"}
        mysql_manage.update_generate_result_message(result_message, ReportTable, 1)
        current_record_id = mysql_manage.create_data(data, ReportTable)
        current_record_id = mysql_manage.create_data(data, ReportTable)
        result_message = {"record": [], "status": False, "message": "The Number of the Day is Not Enough"}
        mysql_manage.update_generate_result_message(result_message, ReportTable, 3)

def create_app(mode : str):
    check_folder_path()
    global logger_con
    logger_con = Logger().logger

    config_instance = config_map[mode]()
    global mysql_manage
    mysql_manage = config_instance.mysql_connect()
    global mongodb_manage
    mongodb_manage = config_instance.mongo_connect()
    # global report_server_token
    # report_server_token = config_instance.get_report_server_token()
    make_fake_data_for_unit_test(mode)
    app = Flask(__name__)
    app.config['SWAGGER'] = {
    "title": "Report Server",
    "description": "Report Server API Doc",
    "version": "0.0.0",
    "termsOfService": "",
    "hide_top_bar": True
    }
    swagger = Swagger(app)

    

    from .contorller import main
    app.register_blueprint(main)

    from .health_server_request import health_server_request
    app.register_blueprint(health_server_request)
    

    return app

from .contorller import main as application_root

import time, threading, json, os
from flask import Flask
from application.setting import q, FOLDER_CONTROLLER_LIST
from flasgger import Swagger
from application.queue_.manage import multithread_run
from config_controller import config_map
from application.setting import LOG_PATH
import logging
from application.logger.model import Logger


def check_folder_path():
    for path in FOLDER_CONTROLLER_LIST:
        if not os.path.exists(path):
            os.mkdir(path)





def create_app(mode : str):
    check_folder_path()
    global logger_con
    logger_con = Logger().logger

    config_instance = config_map[mode]()
    global mysql_manage
    mysql_manage = config_instance.mysql_connect()
    # global seven_days_history_collection
    # seven_days_history_collection = config_instance.mongo_connect()
    # global report_server_token
    # report_server_token = config_instance.get_report_server_token()


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
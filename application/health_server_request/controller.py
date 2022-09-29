import time, os, io
import  application 
from flask import Blueprint, request, send_file
from .model import HealthServerRequestAction
from application.setting import q, ZIP_FILE_PATH_HEALTH_SERVER
from application.mysql_.model import UserTable, FileTable, ReportTable
from application.token.verify_token import verify_report_server_token
from application.logger.model import logger_message

main = Blueprint('health_server_request', __name__)


health_server_request = HealthServerRequestAction()


@main.route('/', methods=['GET'])
def index():
    return 'server test '


@main.route('/report/generate/create', methods=['POST'])
@verify_report_server_token
def report_generate_create():
    try:
        health_server_request.report_generate_progress_reset()
        data = request.get_json()
        check_result, message = health_server_request.check_data_completed(data, 'create')
        if check_result:
            data['report_server_got_post_create_time'] = int(time.time())
            data['generate_status'] = health_server_request.report_generate_progress
            user_table_data = {'time':data['report_server_got_post_create_time'], 'report_code':data['report_code'], 'user_id':data['user_id'], 'user_info':data['user_info']}
            application.mysql_manage.create_data(user_table_data, UserTable)
            current_record_id = application.mysql_manage.create_data(data, ReportTable)
            application.mysql_manage.update_data_generate_status(ReportTable, current_record_id, 'in_create_done')
            logger_message({'sucess_message':{'report_table_index' : current_record_id}})
            return {"sucess_message":{"report_table_index" : current_record_id}}
        else:
            logger_message(({'error_message' : message}, 402))
            return {"error_message" : message}, 402
    except Exception as e:
        logger_message('Exception ---> {}'.format(str(e)))
        return {"error_message" : str(e)}, 505


@main.route('/report/generate/send', methods=['POST'])
@verify_report_server_token
def report_generate_send():
    try:
        if len(request.files) != 1:
            logger_message(({"error_message" : "post too many files at once"}, 402))
            return {"error_message" : "post too many files at once"}, 402
        if not health_server_request.check_file_endswith(request.files['zip_file'].filename, '.zip'):
            logger_message(({"error_message" : "data is not zip file"}, 402))
            return {"error_message" : "data is not zip file"}, 402
        if health_server_request.check_qsize_fulled():
            logger_message(({"error_message" : "Queue is fulled"}, 403))
            return {"error_message" : "Queue is fulled"}, 403
        check_result, message = health_server_request.check_data_completed(request.form, 'send')
        report_table_index = request.form['report_table_index']
        report_table_index_created = application.mysql_manage.query_data_primary_key(ReportTable, report_table_index)
        if not report_table_index_created:
            logger_message(({"error_message" : "have a didn't create report_table_index"}, 405))
            return {"error_message" : "have a didn't create report_table_index"}, 405
        if check_result:
            application.mysql_manage.update_data_generate_status(ReportTable, report_table_index, 'in_send')
            zip_path = os.path.join(ZIP_FILE_PATH_HEALTH_SERVER, 'report_table_index_{}'.format(report_table_index))
            health_server_request.make_dir(zip_path)
            request.files['zip_file'].save(os.path.join(zip_path, request.files['zip_file'].filename))
            file_table_data = {
                'report_table_index' : report_table_index,
                'zip_path' : zip_path,
                'zip_filename' : request.files['zip_file'].filename
            }
            application.mysql_manage.create_data(file_table_data, FileTable)
            if request.form['end_flag'] == "True":
                all_file_list = application.mysql_manage.query_data_same_rtb_zf(FileTable, report_table_index)
                health_server_request.explode_zip_file(all_file_list, zip_path)
                # q.put("health_server_request")
                q.put({"request_type" : "health_server_request","table" : ReportTable, "primary_key" : report_table_index, "zip_path" : zip_path})
                print('q size : {}'.format(q.qsize()))
            application.mysql_manage.update_data_generate_status(ReportTable, report_table_index, 'in_send_done')
            logger_message({"sucess_message": {"result" : True}})
            return {"sucess_message": {"result" : True}}
        else:
            logger_message(({'error_message' : message}, 402))
            return {"error_message" : message}, 402
    except Exception as e:
        logger_message('Exception ---> {}'.format(str(e)))
        return {"error_message" : str(e)}, 505

@main.route('/report/generate/query/<report_table_index>', methods=['GET'])
@verify_report_server_token
def report_generate_query(report_table_index):
    try:
        report_table_index_created = application.mysql_manage.query_data_primary_key(ReportTable, report_table_index)
        if not report_table_index_created:
            logger_message(({"error_message" : "have a didn't create report_table_index"}, 402))
            return {"error_message" : "have a didn't create report_table_index"}, 402
        logger_message((health_server_request.query_generate_status(report_table_index)))
        return health_server_request.query_generate_status(report_table_index)
    except Exception as e:
        logger_message('Exception ---> {}'.format(str(e)))
        return {"error_message" : str(e)}, 505

@main.route('/report/generate/pdf/<report_table_index>', methods=['GET'])
@verify_report_server_token
def report_generate_pdf(report_table_index):
    try:
        report_table_index_created = application.mysql_manage.query_data_primary_key(ReportTable, report_table_index)
        if not report_table_index_created:
            logger_message(({"error_message" : "have a didn't create report_table_index"}, 402))
            return {"error_message" : "have a didn't create report_table_index"}, 402
        if not health_server_request.query_pdf_path(report_table_index):
            logger_message(({"error_message" : "pdf file was not done"}, 403))
            return {"error_message" : "pdf file was not done"}, 403
        with open(health_server_request.query_pdf_path(report_table_index), 'rb') as bites:
            return send_file(io.BytesIO(bites.read()),mimetype='pdf')
    except Exception as e:
        logger_message('Exception ---> {}'.format(str(e)))
        return {"error_message" : str(e)}, 505
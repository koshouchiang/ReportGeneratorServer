import time
import application
from application.setting import q
from application.health_server_request.controller import health_server_request
from application.mysql_.model import UserTable, FileTable, ReportTable
from time import localtime, strftime
from application.logger.model import logger_message
import traceback, sys

'''
refactory Queue get and put time and method, while end_flag = true, not result and status not run algorithm -> put in queue 
'''

def multithread_run():
    print('in multithread_run')
    while True:
        try:
            if q.empty():
                print('[{}] queue is empty'.format(strftime("%Y/%m/%d %H:%M:%S", localtime())))
                search_end_flag_and_not_in_queue()
            else:
                if not health_server_request.report_generating:
                    msg=q.get()
                    application.mysql_manage.update_in_queue(True, ReportTable, msg['primary_key'])
                    print('get {}, qsize: {}'.format( msg, str(q.qsize())))
                    application.contorller.start_process(msg)
        except Exception as e:
            cl, exc, tb = sys.exc_info()
            for line in traceback.extract_tb(tb):
                logger_message('Exception ---> {}'.format(str(line)))
            logger_message('Exception ---> {}'.format(str(e)))
            except_data = {"status": False, "message": "have exception please check log"}
            application.mysql_manage.update_generate_result_message(except_data, ReportTable, msg['primary_key'])
            health_server_request.report_generating = False
        time.sleep(1)

def search_end_flag_and_not_in_queue():
    result, report_table_index_list = application.mysql_manage.query_data_end_flag_and_in_queue(ReportTable, True, False)
    if result:
        # print(report_table_index_list)
        for report_table_index in report_table_index_list:
            zip_path = application.mysql_manage.query_data_zip_path(FileTable, report_table_index)
            all_file_list = application.mysql_manage.query_data_same_rtb_zf(FileTable, report_table_index)
            health_server_request.explode_zip_file(all_file_list, zip_path)
            q.put({"request_type" : "health_server_request","table" : ReportTable, "primary_key" : report_table_index, "zip_path" : zip_path})
            print('q size : {}'.format(q.qsize()))


def reset_in_queue():
    '''
    if server die or unelectron, need to reset, cause maybe somethings in queue, but not run algorithm 
    query report table check end_flag = True, not result, status not run algorithm and in_queue = True
    reset all in queue to false
    '''
    application.mysql_manage.query_data_end_flag(ReportTable, True)
    application.mysql_manage.update_in_queue(True, ReportTable, 3)
    pass



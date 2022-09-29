import time
import application
from application.setting import q, stop_flag
from application.health_server_request.controller import health_server_request
from application.mysql_.model import UserTable, FileTable, ReportTable
from time import localtime, strftime

def multithread_run():
    print('in multithread_run')
    while not stop_flag:
        if q.empty():
            print('[{}] queue is empty'.format(strftime("%Y/%m/%d %H:%M:%S", localtime())))
            pass
        else:
            if not health_server_request.report_generating:
                msg=q.get()
                print('get {}, qsize: {}'.format( msg, str(q.qsize())))
                application.contorller.start_process(msg)

        time.sleep(1)
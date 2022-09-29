import logging
import os
from logging import handlers
import application



class Logger(object):
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    def __init__(self,
                 filename = './log/report_server_log.txt',
                 level='debug',
                 when='H',
                 back_count=0,
                 fmt='[%(asctime)s %(levelname)-3s] %(message)s'):


        self.logger = logging.getLogger()
        format_str = logging.Formatter(fmt)  
        self.logger.setLevel(self.level_relations.get(level))  
        console_handler = logging.StreamHandler()  
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(format_str)  

        timer_handler = handlers.TimedRotatingFileHandler(filename=filename, when=when, backupCount=back_count, encoding='utf-8') 
        timer_handler.suffix = "%Y_%m_%d_%H.txt"
        timer_handler.setFormatter(format_str)  
        self.logger.addHandler(console_handler)  
        self.logger.addHandler(timer_handler)


def logger_message(connect):
    application.logger_con.debug(connect)


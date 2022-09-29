from flask import request
from application.mysql_.model import TokenPermissionTable
from application.logger.model import logger_message
import application

def verify_report_server_token(func):
    def wrapper(*args, **kwargs):
        try:
            token_type, access_token = request.headers.get('Authorization').split(' ')
        except:
            logger_message(({'error':'please verify token'}, 401))
            return {'error':'please verify token'}, 401
        res = application.mysql_manage.query_data_token(TokenPermissionTable, str(access_token))
        if token_type!= 'Bearer':
            logger_message(({'error':'token type error'}, 401))
            return {'error':'token type error'}, 401
        if not res:
            logger_message(({'error':'access token error'}, 401))
            return {'error':'access token error'}, 401
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


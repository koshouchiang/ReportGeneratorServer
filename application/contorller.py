from flask import Blueprint

main = Blueprint('main', __name__)

from application.health_server_request.controller import health_server_request

REQUEST_INSTANCE_MAP = {
    'health_server_request' : health_server_request
}
def start_process(content : dict):
    '''
    Interface of after queue get content, start algorithm and then generate pdf
    '''
    
    REQUEST_INSTANCE_MAP[content['request_type']].start_process_entrance(content)
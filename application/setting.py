import queue, os

global stop_flag
stop_flag = False
QUEUE_SIZE = 10
global q
q = queue.Queue(QUEUE_SIZE)



LOG_PATH = os.path.join(os.getcwd(), 'log')
ZIP_FILE = os.path.join(os.getcwd(), 'zip_file')
ZIP_FILE_PATH_HEALTH_SERVER = os.path.join(os.getcwd(), 'zip_file', 'health_server')
USER_PDF_PATH = os.path.join(os.getcwd(), 'user_pdf')
E001V1_FILES_PATH = os.path.join(os.getcwd(), 'user_pdf', 'E001V1Files')
PDF_A002V2_PATH = os.path.join(USER_PDF_PATH, 'A002V2')
PDF_A002V3_PATH = os.path.join(USER_PDF_PATH, 'A002V3')
PDF_S001V1_PATH = os.path.join(USER_PDF_PATH, 'S001V1')
PDF_E001V1_PATH = os.path.join(USER_PDF_PATH, 'E001V1')

FOLDER_CONTROLLER_LIST = [LOG_PATH, ZIP_FILE, ZIP_FILE_PATH_HEALTH_SERVER, USER_PDF_PATH, E001V1_FILES_PATH, PDF_A002V2_PATH, PDF_A002V3_PATH, PDF_S001V1_PATH, PDF_E001V1_PATH]
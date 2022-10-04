from application import create_app, multithread_run
from swagger_ui import api_doc
from flask_cors import CORS
import threading

app = create_app('develop')
CORS(app)

api_doc(app, config_path='swagger_config.json', url_prefix='/api/doc', title='API doc')

if __name__ == '__main__':
    # multithread 
    multithread_process = threading.Thread(target=multithread_run)
    multithread_process.start()
    app.run(host = '0.0.0.0')
import json
import pymongo
from application.mysql_.model import MySQLAction


class ConfigMaster:
    def __init__(self):
        self.mode_name = 'master'
        self.engine_url = 'mysql+pymysql://{}:{}@{}:{}/{}'.format('koshou', 'f9440127', '192.168.1.187', '3306', 'report_server_test')

    def mysql_connect(self):
        mysql_manage = MySQLAction(engine_url = self.engine_url)
        mysql_manage.create_table()
        return mysql_manage

    def mongo_connect(self):
        engine_url = 'mongodb://{}:{}/'.format('localhost', '27017')
        mongo_client = pymongo.MongoClient(engine_url)
        algorithm_db = mongo_client['algorithm_db']
        seven_days_history_collection = algorithm_db['seven_days_history']
        return seven_days_history_collection

class ConfigTest(ConfigMaster):
    def __init__(self):
        super(ConfigTest,self).__init__()   
        self.mode_name = 'test' 
        self.engine_url = 'mysql+pymysql://{}:{}@{}:{}/{}'.format('test_user', 'tester', 'localhost', '8080', 'test')


class ConfigDevelop(ConfigMaster):
    def __init__(self):
        super(ConfigDevelop,self).__init__()   
        self.mode_name = 'develop' 
        with open('mysql_config.json') as f:
            content = json.load(f)
        self.engine_url = 'mysql+pymysql://{}:{}@{}:{}/{}'.format(content[self.mode_name]['name'], content[self.mode_name]['password'], content[self.mode_name]['host'], content[self.mode_name]['post'], content[self.mode_name]['schema'])




class ConfigRelease(ConfigDevelop):
    def __init__(self):
        super(ConfigRelease,self).__init__()    
        self.mode_name = 'release' 




config_map = {
    'master' : ConfigMaster,
    'test':ConfigTest,
    'develop' : ConfigDevelop,
    'release' : ConfigRelease
}


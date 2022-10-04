import json
import pymongo
from application.mysql_.model import MySQLAction
from application.mongodb_.model import MongodbAction

class ConfigMaster:
    def __init__(self):
        self.mode_name = 'master'
        self.db_name = 'report_server_test'
        self.mysql_engine_url = 'mysql+pymysql://{}:{}@{}:{}/{}'.format('koshou', 'f9440127', '192.168.1.187', '3306', self.db_name )
        self.mongodb_engine_url = 'mongodb://{}:{}@{}:{}/?authMechanism=DEFAULT'.format('koshou', 'f9440127', '192.168.1.187', '27017')

    def mysql_connect(self):
        mysql_manage = MySQLAction(engine_url = self.mysql_engine_url)
        mysql_manage.create_table()
        return mysql_manage

    def mongo_connect(self):
        mongodb_manage = MongodbAction(engine_url = self.mongodb_engine_url, db = self.db_name, collection = 'seven_days_history')
        # mongodb_manage = mongodb_intance.connect()
        # mongodb_manage.connect()
        return mongodb_manage

class ConfigTest(ConfigMaster):
    def __init__(self):
        super(ConfigTest,self).__init__()   
        self.mode_name = 'test' 
        self.db_name = 'supercharge'
        self.mysql_engine_url = 'mysql+pymysql://{}:{}@{}:{}/{}'.format('test_user', 'tester', 'localhost', '8080', 'test')
        self.mongodb_engine_url = 'mongodb://{}:{}@{}:{}/?authMechanism=DEFAULT'.format('supercharge', 'secret', 'localhost', '27017')

class ConfigDevelop(ConfigMaster):
    def __init__(self):
        super(ConfigDevelop,self).__init__()   
        self.mode_name = 'develop' 
        self.db_name = 'report_server_develop'
        with open('mysql_config.json') as f:
            content = json.load(f)
<<<<<<< HEAD
        self.engine_url = 'mysql+pymysql://{}:{}@{}:{}/{}'.format(content[self.mode_name]['name'], content[self.mode_name]['password'], 'localhost', content[self.mode_name]['post'], content[self.mode_name]['schema'])


=======
        self.mysql_engine_url = 'mysql+pymysql://{}:{}@{}:{}/{}'.format(content[self.mode_name]['name'], content[self.mode_name]['password'], content[self.mode_name]['host'], content[self.mode_name]['post'], content[self.mode_name]['algorithm_db'])
        with open('mongo_config.json') as f:
            content = json.load(f)
        self.mongodb_engine_url = 'mongodb://{}:{}@{}:{}/?authMechanism=DEFAULT'.format(content[self.mode_name]['name'], content[self.mode_name]['password'], content[self.mode_name]['host'], content[self.mode_name]['post'])
>>>>>>> 87c31eb4e9f939a466736dfe11ed92e444b13083


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


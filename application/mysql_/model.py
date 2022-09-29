from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column
from sqlalchemy import Integer, String, DATETIME, TEXT, JSON, BigInteger
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from sqlalchemy import update
import json, time, os


base = declarative_base()

class TokenPermissionTable(base):
    __tablename__ = "token_permission"
    token = Column(String(255), primary_key=True)
    server_name = Column(String(55))
    create_time = Column(Integer)
    permission = Column(String(55))


class UserTable(base):
    __tablename__ = "user"
    record_id = Column(Integer, primary_key=True)
    time = Column(BigInteger)
    report_code = Column(String(55))
    user_id = Column(Integer)
    user_info = Column(JSON)

class FileTable(base):
    __tablename__ = "file"
    record_id = Column(Integer, primary_key=True, autoincrement=True)
    report_table_index = Column(Integer)
    zip_path = Column(String(255))
    zip_filename = Column(String(55))

class ReportTable(base):
    __tablename__ = "report"
    record_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    user_info = Column(JSON)
    health_server_got_generate_request_time = Column(BigInteger)
    health_server_post_create_time = Column(BigInteger)
    report_server_got_post_create_time = Column(BigInteger)
    algorithm_input = Column(JSON)
    report_code = Column(String(55))
    generate_status = Column(JSON)
    result_message = Column(JSON)
    pdf_path = Column(String(255))



class MySQLAction:
    def __init__(self, engine_url:str):
        self.connect(engine_url)

    def connect(self, engine_url):
        self.engine = create_engine(engine_url, echo=False)

    def create_table(self):
        base.metadata.create_all(self.engine)


    def drop_table(self):
        base.metadata.drop_all(self.engine)

    def create_session(self):
        Session = sessionmaker(bind=self.engine)
        session = Session()
        return session

    def create_data(self, data, table, mode = 0):
        session = self.create_session()
        session.add(table(**data))
        session.flush()
        if mode == 0:
            for i in session.query(table.record_id):
                current_record_id = i.record_id
            session.commit()
            session.close()
            return current_record_id
        else:
            session.commit()
            session.close()

    def query_data_token(self, table, token):
        session = self.create_session()
        query_result = session.query(table).filter_by(token = token).all()
        if query_result == []:
            return False
        for i in query_result:
            res = i.token == token
        session.commit()
        session.close()
        return res

    def query_data_primary_key(self, table, primary_key):
        session = self.create_session()
        query_result = session.query(table).get(primary_key)
        session.commit()
        session.close()
        return query_result


    def query_data_same_rtb_zf(self, table, report_table_index):
        '''
        get zip filename which are same report table index
        '''

        all_file_list = []
        session = self.create_session()
        res = session.query(table).filter_by(report_table_index = report_table_index).all()
        for i in res:
            all_file_list.append(os.path.join(i.zip_path, i.zip_filename))
        session.commit()
        session.close()
        return all_file_list

    def query_data_algorithm_input(self, content : dict) -> tuple:
        session = self.create_session()
        query_result = session.query(content['table']).get(content['primary_key'])
        algorithm_input = query_result.algorithm_input
        report_code = query_result.report_code
        session.commit()
        session.close()
        return algorithm_input, report_code

    def query_data_generate_status(self, table, primary_key):
        session = self.create_session()
        query_result = session.query(table).get(primary_key).generate_status
        session.commit()
        session.close()
        return query_result

    def query_data_result_message(self, table, primary_key):
        session = self.create_session()
        query_result = session.query(table).get(primary_key).result_message
        session.commit()
        session.close()
        return query_result

    def query_data_pdf_path(self, table, primary_key):
        session = self.create_session()
        query_result = session.query(table).get(primary_key).pdf_path
        session.commit()
        session.close()
        return query_result

    def update_data_generate_status(self, table, primary_key, status):
        target_flag_key = '$.{}.{}'.format(status,'flag')
        target_flag_time = '$.{}.{}'.format(status,'time')
        session = self.create_session()
        session.query(table).filter_by(record_id=primary_key).update({table.generate_status: func.json_set(table.generate_status, target_flag_key, True)})
        session.query(table).filter_by(record_id=primary_key).update({table.generate_status: func.json_set(table.generate_status, target_flag_time, int(time.time()))})

        session.commit()
        session.close()

    def update_generate_result_message(self, data, table, primary_key):
        session = self.create_session()
        session.query(table).filter_by(record_id=primary_key).update({table.result_message: data})
        session.commit()
        session.close()

    def update_generate_pdf_path(self, data, table, primary_key):
        session = self.create_session()
        session.query(table).filter_by(record_id=primary_key).update({table.pdf_path: data})
        session.commit()
        session.close()
    # def update_generate_status_data(self, status, table, primary_key):
    #     target_flag_key = '$.{}.{}'.format(status,'flag')
    #     target_flag_time = '$.{}.{}'.format(status,'time')
    #     session = self.create_session()
    #     session.query(table).filter_by(record_id=primary_key).update({table.generate_status: func.json_set(table.generate_status, target_flag_key, True)})
    #     session.query(table).filter_by(record_id=primary_key).update({table.generate_status: func.json_set(table.generate_status, target_flag_time, int(time.time()))})

    #     session.commit()
    #     session.close()






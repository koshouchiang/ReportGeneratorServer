import pymongo

class MongodbAction:
    def __init__(self, engine_url:str, db : str, collection : str):
        self.engine_url = engine_url
        self.db = db
        self.collection = collection
        self.connect()

    def connect(self):
        self.mongo_client = pymongo.MongoClient(self.engine_url)
        # algorithm_db = mongo_client[self.db]
        # seven_days_history_collection = algorithm_db[self.collection]
        # return seven_days_history_collection


    def create_data(self, data : dict):
        algorithm_db = self.mongo_client[self.db]
        seven_days_history_collection = algorithm_db[self.collection]
        return seven_days_history_collection.insert_one(data)
         
    
    def query_data_id(self, user_id : str):
        history_list = []
        algorithm_db = self.mongo_client[self.db]
        seven_days_history_collection = algorithm_db[self.collection]
        myquery = {"id" : str(user_id)}
        mydoc = seven_days_history_collection.find(myquery).sort("history.date", -1)
        for x in mydoc:
            history_list.append(x['history'])
        return history_list 
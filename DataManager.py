from pymongo import MongoClient
from datetime import datetime


class DBcall(object):
    SECRET_KEY = 'devil in the sky'
    DATABASE = MongoClient()['sci-web']

    def __init__(self, collection, pid):
        """
        infile (list): lines from file
        fields (dict): the columns of the CSV file to load like {num : name}
        """
        self.client = self.DATABASE[collection]
        self.pid = pid
        # self.grid = gridfs.GridFS(MongoClient()['sci-web'])

    def loadData(self, data):
        for doc in data:
            try:
                self.client.insert_one(doc)
            except Exception, e:
                action = "Load to DB failed: " + str(e)
                putLog(action, self.pid, "DB load", "exception")
        # self.client.insert_many(data)

    def updateData(self, keys, values):
        try:
            self.client.update_one(keys, {'$set': values})
        except Exception, e:
            action = "Update DB record failed: " + str(e)
            putLog(action, self.pid, "DB record update", "exception")

    def updateDatapull(self, keys, values):
        try:
            self.client.update_one(keys, {'$addToSet': values})
        except Exception, e:
            action = "Update DB record failed: " + str(e)
            putLog(action, self.pid, "DB record update", "exception")

    def findData(self, keys):
        return self.client.find_one(keys)

    def Distinct(self, field, keys):
        return self.client.distinct(field, keys)

    def findDatalist(self, keys):
        return self.client.find(keys)

    def findDatalistSorted(self, keys, sort, d):
        return self.client.find(keys).sort(sort, d)

    def findDatalist_by_a_key(self, key, lst):
        return self.client.find({key: {'$in': lst}})

    def findDatalist_by_comp_keys(self, keys):
        return self.client.find({'$or': keys})


def putLog(action, pid, task, tp):
    logdata = {"time": datetime.now(), "pid": pid, "action": action, "task": task, "type": tp}
    DBcall("logs", pid).loadData([logdata])

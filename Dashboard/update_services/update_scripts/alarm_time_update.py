
from dateutil import parser
from pymongo import MongoClient
import datetime


MONGODB_HOST = 'mongodb://localhost'
MONGODB_PORT = 27017


url_mongo_fire_depart = "%s:%d/fire_department" % (MONGODB_HOST, MONGODB_PORT)
#print "--> url_mongo_fire_depart:", url_mongo_fire_depart

client = MongoClient(url_mongo_fire_depart)
db = client["fire_department"]["geo_incidents"]
items = db.find()

count = 1

for item in items:
     print(count)
     count += 1
     tempDateTime = item['alarmDateTime']
     try:
        
        if tempDateTime is not 'None': 
            #parsedDate = parser.parse(tempDateTime)

            parsedDate_2 = datetime.datetime.strptime(tempDateTime, '%Y,%m,%d,%H,%M,%S,%f')
            db.update_one({'_id': item['_id']}, {"$set": {"alarmDateTime": parsedDate_2}}, upsert=False)
     except TypeError:
        continue
     except ValueError as e: 
         print('\t' + str(e))
         print('\t' + tempDateTime)
         continue

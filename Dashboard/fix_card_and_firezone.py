#!/opt/rh/rh-python36/root/usr/bin/python3

import os, sys
from stat import *
import pymongo
import xml.etree.ElementTree as ET
import datetime
import re
import json
from darksky import forecast
from datetime import datetime as dt
from dateutil import parser
import time 
import configparser

CONFIG_FILE = "/home/vol-gpettet/analytics-dashboard/update_services/ingest_config.cfg"

config = configparser.ConfigParser()
config.read(CONFIG_FILE)

client = pymongo.MongoClient()
db = client[str(config['INGEST']['db'])]
col_inc = db[str(config['INGEST']['collection'])]

counter = 0

def process_file(filename):
    xml = ET.parse(filename)
    root = xml.getroot()
    
    # process each entry in file
    for event in root.findall('Table'):

        try: 
        
            incident_number = event.find('event_number')
            if incident_number is not None:
                incident_number = incident_number.text

            emdCardNumber = event.find('incident_type_id')
            if emdCardNumber is not None:
                emdCardNumber = emdCardNumber.text

            fireZone = event.find('Beatname')
            if fireZone is not None:
                fireZone = fireZone.text

            en_db_entry = col_inc.find_one({'incidentNumber': str(incident_number)})

            en_db_entry['emdCardNumber'] = str(emdCardNumber)
            en_db_entry['fireZone'] = str(fireZone)
            
            test_res = col_inc.replace_one({'incidentNumber': str(incident_number)},en_db_entry)

            #print(test_res)
            #print(test_res.acknowledged)
            #print(test_res.matched_count, test_res.modified_count, test_res.raw_result)
            #exit(1)
        except TypeError as e: 
            continue
        

def walktree(top, callback):
    '''recursively descend the directory tree rooted at top,
       calling the callback function for each regular file'''

    for f in os.listdir(top):
        pathname = os.path.join(top, f)
        mode = os.stat(pathname)[ST_MODE]
        if S_ISDIR(mode):
            # It's a directory, recurse into it
            #walktree(pathname, callback)
            pass
        elif S_ISREG(mode):
            # It's a file, call the callback function
            callback(pathname)
        else:
            # Unknown file type, print a message
            print('Skipping %s' % pathname)

def visitfile(file):

    ### psudo code

    process_file(file)

    

    # TODO move to processed
    # file_base_name = os.path.basename(file)
    # print(file_base_name) 
    #os.rename(file, '/mnt/processed/' + file_base_name)
    
    #exit(1)

    global counter
    counter += 1
    print(counter)
    print('---------------------------')

if __name__ == '__main__':
    
    #raise Exception('testing exeception')

    #visitfile('/mnt/fff7e23b-fd0a-452a-9251-c4b4406d05cf.xml')
    #wait_time = int(config['INGEST']['wait_time'])
    #min_wait_time = int(config['INGEST']['min_wait_time'])
    #while True: 
    #    start_timer = time.time()
    walktree('/mnt/processed/', visitfile)
    #    eps_time = time.time() - start_timer
    #    if eps_time > wait_time - min_wait_time:
    #        time.sleep(min_wait_time)
    #    else:
    #        time.sleep(wait_time - eps_time)
    #visitfile('/mnt/fff7e23b-fd0a-452a-9251-c4b4406d05cf.xml')



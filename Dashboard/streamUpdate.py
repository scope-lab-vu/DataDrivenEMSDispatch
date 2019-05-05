import time
import os
from datetime import datetime
import ConfigParser
from myapp.views import utils

# import os,sys,inspect
# currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
# parentdir = os.path.dirname(currentdir)
# sys.path.insert(0,parentdir)



Config = ConfigParser.ConfigParser()
Config.read(os.getcwd()+"/update_services/streamUpdate.conf")

def ConfigSectionMap(Config, section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1

frequency = ConfigSectionMap(Config, "stream")["frequency"]
logPath = os.getcwd() + "/update_services/logs/streamUpdateLog.txt"

#get time to sleep from freq
timeToSleep = 24*3600/float(frequency)


with open(logPath,'w+') as f:
    f.write("Streaming Survival Update Service started at {} \n".format(str(datetime.now())))
    while(True):
        time.sleep(timeToSleep)
        try:
            utils.updateCategoryWiseDataStream()
        except AttributeError:
            f.write("Stream Update Failed at {} due to attribute error \n ".format(str(datetime.now())))

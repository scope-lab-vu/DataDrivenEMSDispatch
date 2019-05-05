import csv
import datetime
import pickle
import time
from copy import deepcopy
import os
from operator import itemgetter
from math import atan, sin, cos, copysign, sqrt
import random
import numpy as np
import bisect

import xlrd
from flask import render_template, request
from flask_socketio import emit
from pymongo import MongoClient

from myapp import app
from myapp import socketio
from myapp.utilities import utilities
from myconfig import MONGODB_HOST, MONGODB_PORT
from multiprocessing import Pool
from math import ceil


url_mongo_fire_depart = "%s:%d/fire_department" % (MONGODB_HOST, MONGODB_PORT)
print "--> url_mongo_fire_depart:", url_mongo_fire_depart


velocity = 2.5
getSign = lambda num: copysign(1, num)
utilDumpPath = os.getcwd() + "/utilsDump"

if os.path.isfile(utilDumpPath):
    with open(utilDumpPath, "rb") as input_file:
        utils = pickle.load(input_file)
        print "Loaded Utils"
else:
    utils = utilities()
    with open("utilsDump", "wb") as output_file:
            pickle.dump(utils, output_file)

depotDetails = utils.vehiclesInDepot


def checkIfDestinationExceeded(dest, curr, dir1, dir2):
    dir1Check = True if dir1 * (curr[0] - dest[0]) > 0 else False
    dir2Check = True if dir2 * (curr[1] - dest[1]) > 0 else False
    if dir2Check or dir1Check:
        return True
    else:
        return False

def getRouteUpdated(gridFrom, gridTo, velocity):
    route = []
    if gridFrom == gridTo:
        return [[gridTo, 0]]
    coord1 = utils.reverseCoordinates[gridFrom]
    coord2 = utils.reverseCoordinates[gridTo]
    slope = (coord1[1] - coord2[1]) / (coord1[0] - coord2[0])
    theta = atan(slope)
    xSign = getSign(coord2[0] - coord1[0])  # which direction are we changing x?
    ySign = getSign(coord2[1] - coord1[1])  # which direction are we changing y?
    v_x = xSign * abs(velocity * cos(theta) * 1609.34)
    v_y = ySign * abs(velocity * sin(theta) * 1609.34)
    xTemp = coord1[0]
    yTemp = coord1[1]

    if gridFrom == gridTo:
        return [gridTo, 0]
    reached = False
    while not reached:
        xTemp += v_x
        yTemp += v_y
        gridTemp = utils.getGridNumForCoordinate([xTemp, yTemp], utils.xLow, utils.yLow)
        if checkIfDestinationExceeded(coord2, [xTemp, yTemp], xSign, ySign):
            # update travel time or grid by adjusting for over travel
            dExtra = sqrt((xTemp - coord2[0]) ** 2 + (yTemp - coord2[1]) ** 2)
            tExtra = dExtra / (velocity * 1609.34 / 60)
            route.append([gridTo, 60 - tExtra])
            break
        else:
            # the vehicle has taken full 60 minutes to travel
            gridX = int(gridTemp[0])
            gridY = int(gridTemp[1])
            gridNumTemp = gridY * len(utils.grids) + gridX
            route.append([gridNumTemp, 60])

    # sanity check
    try:
        if route[-1][0] != gridTo:
            print "Error calculating route between grid {} and {}".format(gridFrom, gridTo)
    except IndexError:
        if route[-1][0] != gridTo:
            # print "Error calculating route between grid {} and {}".format(gridFrom, gridTo)
            raise Exception("Error calculating route between grid {} and {}".format(gridFrom, gridTo))

    return route

def updateResponder(t,responders):
    for responder in responders:
        responder.updateResponder(t)

def checkIfIncident():
    pass

def getTravelTime(grid1, grid2):
    # assume that it takes 1 minute to travel a mile. reasonable for emergency vehicles
    # return to and fro travel time
    try:
        coord1 = utils.reverseCoordinates[grid1]
        coord2 = utils.reverseCoordinates[grid2]
    except TypeError:
        raise Exception("Reverse Coordinate Error")
    except KeyError:
        return 0
    dist = (np.sqrt(
        (coord1[0] - coord2[0]) ** 2 + (coord1[1] - coord2[1]) ** 2)) / 1609.34  # convert meters to miles
    distMinutes = dist / velocity
    if distMinutes > 15:
        distMinutes = 15 #outlier data point for dashboard
    return distMinutes * 60  # convert to seconds and return

def dispatchResponder(responders,grid,t):
    bestDist = 1e10
    for responder in responders:
        distTemp = utils.dist(responder.currentPosition,grid)
        if distTemp < bestDist:
            bestDist = distTemp
            bestDispatch = responder.id

    depotDispatch = utils.gridAssignment[grid]
    for responder in responders:
        if responder.currentPosition == depotDispatch and responder.assignedDepot == depotDispatch and responder.statusFree == True:
            if utils.dist(depotDispatch,grid) < bestDist:
                bestDispatch = responder.id

    responders[bestDispatch].statusFree = False
    responders[bestDispatch].assignedRoute = getRouteUpdated(responders[bestDispatch].currentPosition,grid,velocity)
    travelTime = getTravelTime(responders[bestDispatch].currentPosition,grid)
    responders[bestDispatch].nextTime = t + travelTime + 15*60
    responders[bestDispatch].currentPosition = grid #this is not true, but this will never be checked for a busy responder. So it does not matter
    return travelTime, t + travelTime + 15*60

def pickIncidentChain():
    fileName = random.choice(os.listdir(os.getcwd() + "/myapp/data/incidentChain"))
    fileName = os.getcwd() + "/myapp/data/incidentChain/" + fileName
    with open(fileName, 'rb') as f:
        incidentChain = pickle.load(f)
    #create incident chain by seconds:

    return incidentChain

def simulate(responders):
    timeToSimulate = 10 * 24 * 3600
    incidents = utils.times[0:1200]
    incidents = sorted(incidents,key=itemgetter(0))
    incidentTimes = [x[0] for x in incidents]
    totalWaitTime = 0
    incidentsCounter = 0
    timesToCheck = deepcopy(incidentTimes)

    for t in timesToCheck:
        if t>timeToSimulate:
            break
        incidentGrid = -1
        if t in incidentTimes:
            try:
                incidentGrid = incidents[incidentsCounter][1]
                incidentsCounter += 1
            except IndexError:
                break
        updateResponder(t,responders)
        if incidentGrid != -1:
            travelTime, nextTime = dispatchResponder(responders,incidentGrid,t)
            bisect.insort(timesToCheck,nextTime)
            totalWaitTime += travelTime
    print "Total wait time calculated"
    return ceil(totalWaitTime), len(incidents)

        # create responders
        # create incident chain -- load precomputed incident chains
        # simulate for time in parallel

# def calculateResponseTime(msg):

class responder():
    def __init__(self, depot, id):
        self.id = id
        self.statusFree = True
        self.assignedDepot = depot
        self.currentPosition = depot
        self.assignedRoute = None
        self.nextTime = None
        self.step = 0

    def updateResponder(self,t):
        if self.statusFree:
            if self.currentPosition == self.assignedDepot:
                self.nextTime = None
                return
            else:
                self.currentPosition = self.assignedRoute[self.step][0]
                self.step += 1

        if not self.statusFree:
            if t >= self.nextTime:
                self.statusFree = True
                self.assignedRoute = getRouteUpdated(self.currentPosition,self.assignedDepot,velocity)
                self.step = 0
                self.nextTime = None


@app.route('/')
@app.route('/index')
def index():
	return render_template("incidentsPlot.html")

@app.route('/transitPlot')
def transitPlot():
    return render_template('transitPlot.html')

@app.route('/log')
def logIncident():
    return render_template('logIncident.html')

@socketio.on('connect')
def socketio_connet():

    findMinMax()

    '''
    # start: t-hub dashboard
    print "socketio_connect"
    time_change_simulation()
    data_segments = []
    with open('myapp/cached_shared_segments.json') as data_file:
        data_segments = json.load(data_file)
    print "data_segments", len(data_segments)
    emit('draw_all_route_segments', {'data': data_segments})
    # end: t-hub dashboard
    '''
    
    print "-> socketio_connect()\n"
    emit("success")

@socketio.on('pre_process')
def preProcess():
    utils = utilities()
    with open("utilsDump", "wb") as output_file:
            pickle.dump(utils, output_file)

@socketio.on('get_dispatch')
def getDispatch():
    '''
    pendingIncidents = msg[0]
    #sort pending incidents according to time
    pendingIncidents = sorted(pendingIncidents,key=itemgetter(1))
    dispatch = {}
    for incident in pendingIncidents:
        grid = incident[0]
        incidentID = incident[1]
        dispatchSolution = utils.gridAssignment[grid]
        dispatch[incidentID] = dispatchSolution
    '''


    client = MongoClient(url_mongo_fire_depart)
    db = client["fire_department"]["geo_incidents"]

    items = db.find({'served': {'$eq': 'False'}})
    # items = db.find({'alarmDateTime': {'$lt': datetime.datetime.now()}})
    print "Items that match date : {}".format(items.count())

    pendingIncidents = []
    # for counterBatch in range(totalBatches):
    for item in items:
        try:
            time = item['alarmDateTime']
            if not isinstance(time, datetime.date):
                time = datetime.datetime.strptime(time, '%Y,%m,%d,%H,%M,%S,%f')

            # if (start <= time <= end):
            dictIn = {}
            tempID = str(item['_id'])
            tempIncidentNumber = item['incidentNumber']
            tempLat = item['latitude']
            tempLong = item['longitude']
            coordX, coordY = p1(tempLong,tempLat)
            gridTemp = utils.getGridForCoordinate([coordX,coordY],utils.xLow,utils.yLow)
            pendingIncidents.append([gridTemp,tempID,tempLat,tempLong])
        except:
            continue

    dispatch = "<b><u> DISPATCH GUIDANCE </u></b> <br>"
    depotVehicles = deepcopy(utils.vehiclesInDepot)
    depotsWithCalls = [utils.gridAssignment[x[0]] for x in pendingIncidents]
    for incident in pendingIncidents:
        incidentGrid = incident[0]
        if depotVehicles[utils.gridAssignment[incidentGrid]] > 0:
            dispatch += "Dispatch Vehicle from Fire Station ID: {} to incident {} <br>".format(utils.gridAssignment[incidentGrid],incident[1])




    # depots = [1,2,3,4,5,6,7,8]
    # dispatch = []
    # for incident in pendingIncidents:
    #     incidentID = incident[1]
    #     dispatch.append([incidentID,random.choice(depots)])
    emit("dispatch_solution", dispatch)


def calculateResponseTime(responders):
    travelTime = simulate(responders)
    return travelTime

@socketio.on('get_responseTime')
def getResponseTime(msg):
    # pool = Pool(2)
    # inputs = []
    #
    # depotDetails = deepcopy(utils.vehiclesInDepot)
    # responders = []
    # for key, value in depotDetails.iteritems():
    #     responders.append(responder(key, len(responders)))
    #
    # inputs.append(responders)
    #
    # depotDetails = deepcopy(utils.vehiclesInDepot)
    # updatedResponders = []
    # for key, value in depotDetails.iteritems():
    #     updatedResponders.append(responder(key, len(responders)))
    #
    # # add a depot from the msg
    # for tempDepot in msg:
    #     newDepotLat = tempDepot[0]
    #     newDepotLong = tempDepot[1]
    #     coordX, coordY = p1(newDepotLong, newDepotLat)
    #     depotGrid = utils.getGridForCoordinate([coordX, coordY], utils.xLow, utils.yLow)
    #
    #     for counterTemp in range(2):
    #         updatedResponders.append(responder(depotGrid, len(responders)))
    #
    #     if depotGrid in utils.vehiclesInDepot.keys():
    #         utils.vehiclesInDepot[depotGrid] += 3
    #     else:
    #         utils.vehiclesInDepot[depotGrid] = 3
    #
    # inputs.append(updatedResponders)
    #
    # results = pool.map(calculateResponseTime, inputs)
    #
    # pool.close()
    # pool.join()
    # pool.terminate()

    # emit("gotNewResponseTime", [results[0], results[1]])


    print "calculating repsonse time"
    depotDetails = deepcopy(utils.vehiclesInDepot)
    responders = []
    for key, value in depotDetails.iteritems():
        responders.append(responder(key, len(responders)))

    oldTravelTime, numIncidents = simulate(responders)

    #re-init depots
    responders = []
    customDepots = msg[0]
    movedDepots = msg[1]
    for tempDepotKey, tempDepotLoc in movedDepots.iteritems():
        newDepotLat = tempDepotLoc[0][0]
        newDepotLong = tempDepotLoc[0][1]
        coordX, coordY = p1(newDepotLong, newDepotLat)
        depotGridOriginal = utils.getGridForCoordinate([coordX, coordY], utils.xLow, utils.yLow)

        newDepotLat = tempDepotLoc[1][0]
        newDepotLong = tempDepotLoc[1][1]
        coordX, coordY = p1(newDepotLong, newDepotLat)
        depotGridNew = utils.getGridForCoordinate([coordX, coordY], utils.xLow, utils.yLow)
        vehiclesInDepot = utils.vehiclesInDepot[depotGridOriginal]
        depotDetails.pop(depotGridOriginal)
        if depotGridOriginal != depotGridNew:
            print "found moved depot"
        depotDetails[depotGridNew] = vehiclesInDepot


    #initiate responders from original depots: even the ones that might have been moved
    for key, value in depotDetails.iteritems():
        responders.append(responder(key, len(responders)))

    # add a depot from the msg
    for tempDepot in customDepots:
        newDepotLat = tempDepot[0]
        newDepotLong = tempDepot[1]
        coordX, coordY = p1(newDepotLong,newDepotLat)
        depotGrid = utils.getGridForCoordinate([coordX,coordY],utils.xLow,utils.yLow)

        for counterTemp in range(2):
            responders.append(responder(depotGrid, len(responders)))



        if depotGrid in utils.vehiclesInDepot.keys():
            utils.vehiclesInDepot[depotGrid] += 3
        else:
            utils.vehiclesInDepot[depotGrid] = 3

    newTravelTime, numIncidents = simulate(responders)
    emit("gotNewResponseTime", [oldTravelTime/float(60),newTravelTime/float(60), numIncidents])
    # return [random.choice(range(10000,25000)),random.choice(range(10000,25000))]

@socketio.on('get_pending')
def getPending():
    print "-> getIncidentData()\n"
    client = MongoClient(url_mongo_fire_depart)
    db = client["fire_department"]["geo_incidents"]

    items = db.find({'served': {'$eq': 'False'}})
    # items = db.find({'alarmDateTime': {'$lt': datetime.datetime.now()}})
    print "Items that match date : {}".format(items.count())

    arr = []
    # for counterBatch in range(totalBatches):
    for item in items:
        try:
            time = item['alarmDateTime']
            if not isinstance(time, datetime.date):
                time = datetime.datetime.strptime(time, '%Y,%m,%d,%H,%M,%S,%f')

            # if (start <= time <= end):
            dictIn = {}
            dictIn['_id'] = str(item['_id'])
            dictIn['incidentNumber'] = item['incidentNumber']
            dictIn['_lat'] = item['latitude']
            dictIn['_lng'] = item['longitude']
            dictIn['alarmDate'] = str(item['alarmDateTime'])
            #dictIn['fireZone'] = item['fireZone']
            dictIn['emdCardNumber'] = item['emdCardNumber']

            dictIn['city'] = item['city'] if ('city' in item) else "na"
            dictIn['county'] = item['county'] if ('county' in item) else "na"
            dictIn['streetNumber'] = item['streetNumber'] if ('streetNumber' in item) else "na"
            dictIn['streetPrefix'] = item['streetPrefix'] if ('streetPrefix' in item) else "na"
            dictIn['streetName'] = item['streetName'] if ('streetName' in item) else "na"
            dictIn['streetType'] = item['streetType'] if ('streetType' in item) else "na"
            dictIn['streetSuffix'] = item['streetSuffix'] if ('streetSuffix' in item) else "na"
            dictIn['apartment'] = item['apartment'] if ('apartment' in item) else "na"
            dictIn['zipCode'] = ((item['zipCode']).split('.'))[0] if ('zipCode' in item) else "na"

            if 'respondingVehicles' in item:
                tmp = item['respondingVehicles']
                allIDs = ""
                for i in tmp:  # i is a dict
                    if 'dispatchDateTime' not in i:
                        i['dispatchDateTime'] = "na"
                    else:
                        i['dispatchDateTime'] = str(i['dispatchDateTime'])
                    if 'arrivalDateTime' not in i:
                        i['arrivalDateTime'] = "na"
                    else:
                        i['arrivalDateTime'] = str(i['arrivalDateTime'])
                    if 'clearDateTime' not in i:
                        i['clearDateTime'] = "na"
                    else:
                        i['clearDateTime'] = str(i['clearDateTime'])
                    allIDs += i['apparatusID'] + "| "

                dictIn['allIDs'] = allIDs
                dictIn['respondingVehicles'] = tmp
            else:
                dictIn['respondingVehicles'] = "na"
                dictIn['allIDs'] = "na"

            # batchIncident.append(dictIn)

            arr.append(dictIn)

        except:
            continue
    emit("incident_data", arr)

@socketio.on('get_action')
def getAction():
    #get action from MDP
    #create state for MDP : See if the actions exists
    #
    pass

@socketio.on('get_depots')
def getDepots():
    getDepotsData()

@socketio.on('get_date')
def getDate (msg):
    print "-> got date, start = " + msg['start'] +", end = "+ msg['end']
    start = datetime.datetime.strptime(msg['start'], "%Y-%m-%d %H:%M")
    end = datetime.datetime.strptime(msg['end'], "%Y-%m-%d %H:%M")
    delta = end - start
    delta = delta.days
    if (delta > 14):
        arr = getIncidentHeat(start, end)
        # getCrimeData(start, end, "heat")
        print request.sid

        emit("latlngarrofobj",arr)
        # emit("latlngarrofobj", arr)
        emit("heat-success")
    else:
        #log time
        timeStart = datetime.datetime.now()
        getIncidentData(start, end)
        timeEnd = datetime.datetime.now()
        print "Time taken to get incidents : {}".format((timeEnd-timeStart).total_seconds())
        timeStart = datetime.datetime.now()
        getDepotsData()
        timeEnd = datetime.datetime.now()

        # getCrimeData(start, end, "markers")
        emit("markers-success")
        # emit("markers-success")
    
@socketio.on('predictNOW')
def getPredict(msg):
    if (msg['ans'] == 'crime'):
        print "-----> get predict for CRIME"
        getPredictions("crime")
    else:
        print "-----> get predict for FIRE"
        getPredictionsByCategory(msg['category'])
        # getPredictions("fire")

@socketio.on('getOptimization')
def getOptimization():
    getBestDepotPos()
'''
max time is;;;;;;;;;;;;;;;;;
2016-02-05 13:12:00
min time is;;;;;;;;;;;;;;;;;
2014-02-20 10:24:00
'''
global minmax
minmax = [None] * 2
global lastsearch
lastsearch = None
def findMinMax():
#     # global minmax
#     # global lastsearch
#     # if (not minmax or not lastsearch or time.time() - lastsearch > 24 * 60 * 60):
#     #     client = MongoClient("mongodb://127.0.0.1:27017/fire_department")
#     #     db = client["fire_department"]["simple__incident"]
#     #     items = db.find()
#     #     pretime = (items[0])['alarmDateTime']
#     #     if isinstance(pretime, unicode):
#     #         pretime = datetime.datetime.strptime(pretime, "%Y,%m,%d,%H,%M,%S,%f")
#     #         print pretime
#     #     maxT = pretime
#     #     minT = pretime
#
#     #     for item in items:
#     #         _time_ = item['alarmDateTime']
#     #         if isinstance(_time_, unicode):
#     #             if (_time_[0]!="2"): # _time_: "Essentially the time at which the accident occurred"
#     #                 continue
#     #             else:
#     #                 _time_ = datetime.datetime.strptime(_time_, "%Y,%m,%d,%H,%M,%S,%f")
#
#     #         if (_time_>maxT):
#     #             maxT = _time_
#
#     #         if (_time_<minT):
#     #             minT = _time_
#
#     #     minmax[0] = (minT - datetime.datetime(1970,1,1)).total_seconds()
#     #     minmax[1] = (maxT - datetime.datetime(1970,1,1)).total_seconds()
#
#         '''
#         2014-03-21 10:02:48.253000
#         [datetime.datetime(2014, 2, 20, 10, 24, 51, 297000), datetime.datetime(2017, 6, 20, 13, 31, 11)]
#         '''
#
        minmax[0] = (datetime.datetime(2015,2,21) - datetime.datetime(1970,1,1)).total_seconds()
        minmax[1] = (datetime.datetime(2019,6,19) - datetime.datetime(1970,1,1)).total_seconds()

        lastsearch = time.time()
        # print [minT, maxT]
        emit("gotNewMinMaxTime", minmax)

@socketio.on('getHeat_entire')
def getHeat_entire():
    arr = getIncidentHeat(datetime.datetime(2014,1,1),datetime.datetime(2016,1,1))
    emit("gotHeat_entire",arr)

# retrieve a simplified list of information for just heat map layer
def getIncidentHeat(start, end):
    print "-> getIncidentHeat()\n"
    client = MongoClient(url_mongo_fire_depart)
    db = client["fire_department"]["geo_incidents"]
    #items = db.find()
    items = db.find({'alarmDateTime': {'$gte': start, '$lt': end}}).limit(1000)
    arr = []

    for item in items:
        # _time_ = item['alarmDateTime']
        # if isinstance(_time_, unicode):
        #     if (_time_[0]!="2"): # _time_: "Essentially the time at which the accident occurred"
        #         continue
        #     else:
        #         _time_ = datetime.datetime.strptime(_time_, "%Y,%m,%d,%H,%M,%S,%f")
        # elif not isinstance(_time_, datetime.date):
        #     print item
        #
        # if (start <= _time_ <= end):
        dictIn = {}
        dictIn['lat'] = item['latitude']
        dictIn['lng'] = item['longitude']
        dictIn['emdCardNumber'] = item['emdCardNumber']
        arr.append(dictIn)
    #emit("latlngarrofobj", arr)
    return arr


def createDBDate(dt):
    #parse the date in a format that can be queried
    delimiter = '-'
    separator = 'T'
    timeSeparator = ':'
    dateBuilder = str(dt.year) + delimiter
    dateBuilder += str(dt.month) + delimiter
    dateBuilder += str(dt.day) + separator
    dateBuilder += str(dt.hour) + timeSeparator
    dateBuilder += str(dt.minute) + timeSeparator
    dateBuilder += str(dt.second)
    return dateBuilder



# retrieve data from mongo db
def getIncidentData(start, end):
    getDepotsData()
    print "-> getIncidentData()\n"
    client = MongoClient(url_mongo_fire_depart)
    db = client["fire_department"]["geo_incidents"]

    ############################
    ############################
    ############################
    # REMOVE BEFORE CHECK IN
    # print "Debug: remove before check in. Start and end dates modified"
    # start = datetime.datetime(2011, 1, 1)
    # end = datetime.datetime(2018, 1, 1)
    ############################
    ############################
    ############################


    items = db.find({'alarmDateTime':{'$gte':start,'$lt':end}}).limit(600)
    #items = db.find({'alarmDateTime': {'$lt': datetime.datetime.now()}})
    print "Items that match date : {}".format(items.count())

    arr = []
    #for counterBatch in range(totalBatches):
    for item in items:
        try:
            time = item['alarmDateTime']
            if not isinstance(time, datetime.date):
                time = datetime.datetime.strptime(time, '%Y,%m,%d,%H,%M,%S,%f')

            # if (start <= time <= end):
            dictIn = {}
            dictIn['_id'] = str(item['_id'])
            dictIn['incidentNumber'] = item['incidentNumber']
            dictIn['_lat'] = item['latitude']
            dictIn['_lng'] = item['longitude']
            dictIn['alarmDate'] = str(item['alarmDateTime'])
            #dictIn['fireZone'] = item['fireZone']
            dictIn['emdCardNumber'] = item['emdCardNumber']

            dictIn['city'] = item['city'] if ('city' in item) else "na"
            dictIn['county'] = item['county'] if ('county' in item) else "na"
            dictIn['streetNumber'] = item['streetNumber'] if ('streetNumber' in item) else "na"
            dictIn['streetPrefix'] = item['streetPrefix'] if ('streetPrefix' in item) else "na"
            dictIn['streetName'] = item['streetName'] if ('streetName' in item) else "na"
            dictIn['streetType'] = item['streetType'] if ('streetType' in item) else "na"
            dictIn['streetSuffix'] = item['streetSuffix'] if ('streetSuffix' in item) else "na"
            dictIn['apartment'] = item['apartment'] if ('apartment' in item) else "na"
            dictIn['zipCode'] = ((item['zipCode']).split('.'))[0] if ('zipCode' in item) else "na"

            if 'respondingVehicles' in item:
                tmp = item['respondingVehicles']
                allIDs = ""
                for i in tmp: # i is a dict
                    if 'dispatchDateTime' not in i:
                        i['dispatchDateTime'] = "na"
                    else:
                        i['dispatchDateTime'] = str(i['dispatchDateTime'])
                    if 'arrivalDateTime' not in i:
                        i['arrivalDateTime'] = "na"
                    else:
                        i['arrivalDateTime'] = str(i['arrivalDateTime'])
                    if 'clearDateTime' not in i:
                        i['clearDateTime'] = "na"
                    else:
                        i['clearDateTime'] = str(i['clearDateTime'])
                    allIDs += i['apparatusID'] + "| "

                dictIn['allIDs'] = allIDs
                dictIn['respondingVehicles'] = tmp
            else:
                dictIn['respondingVehicles'] = "na"
                dictIn['allIDs'] = "na"

            # batchIncident.append(dictIn)
            
            arr.append(dictIn)

        except:
            continue

    emit("incident_data", arr)

depot_cache = [];
# Retrieve fire depots location and what vehicles live there
def getDepotsData():
    # global depot_cache
    depot_cache = []
    print "-> getDepotsData()\n"

    client = MongoClient(url_mongo_fire_depart)
    #db = client["fire_department"]["depot_details"]
    db = client["fire_department"]["newStations2019"]

    pipeline = [{'$group': {'_id':"$stationLocation","vehicle":{'$addToSet':'$apparatusID'}}}]
    items = list(db.aggregate(pipeline))
    vehiclesInDepot = [deepcopy([]) for x in range(len(items))]
    for counter in range(len(items)):
        if items[counter]['vehicle'][0] == 'sample' or items[counter]['_id'][0] is None or items[counter]['vehicle'] == []:
            continue
        vehiclesInDepot[counter] = items[counter]['vehicle']
        depot_cache.append(items[counter]['_id'])


    # count = 0
    # for item in items:
    #     print "Item"
    #     ##replaced in query
    #     # if (item['apparatusID']=="sample"):
    #     #     continue
    #
    #     #if not depot_cache:
    #     stationArr = item['stationLocation']
    #     if stationArr[0]:
    #         if stationArr[0] not in depot:
    #             depot.append(stationArr[0])
    #         indexOfthis = depot.index(stationArr[0])
    #         # print stationArr
    #         # print indexOfthis
    #         if not vehiclesInDepot[indexOfthis]:
    #             vehiclesInDepot[indexOfthis] = [];
    #         vehiclesInDepot[indexOfthis].append(item['apparatusID'])

    # depot_cache = depot
    emit("depots_data", {'depotLocation': depot_cache, 'depotInterior': vehiclesInDepot})

def getCrimeData(start, end, str):
    print(" --> get Crime Markers csv")
    arr = []
    i=0
    #with open('/Users/wangshibao/SummerProjects/analytics-dashboard/myapp/CrimeHistory.csv','rU') as f:
    with open(os.getcwd()+'/myapp/CrimeHistory.csv','rU') as f:
        reader = csv.reader(f)
        header = reader.next()
        for row in reader:
            date = row[1]
            date_time = datetime.datetime.strptime(date, "%Y%m%d %H:%M")
            if (start <= date_time <= end):
                # print i
                # i += 1

                obj = {}
                for j in range(len(header)):
                    obj[header[j]] = row[j]
                arr.append(obj)
    if (str == "heat"):
        emit("crime_heat", arr)
    else: 
        if (arr != []):
            print "-----> arr is NOT empty"
            emit("crime_data", arr)
        else:
            print "-----> arr is empty"
            emit("crime_none")

# 
# Incidents Predictions
# 
import numpy as np
from random import randint
import os
import pickle
from pyproj import Proj
import random

p1 = Proj(
    '+proj=lcc +lat_1=36.41666666666666 +lat_2=35.25 +lat_0=34.33333333333334 +lon_0=-86 +x_0=600000 +y_0=0 +ellps=GRS80 +datum=NAD83 +no_defs')

def getPredictionsByCategory(category):
    #returns incidents from a specific category (Cardiac, MVA...)
    incidentChains = utils.categoryWiseGrids[category]
    chosenChainIndex = randint(0, len(incidentChains))
    chosenChain = incidentChains[chosenChainIndex]
    incidents = []
    for counter in range(len(chosenChain)):
        coordinates = utils.reverseCoordinates[chosenChain[counter]]
        lat, long = p1(coordinates[0], coordinates[1], inverse=True)
        incidents.append([lat, long, utils.categoryWiseGridWeights[category][chosenChain[counter]]])
    #normalize data weights
    normalizer = sum([x[2] for x in incidents])
    for counter in range(len(incidents)):
        incidents[counter][2] /= float(normalizer)
    emit("predictions_data", incidents)
    # return incidents

def getPredictions(type):
    #type can either be fire or crime
    filepath = os.getcwd() + "/myapp/"
    if type == "fire":
        if os.path.isfile(filepath + 'meanTraffic.txt'):
            exists = True
            print"Found mean file"
            with open(filepath+'meanTraffic.txt','r+') as f:
                mean = float(f.readlines()[0])
        else:
            print"Did not find mean file"
            mean = 200

        if os.path.isfile(filepath + 'predictionsFireDashboard.pickle'):
            print"Found fire prediction file"
            with open(filepath+'predictionsFireDashboard.pickle','r+') as f:
                predictionsOutput = pickle.load(f)

            #sample poisson
            numSample = np.random.poisson(mean, 1)

            #return sampled values
            output = []
            for sampleCounter in range(0,numSample):
                indSample = randint(0,len(predictionsOutput))
                coordinates = list(p1(predictionsOutput[indSample][0],predictionsOutput[indSample][1],inverse=True))
                coordinates.append(predictionsOutput[indSample][2])
                output.append(coordinates)
            emit("predictions_data", output)

        else:
            print"Did not find prediction file"
            emit("predictions_none", [])
    elif type == "crime":
        if os.path.isfile(filepath + "crimePredicted.xls"):
            predictedWorkbook = xlrd.open_workbook(filepath + "crimePredicted.xls")
            predictionWorksheet = predictedWorkbook.sheet_by_index(0)
            # get total rows:
            rows = predictionWorksheet.nrows - 1
            try:
                columns = len(predictionWorksheet.row(0))
            except ValueError:
                return []
            numToSample = 300
            numSampled = 0
            output = []
            while numSampled < numToSample:
                index = randint(1, rows)
                row = []
                for counterCol in range(columns):
                    try:
                        row.append(predictionWorksheet.cell_value(index, counterCol))
                    except IndexError:
                        print "Issue with row {} and column {}".format(index,counterCol)
                output.append(row)
                numSampled+=1
            print len(output)
            emit("predictions_data_crime", output)
        else:
            print"Did not find prediction file"
            emit("predictions_none", [])

def getBestDepotPos():
    print "--> get best bestAssignment of depots"
    filepath = os.getcwd() + "/myapp/"

    arr = []
    dicOfDepot = {}
    with open(filepath + "bestAssignment") as f:
        contents = pickle.load(f)
        for i in range(len(contents[3])):
            if contents[3][i] > 0:
                arr.append(i)
        for i in range(len(contents[2])):
            if contents[2][i][0] is not 0:
                if  contents[2][i][0] not in dicOfDepot:
                    dicOfDepot[contents[2][i][0]] = []
                dicOfDepot[contents[2][i][0]].append(i)
    # print dicOfDepot

    
    with open(filepath + "latLongGrids.pickle") as f:
        contents = pickle.load(f)
        arrOfDict = []
        for key in dicOfDepot:
            dic = {"depotKey": key, "depotLatLng": "", "inChargeOf": []}
            dic["depotLatLng"] = contents[key]
            for grid in dicOfDepot[key]:
                dic["inChargeOf"].append(contents[grid])
            arrOfDict.append(dic)
        emit("bestAreaInCharge", arrOfDict)


'''
# 
# t-hub dashboard
# 
from myapp import app
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO
from flask_socketio import send, emit
from myapp import socketio
from myapp import dashboard
import time
import datetime
import json
import requests
import pytz

# @app.route('/')
# @app.route('/index')
# def index():
#     return render_template("home.html")

def time_change_simulation():
    url = 'http://127.0.0.1:8000/timestamp'
    r = requests.get( url )
    data = r.json()
    if data:        
        current_timestamp = data['timestamp']
        print "-current_timestamp", current_timestamp
        date_time = datetime.datetime.fromtimestamp(current_timestamp, pytz.timezone('America/Chicago'))
        emit('simulated_time', {'timestamp': date_time.strftime("%Y-%m-%d %H:%M")})

# @socketio.on('connect')
# def socketio_connect():
    # print "socketio_connect"
    # time_change_simulation()
    # data_segments = []
    # with open('myapp/cached_shared_segments.json') as data_file:
    #     data_segments = json.load(data_file)
    # print "data_segments", len(data_segments)
    # emit('draw_all_route_segments', {'data': data_segments})

@socketio.on('get_map_routes')
def socketio_get_map_routes(message):
    route_segment = dashboard.route_segment()
    selected = message.get('selected')
    if selected==0:
        data_segments = []
        with open('myapp/cached_shared_segments.json') as data_file:
            data_segments = json.load(data_file)
        print "data_segments", len(data_segments)
        emit('draw_all_route_segments', {'data': data_segments})
    else:
        data_segments = []
        with open('myapp/routes_coors.json') as data_file:
            data_segments = json.load(data_file)
        performance = []
        if selected==1:
            with open('myapp/original_performance_may.json') as data_file:
                performance = json.load(data_file)
        elif selected==2:
            with open('myapp/optimized_performance.json') as data_file:
                performance = json.load(data_file)
        elif selected==3:
            with open('myapp/original_performance_june.json') as data_file:
                performance = json.load(data_file)
        elif selected==4:
            with open('myapp/optimized_performance_june.json') as data_file:
                performance = json.load(data_file)
        emit('response_map_routes', {'data': data_segments, 'performance': performance})


@socketio.on('get_vehicle_location_for_trip')
def socketio_get_vehicle_location_for_trip(message):
    print "socketio_get_vehicle_location_for_trip"
    trip_id = message.get('trip_id')
    url = 'http://127.0.0.1:8000/vehicle/'+str(trip_id)
    r = requests.get( url )
    data = r.json()
    # route_segment = dashboard.route_segment()
    # data = route_segment.get_vehicle_location_for_trip(trip_id)
    print 'vehicle location', data
    if data[0] != -1:
        emit('vehicle_location_for_trip', {'coordinate': data})
    print data

@socketio.on('get_predictions_for_trip')
def socketio_get_predictions_for_trip(message):
    print "socketio_get_predictions_for_trip"
    trip_id = message.get('trip_id')
    route_segment = dashboard.route_segment()
    data = route_segment.get_predictions_for_trip(trip_id)
    segments = route_segment.get_segments_for_tripid(trip_id)
    print "trip_id", trip_id
    print data['coordinates']
    emit('predictions_for_trip', {'prediction': data['prediction'], 'coordinates': data['coordinates'], 'segments': segments})

@socketio.on('get_all_routeid')
def socketio_get_all_routeid():
    route_segment = dashboard.route_segment()
    data = route_segment.get_all_routeid()
    # print "dfasdfasdf:", data
    emit('all_routeid', {'data': data})

@socketio.on('get_directions_for_routeid')
def socketio_get_directions_for_routeid(message):
    route_segment = dashboard.route_segment()
    route_id = message.get('route_id')
    data = route_segment.get_all_headsigns(route_id)
    print data
    emit('directions_for_routeid', {'data': data})

@socketio.on('get_trips_for_routeid_direction')
def socketio_get_trips_for_routeid_direction(message):
    print 'get_trips_for_routeid_direction'
    route_segment = dashboard.route_segment()
    route_id = message.get('route_id')
    trip_headsign = message.get('trip_headsign')
    data = route_segment.get_trips(route_id, trip_headsign)
    emit('trips_for_routeid_direction', {'tripids': data[0], 'departuretimes': data[1]})
'''


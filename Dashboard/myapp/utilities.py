from __future__ import division
#python file to store generic methods
from math import floor
import fiona
import ConfigParser
import numpy as np
import os
from pymongo import MongoClient
from myconfig import MONGODB_HOST, MONGODB_PORT
from datetime import datetime
from datetime import timedelta
from pyproj import Proj
from copy import deepcopy
import operator
from operator import itemgetter
import numpy as np
from math import ceil
from numpy.random import exponential
import random
from random import randint

url_mongo_fire_depart = "%s:%d/fire_department" % (MONGODB_HOST, MONGODB_PORT)
p1 = Proj('+proj=lcc +lat_1=36.41666666666666 +lat_2=35.25 +lat_0=34.33333333333334 +lon_0=-86 +x_0=600000 +y_0=0 +ellps=GRS80 +datum=NAD83 +no_defs')

gridSize = 1609.34
mileToMeter = 1609.34

incidentCategorization= {
		"Cardiac":["6", "9", "11", "12", "19", "28", "31", "32"],
		"Trauma":["1", "2", "3", "4", "5", "7", "8", "10", "13", "14", "15", "16", "17", "18", "20", "21", "22", "23", "24", "25", "26", "27", "30"],
		"MVA":["29"],
		"Fire":["51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73", "74", "75"]
}


Config = ConfigParser.ConfigParser()
Config.read("params.conf")

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

class utilities:
    def __init__(self):
        self.grids, self.xLow, self.yLow = self.getGrid()
        self.getData()
        self.calculateGridWiseIncidentArrival()
        self.calculateCategoryWiseSurvival()
        self.createPredictionsForHeat()
        self.getNumberOfServersPerDepot()
        self.calculateGridWiseArrivalLambda()
        self.calculateDepotAssignemnts()
        self.createIncidentChains()

    def parseEMDCard(self,emd):
        categoryTemp = None
        severity = "OABCDE"
        for u in range(0,len(emd)):
            if emd[u] not in severity:
                pass
            else:
                categoryTemp = str(emd[0:u])
                break

        if categoryTemp is not None:
            for type, categories in incidentCategorization.iteritems():
                if categoryTemp in categories:
                    return type

        return None    
    
    def updateCategoryWiseDataStream(self):
        #given a streaming data source, update the category wise data model
        categoryWiseData = {"Cardiac": [], "Trauma": [], "MVA": [], "Fire": []}

        # get data to update
        try:
            tempData = self.getStreamingData(self.lastUpdateDate)
        except AttributeError:
            #if update has no history, start with using data from the last 24 hours
            self.lastUpdateDate = datetime.now() - timedelta(seconds=3600*24)
            tempData = self.getStreamingData(self.lastUpdateDate)

        if tempData is not None:
            for row in tempData:
                emd = row[3]
                category = self.parseEMDCard(emd)
                if category in self.categoryWiseData.keys():
                    categoryWiseData[category].append(row)

            print "Category wise data segregated"
            # category wise data populated, calculate inter-arrival times
            for category in categoryWiseData.keys():
                # sort arrival data according to time
                sorted(categoryWiseData[category], key=itemgetter(3))
                data = categoryWiseData[category]
                # calculate time differences
                interArrivalTimes = []  # store interarrival times
                gridNums = {}  # which grid sees how many incidents
                for counter in range(len(data)):
                    coordinates = list(p1(data[counter][1], data[counter][0]))
                    gridNumTemp = int(self.getGridForCoordinate(coordinates, self.xLow, self.yLow))
                    if counter == 0:
                        timeTemp = (data[counter][2] - datetime(2014, 1, 1)).total_seconds()
                    else:
                        timeTemp = (data[counter][2] - data[counter - 1][2]).total_seconds()

                    if gridNumTemp in gridNums:
                        gridNums[gridNumTemp] += 1
                    else:
                        gridNums[gridNumTemp] = 1

                    interArrivalTimes.append(timeTemp)

                # fit and exponential Arrival Model
                lastSum = self.categoryWiseExponDenom[category] * self.categoryWiseMean[category]
                exponMeanTemp = (sum(interArrivalTimes) + lastSum) / float(len(interArrivalTimes) + self.categoryWiseExponDenom[category])
                self.categoryWiseMean[category] = exponMeanTemp
                # Normalize grid arrival count
                denominator = sum(gridNums.values())
                for key in gridNums:
                    lastGridArrivalSum = self.categoryWiseCountDenom[category] * self.categoryWiseGridWeights[category][key]
                    currSum = gridNums[key] + lastGridArrivalSum
                    currDenom = denominator + self.categoryWiseCountDenom[category]
                    gridNums[key] = currSum/float(currDenom)

                self.categoryWiseGridWeights[category] = gridNums

        self.lastUpdateDate = datetime.now()

    def calculateCategoryWiseSurvival(self):
        print "Calculating category wise models"
        self.lastUpdateDate = datetime(2010,1,1)#arbitrary date before start time
        self.categoryWiseData = {"Cardiac":[],"Trauma":[],"MVA":[],"Fire":[]}
        self.categoryWiseMean = {"Cardiac":0,"Trauma":0,"MVA":0,"Fire":0}
        self.categoryWiseGridWeights = {"Cardiac":{},"Trauma":{},"MVA":{},"Fire":{}}
        self.categoryWiseExponDenom = {"Cardiac":0,"Trauma":0,"MVA":0,"Fire":0}
        self.categoryWiseCountDenom = {"Cardiac":0,"Trauma":0,"MVA":0,"Fire":0}

        for row in self.data:
            emd = row[3]
            category = self.parseEMDCard(emd)
            if category in self.categoryWiseData.keys():
                self.categoryWiseData[category].append(row)

        print "Category wise data segregated"
        #category wise data populated, calculate inter-arrival times
        for category in self.categoryWiseData.keys():
            #sort arrival data according to time
            sorted(self.categoryWiseData[category],key=itemgetter(3))
            data = self.categoryWiseData[category]
            #calculate time differences
            interArrivalTimes = [] #store interarrival times
            gridNums = {} #which grid sees how many incidents
            for counter in range(len(data)):
                coordinates = list(p1(data[counter][1], data[counter][0]))
                gridNumTemp = int(self.getGridForCoordinate(coordinates,self.xLow,self.yLow))
                if counter == 0:
                    timeTemp = (data[counter][2] - datetime(2014,1,1)).total_seconds()
                else:
                    timeTemp = (data[counter][2] - data[counter-1][2]).total_seconds()

                if gridNumTemp in gridNums:
                    gridNums[gridNumTemp] += 1
                else:
                    gridNums[gridNumTemp] = 1

                interArrivalTimes.append(timeTemp)


            #fit and exponential Arrival Model
            exponMeanTemp = sum(interArrivalTimes)/len(interArrivalTimes)
            self.categoryWiseMean[category] = exponMeanTemp
            self.categoryWiseExponDenom[category] = len(interArrivalTimes)
            #Normalize grid arrival count
            denominator = sum(gridNums.values())
            self.categoryWiseCountDenom[category] = denominator
            for key in gridNums:
                gridNums[key] /= denominator

            self.categoryWiseGridWeights[category] = gridNums

        self.lastUpdateDate = datetime.now()

    def weighted_random_by_dct(self,dct):
        rand_val = random.random()
        total = 0
        for k, v in dct.items():
            total += v
            if rand_val <= total:
                return k

    def createPredictionsForHeat(self):
        #create chains 24 hour long only. Prediction is only for a day
        baseTime = datetime(2018,1,1,0,0)
        numSampleRunsToGenerate = 20
        self.categoryWiseGrids = {"Cardiac":[],"Trauma":[],"MVA":[],"Fire":[]}
        for counterRun in range(numSampleRunsToGenerate):
            for category in self.categoryWiseMean:
                incidents = []
                currTime = datetime(2018, 1, 1, 0, 0)
                dayLeft = True
                while dayLeft:
                    sample = exponential(self.categoryWiseMean[category])
                    if currTime + timedelta(seconds=sample) > baseTime + timedelta(days=1):
                        break
                    else:
                        currTime += timedelta(seconds=sample)
                        dictToSample = self.categoryWiseGridWeights[category]
                        grid = self.weighted_random_by_dct(dictToSample)
                        incidents.append(grid)

                self.categoryWiseGrids[category].append(incidents)
        print "Created predictions for Heat Map"


    def createIncidentChains(self):
        #create chains 1 months long
        self.times = [] #what times do incidents happen
        for grid in range(900):
            t=0
            if grid in self.gridWiseLambda.keys():
                while t<30*24*3600:
                    sample = ceil(np.random.exponential(1/self.gridWiseLambda[grid]))
                    if sample > 3*30*24*60*60:
                        break
                    else:
                        self.times.append([sample,grid])
                        t+=sample
        self.times = sorted(self.times,key=itemgetter(0))
        print "generated static samples"


    def getGrid(self):
        shpFilePath =  os.getcwd() + "/myapp/data/StatePlane_Income_Pop_House.shp"
        fshp = fiona.open(shpFilePath)
        bounds = fshp.bounds
        print(bounds)
        xLow = bounds[0]
        xHigh = bounds[2]
        yLow = bounds[1]
        yHigh = bounds[3]
        self.reverseCoordinates = {}

        numGridsX = int(floor((xHigh - xLow)/float(gridSize)))
        numGridsY = int(floor((yHigh - yLow)/float(gridSize)))
        grids = np.zeros((numGridsX,numGridsY),dtype=object)#so that the default type is not float. we will store lists
        for counterY in range(numGridsY):
            for counterX in range(numGridsX):
                lowerLeftCoords = (xLow+counterX*gridSize,yLow+counterY*gridSize)
                if counterX == (numGridsX-1): # reached the end on x axis
                    xCoord = xHigh
                else:
                    xCoord = xLow+counterX*gridSize+gridSize
                if counterY == (numGridsY-1): # reached the end on y axis
                    yCoord = yHigh
                else:
                    yCoord = yLow+counterY*gridSize+gridSize

                upperRightCoords = (xCoord,yCoord)
                grids[counterX,counterY] = [np.array(lowerLeftCoords),np.array(upperRightCoords)]
                counterGrid = counterY*numGridsX + counterX
                self.reverseCoordinates[counterGrid] = [([np.array(lowerLeftCoords),np.array(upperRightCoords)][0][0] + [np.array(lowerLeftCoords),np.array(upperRightCoords)][1][0])/2,
                                                        ([np.array(lowerLeftCoords), np.array(upperRightCoords)][0][1] +
                                                         [np.array(lowerLeftCoords), np.array(upperRightCoords)][1][
                                                             1]) / 2]

        return grids, xLow, yLow

    def getGridForCoordinate(self,coordinate,xLow,yLow):
        gridSize = 1609.34#1 mile to meter
        x = coordinate[0]
        y = coordinate[1]
        gridX = floor((x-xLow)/float(gridSize))
        gridY = floor((y-yLow)/float(gridSize))
        gridNum = gridY * len(self.grids) + gridX
        return gridNum

    def getGridNumForCoordinate(self, coordinate, xLow, yLow):
        gridSize = 1609.34  # 1 mile to meter
        x = coordinate[0]
        y = coordinate[1]
        gridX = floor((x - xLow) / float(gridSize))
        gridY = floor((y - yLow) / float(gridSize))
        return gridX, gridY


    def getCoordinateForGrid(self,gridNum):
        y = floor(gridNum/30)
        x = gridNum%30
        coordX = self.xLow + gridSize * x
        coordY = self.yLow + gridSize * y
        return [coordX,coordY]
    
    def getStreamingData(self,upperDate):
        client = MongoClient(url_mongo_fire_depart)
        db = client["fire_department"]["geo_incidents"]
        if upperDate is None:
            items = db.find({'served': {'$ne': 'true'}})
        else:
            items = db.find({"$and": [{"served": {'$ne': 'true'}},
                                      {"alarmDateTime": {'$gt': upperDate}}]})

        print "Items that match date : {}".format(items.count())
        self.gridWiseIncidents = {}
        tempData = []

        arr = []
        # for counterBatch in range(totalBatches):
        for item in items:
            try:
                time = item['alarmDateTime']
                lat = item['latitude']
                long = item['longitude']
                emd = item['emdCardNumber']
                tempData.append([lat, long, time, emd])
                coordinates = list(p1(long, lat))
                grid = int(self.getGridForCoordinate([coordinates[0], coordinates[1]], self.xLow, self.yLow))
                if not isinstance(time, datetime):
                    time = datetime.datetime.strptime(time, '%Y,%m,%d,%H,%M,%S,%f')
                if grid not in self.gridWiseIncidents.keys():
                    self.gridWiseIncidents[grid] = [time]
                else:
                    self.gridWiseIncidents[grid].append(time)
            except:
                continue

        return tempData
    
    
    def getData(self,upperDate=None):
        client = MongoClient(url_mongo_fire_depart)
        db = client["fire_department"]["simple_incidents"]
        if upperDate is None:
            items = db.find({'served': {'$ne': 'true'}})
        else:
            items = db.find({"$and": [{"served": {'$ne': 'true'}},
                                      {"alarmDateTime": {'$lt': self.lastUpdateDate}}]})

        print "Items that match date : {}".format(items.count())
        self.gridWiseIncidents = {}
        self.data = []

        arr = []
        # for counterBatch in range(totalBatches):
        for item in items:
            try:
                time = item['alarmDateTime']
                lat = item['latitude']
                long = item['longitude']
                emd = item['emdCardNumber']
                self.data.append([lat,long,time,emd])
                coordinates = list(p1(long,lat))
                grid = int(self.getGridForCoordinate([coordinates[0],coordinates[1]],self.xLow,self.yLow))
                if not isinstance(time, datetime):
                    time = datetime.datetime.strptime(time, '%Y,%m,%d,%H,%M,%S,%f')
                if grid not in self.gridWiseIncidents.keys():
                    self.gridWiseIncidents[grid] = [time]
                else:
                    self.gridWiseIncidents[grid].append(time)
            except:
                continue

    def calculateGridWiseIncidentArrival(self):
        self.gridWiseInterArrival = {}
        for grid,interArrivals in self.gridWiseIncidents.iteritems():
            interArrivals=sorted(interArrivals)
            if len(interArrivals) == 0:
                self.gridWiseInterArrival = []
            if len(interArrivals) == 1:
                self.gridWiseInterArrival[grid] = [(interArrivals[0] - datetime(2014,1,1)).total_seconds()]
            else:
                for counterIncident in range(len(interArrivals)):
                    if counterIncident == 0:
                        self.gridWiseInterArrival[grid] = [(interArrivals[counterIncident] - datetime(2014,1,1)).total_seconds()]
                    else:
                        self.gridWiseInterArrival[grid].append((interArrivals[counterIncident] - interArrivals[counterIncident-1]).total_seconds())



    def factorial(self,n):
        temp = 1
        for i in range(1,n+1):
            temp*=i
        return temp

    def isWaitTimeViolated(self,depot,tempArrivalRate):
        c = self.vehiclesInDepot[depot] #number of servers in the depot
        mu = 1/(30*60) #an incident takes 30 minutes to service
        lambda_param = tempArrivalRate
        limit = 1

        #define rho = lambda/c * mu
        rho = lambda_param/(c*mu)

        t1 = self.factorial(c)/((c*rho)**c)

        t2 = 0
        for k in range(0,c):
            t2 += ((c*rho)**k)/self.factorial(k)


        C_denominator = 1 + (1 - rho)*t1*t2
        C = 1/C_denominator

        responseTime = C/(c*mu - lambda_param)
        if responseTime > limit:
            return True
        else:
            return False


    def getNumberOfServersPerDepot(self):
        depot_cache = []
        print "-> getDepotsData()\n"

        client = MongoClient(url_mongo_fire_depart)
        # db = client["fire_department"]["depot_details"]
        db = client["fire_department"]["newStations2019"]
        pipeline = [{'$group': {'_id': "$stationLocation", "vehicle": {'$addToSet': '$apparatusID'}}}]
        items = list(db.aggregate(pipeline))
        self.vehiclesInDepot = {}
        for counter in range(len(items)):
            if items[counter]['vehicle'][0] == 'sample' or items[counter]['_id'][0] is None or items[counter][
                'vehicle'] == []:
                continue
            coordX, coordY = p1(items[counter]['_id'][0][1],items[counter]['_id'][0][0])
            depotGrid = int(self.getGridForCoordinate([coordX,coordY],self.xLow,self.yLow))
            if depotGrid in self.vehiclesInDepot.keys():
                self.vehiclesInDepot[depotGrid] += len(items[counter]['vehicle'])
            else:
                self.vehiclesInDepot[depotGrid] = len(items[counter]['vehicle'])

        print "Calculated Servers per Depot"

    def dist(self,i, j):
        try:
            coord1 = self.reverseCoordinates[i]
            coord2 = self.reverseCoordinates[j]
            d = np.sqrt((coord1[0] - coord2[0]) ** 2 + (coord1[1] - coord2[1]) ** 2)
            return d / 1609.34  # return in miles
        except TypeError:
            raise Exception("Error with calculating distance between {} and {}".format(i, j))

    def calculateDepotAssignemnts(self):
        # depots and vehicle distribution is assumed fixed. This method only optimizes assignments
        gridWiseArrival = self.calculateGridWiseIncidentArrival()
        # sort grid wise arrival
        depotLocations = self.vehiclesInDepot.keys()
        sortedGrids = sorted(self.gridWiseLambda.items(), key=operator.itemgetter(1), reverse=True)#grids that are unassigned to depots
        grids = [x[0] for x in sortedGrids]#only take the grid nums and leave the rates --> This is still sorted
        activeGrids = {key: True for key in grids} #dict check active grids
        self.depotAssignedLambda = {key:0 for key in grids} #current lambda for the depot - sum of grid lambdas it is responsible for
        self.gridAssignment = {}#grid --> assigned depot mapping


        assignmentOver = False

        for grid in grids:
            if assignmentOver:
                break
            candidates = []
            if activeGrids[grid]:
                for depotCandidate in depotLocations:
                    if depotCandidate > 900 or grid > 900:
                        continue
                    dist = self.dist(grid,depotCandidate)
                    depotArrivalTemp = self.depotAssignedLambda[depotCandidate] + self.gridWiseLambda[grid]
                    if not self.isWaitTimeViolated(depotCandidate,depotArrivalTemp):
                        candidates.append([depotCandidate,dist])

                if len(candidates) > 0:
                    bestDepot = sorted(candidates,key=itemgetter(1))[0][0]
                    self.gridAssignment[grid] = bestDepot
                    self.depotAssignedLambda[bestDepot] += self.gridWiseLambda[grid]

        print "Grid to Depot Assignment complete"

    def calculateGridWiseArrivalLambda(self):
        print "calculating grid wise lambda"
        self.gridWiseLambda = {}
        for grid, interArrivalTimes in self.gridWiseInterArrival.iteritems():
            lambdaTemp = sum(interArrivalTimes)/len(interArrivalTimes)
            self.gridWiseLambda[grid] = 1/lambdaTemp

        print "Inter-Arrival Rates Calculated"

import ConfigParser
import pickle
from datetime import timedelta
import numpy as np
from operator import itemgetter
from pyproj import Proj

Config = ConfigParser.ConfigParser()
Config.read("params.conf")
p1 = Proj(
    '+proj=lcc +lat_1=36.41666666666666 +lat_2=35.25 +lat_0=34.33333333333334 +lon_0=-86 +x_0=600000 +y_0=0 +ellps=GRS80 +datum=NAD83 +no_defs')

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

def runHierarchicalSurvivalAnalysis():
    pass

def predict(predEndTime,predStartTime):
    grids, validGrids = setup()
    global predCount
    totalPredictions = []
    # get Number of time periods
    lenTimePeriod = 4 * 3600
    numTimePeriods = int((predEndTime - predStartTime).total_seconds() / lenTimePeriod)
    # Iterate over each time period
    for counterTimePeriod in range(numTimePeriods):
        timePeriodOver = False
        tempStart = predStartTime + timedelta(seconds=3600 * 4 * counterTimePeriod)
        tempEnd = tempStart + timedelta(seconds=3600 * 4)
        # print("Predicting for Time Period with start time" + str(tempStart))
        # initilize last crime time for each grid
        tempDictLastCrime = {}
        activeGrids = {}
        # initialize last crime dict for the grids:
        for counterY in range(len(grids)):
            for counterX in range(len(grids)):
                tempGridNum = counterY * len(grids) + counterX
                tempDictLastCrime[tempGridNum] = tempStart
                if tempGridNum in validGrids:
                    activeGrids[tempGridNum] = True
                else:
                    activeGrids[tempGridNum] = False

        bookmarkDictCurrRound = {}
        incidentCountPerGrid = {}
        while not timePeriodOver:
            # store as gridNum, crimeTime
            predictedCrimes = []
            # Iterate over each grid
            for counterY in range(len(grids)):
                for counterX in range(len(grids)):
                    tempGridNum = counterY * len(grids) + counterX
                    if tempGridNum in validGrids and activeGrids[tempGridNum]:
                        # predict time to next crime for each grid
                        nextCrimeGrid = __sampleIncidents(tempGridNum, tempDictLastCrime[tempGridNum])
                        if nextCrimeGrid < tempEnd:
                            predictedCrimes.append([tempGridNum, nextCrimeGrid])
                            # sampled crimes
                    if tempGridNum in validGrids:
                        bookmarkDictCurrRound[tempGridNum] = True

            # sort crimes
            predictedCrimes = sorted(predictedCrimes, key=itemgetter(1))
            if len(predictedCrimes) == 0:
                break
            # iteratively start looking at crimes.
            for counter in range(len(predictedCrimes)):
                # find grid c_j with least time to occurrence
                currCrime = predictedCrimes[counter][1]
                currGrid = predictedCrimes[counter][0]
                # check to see if the all remaining crimes are out of time range
                # this can be checked at the 0th crime in every round.
                # at some later counter, crimes can be outside time but they can still get reset, so ignore them.
                # if counter == 0:
                #     if isTimePeriodOver(activeGrids):
                #     #if currCrime >= tempEnd:
                #         timePeriodOver = True
                #         break
                # check if grid is active and event is in the same time zone we are looking at
                if activeGrids[currGrid] and currCrime < tempEnd and self.incidentCountPerGrid[currGrid] > 0:
                    # update crime counter:
                    predCount += 1
                    # if self.verbose: print("Accident at : " + str(predictedCrimes[counter]))
                    totalPredictions.append(predictedCrimes[counter])
                    # for all k in I(j)
                    for grid in self.influencePerGrid[currGrid]:
                        # mark as false in active grids
                        activeGrids[grid] = False
                        bookmarkDictCurrRound[grid] = False
                        # update lastCrime
                        tempDictLastCrime[grid] = currCrime

            for counterY in range(len(grids)):
                for counterX in range(len(grids)):
                    tempGridNum = counterY * len(grids) + counterX
                    if tempGridNum in validGrids:
                        if bookmarkDictCurrRound[tempGridNum] == False:
                            activeGrids[tempGridNum] = True
                        else:
                            activeGrids[tempGridNum] = False

    print("Total Number of crimes predicted is " + str(predCount))
    return totalPredictions

def getInterArrivalData():
    pass

def setup():
    grids = np.load(ConfigSectionMap(Config, "filePaths")["grids"])
    numGrids = len(grids) * len(grids[0])
    # setup reverse coordinates
    reverseCoordinate = {}
    for counterY in range(len(grids)):
        for counterX in range(len(grids)):
            gridNum = counterY * len(grids) + counterX
            reverseCoordinate[gridNum] = (grids[counterY][counterX][0] + grids[counterY][counterX][
                1]) / float(2)
    with open('reverseCoords', 'w') as f:
        pickle.dump(reverseCoordinate, f)

    #get inter-arrival data for incidents
    gridInterArrivals = np.load(ConfigSectionMap(Config, "filePaths")["gridinterarrivals"])
    rangeX, rangeY = gridInterArrivals.shape

    '''Read valid grids created by gridProcessing.py.'''
    ''':::: shapely conflicts with this version of python::::'''
    fileNameValidGrids = ConfigSectionMap(Config, "filePaths")["validgrids"]

def predictIncidents():
    #check if hierarchical learning has already been done
    hierModelLearned = False if (str(ConfigSectionMap(Config, "codeParam")["hiermodellearned"])) == "False" else True

    if not hierModelLearned:
        runHierarchicalSurvivalAnalysis()
    else:
        fileNameClusters = ConfigSectionMap(Config, "filePaths")["clusters"]
        clusters = pickle.load(open(fileNameClusters, 'rb'))

def __sampleIncidents():
    return []

def __predict(predEndTime,predStartTime,grids,validGrids,influencePerGrid):
    global predCount
    totalPredictions = []
    # get Number of time periods
    lenTimePeriod = 4 * 3600
    numTimePeriods = int((predEndTime - predStartTime).total_seconds() / lenTimePeriod)
    # Iterate over each time period
    for counterTimePeriod in range(numTimePeriods):
        timePeriodOver = False
        tempStart = predStartTime + timedelta(seconds=3600 * 4 * counterTimePeriod)
        tempEnd = tempStart + timedelta(seconds=3600 * 4)
        # print("Predicting for Time Period with start time" + str(tempStart))
        # initilize last crime time for each grid
        tempDictLastCrime = {}
        activeGrids = {}
        # initialize last crime dict for the grids:
        for counterY in range(len(grids)):
            for counterX in range(len(grids)):
                tempGridNum = counterY * len(grids) + counterX
                tempDictLastCrime[tempGridNum] = tempStart
                if tempGridNum in validGrids:
                    activeGrids[tempGridNum] = True
                else:
                    activeGrids[tempGridNum] = False

        bookmarkDictCurrRound = {}
        incidentCountPerGrid = {}
        while not timePeriodOver:
            # store as gridNum, crimeTime
            predictedCrimes = []
            # Iterate over each grid
            for counterY in range(len(grids)):
                for counterX in range(len(grids)):
                    tempGridNum = counterY * len(grids) + counterX
                    if tempGridNum in validGrids and activeGrids[tempGridNum]:
                        # predict time to next crime for each grid
                        nextCrimeGrid = __sampleIncidents(tempGridNum, tempDictLastCrime[tempGridNum])
                        if nextCrimeGrid < tempEnd:
                            predictedCrimes.append([tempGridNum, nextCrimeGrid])
                            # sampled crimes
                    if tempGridNum in validGrids:
                        bookmarkDictCurrRound[tempGridNum] = True

            # sort crimes
            predictedCrimes = sorted(predictedCrimes, key=itemgetter(1))
            if len(predictedCrimes) == 0:
                break
            # iteratively start looking at crimes.
            for counter in range(len(predictedCrimes)):
                # find grid c_j with least time to occurrence
                currCrime = predictedCrimes[counter][1]
                currGrid = predictedCrimes[counter][0]
                # check to see if the all remaining crimes are out of time range
                # this can be checked at the 0th crime in every round.
                # at some later counter, crimes can be outside time but they can still get reset, so ignore them.
                # if counter == 0:
                #     if isTimePeriodOver(activeGrids):
                #     #if currCrime >= tempEnd:
                #         timePeriodOver = True
                #         break
                # check if grid is active and event is in the same time zone we are looking at
                if activeGrids[currGrid] and currCrime < tempEnd and incidentCountPerGrid[currGrid] > 0:
                    # update crime counter:
                    predCount += 1
                    # if verbose: print("Accident at : " + str(predictedCrimes[counter]))
                    totalPredictions.append(predictedCrimes[counter])
                    # for all k in I(j)
                    for grid in influencePerGrid[currGrid]:
                        # mark as false in active grids
                        activeGrids[grid] = False
                        bookmarkDictCurrRound[grid] = False
                        # update lastCrime
                        tempDictLastCrime[grid] = currCrime

            for counterY in range(len(grids)):
                for counterX in range(len(grids)):
                    tempGridNum = counterY * len(grids) + counterX
                    if tempGridNum in validGrids:
                        if bookmarkDictCurrRound[tempGridNum] == False:
                            activeGrids[tempGridNum] = True
                        else:
                            activeGrids[tempGridNum] = False

    print("Total Number of crimes predicted is " + str(predCount))
    return totalPredictions

def convertToStatePlane(lat,long):

    return p1(lat,long)

def getGridForCoordinate():
    pass

def createSurvivalInputData(mongoItems,start,end,grids,xLow,yLow):
    #format [x, y, t1, gridX, gridY, severity]
    incidents = []
    for item in mongoItems:
        time = item['alarmDateTime']
        if (item['incidentNumber'] == "sample"):
            break
        if (start <= time <= end):
            lat = item['latitude']
            long = item['longitude']
            x,y = p1(lat,long)
            t1 = item['alarmDateTime']
            grid = getGridForCoordinate([x, y], xLow, yLow)
            gridX = int(grid[0])
            gridY = int(grid[1])
            gridNum = gridY * len(grids) + gridX
            incidents.append([x,y,t1,gridX,gridY])

    interArrivalData = getInterArrivalData(incidents)

def getRegressionFormula(distinctSeason, distinctTimeZone, dataType):
    # create regression formula based on whether factors can be used or not, based on bool values received
    seasonText = "+ factor(season)"
    timeZoneText = "+ factor(timeZone)"
    if not distinctSeason:
        seasonText = ""
    if not distinctTimeZone:
        timeZoneText = ""
    if dataType == "crime":
        rFormula = "Surv(time,death) ~ liquorCounter + liquorCounterRetail +   weather1  + weather2" + seasonText + \
                   timeZoneText + " + weekend + pastCrimeGrid2\
                     +pastCrimeGrid7	 +pastCrimeGrid30	 +pastCrimeNeighbor2	+ pastCrimeNeighbor7	+pastCrimeNeighbor30\
                        + policePriorGrid + policePriorNeighbor + policePriorL1\
                         + policePriorL2 + pawnCounter + homelessCounter	+ popDens\
                            + houseDens	+ meanIncomeScaled"

    elif dataType == "fire":
        rFormula = "Surv(interArrival,death) ~ rain + snow" + seasonText + timeZoneText + " + weekend + pastGrid2 +" \
                                                                                          " pastGrid7 + pastGrid30 + pastNeighbor2 + pastNeighbor7 + pastNeighbor30"

    return rFormula



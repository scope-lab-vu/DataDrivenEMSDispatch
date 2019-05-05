import numpy as np
from random import randint
import os
import pickle
from pyproj import Proj
import xlrd

p1 = Proj(
    '+proj=lcc +lat_1=36.41666666666666 +lat_2=35.25 +lat_0=34.33333333333334 +lon_0=-86 +x_0=600000 +y_0=0 +ellps=GRS80 +datum=NAD83 +no_defs')


def getPredictions(type="fire"):
    #type can either be fire or crime
    if type == "fire":
        if os.path.isfile('meanTraffic.txt'):
            exists = True
            with open('meanTraffic.txt','r+') as f:
                mean = float(f.readlines()[0])
        else:
            mean = 200

        if os.path.isfile('predictionsFireDashboard.pickle'):
            with open('predictionsFireDashboard.pickle','r+') as f:
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

            return output,"Successfully Generated Predictions"

        else:
            return []

    elif type=="crime":
        if os.path.isfile('/Users/ayanmukhopadhyay/Documents/Vanderbilt/CERL/dashboard/analytics-dashboard/myapp/crimePredicted.xls'):
            predictedWorkbook = xlrd.open_workbook("/Users/ayanmukhopadhyay/Documents/Vanderbilt/CERL/dashboard/analytics-dashboard/myapp/crimePredicted.xls")
            predictionWorksheet = predictedWorkbook.sheet_by_index(0)
            # get total rows:
            rows = predictionWorksheet.nrows
            try:
                columns = len(predictionWorksheet.row(0))
            except ValueError:
                return []
            numToSample = 300
            numSampled = 0
            output = []
            while numSampled < numToSample:
                index = randint(1,rows)
                row = []
                for counterCol in range(columns):
                    row.append(predictionWorksheet.cell_value(index,counterCol))
                output.append(row)
            return output
        else:
            return []


getPredictions('crime')
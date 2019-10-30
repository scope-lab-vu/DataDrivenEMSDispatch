import pandas as pd
import geopandas as gpd
import datetime
import csv
from darksky.api import DarkSky


# create nested dictionary of accidents
# to query a list of accidents on a specific interstate in a specific county in a specific logmile
# do dictionary[interstate][county][logmile]
def create_accident_dictionary(crash_data):
    accident_dictionary = {}

    for index, row in crash_data.iterrows():
        interstate = row['Route']
        county = row['County']
        logmile = (row['Beg LM'], row['End LM'])
        if interstate not in accident_dictionary:
            accident_dictionary[interstate] = {}
        if county not in accident_dictionary[interstate]:
            accident_dictionary[interstate][county] = {}
        if logmile not in accident_dictionary[interstate][county]:
            accident_dictionary[interstate][county][logmile] = []
        accident_dictionary[interstate][county][logmile].append(row)

    return accident_dictionary


# count the number of accidents on a specific interstate in a specific county in a specific logmile
def create_count_dictionary(accident_dictionary):
    count_dictionary = {}

    for interstate in accident_dictionary:
        count_dictionary[interstate] = {}
        for county in accident_dictionary[interstate]:
            count_dictionary[interstate][county] = {}
            for logmile in accident_dictionary[interstate][county]:
                num = len(accident_dictionary[interstate][county][logmile])
                count_dictionary[interstate][county][logmile] = num

    return count_dictionary


# create a arrival timeline for accidents on a specific interstate in a specific county in a specific logmile
def create_arrival_time_dictionary(accident_dictionary):
    arrival_time_dictionary = {}

    for interstate in accident_dictionary:
        arrival_time_dictionary[interstate] = {}
        for county in accident_dictionary[interstate]:
            arrival_time_dictionary[interstate][county] = {}
            for logmile in accident_dictionary[interstate][county]:
                arrival_time_dictionary[interstate][county][logmile] = []
                accident_list = accident_dictionary[interstate][county][logmile]
                for accident in accident_list:
                    date_raw = accident['Date of Crash']
                    date = date_raw.split(' ')[0]
                    [month, day, year] = date.split('/')

                    time = accident['Time of Crash']
                    hour = time / 100
                    minute = time % 100

                    accident_datetime = datetime.datetime(2000 + int(year), int(month), int(day), int(hour), int(minute))
                    arrival_time_dictionary.append(accident_datetime)

    return arrival_time_dictionary


# calculate the mean arrival time interval of accidents on a specific interstate in a specific county in a specific logmile
def calc_arrival_time_interval(arrival_time_dictionary):
    arrival_time_interval = {}

    for interstate in arrival_time_dictionary:
        arrival_time_interval[interstate] = {}
        for county in arrival_time_dictionary[interstate]:
            arrival_time_interval[interstate][county] = {}
            for logmile in arrival_time_dictionary[interstate][county]:
                arrival_time_list = arrival_time_dictionary[interstate][county][logmile]
                arrival_time_list.sort()
                # if there is only one accident
                if len(arrival_time_list) < 2:
                    arrival_time_interval[interstate][county][logmile] = float('Inf')
                    continue
                # if there are more than one accidents
                total_time = 0
                for i in range(len(arrival_time_list) - 1):
                    delta = (arrival_time_list[i + 1] - arrival_time_list[i])
                    total_time += delta.total_seconds() / 60  # in minutes
                arrival_time_interval[interstate][county][logmile] = total_time / (len(arrival_time_list) - 1)

    return arrival_time_interval


# write the dictionaries above to a csv file
# can be incorporated into the methods above so that the column names make more sense (i.e. change 'Feature' to something else)
def write_dictionary_to_csv(dictionary):
    with open('output.csv', 'w') as csv_file:
        csvwriter = csv.writer(csv_file, delimiter=',')
        csvwriter.writerow(['Interstate', 'County', 'Logmile', 'Feature'])
        for interstate in dictionary:
            for county in dictionary[interstate]:
                for logmile in dictionary[interstate][county]:
                    csvwriter.writerow([interstate, county, logmile, dictionary[interstate][county][logmile]])


# summarize weather conditions of each county and write to a file
# low-risk weathers are clear and cloudy, high-risk weathers are the rest
# weather conditions are not uniform across the entire state but would be the same within each county
# used later to normalize the rate of accident under different weather conditions
def county_annual_weather(county_location):
    API_KEY = 0 # put in your own darksky api key here
    darksky = DarkSky(API_KEY)

    with open('county_weather.csv', 'w') as csv_file:
        possible_weather = ['clear-day', 'clear-night', 'rain', 'snow', 'sleet', 'wind', 'fog', 'cloudy',
                            'partly-cloudy-day', 'partly-cloudy-night']

        csvwriter = csv.writer(csv_file, delimiter=',')
        csvwriter.writerow(['Name', 'Code', 'Latitude', 'Longitude'] + possible_weather + ['others', 'low-risk weather', 'high-risk weather'])

        for index, row in county_location.iterrows():
            lat = row['latitude']
            long = row['longitude']

            for weather in possible_weather:
                row[weather] = 0
            row['others'] = 0

            # pick a year
            year = 2017
            begin_year = datetime.datetime(year, 1, 1, 12)
            end_year = datetime.datetime(year, 12, 31, 12)
            one_day = datetime.timedelta(days=1)

            # iterate through the entire year
            next_day = begin_year
            while next_day <= end_year:
                forecast = darksky.get_time_machine_forecast(lat, long, next_day)
                report = forecast.currently
                icon = report.icon
                if icon in possible_weather:
                    row[icon] += 1
                else:
                    row['others'] += 1
                # increment date object by one day
                next_day += one_day

            row['low-risk weather'] = row['clear-day'] + row['clear-night'] + row['cloudy'] + row['partly-cloudy-day'] + row['partly-cloudy-night']
            row['high-risk weather'] = 365 - row['low-risk weather']

            csvwriter.writerow(
                [row['Name'], row['Code'], row['latitude'], row['longitude'], row['clear-day'], row['clear-night'],
                 row['rain'], row['snow'], row['sleet'], row['wind'], row['fog'], row['cloudy'],
                 row['partly-cloudy-day'], row['partly-cloudy-night'], row['others'], row['low-risk weather'], row['high-risk weather']])


# split the data into two groups
# those happened under low-risk weather and those happened under high-risk weather
def split_data_weather(crash_data):
    low_risk_weather, high_risk_weather = list(), list()

    for index, row in crash_data.iterrows():
        if row['WEATHERCON'] == 'Clear' or row['WEATHERCON'] == 'Cloudy':
            low_risk_weather.append(row)
        else:
            high_risk_weather.append(row)

    low_risk_weather_pd = pd.DataFrame(low_risk_weather, columns=crash_data.columns)
    high_risk_weather_pd = pd.DataFrame(high_risk_weather, columns=crash_data.columns)

    return low_risk_weather_pd, high_risk_weather_pd


# calculate the rate of accident on each logmile
# normalized by AADT, length of road, number of days within a year with the same weather condition
def calc_normalized_rate(low_risk_data, high_risk_data, county_annual_weather):
    freq_count = {}
    for index, row in low_risk_data.iterrows():
        road = row['Route']
        county = row['County_Cod']
        seg = (row['Begin_Poin'], row['End_Point'])
        if road not in freq_count:
            freq_count[road] = {}
        if county not in freq_count[road]:
            freq_count[road][county] = {}
        if seg not in freq_count[road][county]:
            freq_count[road][county][seg] = [0, 0, row['AADT'], row['Shape_Leng']]
        freq_count[road][county][seg][0] += 1

    for index, row in high_risk_data.iterrows():
        road = row['Route_ID']
        county = row['County_Cod']
        seg = (row['Begin_Poin'], row['End_Point'])
        if road not in freq_count:
            freq_count[road] = {}
        if county not in freq_count[road]:
            freq_count[road][county] = {}
        if seg not in freq_count[road][county]:
            freq_count[road][county][seg] = [0, 0, row['AADT'], row['Shape_Leng']]
        freq_count[road][county][seg][1] += 1

    for road in freq_count:
        for county in freq_count[road]:
            for seg in freq_count[road][county]:
                normal = freq_count[road][county][seg][0]
                extreme = freq_count[road][county][seg][1]
                AADT = freq_count[road][county][seg][2]
                leng = freq_count[road][county][seg][3]
                if AADT == 0 or leng == 0:
                    continue
                weather = county_annual_weather.iloc[int(county / 2)]
                total_low_risk = weather['low-risk weather']
                total_high_risk = 365 - total_low_risk
                freq_count[road][county][seg].append(normal / AADT / leng / total_low_risk)
                freq_count[road][county][seg].append(extreme / AADT / leng / total_high_risk)
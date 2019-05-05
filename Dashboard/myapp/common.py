import pymongo
from pymongo import MongoClient
import json
from bson import json_util
from bson.json_util import dumps
import ast
import datetime
import pytz
import time
from bson.objectid import ObjectId
import calendar
import pykalman
import numpy as np
import math
from math import radians, cos, sin, asin, sqrt
import thread
from myconfig import MONGODB_HOST, MONGODB_PORT

print MONGODB_HOST, MONGODB_PORT

class common_api:

	db_connection_remote = MongoClient(MONGODB_HOST, MONGODB_PORT)

	# static GTFS db name
	DB_GTFS = 'nashville-mta22020160915'
	DB_GTFS_STOPS = 'stops'
	DB_GTFS_TRIPS = 'trips'
	DB_GTFS_SHAPES = 'shapes'
	DB_GTFS_ROUTES = 'routes'
	DB_GTFS_STOPTIMES = 'stop_times'
	DB_GTFS_CALENDAR = 'calendar'

	# real-time GTFS db name
	DB_REALTIME = 'thub_database'
	DB_REALTIME_VEHICLE = 'vehicle_positions'

	db_static_gtfs_stops = None
	db_static_gtfs_trips = None
	db_static_gtfs_routes = None
	db_static_gtfs_shapes = None
	db_static_gtfs_stoptimes = None
	db_static_gtfs_calendar = None

	db_realtime_vehicleposition = None
	
	db_segments_shared_coordinates = None
	db_segments_shared_segments = None
	db_segments_shapes = None

	# 
	db_microservice_vehicle_positions = None
	db_microservice_segment_predictions = None
	db_microservice_trip_predictions = None

	db_thub_dashboard_routeiddirectionid_tripid = None
	db_segments_polylines = None

	def __init__(self):

		self.db_static_gtfs_stops = self.db_connection_remote[self.DB_GTFS][self.DB_GTFS_STOPS]
		self.db_static_gtfs_trips = self.db_connection_remote[self.DB_GTFS][self.DB_GTFS_TRIPS]
		self.db_static_gtfs_routes = self.db_connection_remote[self.DB_GTFS][self.DB_GTFS_ROUTES]
		self.db_static_gtfs_shapes = self.db_connection_remote[self.DB_GTFS][self.DB_GTFS_SHAPES]
		self.db_static_gtfs_stoptimes = self.db_connection_remote[self.DB_GTFS][self.DB_GTFS_STOPTIMES]
		self.db_static_gtfs_calendar = self.db_connection_remote[self.DB_GTFS][self.DB_GTFS_CALENDAR]
		self.db_segments_shared_coordinates = self.db_connection_remote["thub_segments_nashville-mta22020160915"]["shared_coordinates"]
		self.db_segments_shared_segments = self.db_connection_remote["thub_segments_nashville-mta22020160915"]["shared_segments"]
		self.db_segments_shapes = self.db_connection_remote["thub_segments_nashville-mta22020160915"]["shapes"]

		self.db_realtime_vehicleposition = self.db_connection_remote[self.DB_REALTIME][self.DB_REALTIME_VEHICLE]

		self.db_microservice_vehicle_positions = self.db_connection_remote["thub_microservice"]["vehicle_positions"]
		self.db_microservice_segment_predictions = self.db_connection_remote["thub_microservice"]["segment_predictions"]
		self.db_microservice_trip_predictions = self.db_connection_remote["thub_microservice"]['trip_predictions']

		self.db_thub_dashboard_routeiddirectionid_tripid = self.db_connection_remote['thub_dashboard']['routeiddirectionid_tripid']
		self.db_segments_polylines = self.db_connection_remote['thub_segments_nashville-mta22020160915']['polylines']

	def convert_nashvilletime_to_timestamp(self, year, month, day, hour, minute, second):
		# print "%d/%d/%d %d:%d:%d" % (year, month, day, hour, minute, second)
		tz = pytz.timezone('CST6CDT')
		dt_with_tz = tz.localize(datetime.datetime(year, month, day, hour, minute, second), is_dst=None)
		ts = (dt_with_tz - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds()
		return ts

	def get_coor_array_by_tripid(self, trip_id):
		# start_time = time.time()
		array_result = []
		tpResults = self.db_static_gtfs_trips.find({'trip_id': trip_id})
		shape_id = ''
		for tpResult in tpResults:
			shape_id = tpResult['shape_id']
		tpResults = self.db_static_gtfs_shapes.find({'shape_id':shape_id}) \
			.sort([['shape_pt_sequence', pymongo.ASCENDING]])
		for tpResult in tpResults:
			tpResult = json.dumps(tpResult, default=json_util.default)
			tpResult = ast.literal_eval(tpResult)
			array_result.append(tpResult)
		# print("--- %s seconds ---" % (time.time() - start_time))
		return array_result

	def cal_distance(self, origin, destination):
		lat1, lon1 = origin
		lat2, lon2 = destination
		radius = 6367 # km

		dlat = math.radians(lat2-lat1)
		dlon = math.radians(lon2-lon1)
		a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
		    * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
		c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
		km = radius * c
		return km

	def kalman_filter_delay(self, delayArray):
		if len(delayArray)<1:
			return [[0]]
		elif len(delayArray)==1:
			return [[delayArray[0]]]
		kf = pykalman.KalmanFilter(transition_matrices = [1], observation_matrices = [1])
		measurements = np.asarray(delayArray) 
		kf = kf.em(measurements, n_iter = 10)
		# measurements[-1]
		(filtered_state_means, filtered_state_covariances) = kf.filter(measurements)
		(smoothed_state_means, smoothed_state_covariances) = kf.smooth(measurements)
		return filtered_state_means

	def get_shapeid_arraytripid_from_tripids(self, array_tripid):
		map_result = {}
		tpResults = self.db_static_gtfs_trips.find({"trip_id": {"$in": array_tripid}})
		for tpResult in tpResults:
			shape_id = tpResult['shape_id']
			trip_id = tpResult['trip_id']
			if shape_id in map_result:
				map_result[shape_id].append(trip_id)
			else:
				map_result[shape_id] = [ trip_id ]
		return map_result


	# def get_shapeid_tripid_from_tripids(self, array_tripid):
	# 	map_result = {}
	# 	tpResults = self.db_static_gtfs_trips.find({"trip_id": {"$in": array_tripid}})
	# 	for tpResult in tpResults:
	# 		tpResult = json.dumps(tpResult, default=json_util.default)
	# 		tpResult = ast.literal_eval(tpResult)
	# 		map_result[tpResult['shape_id']] = tpResult['trip_id']
	# 		map_result[tpResult['trip_id']] = tpResult['shape_id']
	# 	return map_result

	def intToSeconds(self, intNum):
		intReturn = intNum%100
		intNum = (intNum-intNum%100)/100
		intReturn += 60*(intNum%100)
		intNum = (intNum-intNum%100)/100
		intReturn += 3600*(intNum%100)
		return intReturn

	def convert_stringtime_to_seconds(self, string_time):
		array_time = string_time.split(":")
		int_seconds = 0
		int_seconds += int(array_time[2])
		int_seconds += int(array_time[1])*60
		int_seconds += int(array_time[0])*60*60
		return int_seconds
		
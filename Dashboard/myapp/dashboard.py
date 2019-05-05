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
# from datetime import datetime, date
import calendar
import pykalman
import numpy as np
# import matplotlib.pyplot as pyplot
import math
from math import radians, cos, sin, asin, sqrt
import thread
import random
import common
import requests

global common_api
common_api = common.common_api()

class route_segment:

	def get_map_routes(self):
		array_route = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 15, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 33, 34, 35, 36, 37, 38, 41, 42, 43, 44, 50, 52, 55, 56, 60, 61, 72, 76, 84, 86, 93, 96]
		array_result = []
		for route in array_route:
			route = str(route)
			print route
			results = common_api.db_static_gtfs_trips.find({"route_id": str(route)})
			for result in results:
				trip_id = result['trip_id']
				results_trips = common_api.db_static_gtfs_trips.find({"trip_id": trip_id})
				for result_trip in results_trips:
					shape_id = result_trip['shape_id']
					array_coor = []
					tpResults = common_api.db_static_gtfs_shapes.find({'shape_id':shape_id}) \
						.sort([['shape_pt_sequence', pymongo.ASCENDING]])
					for tpResult in tpResults:
						tpResult = json.dumps(tpResult, default=json_util.default)
						tpResult = ast.literal_eval(tpResult)
						array_coor.append([tpResult['shape_pt_lat'], tpResult['shape_pt_lon']])
					array_result.append(array_coor)
					break
				break
		print len(array_result), len(array_route)
		with open('routes_coors.json', 'w') as fp:
			json.dump(array_result, fp)


	#########################################################
	### run once, demo only, needs to be modified for all gtfs versions
	#########################################################
	def get_trips_for_all_routes_and_headsigns(self):
		array_valid_service_id = []
		calendars = common_api.db_static_gtfs_calendar.find()
		for calendar in calendars:
			service_id = calendar['service_id']
			start_date = calendar['start_date']
			end_date = calendar['end_date']
			monday = calendar['monday']
			if start_date<="20161003" and end_date>="20161003" and monday=="1":
				array_valid_service_id.append(service_id)
		print "array_valid_service_id:", array_valid_service_id

		result_map = {}
		trips = common_api.db_static_gtfs_trips.find()
		count=0
		for trip in trips:
			service_id = trip['service_id']
			if service_id not in array_valid_service_id:
				continue
			print "-> get_trips_for_all_routes_and_headsigns:", count
			count+=1
			key = trip['route_id']+'|'+trip['trip_headsign']
			if key in result_map:
				result_map[key].append(trip['trip_id'])
			else:
				result_map[key] = [trip['trip_id']]
		array_to_insert = []
		iii=0
		for key, trips in result_map.iteritems():
			iii+=1
			print iii
			array_tripid = []
			array_departuretime = []
			map_departuretime_tripid = {}
			for trip in trips:
				trip_id = trip
				if trip_id not in array_tripid:				
					stoptime = common_api.db_static_gtfs_stoptimes.find_one({'trip_id':trip_id,'stop_sequence': 1})
					if stoptime:
						array_departuretime.append(stoptime['departure_time'])
						map_departuretime_tripid[stoptime['departure_time']] = trip_id
			array_departuretime = list(set(array_departuretime))
			array_departuretime.sort()
			for departure_time in array_departuretime:
				array_tripid.append(map_departuretime_tripid[departure_time])
			array_to_insert.append({"routeiddirectionid":key, "trip_ids": array_tripid, "departure_times": array_departuretime})
		common_api.db_thub_dashboard_routeiddirectionid_tripid.insert_many(array_to_insert, ordered=False)


	def get_trips(self, route_id, trip_headsign):
		key = route_id+'|'+trip_headsign
		result = common_api.db_thub_dashboard_routeiddirectionid_tripid.find_one({"routeiddirectionid":key})
		if result:
			result = json.dumps(result, default=json_util.default)
    			result = ast.literal_eval(result)
			return [result['trip_ids'], result['departure_times']]
		array_tripid = []
		array_departuretime = []
		map_departuretime_tripid = {}
		route_id = str(route_id)
		trips = common_api.db_static_gtfs_trips.find({'route_id': route_id, 'trip_headsign': trip_headsign})
		for trip in trips:
			trip_id = trip['trip_id']
			if trip_id not in array_tripid:				
				stoptime = common_api.db_static_gtfs_stoptimes.find_one({'trip_id':trip_id,'stop_sequence': 1})
				if stoptime:
					array_departuretime.append(stoptime['departure_time'])
					map_departuretime_tripid[stoptime['departure_time']] = trip_id
		array_departuretime.sort()
		for departure_time in array_departuretime:
			array_tripid.append(map_departuretime_tripid[departure_time])
		return [array_tripid, array_departuretime]

	def get_all_headsigns(self, route_id):
		array_headsigns = []
		route_id = str(route_id)
		trips = common_api.db_static_gtfs_trips.find({'route_id': route_id})
		for trip in trips:
			headsign = trip['trip_headsign']
			if headsign not in array_headsigns:
				array_headsigns.append(headsign)
		return array_headsigns

	def get_all_routeid(self):
		array_routeid = []
		routes = common_api.db_static_gtfs_routes.find()
		for route in routes:
			route = json.dumps(route, default=json_util.default)
    			route = ast.literal_eval(route)
			array_routeid.append(route['route_id'])
		for i in range(len(array_routeid)):
			array_routeid[i] = int(array_routeid[i])
		array_routeid = list(set(array_routeid))
		array_routeid.sort()
		for i in range(len(array_routeid)):
			array_routeid[i] = str(array_routeid[i])
		return array_routeid

	def get_predictions_for_trip(self, trip_id):
		try:
			url = 'http://127.0.0.1:8000/predict/tripid/'+str(trip_id)
			# print "url", url
			r = requests.get( url )
			responseJson = r.json()
			stop_times = responseJson['stops']
			
			# realtime_prediction = analytics_realtime.realtime_prediction()
			# stop_times = realtime_prediction.get_prediction_for_trip_id(trip_id, current_timestamp)
			array_coor = []
			string_prediction = ""
			for stop_time in stop_times:
				lat = stop_time['stop_lat']
				lng = stop_time['stop_lon']
				array_coor.append([lat, lng])
				prediction_minute = int(stop_time['delay'][0]/60)
				string_prediction+= '<p><span class="stop-label">%d. %s</span><br/><span class="scheduled-label">Scheduled Time: %s</span><span class="prediction-label">Delay: %d min</span></p><hr/>' % (stop_time['stop_sequence'], stop_time['stop_name'].replace('&', '&#38;'), stop_time['arrival_time'][:5], prediction_minute)
			return {'coordinates': array_coor, 'prediction': string_prediction}
		except:
			print "Exception: get_predictions_for_trip"

	# TESTING
	def get_stops_of_trip(self):
		array_coor = []
		shape_id = "9969"
		tpResults = common_api.db_static_gtfs_stoptimes.find({'trip_id':"121155"}) \
			.sort([['stop_sequence', pymongo.ASCENDING]])
		for tpResult in tpResults:
			stop_id = tpResult['stop_id']
			stop = common_api.db_static_gtfs_stops.find_one({'stop_id': stop_id})
			if stop:
				lat = stop['stop_lat']
				lng = stop['stop_lon']
				array_coor.append([lat, lng])
				print '<p><span class="stop-label">%d. %s</span><br/><span class="scheduled-label">Scheduled Time: %s</span><span class="prediction-label">Delay: %d min</span></p><hr/>' % (tpResult['stop_sequence'], stop['stop_name'].replace('&', '&#38;'), tpResult['arrival_time'][:5], random.randrange(0, 3))
		return array_coor

	def get_all_shapeids(self):
		array_shapeid = []
		trips = common_api.db_static_gtfs_trips.find()
		for trip in trips:
			shape_id = trip['shape_id']
			if shape_id and shape_id not in array_shapeid:
				array_shapeid.append(shape_id)
		# return ['9969']
		return array_shapeid

	def get_shape_array(self, shape_id):
		array_result = []
		tpResults = common_api.db_static_gtfs_shapes.find({'shape_id':shape_id}) \
			.sort([['shape_pt_sequence', pymongo.ASCENDING]])
		for tpResult in tpResults:
			tpResult = json.dumps(tpResult, default=json_util.default)
			tpResult = ast.literal_eval(tpResult)
			array_result.append(tpResult)
		return array_result

	def get_polylines_for_all_shapeids(self):
		array_shapeid = self.get_all_shapeids()
		# print array_shapeid
		array_segmentid = []
		# array_shapeid = ['9781']
		
		for shape_id in array_shapeid:
			print "--> calculating", shape_id, array_shapeid.index(shape_id), len(array_shapeid)
			check_db = common_api.db_segments_polylines.find_one({"shape_id": shape_id})
			if check_db:
				continue
			result_array_segments = []
			route = common_api.db_segments_shapes.find_one({'shape_id': shape_id})
			array_one_shape = self.get_shape_array(shape_id)
			if route:
				segments = route['segments']
				sequence_flag = 0

				for segment in segments:
					segment_id = segment['segment_id']
					tuple_distance = segment['distance']
					# if segment_id not in array_segmentid:
					# 	array_segmentid.append(segment_id)
					if True:
						if len(tuple_distance)==2:
							# print "++++++++++++++++++++++++++++++++++++++   ",tuple_distance
							if array_one_shape[sequence_flag]['shape_dist_traveled']<tuple_distance[0]:
								new_array_coor = []
								for i in range(sequence_flag, len(array_one_shape)):
									sequence_flag = i
									if array_one_shape[i]['shape_dist_traveled']<tuple_distance[0]:
										new_array_coor.append([array_one_shape[i]['shape_pt_lat'], array_one_shape[i]['shape_pt_lon']])
										# print "-- >", array_one_shape[i]['shape_dist_traveled']
									else: break
								
								# print new_array_coor

								if len(new_array_coor)>=2: 
									result_array_segments.append(new_array_coor)
							if array_one_shape[sequence_flag]['shape_dist_traveled']>=tuple_distance[0]:
								new_array_coor = []
								for i in range(sequence_flag, len(array_one_shape)):
									sequence_flag = i
									if array_one_shape[i]['shape_dist_traveled']>=tuple_distance[0] and array_one_shape[i]['shape_dist_traveled']<=tuple_distance[1]:
										new_array_coor.append([array_one_shape[i]['shape_pt_lat'], array_one_shape[i]['shape_pt_lon']])
										# print "## >", array_one_shape[i]['shape_dist_traveled']
									else: break
								
								# print new_array_coor
								if len(new_array_coor)>=2: 
									result_array_segments.append(new_array_coor)
			if len(result_array_segments)<2:
				print " -------------------------------------------------------  ", shape_id
			common_api.db_segments_polylines.insert({"shape_id": shape_id, "polylines":result_array_segments})

	# def get_shapeids_for_routes(self):
	# 	array_routeid = []
	# 	# get all route ids
	# 	all_routes = col_gtfs_routes.find()
	# 	for route in all_routes:
	# 		array_routeid.append(route['route_id'])
	# 	print len(array_routeid)
	# 	# get a shape for each route
	# 	array_shapeid = []
	# 	for route_id in array_routeid:
	# 		trip = col_gtfs_trips.find_one({'route_id': route_id})
	# 		if trip:
	# 			array_shapeid.append(trip['shape_id'])
	# 	return array_shapeid

	def get_segments_for_tripid(self, trip_id):
		result_array_segments = []
		trip = common_api.db_static_gtfs_trips.find_one({'trip_id': trip_id})
		if trip:
			shape_id = trip['shape_id']
			check_db = common_api.db_segments_polylines.find_one({"shape_id": shape_id})
			if not check_db:
				self.get_polylines_for_all_shapeids()
				check_db = common_api.db_segments_polylines.find_one({"shape_id": shape_id})
			if check_db and "polylines" in check_db:
				for segment in check_db['polylines']:
					if segment not in result_array_segments:
						result_array_segments.append(segment)

		print len(result_array_segments)
		return result_array_segments

	def get_all_segments(self):
		result_array_segments = []
		array_shapeid = self.get_all_shapeids()
		for shape_id in array_shapeid:
			# print "--> pulling", shape_id, array_shapeid.index(shape_id), len(array_shapeid)
			check_db = common_api.db_segments_polylines.find_one({"shape_id": shape_id})
			if not check_db:
				self.get_polylines_for_all_shapeids()
				check_db = common_api.db_segments_polylines.find_one({"shape_id": shape_id})
			if check_db and "polylines" in check_db:
				for segment in check_db['polylines']:
					if segment not in result_array_segments:
						result_array_segments.append(segment)

		print len(result_array_segments)
		return result_array_segments

# ccc = route_segment()
# ccc.get_map_routes()
# get_all_segments()
# ccc = route_segment()
# ccc.get_trips_for_all_routes_and_headsigns()
# print ccc.get_vehicle_location_for_trip("124720", 1464886800)
# ccc.get_polylines_for_all_shapeids()
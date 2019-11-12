import math
import geopandas as gpd
import pandas as pd
import numpy as np


# use the haversine formula to calculate the distance (in miles) between two points based on their GPS coordinates
def haversine_distance(point1, point2):
    (lat1, lon1), (lat2, lon2) = point1, point2
    earthR = 3958.8
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1ra = math.radians(lat1)
    lat2ra = math.radians(lat2)

    # haversine formula
    a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.sin(dLon / 2) * math.sin(dLon / 2) * math.cos(
        lat1ra) * math.cos(lat2ra)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earthR * c


# calculate the length (in miles) of a road based on its linestring representation
def linestring_length(linestring):
    length = 0
    points = linestring.coords
    for i in range(len(points) - 1):
        length += haversine_distance(points[i], points[i + 1])
    return length


# use the menger theory to calculate the curvature based on three points
def menger_curvature(linestring):
    # pick the first point, last point, and middle point of linestring
    point1 = linestring.coords[0]
    point2 = linestring.coords[-1]
    point3 = linestring.coords[int(len(linestring.coords) / 2)]

    dis1 = haversine_distance(point1, point2)
    dis2 = haversine_distance(point1, point3)
    dis3 = haversine_distance(point2, point3)

    half = (dis1 + dis2 + dis3) / 2
    area = math.sqrt(half * (half - dis1) * (half - dis2) * (half - dis3))
    # menger theory
    return 4 * area / dis1 / dis2 / dis3


# calculate the sinuosity of a road based on its linestring representation
def calc_sinuosity(linestring):
    start = linestring.coords[0]
    end = linestring.coords[-1]
    length = linestring_length(linestring)
    straight_line_distance = haversine_distance(start, end)
    # definition of sinuosity
    return length / straight_line_distance


# calculate the length (in miles), sinuosity and curvature of a road based on its linestring representation
def haversine_sinuosity_menger(shapefile):
    length, sinuosity, curvature = list(), list(), list()
    for linestring in shapefile['geometry']:
        # skip unknown geometry type
        if linestring is None or (linestring.geom_type != 'LineString' and linestring.geom_type != 'MultiLineString'):
            length.append(0)
            sinuosity.append(0)
            curvature.append(0)
            continue
        # if it's a multi linestring, pick the first linestring
        if linestring.geom_type == 'MultiLineString':
            linestring = list(linestring.geoms)[0]

        # if there are fewer than 3 points on the linestring, no need to calculate sinuosity and curvature
        if len(linestring.coords) < 3:
            length.append(linestring_length(linestring))
            sinuosity.append(1)
            curvature.append(0)
        else:
            length.append(linestring_length(linestring))
            sinuosity.append(calc_sinuosity(linestring))
            curvature.append(menger_curvature(linestring))

    shape_feature = {'length': length, 'sinuosity': sinuosity, 'curvature': curvature}

    return pd.DataFrame(shape_feature)


def ramp(shapefile):
    standard_id_length = 10
    is_ramp = list()
    for index, row in shapefile.iterrows():
        route_id = row['Route_ID']
        if len(route_id) > standard_id_length:
            is_ramp.append(1)
        else:
            is_ramp.append(0)
    return pd.DataFrame({'is_ramp': is_ramp})


def count_intersections(shapefile):
    ramp_shapefile = shapefile[shapefile.is_ramp == 1]
    ramp_buffer = gpd.GeoDataFrame(geometry=ramp_shapefile.geometry.buffer(0.001))
    exclude_ramp_shapefile = shapefile[shapefile.is_ramp == 0]
    join_shapefile = gpd.sjoin(exclude_ramp_shapefile, ramp_buffer, op='intersects', how='left')

    count = []
    for index, row in join_shapefile.iterrows():
        if math.isnan(row['index_right']):
            count.append(0)
        else:
            count.append(1)
    join_shapefile['intersection_count'] = count

    counts = pd.pivot_table(join_shapefile, index=join_shapefile.index, values='intersection_count', aggfunc=np.sum)

    return counts
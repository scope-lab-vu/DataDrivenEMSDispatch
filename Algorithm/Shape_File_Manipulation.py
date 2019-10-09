# import necessary packages
import geopandas as gpd
import pandas as pd
import math


# read in shapefile
shapefile = gpd.read_file("tennessee2017/Tennessee2017.shp")


# print out the features of the shapefile
print(shapefile.columns)
print()
print(shapefile.shape)


# determine if a road ID is interstate
def is_interstate(ID, interstate_list):
    for interstate in interstate_list:
        if interstate in ID:
            return True
    return False


# identify interstates in a list of road IDs
def interstate_filter(ID_list, interstate_list):
    boolean_list = list()
    for ID in ID_list:
        boolean_list.append(is_interstate(ID, interstate_list))
    return boolean_list


interstate_list = ['I0003', 'I0022', 'I0024', 'I0026', 'I0040',
                   'I0055', 'I0065', 'I0069', 'I0075', 'I0081',
                   'I0124', 'I0140', 'I0155', 'I0169', 'I0181',
                   'I0240', 'I0255', 'I0265', 'I0269', 'I0275',
                   'I0440', 'I0475', 'I0640', 'I0840']


interstate_shapefile = shapefile[interstate_filter(shapefile['Route_ID'], interstate_list)]
interstate_shapefile = interstate_shapefile.reset_index(drop=True)


# calculate the distance (in km) between two points based on their GPS coordinates
def distance(point1, point2):
    (lat1, lon1), (lat2, lon2) = point1, point2
    earthR = 6371
    dLat = math.radians(lat2-lat1)
    dLon = math.radians(lon2-lon1)
    lat1ra = math.radians(lat1)
    lat2ra = math.radians(lat2)

    # use the haversine formula
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.sin(dLon/2) * math.sin(dLon/2) * math.cos(lat1ra) * math.cos(lat2ra)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return earthR * c


# calculate the length of a road based on its linestring representation
def linestring_length(linestring):
    length = 0
    points = linestring.coords
    for i in range(len(points) - 1):
        length += distance(points[i], points[i+1])
    return length


# calculate the length, straight line distance, and sinuosity of a road based on its linestring representation
# return (length, straight_line_distance, sinuosity)
def calculate_sinuosity(linestring):
    if linestring is None:
        return (0,0,0)
    elif linestring.geom_type == 'LineString':
        start = linestring.coords[0]
        end = linestring.coords[-1]
        length = linestring_length(linestring)
        straight_line_distance = distance(start, end)
        sinuosity = length / straight_line_distance
        return (length, straight_line_distance, sinuosity)
    elif linestring.geom_type == 'MultiLineString':
        linestring = list(linestring.geoms)[0]
        start = linestring.coords[0]
        end = linestring.coords[-1]
        length = linestring_length(linestring)
        straight_line_distance = distance(start, end)
        sinuosity = length / straight_line_distance
        return (length, straight_line_distance, sinuosity)


road_length, straight_line_distance, sinuosity = list(), list(), list()
for linestring in interstate_shapefile['geometry']:
    l, d, s = calculate_sinuosity(linestring)
    road_length.append(l)
    straight_line_distance.append(d)
    sinuosity.append(s)


# use the menger theory to calculate the curvature based on three points
def menger_curvature(point1, point2, point3):
    dis1 = distance(point1, point2)
    dis2 = distance(point1, point3)
    dis3 = distance(point2, point3)
    half = (dis1 + dis2 + dis3) / 2
    area = math.sqrt(half * (half-dis1) * (half-dis2) * (half-dis3))
    return 4 * area / dis1 / dis2 / dis3


curvature = list()
for linestring in interstate_shapefile['geometry']:
    if linestring is None:
        curvature.append(0)
    elif linestring.geom_type == 'LineString':
        if len(linestring.coords) < 3:
            curvature.append(0)
        else:
            div = int(len(linestring.coords) / 3)
            point1 = linestring.coords[0]
            point2 = linestring.coords[div]
            point3 = linestring.coords[div*2]
            curvature.append(menger_curvature(point1, point2, point3))
    elif linestring.geom_type == 'MultiLineString':
        linestring = list(linestring.geoms)[0]
        if len(linestring.coords) < 3:
            curvature.append(0)
        else:
            div = int(len(linestring.coords) / 3)
            point1 = linestring.coords[0]
            point2 = linestring.coords[div]
            point3 = linestring.coords[div*2]
            curvature.append(menger_curvature(point1, point2, point3))


new_feature = pd.concat([pd.DataFrame(road_length), pd.DataFrame(straight_line_distance), pd.DataFrame(sinuosity), pd.DataFrame(curvature)], axis = 1)
new_feature.columns = ['road length', 'straight line distance', 'sinuosity', 'curvature']
interstate_shapefile = pd.concat([interstate_shapefile, new_feature], axis = 1)


interstate_shapefile.to_excel('interstate_shapefile.xlsx')
import math


# used to filter interstates of etrim data
def etrim_interstate_filter(etrim, interstate_list):
    interstate_etrim = etrim[etrim['Route'].isin(interstate_list)]
    return interstate_etrim.reset_index(drop=True)


# used to filter interstates of shapefile
# shapefile's route ids are more complicated, interstate ids are embedded in the route ids
def shapefile_interstate_filter(shapefile, interstate_list):
    boolean_list = list()
    for id in shapefile['Route_ID']:
        boolean_list.append(contain_interstate(id, interstate_list))
    interstate_shapefile = shapefile[boolean_list]
    return interstate_shapefile.reset_index(drop=True)


# determine if a route id contains an interstate id
def contain_interstate(id, interstate_list):
    for interstate in interstate_list:
        if interstate in id:
            return True
    return False


# features with too many missing values and unimportant features are eliminated
def etrim_feature_filter(etrim):
    return etrim[
        ['GPS Coordinate Latitude', 'GPS Coordinate Longitude', 'Date of Crash', 'Time of Crash', 'Weather Cond',
         'Light Conditions']]


# features with too many missing values and unimportant features are eliminated
def shapefile_feature_filter(shapefile):
    return shapefile[
        ['Route_ID', 'Begin_Poin', 'End_Point', 'Route_Numb', 'Route_Name', 'Urban_Code', 'County_Cod', 'Truck_NN',
         'Through_La', 'Speed_Limi', 'AADT', 'AADT_Singl', 'AADT_Combi', 'IRI', 'geometry']]


# cleans bad records in etrim data
# wrong latitude and longitude, missing coordinates
def etrim_cleaner(etrim):
    for index, row in etrim.iterrows():
        if row['GPS Coordinate Latitude'] == 0 or row['GPS Coordinate Longitude'] == 0 or math.isnan(
                row['GPS Coordinate Latitude']) or math.isnan(row['GPS Coordinate Longitude']):
            etrim.drop(index, inplace=True)
        if row['GPS Coordinate Latitude'] < 0:
            etrim.at[index, 'GPS Coordinate Latitude'] = -row['GPS Coordinate Latitude']
        if row['GPS Coordinate Longitude'] > 0:
            etrim.at[index, 'GPS Coordinate Longitude'] = -row['GPS Coordinate Longitude']
    return etrim.reset_index(drop=True)


# cleans bad records in shapefile
# missing linestring
def shapefile_cleaner(shapefile):
    return shapefile[shapefile.loc[:, 'Shape_Leng'] != 0].reset_index(drop=True)

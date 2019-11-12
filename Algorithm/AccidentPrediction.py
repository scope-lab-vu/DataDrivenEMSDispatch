import datetime
import math
import holidays
import matplotlib.pyplot as plt
import pandas as pd
import geopandas as gpd
import numpy as np
from darksky.api import DarkSky


from Algorithms.general_data_preprocessing import *
from Algorithms.etrim_data_manipulation import *
from Algorithms.shapefile_analysis import *

interstate_list = ['I0003', 'I0022', 'I0024', 'I0026', 'I0040',
                   'I0055', 'I0065', 'I0069', 'I0075', 'I0081',
                   'I0124', 'I0140', 'I0155', 'I0169', 'I0181',
                   'I0240', 'I0255', 'I0265', 'I0269', 'I0275',
                   'I0440', 'I0475', 'I0640', 'I0840']

darksky_key = 0

# step 1: obtain dataset
etrim_data = pd.read_csv("Data/etrim.csv")
shapefile = gpd.read_file('Data/tennessee2017/Tennessee2017.shp')


# step 2: general data preproessing
# step 2(a): filter interstates
interstate_etrim = etrim_interstate_filter(etrim_data, interstate_list)
interstate_shapefile = shapefile_interstate_filter(shapefile, interstate_list)
# step 2(b): clean bad record
interstate_etrim = etrim_cleaner(interstate_etrim)
interstate_shapefile = shapefile_cleaner(interstate_shapefile)
# step 2(c): filter important features
interstate_etrim = etrim_feature_filter(interstate_etrim)
interstate_shapefile = shapefile_feature_filter(interstate_shapefile)


# step 3: etrim data manipulation
# step 3(a): process temporal features
temporal_features = process_temporal(interstate_etrim)
interstate_etrim = pd.concat([interstate_etrim.loc[:, :'GPS Coordinate Longitude'], temporal_features, interstate_etrim.loc[:, 'Weather Cond':]], axis=1)
derived_temporal_features = derive_temporal(interstate_etrim)
interstate_etrim = pd.concat([interstate_etrim.loc[:, :'timestamp'], derived_temporal_features, interstate_etrim.loc[:, 'Weather Cond':]], axis=1)
# step 3(b): aggregate dark sky data
darksky = DarkSky(darksky_key)
weather_data = get_darksky_feature(interstate_etrim, darksky)
interstate_etrim = pd.concat([interstate_etrim.loc[:, :'timestamp'], weather_data, interstate_etrim.loc[:, 'Light Conditions':]], axis=1)


# finish step 3, write to file
interstate_etrim.to_csv("Data/interstate_etrim.csv")


# step 4: shapefile analysis
# step 4(a)(b): haversine distance, sinuosity, menger curvature
shape_features = haversine_sinuosity_menger(interstate_shapefile)
interstate_shapefile = pd.concat([interstate_shapefile.loc[:, :'IRI'], shape_features, interstate_shapefile['geometry']], axis=1)
# step 4(c): is_ramp
is_ramp = ramp(interstate_shapefile)
interstate_shapefile = pd.concat([interstate_shapefile.loc[:, :'curvature'], is_ramp, interstate_shapefile['geometry']], axis=1)
# step 4(d): number of intersection
count = count_intersections(interstate_shapefile)
interstate_shapefile = pd.concat([interstate_shapefile.loc[:, :'is_ramp'], count, interstate_shapefile['geometry']], axis=1)
# for ramps, the number of intersections is 2
for index, row in interstate_shapefile.iterrows():
    if row['is_ramp'] == 1:
        interstate_shapefile.at[index, 'count'] = 2

# finish step 4, write to file
interstate_shapefile.to_file('Data/interstate_shapefile/interstate_shapefile.shp')

# step 5: spatial join etrim and shapefile
etrim_onto_shapefile = gpd.read_file('Data/etrim_onto_shapefile/etrim_onto_shapefile.shp')
shapefile_onto_etrim = gpd.read_file('Data/shapefile_onto_etrim/shapefile_onto_etrim.shp')


# finish step 5, write to file
etrim_onto_shapefile.to_csv('Data/etrim_onto_shapefile.csv')
shapefile_onto_etrim.to_csv('Data/shapefile_onto_etrim.csv')
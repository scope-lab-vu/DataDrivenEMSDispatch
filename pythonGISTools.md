

# List of python GIS tools

* Shapely: We use shapely mostly for representing spatial objects. Commonly we use geopoints of type (latitude, longitude), linestrings which are a path of geocoordinates and polygons which are closed linestrings.

* Reference documentation: https://shapely.readthedocs.io/en/stable/manual.html#

* Rtree: This is a python wrapper around libspatialindex. We use it mostly for indexing as Rtree is a pretty efficient geospatial index commonly used in PostGIS/ESRI ect. It is particularly useful for in memory indexing.

* Reference documentation: http://toblerity.org/rtree/

* Geopandas: this is built on top of Shapely and Rtree. It is essentially a fork of the Python Pandas module, with the ability to store geometric objects in Pandas Series and Dataframes. You can perform regular Pandas queries (closely related to SQL) with geometry columns indexed with Rtree.

* Reference documentation: http://geopandas.org/

* Networkx: This is a graph module. It provides efficient representations of graph structures and integrated algorithms such as Dikstra ect. 

* Reference documentation: https://networkx.github.io/

* OSMnx: I have used this module in past research. It is poorly maintained, however very usefully for transportation research. It is built on top of networkx with OpenStreetMap (OSM) support. It allows you to download OSM data for a region and directly maps it to a networkx structure.

* Reference documentation: https://osmnx.readthedocs.io/en/stable/

* Folium: This is a python wrapper around a javascript geospatial visualization library. I highly recommend it, it provides interactive tileset visualizations. It includes builtin tilesets from OpenStreetMaps and Mapbox.

* Reference documentation: https://python-visualization.github.io/folium/

* GeoJSON: this is a useful data schema for geospatial data which interacts seemlessly with JSON based applications

* Reference documentation: https://geojson.org/

* PyMongo: much of our long term data is stored in MongoDB, I typically use the pymongo client. This is good to know as most of our data regardless of storage mechanism is typically in JSON format.

* Reference documentation: https://api.mongodb.com/python/current/

* Kepler for Juptyer -- https://medium.com/vis-gl/introducing-kepler-gl-for-jupyter-f72d41659fbf

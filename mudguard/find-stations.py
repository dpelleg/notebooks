import os
import sys
import datetime
import pandas as pd
from math import radians, cos, sin, asin, sqrt


# for each segment, find the IMS climate station closest to it

datadir = 'data/'
stations_file = 'climate/stations.csv'

if __name__ == "__main__":
    # change dir to the script's dir
    os.chdir(sys.path[0])

# load stations into a dataframe
def load_stations():
    return pd.read_csv(datadir + stations_file)
    
def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r


# find the closest station for a given location
def closest_station(lat, lon):
    stations['dist'] = stations.apply(lambda s: haversine(lon, lat, s['lon'], s['lat']) , axis=1)
    closest = stations['dist'].idxmin()
    print("Closest is {}".format(closest))
    return(stations[closest])
                                          
stations = load_stations()

if __name__ == "__main__":
    latlng = [32.742056, 35.05223]
    lat = latlng[0]
    lon = latlng[1]

    foo = closest_station(lat, lon)

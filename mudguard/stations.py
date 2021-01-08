import datetime
import pandas as pd
import os
from math import radians, cos, sin, asin, sqrt


# for each segment, find the IMS climate station closest to it

datadir = 'data/'
stations_file = 'climate/stations.csv'
excluded_file = 'climate/excluded_stations.csv'

if __name__ == "__main__":
    # change dir to the script's dir
    import os
    import sys
    os.chdir(sys.path[0])

# load stations into a dataframe
def load_stations():
    ret = pd.read_csv(datadir + stations_file)
    
    if(os.path.isfile(datadir + excluded_file)):
        exclude = pd.read_csv(datadir + excluded_file)
        r2 = ret.merge(exclude, how='left', left_on='stationId', right_on='stationId', indicator=True)
        r3 = r2[r2['_merge'] == 'left_only'].drop(columns=['reason', '_merge'])
        ret = r3.copy()

    ret.set_index('stationId', drop=False, inplace=True);
    return ret
    
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
    dist = stations.apply(lambda s: haversine(lon, lat, s['lon'], s['lat']) , axis=1)
    closest = dist.idxmin()
    return(closest)
                                          
stations = load_stations()

if __name__ == "__main__":
    latlng=[31.384298, 34.8427]
    lat = latlng[0]
    lon = latlng[1]
    s = load_stations()
    dist = s.apply(lambda s: haversine(lon, lat, s['lon'], s['lat']) , axis=1)
    #print(s.info())
    print(s.loc[dist.idxmin()])
    #foo = closest_station(lat, lon)

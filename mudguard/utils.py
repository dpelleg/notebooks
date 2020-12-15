import pandas as pd
import glob as mod_glob
import json
import math
import ims
from stations import closest_station

datadir = 'data/'
segfile = 'segments/segments.csv'
rain_file = 'climate/rain_days.csv'

# a bunch of helper functions


# find rain amounts for all missing dates, and cache the result
def get_rain_days(additional_days):
    # load the values computed in previous runs
    try:
        rain_days = pd.read_csv(datadir + rain_file)
    except FileNotFoundError:
        rain_days = pd.DataFrame(columns=['date', 'closest_ims', 'rain_mm'])

    rain_days['date'] = pd.to_datetime(rain_days['date'])

    # add any dates/segments which were added
    curr_rain_days = additional_days[['date', 'closest_ims']].drop_duplicates()
    curr_rain_days['rain_mm'] = math.nan

    rain_days = pd.concat([rain_days, curr_rain_days], ignore_index=True).drop_duplicates(subset=['date', 'closest_ims'], keep='first')[['date', 'closest_ims', 'rain_mm']]

    # Fill missing values
    # To do: for days of missing data at the source, instead of repeatedly querying for them, mark when was the last query, and only query once in a period, and if too long has passed, give up
    rain_days['rain_mm'] = rain_days.apply(lambda r : ims.get_rain_day(r['closest_ims'], r['date']) if pd.isnull(r['rain_mm']) else r['rain_mm'], axis=1)

    # cache values for next time
    rain_days.to_csv(datadir + rain_file, index=False)
    return rain_days


def get_ridelogs():
    
    rl_ = None

    # Read usage records
    ridelog_files = mod_glob.glob(datadir + 'ridelogs/' + r"*.json")
    for rf in ridelog_files:
        print(rf)
        jdata = []
        with open(rf) as ridelog:
            for line in ridelog:
                jdata.append(json.loads(line))
                if(rl_ is None):
                    rl_ = pd.DataFrame(jdata)
                else:
                    rl_ = pd.concat([rl_, pd.DataFrame(jdata)], ignore_index=True)
    rl_['date'] = pd.to_datetime(rl_['time_retrieved'], unit='s').dt.date

    return rl_

def get_segment_metadata():
    md = pd.read_csv(datadir + segfile)
    # md.drop(columns='Unnamed: 0', inplace=True)
    #md.set_index('id', inplace=True)
    md['id'] = md['id'].map(str)


    # Add closest climate station 
    #TODO: cache the result and store back in segments file

    def parse_loc(x):
        xl = list(map(float, x.strip('][').split(', ')))
        ret = { 'lat' : xl[0], 'lon' : xl[1]}
        return ret

    def find_closest(x):
        return(closest_station(x['lat'], x['lon']))

    # parse coordinates
    md = pd.concat([md.apply(lambda r : parse_loc(r['start_latlng']), axis=1, result_type='expand'), md], axis=1)

    # Add a fake no-location segment
    if len(md.query('id == "ALL"')) == 0:
        ALL={'id' : 'ALL', 'name' : 'ALL'}
        ALL.update(md[['lat', 'lon']].mean().to_dict())
        md = md.append(ALL, ignore_index=True)
    
    md['closest_ims'] = None
    # fill closest station 
    md['closest_ims'] = md.apply(lambda r : find_closest(r) if pd.isnull(r['closest_ims']) else r['closest_ims'], axis=1)




    return md

# add accumulated rainfall using a bathtub model:
#  Bathtub model of soil moisture:
#  Daily new rainfall is added to the ground, up to the ground's capacity (then its lost in groundwater flow)
#  Additionally, the ground is drained at a constant rate per day

def bathtub_(v, capacity, drainage):
    ret = []
    prev = 0;
    for vv in v:
        val = max(0, min(capacity, prev + vv) - drainage)
        prev = val
        ret.append(val)
    return ret

def bathtub(v, capacity=10, drainage=3):
    return pd.Series(bathtub_(v, capacity, drainage), index=v.index)

if __name__ == "__main__":
    get_rain_days(pd.DataFrame(columns=['date', 'closest_ims']))
    #md = get_segment_metadata()
    #rl_ = get_ridelogs()

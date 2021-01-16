import pandas as pd
import glob as mod_glob
import json
import math
import ims
import datetime
from stations import closest_station

datadir = 'data/'
segfile = 'segments/segments.csv'
weather_file = 'climate/weather_days.csv'

# a bunch of helper functions


# find rain and wind amounts for all missing dates, and cache the result
def get_weather_days(additional_days, lookback_horizon=7):
    k1 = 'rain_mm'
    k2 = 'wind_ms'

    def use_cache(r):
        if pd.isnull(r[k1]) or math.isnan(r[k1]) or pd.isnull(r[k2]) or math.isnan(r[k2]):
            return get_weather_day_helper(r)
        else:
            return r
        
    def get_weather_day_helper(r):
        if(pd.isnull(r['date'])): # This could happen if we just added a segment, but no ride logs had been associated with it yet
            return None
            
        if (pd.to_datetime('today') - r['date']).days > lookback_horizon:   # if the missing data is for a date far in the past, stop asking, it's unlikely to appear
            return None

        c_ims = r['closest_ims'] 
        if type(c_ims) == float:
            c_ims = '%.0f' % c_ims

        return ims.get_weather_day(c_ims, r['date'])

    # load the values computed in previous runs
    try:
        weather_days = pd.read_csv(datadir + weather_file)
        weather_days['closest_ims'] = weather_days['closest_ims'].map(str)
    except FileNotFoundError:
        weather_days = pd.DataFrame(columns=['date', 'closest_ims', k1, k2])

    weather_days['date'] = pd.to_datetime(weather_days['date'])
    additional_days['date'] = pd.to_datetime(additional_days['date'])
    k='closest_ims'
    weather_days[k] = weather_days[k].map(int)
    additional_days[k] = additional_days[k].map(int)

    # add any dates/segments which were added
    curr_weather_days = additional_days[['date', 'closest_ims']].drop_duplicates()
    curr_weather_days[k1] = None
    curr_weather_days[k2] = None

    weather_days = pd.concat([weather_days, curr_weather_days], ignore_index=True).drop_duplicates(subset=['date', 'closest_ims'], keep='first')[['date', 'closest_ims', k1, k2]]

    # Fill missing values
    newcols = weather_days.apply(use_cache, axis='columns', result_type='expand')

    weather_days[k1] = newcols[k1]
    weather_days[k2] = newcols[k2]
    
    # cache values for next time
    weather_days.dropna(inplace=True)
    weather_days.to_csv(datadir + weather_file, index=False, float_format='%.3g')
    return weather_days

def tabulate_ridelogs(rl_, upper_nrides):
    rl2 = pd.pivot_table(rl_, index='date', values='effort_count', columns='segment_id')
    rl2.set_index(pd.DatetimeIndex(rl2.index.values), inplace=True)

    # resample daily, interpolate missing values, and diff against the previous day
    # If there are multiple readings on the same day, the implementation of "resample" will average them. I did not see an easy way to change this. Ideally, this should either be the maximum, or the most recent of the readings
    daily = rl2.resample('1D').interpolate().diff()
    # negative values might come up if Strava removes rides
    daily.clip(lower=0, inplace=True)

    # normalize by day-of-week average
    all_segs = daily.columns
    d2 = daily.reset_index()
    d3 = d2.melt(id_vars = 'index', value_vars=all_segs)
    d4 = d3.rename(columns = {'index' : 'date', 'value' : 'rides'})

    # Code to add a meta-segment to gather all segments
    #all_rides = pd.DataFrame(d4.groupby('date')['rides'].sum()).reset_index()
    #all_rides['segment_id'] = 'ALL'
    #d4 = d4.append(all_rides)

    d4['weekday'] = d4['date'].dt.weekday

    by_dow = d4.groupby(['segment_id', 'weekday']).mean().rename(columns={'rides' : 'rides_dow'})
    d5 = d4.merge(by_dow, how='left', left_on=['segment_id', 'weekday'], right_on=['segment_id', 'weekday'])
    # normalize (nrides = normalized rides)
    d5['nrides'] = d5['rides'] / d5['rides_dow']
    d5['nrides_raw'] = d5['nrides']

    # negative values might come up if Strava removes rides
    # positive values which are too high are not useful for the analysis
    d5['nrides'].clip(lower=0, upper=upper_nrides, inplace=True)
    return d5

def get_ridelogs(upper_nrides = 2.0):
    
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

    return tabulate_ridelogs(rl_, upper_nrides)

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
    if False and len(md.query('id == "ALL"')) == 0:
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

def bathtub_(v, capacity, drainage, fwind):
    ret = []
    prev = 0;
    v_rain = v['rain_mm'].values
    v_wind = v['wind_ms'].values
    for vi in range(len(v_rain)):
        if math.isnan(v_rain[vi]):
            val = math.nan
        else:
            if math.isnan(prev):     # the "min" operation will ignore the value which is nan, and instead use the capacity value. Need to protect against that
                prev = 0
            val = max(0, min(capacity, prev + v_rain[vi]) - drainage - v_wind[vi]*fwind)
        prev = val
        ret.append(val)
    return ret

# a version of the bathtub model, where the drainage is a fraction of the moisture (ie, multiplicative instead of additive)

def bathtub_geom_(v, capacity, drainage_factor, fwind):
    ret = []
    prev = 0;
    v_rain = v['rain_mm'].values
    v_wind = v['wind_ms'].values
    for vi in range(len(v_rain)):
        if math.isnan(v_rain[vi]):
            val = math.nan
        else:
            if math.isnan(prev):     # the "min" operation will ignore the value which is nan, and instead use the capacity value. Need to protect against that
                prev = 0
            val = max(0, min(capacity, prev + v_rain[vi]) - v_wind[vi]*fwind) * drainage_factor
            if val < 1:
                val = 0
        prev = val
        ret.append(val)
    return ret

if __name__ == "__main__":
#    get_weather_days(pd.DataFrame(data={'date': ['2020-11-25'], 'closest_ims': ['44']}), lookback_horizon=100)
    #md = get_segment_metadata()
    #rl_ = get_ridelogs()
    d = pd.read_csv('foo.csv')
    print(bathtub_geom_(d[['rain_mm', 'wind_ms']], capacity=100, drainage_factor=0.9, fwind=0))

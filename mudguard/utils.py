import pandas as pd
import glob as mod_glob
import json
import math
import ims
import datetime
from stations import closest_station
import time
import numpy as np

datadir = 'data/'
segfile = 'segments/segments.csv'
weather_file = 'climate/weather_days.csv'

NM=12   # number of months
FWHM = 1.5  # shape of kernel

# a bunch of helper functions

def sigma2fwhm(sigma):
    return sigma * np.sqrt(8 * np.log(2))

def fwhm2sigma(fwhm):
    return fwhm / np.sqrt(8 * np.log(2))

def month_dist(i, j):  # compute distance in number of months
    d = abs(i-j)
    d_rev = abs(NM-d)
    return min(d, d_rev) # choose the smaller of the current year or the preceding/next year

def apply_kernel(ts_, kernel, cell, month_vals):
    sum_w = 0.0
    sum_v = 0.0
    for i in range(len(ts_)):
        d = month_dist(month_vals[i], month_vals[cell])
        k = kernel[d]
        v = ts_[i]
        if v is not None and not math.isnan(v):
            sum_w += k
            sum_v += v*k
    if sum_w > 0:
        return sum_v/sum_w
    return None

def get_kernel():
    sigma = fwhm2sigma(FWHM)
    x_vals = np.arange(NM)         #it's true we'll only need half
    kernel = np.exp(-(x_vals) ** 2 / (2 * sigma ** 2))
    kernel = kernel / sum(kernel)
    return kernel

def mdow_average(data_, colname, colvals, rowname, rowvals, idname):
    # given a matrix of average values per month-of-year and day-of-week, smooth the values using a kernel based on neighboring months
    # return a dictionary of smoothed values

    # unpack the row values
    month_vals = list(map(lambda x: x[1], rowvals))

    # transpose so we have months in columns
    data = data_.T

    ret_id = []
    ret_day = []
    ret_month = []
    ret_val = []

    kernel = get_kernel()

    for day in colvals:
        ts = data[day]

        for month in range(len(ts)):
            v = apply_kernel(ts, kernel, month, month_vals)
            ret_id.append(idname)
            ret_day.append(day)
            ret_month.append(month_vals[month])
            if v is None:
                v=0.
            ret_val.append(v)

    ret = pd.DataFrame({ 'segment_id' : ret_id, 'weekday' : ret_day, 'month' : ret_month, 'rides_mdow' : ret_val})
    return ret

# find rain and wind amounts for all missing dates, and cache the result
def get_weather_days(additional_days, lookback_horizon=7):
    newkeys = ['rain_mm', 'wind_ms', 'temp_deg', 'rain_morning', 'wind_morning', 'temp_morning']
    weather_keys = ['date', 'closest_ims']
    weather_keys.extend(newkeys)

    def use_cache(r):
        missing = False
        for k in newkeys:
            if pd.isnull(r[k]) or math.isnan(r[k]):
                missing = True

        if missing:
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

        #time.sleep(0.5)
        return ims.get_weather_day(c_ims, r['date'])

    # load the values computed in previous runs
    try:
        weather_days = pd.read_csv(datadir + weather_file)
        weather_days['closest_ims'] = weather_days['closest_ims'].map(str)
    except FileNotFoundError:
        weather_days = pd.DataFrame(columns=weather_keys)

    weather_days['date'] = pd.to_datetime(weather_days['date'])
    additional_days['date'] = pd.to_datetime(additional_days['date'])
    k='closest_ims'
    weather_days[k] = weather_days[k].map(int)
    additional_days[k] = additional_days[k].map(int)

    # add any dates/segments which were added
    curr_weather_days = additional_days[['date', 'closest_ims']].drop_duplicates()
    for k in newkeys:
        curr_weather_days[k] = None

    weather_days = pd.concat([weather_days, curr_weather_days], ignore_index=True).drop_duplicates(subset=['date', 'closest_ims'], keep='first')[weather_keys]

    # Fill missing values
    newcols = weather_days.apply(use_cache, axis='columns', result_type='expand')

    for k in newkeys:
        weather_days[k] = newcols[k]

    # cache values for next time
    weather_days.dropna(inplace=True)
    weather_days.to_csv(datadir + weather_file, index=False, float_format='%.3g')
    return weather_days

# compute averages per day of week, smoothed with neighboring month's data
def get_mdow(mydf):
    by_mdow = mydf.groupby(['segment_id', 'month', 'weekday']).mean(numeric_only=True).rename(columns={'rides' : 'rides_mdow'})

    mdow = None
    seglist = mydf['segment_id'].unique()

    for seg in seglist:
        this_segment = by_mdow.query("segment_id == @seg")['rides_mdow'].unstack()
        colname = this_segment.columns.name
        colvals =  this_segment.columns.values
        rowname = this_segment.index.names[1]
        rowvals = this_segment.index.values
        dat = this_segment.to_numpy()
        r = mdow_average(dat, colname, colvals, rowname, rowvals, seg)
        if mdow is None:
            mdow = r.copy()
        else:
            mdow = pd.concat([mdow, r])
    return mdow

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
    d4['month'] =   d4['date'].dt.month

    by_dow = d4.groupby(['segment_id', 'weekday']).mean(numeric_only=True).rename(columns={'rides' : 'rides_dow'}).drop(columns='month')
    by_mdow = get_mdow(d4)
    d5 = d4.merge(by_dow, how='left', left_on=['segment_id', 'weekday'], right_on=['segment_id', 'weekday'], suffixes=('', '_y'))
    d5 = d5.merge(by_mdow, how='left', left_on=['segment_id', 'weekday', 'month'], right_on=['segment_id', 'weekday', 'month'])
    # normalize (nrides = normalized rides)
    d5['nrides_dow'] = d5['rides'] / d5['rides_dow']
    d5['nrides'] = d5['rides'] / d5['rides_mdow']
    d5['nrides_raw'] = d5['nrides']

    # negative values might come up if Strava removes rides
    # positive values which are too high are not useful for the analysis
    d5['nrides'].clip(lower=0, upper=upper_nrides, inplace=True)
    #return (d5, by_mdow)
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
            val1 = max(0, min(capacity, prev + v_rain[vi]) - v_wind[vi]*fwind)
            # we want to ensure the geometric steps don't get too small near the end
            val2_geom = val1 * drainage_factor
            val2_additive = max(0, val1 - 1)
            val = min(val2_geom, val2_additive)
            if val < 1:
                val = 0
        prev = val
        ret.append(val)
    return ret

# a soil model which accounts the number of days since the last rain
def daycounter_(v, cday, rain_thresh, fwind):
    ret = []
    days_left = 0
    v_rain = v['rain_mm'].values
    v_wind = v['wind_ms'].values
    for vi in range(len(v_rain)):
        # if rainfall is more than the rain_thresh, reset the counter of days since last rain
        # otherwise decrease counter, and deduct any effect of wind
        if math.isnan(v_rain[vi]) or (v_rain[vi] < rain_thresh):
            days_left = max(0, days_left - 1 - v_wind[vi]*fwind)
        else:
            days_left = cday
        ret.append(days_left)
    return ret

if __name__ == "__main__":
    get_weather_days(pd.DataFrame(data={'date': ['2021-03-26'], 'closest_ims': ['44']}), lookback_horizon=200)
    #md = get_segment_metadata()
    #rl_ = get_ridelogs()
    #d = pd.read_csv('foo.csv')
    #print(bathtub_geom_(d[['rain_mm', 'wind_ms']], capacity=100, drainage_factor=0.9, fwind=0))

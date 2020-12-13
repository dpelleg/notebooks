import pandas as pd
import glob as mod_glob
import json
import math
import ims

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
    md.drop(columns='Unnamed: 0', inplace=True)
    #md.set_index('id', inplace=True)
    md['id'] = md['id'].map(str)
    return md

if __name__ == "__main__":
    get_rain_days(pd.DataFrame(columns=['date', 'closest_ims']))
    #md = get_segment_metadata()
    #rl_ = get_ridelogs()

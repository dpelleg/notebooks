#!/usr/bin/env python3

import pandas as pd
import time
import datetime
import glob as mod_glob
import json
import conf

# Analyse segment statistics

# Read meta-data for all segments
datadir = conf.conf['datadir']
segfile = 'segments/segments.csv'

md = pd.read_csv(datadir + segfile)

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

# Get historical average user per day
c = 'created_at'
md[c] = pd.to_datetime(md[c])
c = 'time_retrieved'
md[c] = pd.to_datetime(md[c], utc=True)
md['hist_length'] = md['time_retrieved'] - md['created_at']
md['hist_length_days'] = md['hist_length'].apply(lambda x: x.days)

# Tabulate ridelog data with date as index
rl = pd.pivot_table(rl_, index='date', values='effort_count', columns='segment_id')

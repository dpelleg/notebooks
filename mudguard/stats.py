#!/usr/bin/env python3

import pandas as pd
import time
import datetime
import glob as mod_glob
import json

# Analyse segment statistics

# Read meta-data for all segments
datadir = 'data/'
segfile = 'segments/segments.csv'

md = pd.read_csv(datadir + segfile)

df = None

# Read usage records
ridelog_files = mod_glob.glob(datadir + 'ridelogs/' + r"*.json")
for rf in ridelog_files:
    print(rf)
    jdata = []
    with open(rf) as ridelog:
        for line in ridelog:
            jdata.append(json.loads(line))
    if(df is None):
        df = pd.DataFrame(jdata)
    else:
        df = pd.concat([df, pd.DataFrame(jdata)], ignore_index=True)

# Get historical average user per day



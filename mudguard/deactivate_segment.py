#!/usr/bin/env python3

# given a list of Strava segments, fetch and store their metadata

import pandas as pd
import sys

d = {'strava' : 'active_strava', 'model' : 'active_modeling', 'html' : 'active_html'}

all_keys = '|'.join(d.keys())

if len(sys.argv) < 3:
    print("Usage: deactivate_segment segment_id " + all_keys)
    exit(1)

segment = sys.argv[1]
what = sys.argv[2]

segfile = 'data/segments/segments.csv'

s = pd.read_csv(segfile)

colname = d.get(what)
if colname is None:
    print('Unknown type: %s. Available types: %s' % (what, all_keys))
    exit(1)

for c in d.values():
    if c not in s.columns:   # create the column if needed
        s[c] = True

s.loc[s['id'].astype(str) == segment, [colname]] = False

s.to_csv(segfile, float_format='%.5g', index=False)

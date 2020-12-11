import json
import requests
import os
import sys
import pandas as pd
import ims

# get a fresh list of IMS climate stations and store it

# change dir to the script's dir
os.chdir(sys.path[0])

data_read = ims.stations_metadata()
data = json.loads(data_read)

df = []

for row in data:
    if row['active']:
        row_dict = row.copy()
        channels = row['monitors']
        chan_dict = {}
        for c in channels:
            if c['active']:
                chan_dict["channel_" + c['name']] = c['units']
        row_dict['lat'] = row['location']['latitude']
        row_dict['lon'] = row['location']['longitude']
        del row_dict['location']
        del row_dict['monitors']
        row_dict.update(chan_dict)
        df.append(row_dict)

df = pd.DataFrame(df)
df.to_csv('data/climate/stations.csv', index=False)


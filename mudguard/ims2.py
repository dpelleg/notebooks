import json
import requests
import os
import sys
import pandas as pd

# change dir to the script's dir
os.chdir(sys.path[0])

with open('stuff.txt', 'r') as infile:
     read_data = infile.read()

#print(read_data)


data = json.loads(read_data)
df = []
stationId = data['stationId']
data = data['data']

for row in data:
    datetime = row['datetime']
    for channel in row['channels']:
        dict = channel.copy()
        dict['stationId'] = stationId
        dict['datetime'] = datetime
        df.append(dict)
        #df.append(row['data'])

df = pd.DataFrame((df))
df.to_csv('ims2.csv')
#print(df)


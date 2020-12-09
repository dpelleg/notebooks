import json
import requests
import os
import sys
import pandas as pd

# get a fresh list of IMS climate stations and store it

# change dir to the script's dir
os.chdir(sys.path[0])

token_file = 'tokens/ims_token.json'

# Get the tokens from file
with open(token_file) as json_file:
    ims_tokens = json.load(json_file)# Loop through all activities

ims_token = ims_tokens['token']

url = "https://api.ims.gov.il/v1/Envista/stations"

headers = {
  'Authorization': 'ApiToken ' + ims_token
}

if False:
    response = requests.request("GET", url, headers=headers)
    data_read = response.text.encode('utf8')
else:
    with open('stations.txt', 'r') as infile:
        data_read = infile.read()

data = json.loads(data_read)
df = []

for row in data:
    if row['active']:
        print(row['stationId'])
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
df.to_csv('data/climate/stations.csv')


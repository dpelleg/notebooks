import json
import requests
import os
import sys
import pandas as pd

# change dir to the script's dir
os.chdir(sys.path[0])

token_file = 'tokens/ims_token.json'

# Get the tokens from file
with open(token_file) as json_file:
    ims_tokens = json.load(json_file)# Loop through all activities

ims_token = ims_tokens['token']

#url = "https://api.ims.gov.il/v1/envista/stations/2/data/daily/2020/11/25"
url = "https://api.ims.gov.il/v1/Envista/stations"

headers = {
  'Authorization': 'ApiToken ' + ims_token
}

response = requests.request("GET", url, headers=headers)
data=response.text.encode('utf8')
with open('stations.txt', 'wb') as outfile:
     outfile.write(data)


if False:
   data = json.loads(data_read)
   df = []
   data = data['data']

   for row in data:
       for channel in row['channels']:
           df.append(channel)
           #df.append(row['data'])

   df = pd.DataFrame((df))
   df.to_csv('ims2.csv')
   #print(df)


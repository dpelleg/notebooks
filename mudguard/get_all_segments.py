#!/usr/bin/env python3

# Use the Strava API to get effort counts on a list of segments

import requests
import json
import time
import csv
import os
import pandas as pd
import math
import random
import sys

# change dir to the script's dir
os.chdir(sys.path[0])

token_file = 'tokens/strava_tokens.json'
secret_file = 'tokens/strava_secret.json'
datadir = 'data/'

# Get the tokens from file to connect to Strava
with open(token_file) as json_file:
    strava_tokens = json.load(json_file)# Loop through all activities

# If access_token has expired then
# use the refresh_token to get the new access_token
if 'expires_at' not in strava_tokens or strava_tokens['expires_at'] < time.time():# Make Strava auth API call with current refresh token
    print('refreshing token',  file=sys.stderr)
    with open(secret_file) as secret:
        secrets = json.load(secret)
        response = requests.post(
                        url = 'https://www.strava.com/oauth/token',
                        data = {
                                'client_id': secrets['client_id'],
                                'client_secret': secrets['client_secret'],
                                'grant_type': 'refresh_token',
                                'refresh_token': strava_tokens['refresh_token']
                                }
                    )# Save response as json in new variable
        new_strava_tokens = response.json()# Save new tokens to file
        with open(token_file, 'w') as outfile:
            json.dump(new_strava_tokens, outfile)# Use new Strava tokens from now
        strava_tokens = new_strava_tokens

segfile = datadir + 'segments/segments.csv'

if(os.path.isfile(segfile)):
    segments = pd.read_csv(segfile)
    all_ids = list(map(str, segments['id'].values))
    random.shuffle(all_ids)                   # get some variation in the order we fetch the segments
else:
    exit('no segment file!?!?')

# ignore inactive segments
segments = segments[segments['active_strava']]

url = "https://www.strava.com/api/v3/segments/"

access_token = strava_tokens['access_token']# Get first page of activities from Strava with all fields

outfile = datadir + 'ridelogs/' + time.strftime('%Y%m') + ".json"

with open(outfile, 'a') as outfile:
    for segment in all_ids:
        # print("Fetching " + segment)
        r = requests.get(url + segment + '?access_token=' + access_token)
        r = r.json()
        # print(r)
        out = { 'effort_count' : r['effort_count'],
                'athlete_count' : r['athlete_count'],
                'segment_id' : segment,
                'time_retrieved' : math.floor(time.time())
                }
        print(json.dumps(out, sort_keys=True), file=outfile)
        time.sleep(1)

outfile.close()

#!/usr/bin/env python3

# given a list of Strava segments, fetch and store their metadata

import requests
import pandas as pd
import json
import time
import csv
import os.path

# Get the tokens from file to connect to Strava
with open('strava_tokens.json') as json_file:
    strava_tokens = json.load(json_file)

# If access_token has expired then 
# use the refresh_token to get the new access_token
if strava_tokens['expires_at'] < time.time():# Make Strava auth API call with current refresh token
    print('refreshing token')
    with open('strava_secret.json') as secret:
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
        with open('strava_tokens.json', 'w') as outfile:
            json.dump(new_strava_tokens, outfile)# Use new Strava tokens from now
        strava_tokens = new_strava_tokens


segments_to_add = ['3808938', '1248017', '4267589', '18952377', '2481821', '7774409', '8574425', '17421855', '4202076', '1717839', '24208670']

# load the current list of segments, if it exists
segfile = 'segments.csv'


if(os.path.isfile(segfile)):
    segments = pd.read_csv(segfile)
    all_ids = segments['id'].to_string()
else:
    segments = pd.DataFrame()
    all_ids = []

url = "https://www.strava.com/api/v3/segments/"
access_token = strava_tokens['access_token']# Get first page of activities from Strava with all fields

for segment in segments_to_add:
    if(segment not in all_ids):
        print("Adding " + segment)
        r = requests.get(url + segment + '?access_token=' + access_token)
        r = r.json()
        newpd = pd.DataFrame(pd.json_normalize(r))
        segments = segments.append(newpd)

segments.to_csv(segfile, index=False)

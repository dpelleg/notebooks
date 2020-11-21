import requests
from pandas import json_normalize
import json
import csv# Get the tokens from file to connect to Strava
with open('strava_tokens.json') as json_file:
    strava_tokens = json.load(json_file)# Loop through all activities

segment_id = '24208670'

url = "https://www.strava.com/api/v3/segments/"
access_token = strava_tokens['access_token']# Get first page of activities from Strava with all fields
r = requests.get(url + segment_id + '?access_token=' + access_token)
r = r.json()
    
print(r)

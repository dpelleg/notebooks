import json
import requests
import os
import sys
import datetime
import pandas as pd

# get climate data for a given date and station

# change dir to the script's dir
os.chdir(sys.path[0])

# This is the threshold hour for daily rain amount calculations
threshold_hour = 19

ims_token = None

ims_cache = {}

def get_tokens():
    global ims_token
    if ims_token is None:
        token_file = 'tokens/ims_token.json'

        # Get the tokens from file
        with open(token_file) as json_file:
            ims_tokens = json.load(json_file)# Loop through all activities

        ims_token = ims_tokens['token']

def get_climate_day(station, date):
    #url = "https://api.ims.gov.il/v1/envista/stations/2/data/daily/2020/11/25"

    # check if we have this date and station cached already
    global ims_cache
    date_fmtd = date.strftime("%Y/%m/%d")
    cache_key = "{}##{}".format(station, date_fmtd)
    print("Cache key: " + cache_key)

    if cache_key in ims_cache:
        data = ims_cache[cache_key]
    else:
        url = "https://api.ims.gov.il/v1/envista/stations/{}/data/daily/{}".format(station, date_fmtd)
    
        get_tokens()
        headers = {
            'Authorization': 'ApiToken ' + ims_token
        }

        print("URL = " + url)
        
        response = requests.request("GET", url, headers=headers)
        data=json.loads(response.text.encode('utf8'))

        # update cache
        ims_cache[cache_key] = data
    
    return data

def ims_to_dictlist(data):
    dl = []
    stationId = data['stationId']
    data = data['data']

    for row in data:
        datetime = row['datetime']
        for channel in row['channels']:
            dict = channel.copy()
            dict['stationId'] = stationId
            dict['datetime'] = datetime
            dl.append(dict)
    return dl

# given a date, return the amount of rain in the 24-hour period ending on the threshold hour on that date
def get_rain_day(station, date):
    # get the list of dates we need to query
    yesterdate = date - datetime.timedelta(days=1)
    d1 = get_climate_day(station, date)
    d2 = get_climate_day(station, yesterdate)
    # merge
    df = pd.DataFrame(ims_to_dictlist(d1))
    df.append(ims_to_dictlist(d2))
    print(df)


get_rain_day("2", datetime.date(2020, 11, 25))
get_rain_day("2", datetime.date(2020, 11, 26))

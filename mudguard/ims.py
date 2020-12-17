import json
import requests
import datetime
import os
import sys
import pandas as pd
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# access functions to IMS API (Israeli climate agency)

# This is the threshold hour for daily rain amount calculations
threshold_hour = 19

ims_token = None

ims_cache = {}

# Note: used both for the IMS API, and for our own internal cache keying
date_format = "%Y/%m/%d"

token_file = 'tokens/ims_token.json'

# Get the tokens from file
with open(token_file) as json_file:
    ims_tokens = json.load(json_file)

ims_token = ims_tokens['token']

headers = {
  'Authorization': 'ApiToken ' + ims_token
}

def retry_session(retries, session=None, backoff_factor=0.3):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        method_whitelist=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

session = retry_session(retries=5)

def httpreq(urlsuff):
    MAX_RETRY = 3
    retries = 0

    url = "https://api.ims.gov.il/v1/envista/" + urlsuff

    try:
        response = session.get(url=url, headers=headers)
        # requests.request("GET", url, headers=headers)
        data=response.text.encode('utf8')
        return data
    except ConnectionEror:
        return None
    
    return None

def stations_metadata():
    return httpreq("stations/")

def climate_bydate(station, date):
    ret = httpreq("stations/{}/data/daily/{}".format(station, date.strftime(date_format)))
    return ret

def get_climate_day(station, date):
    global ims_cache

    cache_key = "{}##{}".format(station, date.strftime(date_format))

    if cache_key in ims_cache:
        data = ims_cache[cache_key]
    else:  # cache miss
        print(cache_key)
        data = climate_bydate(station, date)
        #print(data)
        if(len(data) > 0):
            data=json.loads(data)
            # update cache
            ims_cache[cache_key] = data
        else:
            data = None
    
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
    total=None

    # get the list of dates we need to query
    try:
        yesterdate = date - datetime.timedelta(days=1)
        d1 = get_climate_day(station, date)
        d2 = get_climate_day(station, yesterdate)
        dlist = ims_to_dictlist(d1)
        # merge
        dlist.extend(ims_to_dictlist(d2))
        df = pd.DataFrame(dlist)
        df['datetime'] = pd.to_datetime(df['datetime']).dt.tz_localize(None)

        valid = df.query("valid and name=='Rain'")
        if(len(valid) < 50):  # not enough data
            return None

        end_ts = datetime.datetime.combine(date, datetime.time(19, 0))
        start_ts = end_ts - datetime.timedelta(days=1, seconds=-1)
        idxlist = valid['datetime'].between(start_ts, end_ts)
        total = valid['value'][idxlist].sum()
    except TypeError:
        return None
    return total

if __name__ == "__main__":
    # change dir to the script's dir
    os.chdir(sys.path[0])
    #print(climate_bydate("67", datetime.date(2020, 12, 5)))
    print(get_rain_day("78", datetime.date(2020, 12, 16)))
    #d1 = datetime.date(2020, 11, 27)
    #d2 = datetime.time(19, 00)

import requests
import datetime
import os
import sys
import time
import re
from datetime import date, timedelta
import xml.sax
import pandas as pd
import pickle
# access functions to IMS API (Israeli climate agency)
# From: https://ims.gov.il/he/CurrentDataXML
# Doc: https://ims.gov.il/sites/default/files/2020-08/%D7%94%D7%A1%D7%91%D7%A8_%D7%A0%D7%AA%D7%95%D7%A0%D7%99%D7%9D_%D7%A9%D7%A2%D7%AA%D7%99%D7%99%D7%9D_%D7%94%D7%97%D7%9C_01082018.pdf
#   (a copy of which should reside in this source tree as well)

datadir = 'data/'

# import data from the IMS
# Default URL: https://ims.gov.il/sites/default/files/ims_data/xml_files/observ.xml
#   This should update hourly, about 30 mins after the hour, and have observations for 3 hours back

class XMLHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.stations = []
        self.cur_station = None
        self.cur_station_id = None
        self.state = []
        self.station_key = None
        self.content = ''
        self.all_obs = []

   # Call when an element starts
    def startElement(self, tag, attributes):
        self.content = ''
        self.state.append(tag)
        if tag == "Station":
            #assert(self.state is None)
            self.cur_station = {}
            return
        if tag == "Observation":
            self.obs = {}
            return
        if len(self.state) > 1 and self.state[-2] == 'Station':
            self.station_key = tag
            return

   # Call when an element ends
    def endElement(self, tag):
        last_state = self.state.pop()
        last_content = self.content.strip()
        prev_state = ''
        if len(self.state) >= 1:
            prev_state = self.state[-1]

        if tag == "Station":
            assert(last_state == tag)
            self.stations.append(self.cur_station)
            self.cur_station_id = self.cur_station['StationNumber']
            self.cur_station = None
            return
        if tag == "DateTime":
            self.obs[tag] = last_content
            return

        if prev_state == "Observation":
            if tag == "Parameter":
                self.obs[self.parm_name] = self.parm_val
        prev_prev_state = ''
        if len(self.state) >= 2:
            prev_prev_state = self.state[-2]
        if prev_prev_state == "Observation":
            if tag == "ParameterShortName":
                self.parm_name = last_content
            if tag == "ParameterValue":
                self.parm_val = last_content
        if prev_state == 'Station':   # one more station parameter
            self.cur_station[self.station_key] = last_content
            return
        if tag == "Observation":
            self.obs['StationNumber'] = self.cur_station_id
            self.all_obs.append(self.obs)
            return

   # Call when a character is read
    def characters(self, content):
        self.content += content

def parse_file(filename):
    # create an XMLReader
    parser = xml.sax.make_parser()

    # turn off namepsaces
    parser.setFeature(xml.sax.handler.feature_namespaces, 0)

    # override the default ContextHandler
    Handler = XMLHandler()
    parser.setContentHandler( Handler )
    parser.parse(filename)

    stations = pd.DataFrame(data=Handler.stations).drop_duplicates()
    obs = pd.DataFrame(data=Handler.all_obs).drop_duplicates()
    obs = obs.apply(pd.to_numeric, errors='ignore')
    fix_units(obs)
    obs['DateTime'] = pd.to_datetime(obs['DateTime'])
    return stations, obs

def fix_unit(df, unit_name, factor):
    if unit_name in df.columns:
        df[unit_name] = df[unit_name]*factor

def fix_units(df):
    # tenths
    for u in ['FF', 'TT', 'TD', 'PO', 'PP', 'PP1', 'PP3', 'R01', 'R12', 'R24', 'TW', 'TX', 'TN', 'EEE', 'TWE', 'TG', 'RRS']:
        fix_unit(df, u, 0.1)
    # halves
    for u in ['HW']:
        fix_unit(df, u, 0.5)

def load_weather_data(n_data_files=10, save_stations=False):
    # first get a list of all available weather files
    filelist = []
    weather_dir = os.path.join(datadir, 'weather')
    pat=re.compile('\.xml$')
    for root, dirs, files in os.walk(weather_dir):
        if files:
            filelist.extend([(root, name) for name in [f for f in files if pat.search(f)]])

            filelist.extend([(root, name) for name in files])
    # We assume the file names are lexicographically ordered by date, eg YYYYMMDD
    filelist.sort(key=lambda e:e[1], reverse=True)

    # read and collate the the N most recent files
    stations_to_save = None
    all = []
    for f in filelist[:n_data_files]:
        fname = os.path.join(f[0], f[1])
        stations, obs = parse_file(fname)
        if stations_to_save is None:
            stations_to_save = stations
        all.append(obs.copy())
    if save_stations:
        # save a copy of the stations file
        stations_to_save.to_csv(os.path.join(datadir, 'climate', 'stations.csv'), index=False)

    all = pd.concat(all).drop_duplicates()
    return all

def get_weather_days(reference_date, ndays=3, n_data_files=10, save_stations=False):
    '''Aggregate the most recent weather data, and return the metrics for the last few days.
    '''
    reference_date = pd.to_datetime(reference_date)
    df = load_weather_data(n_data_files, save_stations)
    # Remove the hour and leave just the date, this is the data resoultion we have for the ride logs
    df['date'] = pd.to_datetime(df['DateTime'].dt.date)

    if reference_date is None:
        # Take the latest report
        latest_date = df['date'].max()
        reference_date = lastest_date
    # Because there are usually multiple observations per date, we pick the one with the latest time within that date
    reference_time = df.query('date == @reference_date')['DateTime'].max()
    df_ref=df.query("DateTime == @reference_time")

    # cumulative rain over X days
    cutoff_date = reference_date + timedelta(days=-ndays)
    after_cutoff = df.query("date > @cutoff_date & date <= @reference_date")
    sum_after_cutoff = after_cutoff.fillna(0).groupby(['StationNumber'])[['R01']].sum().rename(columns={'R01': 'R01_sum'})

    return df_ref.merge(sum_after_cutoff, on='StationNumber')

if __name__ == "__main__":
    # change dir to the script's dir
    os.chdir(sys.path[0])
#    print(climate_bydate("67", datetime.date(2020, 12, 5)))
#    print(get_weather_day("64", datetime.date(2020, 12, 1)))
#    print(get_weather_day("67", datetime.date(2021, 3, 26)))
    #print(get_climate_day("67", datetime.date(2021, 3, 26)))
    #foo = pd.DataFrame(ims_to_dictlist(get_climate_day("259", datetime.date(2020, 12, 23))))
    #foo.to_csv('foo.csv')
    #d1 = datetime.date(2020, 11, 27)
    #d2 = datetime.time(19, 00)
    r = get_weather_days(reference_date='2022-11-20', ndays=3, n_data_files=20, save_stations=True)  [['StationNumber', 'DateTime', 'R12', 'R01_sum']].sort_values('R01_sum', ascending=False)
    print(r)

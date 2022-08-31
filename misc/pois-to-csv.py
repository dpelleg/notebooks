#!/usr/bin/env python3

# use the Google Places API to list synagouges

# Discovery run:
#   get-synagogues.py
# Exploit run:
#   get-synagouges.py 30.15,30.25,34.6,34.7
import requests
import pandas as pd
import json
import os
import sys
import re
import glob
import numpy as np
from math import radians, cos, sin, asin, sqrt
from shapely.geometry import Point, Polygon

datapath = 'data2/'
search_type = 'synagogue'

def pois_to_list(d):
    dat =[]
    for p in d['results']:
        if True:
            datum = {}
            for f in ['name', 'place_id', 'vicinity']:
                datum[f] = p.get(f)
            for f in ['lat', 'lng']:
                datum[f] = p['geometry']['location'][f]
            dat.append(datum)
    return dat

def load_all_data(datadir):
    dat = []
    files = glob.glob(datadir + "/pois/*.json")
    for infile in files:
        with open(infile) as json_file:
            d=json.load(json_file)
            dat.extend(pois_to_list(d))

    return pd.DataFrame(dat).drop_duplicates(ignore_index = True)


pois = load_all_data(datapath)
pois.to_csv('out.csv')

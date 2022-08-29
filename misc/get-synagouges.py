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

datapath = 'data/'
secret_file = 'secrets/gcloud.json'
search_keyword = 'synagogue'
search_type = 'synagogue'
search_radius = 1000  # meters

known_pois = []    # place IDs of the known places

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

# find the closest station for a given location
def closest_poi(pois, lat, lng):
    dist = pois.apply(lambda s: haversine(lng, lat, s['lng'], s['lat']) , axis=1)
    closest = dist.idxmin()
    closest_dist = dist[closest]
    return (pois.loc[closest], closest_dist)

def read_borders(infile):
    with open(infile) as json_file:
        d=json.load(json_file)

    coords = d['features'][0]['geometry']['coordinates'][0][0]
    # swap coordinates so it's (lat, lng)
    for i in range(len(coords)):
        coords[i] = (coords[i][1], coords[i][0])
    return Polygon(coords)

def get_cities():
    # list of cities, from: https://en.wikipedia.org/wiki/List_of_cities_in_Israel
    #         converted using: https://wikitable2csv.ggor.de/
    cities = pd.read_csv(datapath + '/cities.csv')
    cities['Name'] = cities['Name'].apply(lambda c : re.sub('\[.*', '', c))
    cities.columns = map(lambda c : re.sub(',[0-9]+|\[.*', '', c), cities.columns)
    cities.fillna("", inplace=True)
    for f in ['Populationestimate', 'Populationcensus', 'Density,per km2']:
        cities[f] = cities[f].apply(lambda c : re.sub(',', '', c ))
        cities[f] = pd.to_numeric(cities[f])
    return cities.query('Populationestimate > 100000')['Name'].to_list()

def get_place_loc(api_key, name):
    response = requests.get(
                    url = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json?',
                    params = {
                        'input' : name,
                        'inputtype' : 'textquery',
                        'fields' : 'geometry',
                        'key' :  api_key
                            }
                )
    poi = response.json()
    return poi

def get_and_save_chunk(api_key, search_lat, search_lng, outdir, name, radius=search_radius):
    if name is not None:
        outfile = "{}/pois/{}.json".format(outdir, name)
        if os.path.exists(outfile):
            return                  # this was already fetched

    if search_lat is None or search_lng is None:
        assert(name)
        loc = get_place_loc(secrets['api_key'], name)
        loc = loc['candidates'][0]
        search_lat = loc['geometry']['location']['lat']
        search_lng = loc['geometry']['location']['lng']

    # round the location parameters
    search_lat = "{:0.2f}".format(search_lat)
    search_lng = "{:0.2f}".format(search_lng)
    latlng = ",".join([search_lat, search_lng])

    outfile = "{}/pois/{}.json".format(outdir, latlng)

    if os.path.exists(outfile):
        return                  # this was already fetched

    response = requests.get(
                    url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?',
                    params = {
                        'keyword' : search_keyword,
                        'type' : search_type,
                        'location' : latlng,
                        'radius' : radius,
                        'key' :  api_key
                            }
                )
    pois = response.json()

    if(len(pois['results']) > 0):
        with open(outfile, 'w') as outfile:
            print(json.dumps(pois), file=outfile)

    return pd.DataFrame(pois_to_list(pois))

def pois_to_list(d):
    dat =[]
    for p in d['results']:
        if 'synagogue' in p['types']:
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

def sample_point(bbox):
    lat = np.random.uniform(bbox['minlat'], bbox['maxlat'])
    lng = np.random.uniform(bbox['minlng'], bbox['maxlng'])
    return {'lat' : lat, 'lng' : lng}

def minmax_sample(pois, borders, nsamples):
    (minx, miny, maxx, maxy) = borders.bounds
    bb = {'minlat' : minx, 'maxlat' : maxx, 'minlng' : miny, 'maxlng' : maxy}
    points = [sample_point(bb) for _ in range(nsamples)]
    return minmax_set(pois, borders, points)

def minmax_set(pois, borders, points):
    ret = None
    for point_ in points:
        point = Point(point_['lat'], point_['lng'])
        if point.within(borders):
            closest_point, closest_dist = closest_poi(pois, point_['lat'], point_['lng'])
            if ret is None or closest_dist > ret['closest_dist']:
                ret = point_
                ret['closest_dist'] = closest_dist
    return ret

with open(secret_file) as json_file:
    secrets = json.load(json_file)

if not os.path.exists(datapath):
    os.makedirs(datapath)

for city in get_cities():
    get_and_save_chunk(secrets['api_key'], None, None, datapath, city)

pois = load_all_data(datapath)
print("Initial POI count %d" % len(pois['place_id'].unique()))
borders = read_borders('data/gadm41_ISR_0.json')  # Israel polygon data from https://gadm.org/download_country.html


if len(sys.argv) > 1:
    exploit_bb = sys.argv[1].split(',')
    if len(exploit_bb) != 4:
        print("Usage:\nDISCOVER MODE:\nget_synagouges\nEXPLOIT MODE:\n get_synagouges minlat,maxlat,minlon,maxlon")
        exit(1)

    (minlat, maxlat, minlng, maxlng) = map(float, exploit_bb)

    # first run a grid search to find the point with lowest minmax distance
    grid = []
    for lat in np.linspace(minlat, maxlat, 200):
        for lng in np.linspace(minlng, maxlng, 200):
            grid.append({'lat' : lat, 'lng' : lng})
    minmax = minmax_set(pois, borders, grid)
    print(minmax)

    # for the minimax point, list the closest POIs
    dist = pois.apply(lambda s: haversine(minmax['lng'], minmax['lat'], s['lng'], s['lat']) , axis=1)
    p_copy = pois.copy()
    p_copy['dist'] = dist
    p_copy.sort_values(by='dist', inplace=True)
    print(p_copy[0:10])
    exit(0)
    #closest_dist = dist[closest]


for _ in range(5):
    # find point furthest from any poi
    minmax = minmax_sample(pois, borders, 2000)
    print(minmax)
    r = search_radius
    done_search = False
    attempts = 6
    while not done_search:
        # run another search around it and save the results
        new_pois = get_and_save_chunk(secrets['api_key'], minmax['lat'], minmax['lng'], datapath, None, r)
        if new_pois is not None and new_pois.shape[0] > 0:
            done_search = True
        r *= 2
        attempts -= 1
        print(attempts)
        if attempts == 0:
            done_search = True

    if attempts > 0:
        newly_discovered = list(set(new_pois['place_id'].unique()) - set(pois['place_id'].unique()))
        pois = pd.concat([pois, new_pois], ignore_index = True)
        print("%d newly discovered" % len(newly_discovered))
    else:
        print("Skip, looks like we're close to convergence")

#!/usr/bin/env python3

# get a list of trail reports from trailforks

import urllib.parse
import urllib.request
import pandas as pd
from bs4 import BeautifulSoup
import time

url = 'https://www.trailforks.com/reports/all/?activitytype=1&published=1&nearby_range=50'
data = []

while(url):
    print(url)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        the_page = response.read()
        soup = BeautifulSoup(the_page, features="lxml")
        #print(soup)
        table_body  = soup.find('table')
        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            if(len(cols) > 0):
                data.append(cols) # Get rid of empty values
        link_next = soup.find('a', href=True, text='Next Page')
        if(link_next):
            url = link_next['href']
        else:
            url = None
    time.sleep(2.7)
df = pd.DataFrame(data, columns = ['dummy', 'trail', 'region', 'date', 'description', 'condition', 'link'])
df.to_csv('data/trailforks.csv')

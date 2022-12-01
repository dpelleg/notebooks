#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import time
import datetime
import math
import ims
import utils
import locale
import re
import ast
from datetime import date, timedelta

# Analyse segment statistics and generate an HTML table for public consumption


# In[ ]:


# gather data
md = utils.get_segment_metadata()
# ignore inactive segments
md = md[md['active_html']]

rl_ = utils.get_ridelogs()

# save a table aside
md_meta = md[['id', 'name', 'distance', 'region_name', 'region_url', 'closest_ims']].copy()


# In[ ]:


d5 = rl_.copy()
latest_ridelog = d5['date'].max().date()
todays_date = pd.to_datetime(pd.Timestamp.now()).date()
d5 = d5.query('date == @latest_ridelog')

# add the closest IMS station
d6 = d5.merge(md_meta, how='right', left_on=['segment_id'], right_on=['id'])


# In[ ]:


# If we run in the morning, then the ridelog data is only for yesterday. In this case, use weather data
#  for the day following the last ridelog data
# If we run in the evening, then the ridelog data should have already caught up.
if todays_date > latest_ridelog:  
    reference_date = latest_ridelog + timedelta(days=1)
else:
    reference_date = latest_ridelog


# In[ ]:


weather_days, weather_ts = ims.get_weather_days(reference_date=reference_date, ndays=3, n_data_files=10, save_stations=True)
weather_days.drop(columns=['date'], inplace=True)  # we assume the date is the reference date we sent


# In[ ]:


#weather_days.query('StationNumber == 567')[['R01', 'R12', 'R24', 'R24_sum']]


# In[ ]:


# Add rain measurements to ride data
d7 = d6.merge(weather_days, how='left', left_on=['closest_ims'], right_on=['StationNumber'])
d7.rename(columns={'R24_sum':'rain_3d', 'R12':'rain_mm'}, inplace=True)


# In[ ]:


#d7[['segment_id', 'closest_ims', 'rain_3d', 'rain_mm']]


# In[ ]:


df_orig = d7.sort_values('date').copy()
today = df_orig.copy()


# In[ ]:


if False:
    from matplotlib.dates import DateFormatter
    sns.lineplot(data=d8, dashes=False, marker='o')
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

    plt.gca().xaxis.set_major_formatter(DateFormatter("%m-%d"))
    plt.xticks(rotation=45)
    None


# In[ ]:


def scaleup(a, b):
    return a<b

def scaledown(a, b):
    return a>b


def scalestr(v, scale, mycmp=scaleup):
    for t in scale:
        val = t[0]
        s = t[1]
        if val is None:
            return s
        if mycmp(v, val):
            return s


# In[ ]:


# prepare for display as nice HTML
def link2(a, id):
    return f'<a href="{a}">{id}</a>'

def nopct(s):
    return re.sub(r'%', '', s)

def nonan(v):
    if v is None or (type(v) == str and (v == "" or v == "nan" or v == "NaN")) or (isinstance(v, float) and (math.isnan(v) or v == -1)):
        return ""
    return v

def trafficlight(v):
    v = nonan(v)
    if v == "":
        return ""
    return scalestr(float(v), [(80, 'Chartreuse'), (30, 'DarkOrange'), (None, 'OrangeRed')], mycmp=scaledown)

def trafficlight_riderskill(v):
    v = nonan(v)
    if v == "":
        return ""
    return scalestr(float(v), [(0.2, '#e60000'),
                               (0.4, 'OrangeRed'),
                               (0.8, 'DarkOrange'),
                               (None, 'Chartreuse')],
                    mycmp=scaleup)

DEBUG = False

def riderskill_string(v):
    if DEBUG:
        return "{:.2f}".format(float(v))
    v = nonan(v)
    if v == "":
        return ""
    return scalestr(float(v), [(0.2, 'מורעל'),
                               (0.4, 'נחוש'),
                               (0.8, 'לא מסוכר'),
                               (None, 'בכיף שלו')],
                    mycmp=scaleup)

rideability_color = lambda x: '<div style="background-color: {}">{}</div>'.format(trafficlight(nopct(x)), x)

skill_color = lambda x: '<div style="background-color: {}">{}</div>'.format(trafficlight_riderskill(x), riderskill_string(x))


# In[ ]:


today[['name', 'rain_mm', 'rain_3d', 'closest_ims', 'StationNumber']].sort_values('rain_3d')


# In[ ]:


str(latest_ridelog)


# In[ ]:


locale.setlocale(locale.LC_ALL, 'he_IL')
def prettify_date(ts_, also_tod=False):
    if str(ts_) == 'NaT':
        return 'אין נתונים'
    if type(ts_) is not pd.Timestamp:
        ts_ = pd.Timestamp(ts_, tz='UTC')
    ts = ts_.astimezone(tz='Asia/Jerusalem')
    
    ret = ts.strftime('יום %A %d/%m/%Y')
    if also_tod:
        ret += ts.strftime(' שעה %H:%M')

    return ret


# In[ ]:


dfout = today.sort_values(['region_name', 'name']).copy()

#format the date
data_ts_str = "רכיבות {}".format(prettify_date(latest_ridelog))
data_ts_str += ", מזג אויר {}".format(prettify_date(weather_ts, also_tod=True))

weekday_name = latest_ridelog.strftime('%A')

# truncate name if too long
max_name_len = 20
dfout['name'] = dfout['name'].map(lambda s: s[:max_name_len] + (s[max_name_len:] and '..'))
dfout['link'] = dfout.apply(lambda x: link2(f"https://www.strava.com/segments/{x['id']}", x['name']), axis=1)
dfout['region_link'] = dfout.apply(lambda x: link2(x['region_url'], x['region_name']), axis=1)
dfout['distance'] = dfout['distance'].map(lambda x : "%.0f" % x)

dfout.drop(columns=['date', 'name', 'id', 'distance'], inplace=True)
dfout['nrides'] = dfout['nrides'].map(lambda x : "" if math.isnan(x) else "%.0f%%" % (100*x))
dfout['rain_mm'] = dfout['rain_mm'].map(lambda x : "" if math.isnan(x) else "%.1f" % x)
dfout['rain_3d'] = dfout['rain_3d'].map(lambda x : "%.0f" % x)
                                 
# re-order columns
dfout = dfout[['link', 'region_link', 'nrides', 'rain_mm', 'rain_3d']].copy()

nrides_str = "מספר רכיבות <br> ביחס ליום %s ממוצע" % (weekday_name)

dfout.rename(columns = {'link' : 'מקטע', 'region_link' : 'איזור',
                        'nrides' : nrides_str,
                        'rain_mm' : 'מ״מ גשם <br> 12 שעות', 'rain_3d' : 'מ״מ גשם<br>3 ימים',
                       },
             inplace=True)

htmlout = dfout.to_html(formatters={nrides_str: rideability_color},
                        render_links=True, classes="table",
                        escape=False, index=False, border=1)


# Add decorations and save to file

title = 'מדד בוציות בסינגלים'
update_ts = '<br><b>' +  "עדכון אחרון: {}".format(data_ts_str) + '</b></br>\n'

with open('preamble.txt', encoding="utf-8") as f:
    preamble = " ".join([l.rstrip() for l in f]) 

with open('epilog.txt', encoding="utf-8") as f:
    epilog = "\n".join([l.rstrip() for l in f]) 

html_preamble = '<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\n<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css">\n<title>' + title + '</title>\n</head><body dir=rtl>\n' + preamble + "\n" + update_ts + '<div class="container">\n'
htmlout = html_preamble + htmlout + "</div>\n" + epilog

fileout = "data/out/rides.html"

with open(fileout, "w", encoding="utf-8") as file:
    file.write(htmlout)


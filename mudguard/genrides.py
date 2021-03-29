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

# add the closest IMS station
d6 = d5.merge(md_meta, how='right', left_on=['segment_id'], right_on=['id'])


# In[ ]:


weather_days = utils.get_weather_days(d6)


# In[ ]:


# Add rain measurements to ride data
d7 = d6.merge(weather_days, how='left', left_on=['closest_ims', 'date'], right_on=['closest_ims', 'date'])

# cumulative measures of rainfall

d7.sort_values('date', inplace=True)
d7['rain_7d'] = d7.fillna(0).groupby('segment_id')['rain_mm'].apply(lambda x : x.rolling(7).sum().clip(lower=0))


# In[ ]:


# we add another day of data, so we could predict based on simulated weather conditions

lastdate = d7['date'].max()

lastdate_copy = d7.query('date == @lastdate').copy()
tomorrow = lastdate + timedelta(days=1)

lastdate_copy['date'] = tomorrow

# we will optimistically assume no rain tomorrow
# In case of NAs, we probably didn't get weather data. In this case better to invalidate the prediction too
#  (bug: for the daycounter model, this will not stop it from still giving a prediction)
lastdate_copy.loc[lastdate_copy['rain_mm'].notna(), 'rain_mm'] = 0

# now add back
d7 = pd.concat([d7, lastdate_copy], ignore_index=True)

df_orig = d7.sort_values('date').copy()


# In[ ]:


# Load parameters fitted via a statistical model
df = df_orig.copy()

params = pd.read_csv('data/segments/params.csv')

# apply moisture estimate to each segment
df['soil_moisture'] = None
df['pred'] = None

segments = df['id'].unique()

for seg in segments:
    par = params.query("segment_id == @seg")
    if len(par) > 0:
        pdict = par.iloc[0].to_dict()
        pdict.update(ast.literal_eval(par.iloc[0]['par']))
        if(pdict['score'] >= 0.35):  # only try to predict if the quality of the model is good enough
            rows = df['id'] == seg
            coef = pdict['c_soil']
            intercept = pdict['intercept']
            # We compute the moisture value which yields 0.9 of the intercept (soil is 90% dry)
            # We ignore the factors which aren't soil moisture (pessimistically assume they'll be zero throughout)
            y90 = 0.9*intercept
            if abs(coef) < 1e-6:
                coef = -1e-6
            x90 = (y90-intercept)/coef
            if pdict['f'] == 'bathtub':
                d = pdict['drainage']
                c = pdict['capacity']
                w = pdict['fwind']
                moisture = utils.bathtub_(df[rows], capacity=c, drainage=d, fwind=w)
                df.loc[rows, 'soil_moisture'] = moisture
                df.loc[rows, 'dtd'] = df.loc[rows].apply(lambda r : (r['soil_moisture'] - x90)/d, axis=1)
            elif pdict['f'] == 'bathtub_geom':
                d = pdict['drainage_factor']
                c = pdict['capacity']
                w = pdict['fwind']
                moisture = utils.bathtub_geom_(df[rows], capacity=c, drainage_factor=d, fwind=w)
                df.loc[rows, 'soil_moisture'] = moisture
                df.loc[rows, 'dtd'] = df.loc[rows].apply(lambda r : 0 if r['soil_moisture'] < 1 else (math.log(y90) -math.log(r['soil_moisture']))/math.log(d), axis=1)
            elif pdict['f'] == 'daycounter':
                d = pdict['cday']
                r = pdict['rain_thresh']
                w = pdict['fwind']
                moisture = utils.daycounter_(df[rows], cday=d, rain_thresh=r, fwind=w)
                df.loc[rows, 'soil_moisture'] = moisture
                df.loc[rows, 'dtd'] = d
            else:
                print("Uh")
            # Predict level of usage on trail: compute the value of the function, given the soil moisture value
            # (we take the other vars to be zero: rain per day, and lockdown)
            # Normalize by the intercept, which is where the function is at x=0
            df.loc[rows, 'pred'] = 1 + coef*df.loc[rows, 'soil_moisture']/intercept


# if parameters make no sense, also invalidae the nrides
#rows = (df['capacity'] == 0) | (df['drainage'] == 0)
#df.loc[rows, 'nrides'] = math.nan


# In[ ]:


# trim to just most recent observation. This also includes the fake day which we added for prediction
df_all = df.copy()
df = df.query("date >= @lastdate").copy()


# In[ ]:


# average the prediction of the fake day and the last real day
pred2 = df[['date', 'segment_id', 'pred']].fillna(math.nan).groupby(['segment_id'], as_index=False).mean()


# In[ ]:


# put predicted value back for the last real day's prediction
today = df.query("date == @lastdate").drop(columns='pred').copy()
today_pred = today.merge(pred2, how='left', left_on='segment_id', right_on='segment_id')


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
    if v is None or (type(v) == str and (v == "" or v =="nan")) or (isinstance(v, float) and math.isnan(v)):
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


today_pred[['name', 'rain_mm', 'wind_ms', 'rain_7d', 'soil_moisture', 'pred', 'closest_ims']].sort_values('pred')


# In[ ]:


dfout = today_pred.sort_values(['region_name', 'name']).copy()

#format the date
locale.setlocale(locale.LC_ALL, 'he_IL')

dateout = lastdate.strftime('יום %A %d/%m/%Y')

weekday_name = lastdate.strftime('%A')

# truncate name if too long
max_name_len = 20
dfout['name'] = dfout['name'].map(lambda s: s[:max_name_len] + (s[max_name_len:] and '..'))
dfout['link'] = dfout.apply(lambda x: link2(f"https://www.strava.com/segments/{x['id']}", x['name']), axis=1)
dfout['region_link'] = dfout.apply(lambda x: link2(x['region_url'], x['region_name']), axis=1)
dfout['distance'] = dfout['distance'].map(lambda x : "%.0f" % x)

dfout.drop(columns=['date', 'name', 'id', 'distance'], inplace=True)
dfout['nrides'] = dfout['nrides'].map(lambda x : "" if math.isnan(x) else "%.0f%%" % (100*x))
dfout['rain_mm'] = dfout['rain_mm'].map(lambda x : "" if math.isnan(x) else "%.1f" % x)
dfout['wind_ms'] = dfout['wind_ms'].map(lambda x : "" if math.isnan(x) else "%.1f" % x)
dfout['rain_7d'] = dfout['rain_7d'].map(lambda x : "%.0f" % x)
dfout['days_to_dry'] = dfout['dtd'].map(lambda x : "%.1f" % x)
dfout['pred'].fillna(math.nan, inplace=True)
                                      
# re-order columns
dfout = dfout[['link', 'region_link', 'nrides', 'rain_mm', 'rain_7d', 'pred']].copy()

nrides_str = "מספר רכיבות <br> ביחס ליום %s ממוצע" % (weekday_name)
#dryness_str = 'מספר ימים <br>עד לייבוש'
skill_str = 'דרגת נחישות'

dfout.rename(columns = {'link' : 'מקטע', 'region_link' : 'איזור',
                        'nrides' : nrides_str,
                        'rain_mm' : 'גשם יומי מ״מ', 'rain_7d' : 'גשם מצטבר  <br>שבועי מ״מ',
                        'wind_ms' : 'מהירות רוח יומי',
                        'pred' : skill_str
                       },
             inplace=True)

htmlout = dfout.to_html(formatters={nrides_str: rideability_color, skill_str: skill_color},
                        render_links=True, classes="table",
                        escape=False, index=False, border=1)


# Add decorations and save to file

title = 'מדד בוציות בסינגלים'
update_ts = '<br><b>' +  "עדכון אחרון: {}".format(dateout) + '</b></br>\n'

with open('preamble.txt') as f:
    preamble = " ".join([l.rstrip() for l in f]) 

with open('epilog.txt') as f:
    epilog = "\n".join([l.rstrip() for l in f]) 

html_preamble = '<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\n<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css">\n<title>' + title + '</title>\n</head><body dir=rtl>\n' + preamble + "\n" + update_ts + '<div class="container">\n'
htmlout = html_preamble + htmlout + "</div>\n" + epilog

fileout = "data/out/rides.html"

with open(fileout, "w", encoding="utf-8") as file:
    file.write(htmlout)


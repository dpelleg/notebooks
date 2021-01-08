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

# Analyse segment statistics and generate an HTML table for public consumption


# In[ ]:


# gather data
md = utils.get_segment_metadata()
# ignore inactive segments
md = md[md['active_modeling'] & md['active_strava']]

rl_ = utils.get_ridelogs()

# save a table aside
md_meta = md[['id', 'name', 'distance', 'region_name', 'region_url', 'closest_ims']].copy()


# In[ ]:


d5 = rl_.copy()

# add the closest IMS station
d6 = d5.merge(md_meta, how='right', left_on=['segment_id'], right_on=['id'])


# In[ ]:


#d6.query("segment_id == '6958098'")[['date', 'rides', 'nrides']]


# In[ ]:


weather_days = utils.get_weather_days(d6)

# Add rain measurements
d7 = d6.merge(weather_days, how='left', left_on=['closest_ims', 'date'], right_on=['closest_ims', 'date'])

# cumulative measures of rainfall

d7.sort_values('date', inplace=True)
d7['rain_7d'] = d7.fillna(0).groupby('segment_id')['rain_mm'].apply(lambda x : x.rolling(7).sum().clip(lower=0))
#data['soil_moisture'] = data.groupby('segment_id')['rain_mm'].apply(utils.bathtub)
df_orig = d7.sort_values('date').copy()


# In[ ]:


d7[['name', 'closest_ims']][1:20]


# In[ ]:


# Load parameters fitted via a statistical model
df = df_orig.copy()

params = pd.read_csv('data/segments/params.csv')

# apply moisture estimate to each segment
df['soil_moisture'] = None
df['capacity'] = None
df['drainage'] = None
df['fwind'] = None

segments = df['id'].unique()

for seg in segments:
    par = params.query("segment_id == @seg")
    if len(par) > 0:
        pdict = par.iloc[0].to_dict()
        pdict.update(ast.literal_eval(par.iloc[0]['par']))
        if(pdict['score'] >= 0.45):
            rows = df['id'] == seg
            coef = pdict['coef']
            intercept = pdict['intercept']
            # We compute the moisture value which yields 0.9 of the intercept (soil is 90% dry)
            y90 = 0.9*intercept
            x90 = -0.1*intercept/coef
            if pdict['f'] == 'bathtub':
                d = pdict['drainage']
                c = pdict['capacity']
                w = pdict['fwind']
                if c > 0 and d > 0:
                    moisture = utils.bathtub_(df[rows], capacity=c, drainage=d, fwind=w)
                    df.loc[rows, 'soil_moisture'] = moisture
                    df.loc[rows, 'dtd'] = df.loc[rows].apply(lambda r : (r['soil_moisture'] - x90)/d, axis=1)
            elif pdict['f'] == 'bathtub_geom':
                d = pdict['drainage_factor']
                c = pdict['capacity']
                w = pdict['fwind']
                if c > 0 and d > 0:
                    moisture = utils.bathtub_geom_(df[rows], capacity=c, drainage_factor=d, fwind=w)
                    df.loc[rows, 'soil_moisture'] = moisture
                    df.loc[rows, 'dtd'] = df.loc[rows].apply(lambda r : 0 if r['soil_moisture'] < 1 else (math.log(y90) -math.log(r['soil_moisture']))/math.log(1/d), axis=1)
            else:
                print("Uh")

#Bug: we need a better way to guarantee sane values
df['dtd'].clip(lower=0, upper=10, inplace=True)

# if parameters make no sense, also invalidae the nrides
#rows = (df['capacity'] == 0) | (df['drainage'] == 0)
#df.loc[rows, 'nrides'] = math.nan


# In[ ]:


# trim to just most recent day
df_all = df.copy()
lastdate = df['date'].max()
df = df.query("date == @lastdate").copy()


# In[ ]:


df_all.query("segment_id == '17421855'")[['date', 'rides', 'rides_dow', 'nrides', 'rain_7d', 'soil_moisture']]


# In[ ]:


if False:
    from matplotlib.dates import DateFormatter
    sns.lineplot(data=d8, dashes=False, marker='o')
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

    plt.gca().xaxis.set_major_formatter(DateFormatter("%m-%d"))
    plt.xticks(rotation=45)
    None


# In[ ]:


# prepare for display as nice HTML
def link2(a, id):
    return f'<a href="{a}">{id}</a>'

def nopct(s):
    return re.sub(r'%', '', s)

def nonan(v):
    if v is None or (type(v) == str and (v == "" or v =="nan")) or (type(v) == float and math.isnan(v)):
        return ""
    return v


def trafficlight(v, scale=[80, 30]):
    v = nonan(v)
    if v == "":
        return ""

    v = float(v)
    if v>scale[0]:
        return 'Chartreuse'
    if v>scale[1]:
        return 'DarkOrange'
    return 'OrangeRed'

rideability_color = lambda x: '<div style="background-color: {}">{}</div>'.format(trafficlight(nopct(x)), x)
dryness_color = lambda x: '<div style="background-color: {}">{}</div>'.format(trafficlight(-float(x), scale=[-1, -2]), nonan(x))


# In[ ]:


dfout = df.sort_values(['region_name', 'name']).copy()

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

                                      
# re-order columns
dfout = dfout[['link', 'region_link', 'nrides', 'rain_mm', 'wind_ms', 'rain_7d', 'days_to_dry']].copy()

nrides_str = "מספר רכיבות אתמול <br> ביחס ליום %s ממוצע" % (weekday_name)
dryness_str = 'מספר ימים <br>עד לייבוש'
dfout.rename(columns = {'link' : 'מקטע', 'region_link' : 'איזור',
                        'nrides' : nrides_str,
                        'rain_mm' : 'גשם יומי מ״מ', 'rain_7d' : 'גשם מצטבר  <br>שבועי מ״מ',
                        'wind_ms' : 'מהירות רוח יומי',
                        'days_to_dry' : dryness_str
                       },
             inplace=True)

htmlout = dfout.to_html(formatters={nrides_str: rideability_color, dryness_str: dryness_color},
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


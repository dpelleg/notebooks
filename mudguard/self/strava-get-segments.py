#!/usr/local/bin/python3.9
# coding: utf-8

# # Accessing my data via the Strava API using Stravalib
# This notebook includes the code as dicussed in the following Medium blog post:
# https://medium.com/@mandieq/accessing-user-data-via-the-strava-api-using-stravalib-d5bee7fdde17

# ## Set up and authentication

import time
import pickle
import pandas as pd
import numpy as np

import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

from stravalib.client import Client
client = Client()


# Load ID and secret for your Strava App as set up via Strava's developer area:

MY_STRAVA_CLIENT_ID, MY_STRAVA_CLIENT_SECRET = open('client.secret').read().strip().split(',')
print ('Client ID {} and secret {} read from file'.format(MY_STRAVA_CLIENT_ID, MY_STRAVA_CLIENT_SECRET) )


# ### One time authentication with athlete
#
# Only needs to be done once in order to get access token and refresh token. Hereafter you use the refresh token to get a new one when the old one runs out.
# The cells below need to be converted back to code cells in order to run them. Note: **once only**!

CODE = '291dfbb85fd6289f12b387f0c9ae23b90e0425e5'

if CODE is None:
    url = client.authorization_url(client_id=MY_STRAVA_CLIENT_ID,
                                redirect_uri='http://127.0.0.1:5000/authorization',
                                scope=['read_all','profile:read_all','activity:read_all']
                                )
    print(url)
    print("Use URL for althete approving access, then manually copy the code returned as part of the output URL")

    access_token = client.exchange_code_for_token(client_id=MY_STRAVA_CLIENT_ID,
                                                client_secret=MY_STRAVA_CLIENT_SECRET,
                                                code=CODE)
    with open('access_token.pickle', 'wb') as f:
        pickle.dump(access_token, f)
    exit

# ### Read in access token and refresh if expired
with open('access_token.pickle', 'rb') as f:
    access_token = pickle.load(f)

print('Latest access token read from file:')
print(access_token)

if time.time() > access_token['expires_at']:
    print('Token has expired, will refresh')
    refresh_response = client.refresh_access_token(client_id=MY_STRAVA_CLIENT_ID,
                                                client_secret=MY_STRAVA_CLIENT_SECRET,
                                                refresh_token=access_token['refresh_token'])
    access_token = refresh_response
    with open('access_token.pickle', 'wb') as f:
        pickle.dump(refresh_response, f)
    print('Refreshed token saved to file')

    client.access_token = refresh_response['access_token']
    client.refresh_token = refresh_response['refresh_token']
    client.token_expires_at = refresh_response['expires_at']

else:
    print('Token still valid, expires at {}'
          .format(time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime(access_token['expires_at']))))

    client.access_token = access_token['access_token']
    client.refresh_token = access_token['refresh_token']
    client.token_expires_at = access_token['expires_at']


athlete = client.get_athlete()
print("Athlete's name is {} {}, based in {}, {}"
      .format(athlete.firstname, athlete.lastname, athlete.city, athlete.country))

seg_id = 3808938;

seg = client.get_segment(seg_id)
# To see all fields / information available
#athlete.to_dict()

print(seg.to_dict())

# this fails with no permissions unless is performed by the athlete
seg_leaderboard = client.get_segment_leaderboard(seg_id)
print(seg_leaderboard.to_dict())

exit()

# ## Working with activities

activities = client.get_activities(limit=1000)

# Choose some fields of interest from this data in order to read into a DataFrame

my_cols =['name',
          'start_date_local',
          'type',
          'distance',
          'moving_time',
          'elapsed_time',
          'total_elevation_gain',
          'elev_high',
          'elev_low',
          'average_speed',
          'max_speed',
          'average_heartrate',
          'max_heartrate',
          'start_latitude',
          'start_longitude',
          'achievement_count',
          'pr_count',
          'kudos_count',
          'total_photo_count',
          'suffer_score']


data = []
for activity in activities:
    my_dict = activity.to_dict()
    data.append([activity.id]+[my_dict.get(x) for x in my_cols])

# Add id to the beginning of the columns, used when selecting a specific activity
my_cols.insert(0,'id')


# In[26]:


df = pd.DataFrame(data, columns=my_cols)

# Make all walks into hikes for consistency
df['type'] = df['type'].replace('Walk','Hike')

# Create a distance in km column
df['distance_km'] = df['distance']/1e3

# Convert dates to datetime type
df['start_date_local'] = pd.to_datetime(df['start_date_local'])

# Create a day of the week and week of the year columns
df['day_of_week'] = df['start_date_local'].dt.day_name()
df['month_of_year'] = df['start_date_local'].dt.month

# Convert times to timedeltas
df['moving_time'] = pd.to_timedelta(df['moving_time'])
df['elapsed_time'] = pd.to_timedelta(df['elapsed_time'])

# Convert timings to hours for plotting
df['elapsed_time_hr'] = df['elapsed_time'].astype(int)/3600e9
df['moving_time_hr'] = df['moving_time'].astype(int)/3600e9


# In[21]:


df.head()


# In[22]:


df.dtypes


# In[27]:



# Split activities seen

df.type.value_counts()


# In[28]:


# Output to an external csv file

df.to_csv('../activities.csv')


# Let's look at some specifics of data (most output removed for privacy):

# In[ ]:


df.nlargest(5,'max_speed')


# In[ ]:


df.nsmallest(5,'max_speed')


# In[29]:


sns.catplot(x='type', kind='count', data=df);


# In[30]:


day_of_week_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday' ]

g = sns.catplot(x='day_of_week', y='distance_km', kind='strip', data=df,
                order=day_of_week_order, col='type', height=4, aspect=0.9,
                palette='pastel')

(g.set_axis_labels("Week day", "Distance (km)")
  .set_titles("Activity type: {col_name}")
  .set_xticklabels(rotation=30));


# In[31]:


temp_df = df[['type','moving_time_hr','distance_km','total_elevation_gain','average_speed']]

g = sns.PairGrid(temp_df, hue='type', palette='pastel')
g.map_diag(plt.hist)
g.map_offdiag(plt.scatter)
g.add_legend();


# ## Plot a specific activity onto a map

# Let's plot the route of the most recent activity...

# In[32]:


activity_number = 0

df['id'][activity_number]


# In[33]:


types = ['time', 'distance', 'latlng', 'altitude', 'velocity_smooth', 'moving', 'grade_smooth']
activity_data=client.get_activity_streams(df['id'][activity_number], types=types)


# In[34]:


map = folium.Map(location=[df['start_latitude'][activity_number],df['start_longitude'][activity_number]],
                 zoom_start=14,
                 width='100%'
                )

folium.PolyLine(activity_data['latlng'].data).add_to(map)
map

import os
import sys
import datetime
import pandas as pd
import ims

# get climate data for a given date and station

# change dir to the script's dir
os.chdir(sys.path[0])

# This is the threshold hour for daily rain amount calculations
threshold_hour = 19

#df = ims.get_rain_day("2", datetime.date(2020, 11, 25))

df = ims.get_rain_day("2", datetime.date(2020, 11, 25))

valid['value'][valid['datetime'].between('2020-11-24T19:00', '2020-11-25T19:00')].sum()

df.to_csv('rainday.csv')
#df = pd.read_csv('rainday.csv')

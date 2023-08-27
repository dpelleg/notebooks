#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
import locale
import json

with open('data/conf.json', 'r') as json_file:
    conf = json.load(json_file)

kwh_rate = conf['kwh_rate']
kw_rate_date = conf['kwh_rate_date']

def read_data(fname):
    meter = pd.read_csv('data/meter.csv', skiprows=11)
    meter.columns=['time', 'consumption']
    meter['time'] = pd.to_datetime(meter['time'], format='%d/%m/%Y %H:%M')
    meter.set_index('time', inplace=True)
    meter = meter.resample('1H').sum()
    locale.setlocale(locale.LC_ALL, 'he_IL')
    meter['date'] = meter.index.date
    meter['wday'] = meter.index.weekday
    meter['hour'] = meter.index.hour
    meter['wday_name'] = meter.index.day_name()
    meter['timeperiod'] = meter.index.strftime('%B %Y')
    return meter

def get_timeperiods_with_count_above_threshold(df, threshold=10):
    # Group by 'timeperiod' and count unique dates
    result = df.groupby('timeperiod')['date'].nunique()
    # Create a list of timeperiod values where count is above the threshold
    timeperiods_above_threshold = result[result > threshold].index.tolist()
    return timeperiods_above_threshold

#--------------------------------------
# implementation of time-based billing
#--------------------------------------

def filter_hour_and(df, start_hour, end_hour):
    return pd.Series((df.index.hour >= start_hour) & (df.index.hour < end_hour), index=df.index)

def filter_hour_or(df, start_hour, end_hour):
    return pd.Series((df.index.hour >= start_hour) | (df.index.hour < end_hour), index=df.index)

def filter_days(df, days):
    return pd.Series(df.index.day_name().isin(days), index=df.index)

def apply_filter(df, val, filter_func):
    pred = filter_func(df)
    ret = pd.Series(0, index=pred.index)
    ret[pred] = val
    return ret

# pazgas sources:
# https://campaigns.pazgas.co.il/ele/

def pazgas_daytime(df):
    return apply_filter(df, 15, lambda x:filter_hour_and(x, 8, 16))

def pazgas_nighttime(df):
    return apply_filter(df, 15, lambda x:filter_hour_or(x, 23, 7))

def pazgas_unlimited(df):
    return pd.Series(5, index=df.index)

def pazgas_weekend(df):
    return apply_filter(df, 10, lambda x:filter_days(x, ['Friday', 'Saturday']))

# Amisragas sources:
# https://lp.amisragas.co.il/electric/
def amisragas_unlimited(df):
    return pd.Series(6.5, index=df.index)

# Electra sources:
# https://electra-power.co.il/

def electra_power(df):
    return pd.Series(5, index=df.index)

def electra_hitec(df):
    return apply_filter(df, 8, lambda x:filter_hour_or(x, 23, 17))

# This is the base rate
def no_discount(df):
    return pd.Series(0, index=df.index)


#+++-----------------------------------


# human-readable names for the schedules
schedule_xlat = {
    'no_discount' : 'חחי',
    'pazgas_daytime' : 'פזגז יום',
    'pazgas_unlimited' : 'פזגז ללא הגבלה',
    'pazgas_weekend' : 'פזגז סופ״ש',
    'pazgas_nighttime' : 'פזגז לילה',
    'amisragas_unlimited' : 'אמישראגז',
    'electra_power' : 'אלקטרה פאואר',
    'electra_hitec' : 'אלקטרה הייטק',
}

# a list of different cost schedules to consider
schedules = [
    no_discount,
    pazgas_daytime,
    pazgas_unlimited,
    pazgas_weekend,
    pazgas_nighttime,
    amisragas_unlimited,
    electra_power,
    electra_hitec,
]

#----------------------------------------


def cost_by_schedule(df, schedule):
    discount_pct=schedule(df)     # for each reading, get the discount percent (0 if no discount)
    multiplier = 1. - discount_pct/100.
    cost = pd.DataFrame(data={
        'cost' : df['consumption'] * kwh_rate * multiplier,
        'timeperiod' : df['timeperiod']},
        index=df.index)
    return cost

def cost_by_month(df):
    return df.groupby('timeperiod').sum()

def compute_costs(df):
    meter = df.copy()

    # find which months have enough days
    timeperiods = get_timeperiods_with_count_above_threshold(meter, 10)

    # filter out months with too little data
    meter = meter[meter['timeperiod'].isin(timeperiods)]

    costs = None
    if len(meter) > 0:
        for schedule in schedules:
            cost = cost_by_month(cost_by_schedule(meter, schedule))
            cost.rename(columns={cost.columns[0]:schedule.__name__}, inplace=True)
            if costs is None:
                costs = cost
            else:
                costs = pd.concat([costs, cost], axis=1)

    return costs

def style_table(df):
    df.rename(columns = schedule_xlat, inplace=True)
    df.rename_axis('תקופה', inplace=True)

    styled_df = df.style.format('{:.2f}').highlight_min(color='#b1d77a', axis=1).highlight_max(color='#f287d0', axis=1)

    # Convert the Styler to HTML
    html_table = styled_df.to_html()

    # to use within Jupyter notebook: display(style_table(costs))
    return styled_df

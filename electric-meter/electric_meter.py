#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
import locale
import json
from functools import lru_cache
from pyluach import dates
from datetime import timedelta
import io
import re
import unittest

with open('data/conf.json', 'r') as json_file:
    conf = json.load(json_file)

kwh_rate = conf['kwh_rate']
kwh_rate_date = conf['kwh_rate_date']

_header_pattern = re.compile(r'^\s*"?Interval starting"?,"?Consumption, kWh"?\s*$')

# TAOZ definitions - https://www.iec.co.il/content/tariffs/contentpages/taozb-namuch
month_to_season = {
    1: "winter",
    2: "winter",
    3: "transition",
    4: "transition",
    5: "transition",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "summer",
    10: "transition",
    11: "transition",
    12: "winter"
}

def file_contains_header(file, header=_header_pattern):
    with open(file, 'r', encoding='UTF-8') as f:
        while True:
            line = f.readline()
            if not line:
                return False
            if header.match(line):
                return True
    return False

def first_non_digit_char(input_string):
    match = re.match(r'("?)(\d*)(\D)', input_string)
    if match:
        return match.group(3)
    else:
        return None  # No non-digit character found

def read_file_from_header(file, header=_header_pattern):
    max_lines = 100000
    max_size_mb = 10

    data_started = False
    data_lines = []

    line_count = 0
    file_size = 0
    date_format = None

    with open(file, 'r', encoding='UTF-8') as f:
        while True:
            line = f.readline().strip()
            if not line:
                break
            if header.match(line):
                data_started = True
                data_lines.append(line)
            elif data_started:
                if date_format is None:
                    sep = first_non_digit_char(line)
                    if sep == '-':
                        date_format = '%d-%m-%y %H:%M'
                    elif sep == '/':
                        date_format = '%d/%m/%Y %H:%M'
                data_lines.append(line)
                line_count += 1
                file_size += len(line)  # Add the length of the line to the file size
                if line_count > max_lines or file_size > max_size_mb * (1024 * 1024):  # Convert max_size_mb to bytes
                    raise ValueError("File exceeds the maximum allowed lines or size.")

    csv_content = '\n'.join(data_lines)
    if len(csv_content) > 0:
        return pd.read_csv(io.StringIO(csv_content)), date_format
    raise ValueError("Bad file contents")

def read_data(fname):

    def reformat_date_string(date_str):
        if isinstance(date_str, str) and '/' in date_str:
            match = re.match(r'(\d{2}/\d{2}/\d{4} \d{2}:\d{2})', date_str)
            if match:
                original_date = match.group(1)
                new_date = pd.to_datetime(original_date, format='%d/%m/%Y %H:%M').strftime('%Y-%d-%m %H:%M:%S')
                return date_str.replace(original_date, new_date)

        return str(date_str)

    if fname.endswith('.csv'):
        meter, date_format = read_file_from_header(fname)
    elif fname.endswith('.xlsx'):
        meter = pd.read_excel(fname, skiprows=11, dtype={'Interval starting':object, 'Consumption, kWh':object})
        colname = meter.columns[0]
        meter[colname] = pd.Series(meter[colname].apply(reformat_date_string), dtype=str)
        date_format='%Y-%d-%m %H:%M:%S'
    else:
        raise ValueError('Unknown file type')
    meter.columns=['time', 'consumption']
    meter['time'] = pd.to_datetime(meter['time'], format=date_format)
    meter.set_index('time', inplace=True)
    meter = meter.resample('1H').sum()
    locale.setlocale(locale.LC_ALL, 'he_IL')
    meter['date'] = meter.index.date
    meter['month'] = meter.index.month
    meter['wday'] = meter.index.weekday
    meter['hour'] = meter.index.hour
    meter['wday_name'] = meter.index.day_name()
    meter['timeperiod'] = meter.index.strftime('%Y%m01')   # keep it in YYYYMMDD format, we'll later sort it and format it nicely
    meter['season'] = meter['month'].map(month_to_season)
    set_hhi_weekends(meter)
    return meter

def get_timeperiods_with_count_above_threshold(df, threshold=10):
    # Group by 'timeperiod' and count unique dates
    result = df.groupby('timeperiod')['date'].nunique()
    # Create a list of timeperiod values where count is above the threshold
    timeperiods_above_threshold = result[result > threshold].index.tolist()
    return timeperiods_above_threshold

#--------------------------------------
# Utility functions for holidays and weekends
#--------------------------------------
@lru_cache
def hhi_holiday(date):
    """Return holiday of given date, constrained to Hevrat Hashmal holidays for TAOZ
    Source: https://www.iec.co.il/content/tariffs/contentpages/taozb-namuch

    Parameters
    ----------
    date : ``HebrewDate``, ``GregorianDate``, or ``JulianDay``
      Any date that implements a ``to_heb()`` method which returns a
      ``HebrewDate`` can be used.

    Returns
    -------
    str or ``None``
      The name of the holiday or ``None`` if the given date is not
      a Jewish holiday.
    """
    date = date.to_heb()
    year = date.year
    month = date.month
    day = date.day
    if month == 7:
        if day in range(1, 3):
            return 'Rosh Hashana'
        elif day == 10:
            return 'Yom Kippur'
        elif day == 15:
            return 'Succos'
        elif day == 22:
            return 'Simhat Torah'
    elif month == 1 and day in [15, 21]:
        return 'Pesach'
    elif month == 3 and day == 6:
        return 'Shavuos'

@lru_cache
def yom_atzmaut_heb_date(heb_year):
    target_date = dates.HebrewDate(heb_year, 2, 5)
    weekday = int(target_date.to_pydate().strftime('%w'))  # 0=Sunday
    # offsets - from https://he.wikipedia.org/wiki/%D7%99%D7%95%D7%9D_%D7%94%D7%A2%D7%A6%D7%9E%D7%90%D7%95%D7%AA
    if weekday == 5:     #Friday
        target_date -= 1
    elif weekday == 6:   # Saturday
        target_date -= 2
    elif weekday == 1:   # Monday
        target_date += 1
    return target_date.to_pydate()

def is_yom_atzmaut(year, month, day):
    heb_date = dates.GregorianDate(year, month, day).to_heb()
    heb_year = heb_date.year
    yom_atzmaut_date = yom_atzmaut_heb_date(heb_year)
    return yom_atzmaut_date == heb_date.to_pydate()

def get_holidays(df):
    holiday_dates = []
    for d in set(df.index.date):
        if is_yom_atzmaut(d.year, d.month, d.day):
            holiday_dates.append(d)
        else:
            hd=dates.GregorianDate(d.year, d.month, d.day)
            holiday = hhi_holiday(hd)
            if holiday is not None:
                holiday_dates.append(hd.to_pydate())
    return holiday_dates

def set_hhi_weekends(df):
    # Get the list of holidays
    holidays = get_holidays(df)

    # Add the dates which precede each holiday by one day
    expanded_holidays = [date - pd.Timedelta(days=1) for date in holidays] + holidays

    # Add Fridays and Saturdays
    for d in set(df.index.date):
        if d.weekday() in [4,5]:
            expanded_holidays.append(d)

    # Convert the datetime index to a list of datetime.date objects
    date_list = [date.date() for date in df.index]

    df['hhi_weekend'] = [d in expanded_holidays for d in date_list]

    return df
#--------------------------------------
# implementation of time-based billing
#--------------------------------------

def filter_hour_and(df, start_hour, end_hour):
    return pd.Series((df.index.hour >= start_hour) & (df.index.hour < end_hour), index=df.index)

def filter_hour_or(df, start_hour, end_hour):
    return pd.Series((df.index.hour >= start_hour) | (df.index.hour < end_hour), index=df.index)

def filter_days(df, days):
    return pd.Series(df.index.day_name().isin(days), index=df.index)

def apply_filter(df, val, filter_func, default_val=0):
    pred = filter_func(df)
    ret = pd.Series(default_val, index=pred.index)
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

# Cellcom sources:
# https://cellcom.co.il/production/Private/1/energy3/
def cellcom_flat(df):
    # Flat 5%
    return pd.Series(5, index=df.index)

def cellcom_home_office(df):
    # 15% off Sun-Thu from 7:00 to 17:00
    return apply_filter(df, 15, lambda x: (~filter_days(x, ['Friday', 'Saturday'])) & filter_hour_and(x, 7, 17))

def cellcom_nighttime(df):
    # 20% off Sun-Thu 22:00 till 7:00 next morning
    def filter_sun_thu_night(x):
        return (~filter_days(x, ['Friday', 'Saturday']) & filter_hour_and(x, 22, 24))

    def filter_mon_fri_morning(x):
        return (~filter_days(x, ['Saturday', 'Sunday']) & filter_hour_and(x, 0, 7))

    return apply_filter(df, 20, lambda x:filter_sun_thu_night(x) | filter_mon_fri_morning(x))

# This is the base rate
def no_discount(df):
    return pd.Series(0, index=df.index)

# placeholers
def taoz1(df):
    C = taoz_rate_all_seasons(df, conf['taoz'])
    return C, conf['taoz1_fixed_cost']    # haluka + aspaka

def taoz2(df):
    C = taoz_rate_all_seasons(df, conf['taoz'])
    return C, conf['taoz2_fixed_cost']    # haluka + aspaka
#+++-----------------------------------


# human-readable names for the schedules
schedule_xlat = {
    'no_discount' : 'חחי',
    'pazgas_daytime' : 'פזגז יום',
    'pazgas_unlimited' : 'פזגז ללא הגבלה',
    'pazgas_weekend' : 'פזגז סופ״ש',
    'pazgas_nighttime' : 'פזגז לילה',
    'amisragas_unlimited' : 'אמישראגז',
    'electra_power' : '5% אלקטרה פאואר',
    'electra_hitec' : 'אלקטרה הייטק',
    'cellcom_flat' : 'סלקום 5%',
    'cellcom_home_office' : 'סלקום מהבית',
    'cellcom_nighttime' : 'סלקום לילה',
    'taoz1' : 'תעו״ז חד-חודשי',
    'taoz2' : 'תעו״ז דו-חודשי',
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
    cellcom_flat,
    cellcom_home_office,
    cellcom_nighttime,
    taoz1,
    taoz2
]

## TAOZ
#----------------------------------------

def taoz_rate_one_season(df, low_price, high_price, weekday_high_hours, weekend_high_hours):

    def rate_helper(df, selector, start_hour, end_hour):
        F = apply_filter(df[selector],
                         val=high_price,
                         filter_func=lambda x: filter_hour_and(x, start_hour, end_hour),
                         default_val=low_price)
        ret.loc[F.index] = F

    ret = pd.Series(np.nan, index=df.index)

    hhi_weekend = df['hhi_weekend']
    # weekdays
    rate_helper(df, ~hhi_weekend, weekday_high_hours['start'], weekday_high_hours['end'])
    # weekends
    rate_helper(df,  hhi_weekend, weekend_high_hours['start'], weekend_high_hours['end'])

    return ret

def taoz_rate_all_seasons(df, taoz_schedule):
    ret = pd.Series(np.nan, index=df.index)
    for season in df['season'].unique():
        season_conf=taoz_schedule[season]
        low_price = season_conf['low_price']
        high_price = season_conf['high_price']
        weekday_high_hours = season_conf['weekday_high_hours']
        weekend_high_hours = season_conf['weekend_high_hours']
        R = taoz_rate_one_season(df[df['season']==season], low_price, high_price, weekday_high_hours, weekend_high_hours)
        ret.loc[R.index] = R

    return ret
#------------------------------------------

def cost_by_schedule(df, schedule):
    if schedule.__name__.startswith('taoz'):    # these schedules return the actual rate per reading
        cost_items, fixed_cost_per_timeperiod = schedule(df)
        cost_items = cost_items * df['consumption']
    else:
        discount_pct = schedule(df)     # these schedules return the discount percent per reading (0 if no discount)
        multiplier = 1. - discount_pct/100.
        cost_items = df['consumption'] * kwh_rate * multiplier
        fixed_cost_per_timeperiod = 0
    cost = pd.DataFrame(data={
        'cost' : cost_items,
        'timeperiod' : df['timeperiod']},
        index=df.index)

    return cost, fixed_cost_per_timeperiod

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
            cost_items, cost_fixed = cost_by_schedule(meter, schedule)
            cost = cost_by_month(cost_items) + cost_fixed
            cost.rename(columns={cost.columns[0]:schedule.__name__}, inplace=True)
            if costs is None:
                costs = cost
            else:
                costs = pd.concat([costs, cost], axis=1)

    # make sure it's sorted
    costs.sort_index(ascending=True, inplace=True)
    # transform YYYYMMDD format to "month year"
    costs.index = pd.to_datetime(costs.index).to_series().dt.strftime('%B %Y')
    return costs, conf

def style_table(df):

    df.rename(columns = schedule_xlat, inplace=True)
    df.rename_axis('תקופה', inplace=True)

    styled_df = df.style.format('{:.2f}').highlight_min(color='#b1d77a', axis=1).highlight_max(color='#f287d0', axis=1)
    styled_df.set_table_attributes('class="cost-table"')

    classes = pd.DataFrame("optional", index=df.index, columns=[schedule_xlat[t] for t in ['taoz1', 'taoz2']])

    styled_df.set_td_classes(classes)

    # Convert the Styler to HTML
    html_table = styled_df.to_html()

    # to use within Jupyter notebook: display(style_table(costs))
    return styled_df


#------------------------------------------
#   Tests
#------------------------------------------

class Test_meter(unittest.TestCase):
    def setUp(self):
        test_dates = [
            '2023-10-01 21:00',
            '2023-10-01 22:00',
            '2023-03-04 21:00',
            '2023-03-04 22:00',
            '2023-06-07 16:00',
            '2023-06-07 17:00',
            '2023-06-09 16:00',
            '2023-06-09 17:00',
            '2023-01-03 21:00',
            '2023-01-03 22:00',
            '2023-01-07 16:00',
            '2023-01-07 17:00',
        ]

        mymeter = pd.DataFrame(data={'time':pd.to_datetime(test_dates)})

        mymeter.set_index('time', inplace=True)

        mymeter['date'] = mymeter.index.date
        mymeter['wday'] = mymeter.index.weekday
        mymeter['hour'] = mymeter.index.hour
        mymeter['month'] = mymeter.index.month
        mymeter['wday_name'] = mymeter.index.day_name()
        F=filter_days(mymeter, ['Friday', 'Saturday'])
        mymeter['hhi_weekend'] = F
        mymeter['season'] = mymeter['month'].map(month_to_season)
        self.mymeter = mymeter

    def test_taoz(self):
        taoz_schedule = {
        'summer' : {'low_price':'lowsummer', 'high_price':'highsummer', 'weekday_high_hours':{'start':17, 'end':23}, 'weekend_high_hours':{'start':-1, 'end':-1}},
        'winter' : {'low_price':'lowwinter', 'high_price':'highwinter', 'weekday_high_hours':{'start':17, 'end':22}, 'weekend_high_hours':{'start':17, 'end':22}},
        'transition' : {'low_price':'lowtrans', 'high_price':'hightrans', 'weekday_high_hours':{'start':17, 'end':22}, 'weekend_high_hours':{'start':-1, 'end':-1}},
        }

        mymeter = self.mymeter

        for season in mymeter['season'].unique():
            season_conf=taoz_schedule[season]
            low_price = season_conf['low_price']
            high_price = season_conf['high_price']
            weekday_high_hours = season_conf['weekday_high_hours']
            weekend_high_hours = season_conf['weekend_high_hours']
            R = taoz_rate_one_season(mymeter[mymeter['season']==season], low_price, high_price, weekday_high_hours, weekend_high_hours)
            mymeter.loc[R.index, 'price'] = R

        expected = ['hightrans',
             'lowtrans',
             'lowtrans',
             'lowtrans',
             'lowsummer',
             'highsummer',
             'lowsummer',
             'lowsummer',
             'highwinter',
             'lowwinter',
             'lowwinter',
             'highwinter']

        computed = mymeter['price'].to_list()

        self.assertEqual(len(computed), len(expected))
        for i in range(len(expected)):
            self.assertEqual(computed[i], expected[i])

if __name__ == '__main__':
    if False:
        unittest.main()
    else:
        meter = read_data('uploads/was-excel.xlsx')
#        meter = read_data('uploads/1694378597_9_169c543f.csv')
#        meter = read_data('data/1694094031_9_532da2ca.csv')
        #meter = read_data('data/dirty1.csv')
        costs, conf = compute_costs(meter)
        print(costs)
        print(conf)

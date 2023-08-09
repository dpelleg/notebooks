#!/usr/bin/env python

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import math

import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import statsmodels.api as sm

datadir = '../data/'

def read_file_helper(fname, enc='iso8859-8'):
    fd = open(fname, encoding=enc, errors='replace')
    df = pd.read_csv(fd, sep='|')
    return df

def add_model(df):
    df['model'] = df.apply(lambda x: '_'.join([x[y] for y in ['tozeret_cd', 'degem_cd', 'shnat_yitzur', 'sug_degem']]), axis=1)

def get_model_name(ns):
    names = pd.DataFrame(data={'model':ns})
    ret = pd.merge(names, models, how='left', on='model')[['tozeret_nm', 'kinuy_mishari']]
    return ret


def convert_make(df, oldcol='tozeret_nm', newcol='make'):
    # read dictionary
    filename=datadir + 'makes_dict.csv'

    with open(filename, 'r') as f:
        lines = f.readlines()

    make_dict = []
    for line in lines:
        line = line.strip()
        items = line.split(',', 1)
        itm = items[0].strip()
        if len(items) > 1:
            make_dict.append((itm, items[1].strip()))
        else:
            make_dict.append((itm, itm))

    newdat = df[oldcol].copy()
    for (m_in, m_out) in make_dict:
        newdat[newdat.str.startswith(m_in)] = m_out
    df[newcol] = newdat


def _convert_helper(df, oldcol, newcol, dictfile):
    # read dictionary
    filename=datadir + dictfile

    with open(filename, 'r') as f:
        lines = f.readlines()

    make_dict = []
    for line in lines:
        line = line.strip()
        items = line.split(',', 1)
        itm = items[0].strip()
        if len(items) > 1:
            make_dict.append((itm, items[1].strip()))
        else:
            make_dict.append((itm, itm))

    newdat = df[oldcol].copy()
    for (m_in, m_out) in make_dict:
        newdat[newdat.str.startswith(m_in)] = m_out
    df[newcol] = newdat

def convert_make(df, oldcol='tozeret_nm', newcol='make'):
    _convert_helper(df, oldcol, newcol, 'makes_dict.csv')

def convert_color(df, oldcol='tzeva_rechev', newcol='color'):
    _convert_helper(df, oldcol, newcol, 'color_dict.csv')

def trade_category(d):
    oc = d['ownership_count']
    months = d['months_to_first_trade']
    if math.isnan(oc):
        return 'ללא'
    if (oc == 1) & (months == 0):
        return 'מקורי'
    if months < 12:
        return 'נמכר תוך שנה'
    return 'נמכר תוך יותר משנה'

# source : https://data.gov.il/dataset/private-and-commercial-vehicles

def read_file(fname):
    fname = datadir + fname
    df = read_file_helper(fname)

    for c in ['mispar_rechev', 'degem_cd', 'tozeret_cd', 'shnat_yitzur']:
        df[c] = df[c].astype(str)

    df['test']= pd.to_datetime(df.mivchan_acharon_dt)
    df['test_expiry']= pd.to_datetime(df.tokef_dt)
    df['year'] = df['shnat_yitzur'].astype(int)
    c='moed_aliya_lakvish'
    df[c] = pd.to_datetime(df[c], format="%Y-%m")
    df['kvish_ym'] = df[c].dt.strftime('%Y%m')
    df['sidra'] = df['mispar_rechev'].apply(lambda k : k[-2:])
    add_model(df)
    convert_make(df)
    convert_color(df)
    return df

def rev(s):
    return s[::-1]

def stringify_cols(df, cols):
    for c in cols:
        df[c] = df[c].astype(str)

# Fetch data from https://www.noga-iso.co.il/piechartspage/#

import datetime

import pandas as pd
import requests
import time
import os

start_date = datetime.datetime(2023, 4, 1)
#end_date = datetime.datetime(2023, 4, 2)
end_date = datetime.datetime(2024, 3, 1)

tempfile = 'tmp.xlsx'

date = start_date
while date <= end_date:
    formatted_date = date.strftime("%d/%m/%Y")
    url = f'https://www.noga-iso.co.il/Umbraco/Surface/Export/ExportCost/?startDateString={formatted_date}&endDateString={formatted_date}&culture=he-IL&dataType=DemandForecastNEW&forecastCategory=6'
    filename = f"../data/noga/{date.strftime('%Y%m%d')}.csv"
    print(filename)#, end='...', flush=True)
    if not os.path.exists(filename):
        response = requests.get(url)
        if response.status_code == 200:
            with open(tempfile, "wb") as file:
                file.write(response.content)

                df = pd.read_excel(tempfile, skiprows=1)
                # choose the 9th column of df (PV generation) and the time columns
                df2 = pd.DataFrame(data={'date': df.iloc[:, 0], 'time': df.iloc[:, 1], 'PV generation': df.iloc[:, 8]})
                df2['time'] = df2.apply(lambda x: " ".join([x['date'], x['time']]), axis=1)
                df2.drop(columns='date', inplace=True)
                df2['time'] = pd.to_datetime(df2['time'], format='%d/%m/%Y %H:%M:%S')
                df2 = df2.set_index('time').resample('1H').sum()
                df2.to_csv(filename, index=True, float_format='%.2f')
        time.sleep(1)
    date += datetime.timedelta(days=1)

print()

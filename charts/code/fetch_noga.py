# Fetch data from https://www.noga-iso.co.il/piechartspage/#

import datetime
import requests
import time
import os

start_date = datetime.datetime(2023, 4, 1)
#end_date = datetime.datetime(2023, 4, 2)
end_date = datetime.datetime(2023, 5, 30)

base_url1 = 'https://www.noga-iso.co.il/Umbraco/Surface/Export/ExportCost/?startDateString='
base_url2 = '&endDateString=30/05/2023&culture=he-IL&dataType=DemandForecastNEW&forecastCategory=6'

date = start_date
while date <= end_date:
    formatted_date = date.strftime("%d/%m/%Y")
    url = base_url1 + formatted_date + base_url2
    filename = date.strftime("%Y%m%d") + ".xlsx"
    if not os.path.exists(filename):
        response = requests.get(url)
        print(formatted_date, end='...', flush=True)
        if response.status_code == 200:
            with open(filename, "wb") as file:
                file.write(response.content)
        time.sleep(1)
    date += datetime.timedelta(days=1)

print()

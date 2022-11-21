import requests
import os
import sys
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from datetime import datetime

# download weather files from the Israeli Meteorolgical Service

# Default URL: https://ims.gov.il/sites/default/files/ims_data/xml_files/observ.xml
#   This should update hourly, about 30 mins after the hour, and have observations for 3 hours back

weather_dir = 'data/weather/'
URL = 'https://ims.gov.il/sites/default/files/ims_data/xml_files/observ.xml'

def retry_session(retries, session=None, backoff_factor=0.3):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        allowed_methods=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def httpreq(url):
    session = retry_session(retries=5)

    try:
        response = session.get(url=url)
        # requests.request("GET", url, headers=headers)
        #data=response.text.encode('utf8')
        return response.text
    except ConnectionEror:
        return None

    return None


# change dir to the script's dir
os.chdir(sys.path[0])

now = datetime.now()

data = httpreq(URL)
if data:
    # name of directory to store into
    date_str = now.strftime("%Y-%m-%d")
    dt_str = now.strftime("%Y-%m-%d:%H:%M:%S")
    outdir = weather_dir + date_str
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, dt_str + '.xml'), 'w') as f:
        f.write(data)

#!/usr/bin/env python3

import requests
import json

# Make Strava auth API call with your 
# client_code, client_secret and code

# following a tutorial at: https://medium.com/swlh/using-python-to-connect-to-stravas-api-and-analyse-your-activities-dummies-guide-5f49727aac86

#To get the code, log into Strava with a browser, and go to:
# https://www.strava.com/oauth/authorize?client_id=56590&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=read
# the code will be present inside the URL after authorization
# Note: the code can only by used once, so you need to do the auth step above each time you run this script

with open('strava_secret.json') as secret:
  secrets = json.load(secret)


response = requests.post(
                    url = 'https://www.strava.com/oauth/token',
                    data = {
                            'client_id': secrets['client_id'],
                            'client_secret': secrets['client_secret'],
                            'code': secrets['code'],
                            'grant_type': 'authorization_code'
                            }
                )

#Save json response as a variable
strava_tokens = response.json()# Save tokens to file
with open('strava_tokens.json', 'w') as outfile:
    json.dump(strava_tokens, outfile)


# Open JSON file and print the file contents 
# to check it's worked properly
with open('strava_tokens.json') as check:
  data = json.load(check)
  print(data)




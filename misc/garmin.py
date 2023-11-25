#import garminconnect
import os

from getpass import getpass
import garth
GARTH_HOME = os.getenv("GARTH_HOME", "~/.garth")

garth.resume(GARTH_HOME)
try:
    garth.client.username
except:
    # Session is expired. You'll need to log in again
    email = 'daniel-garminconnect@pelleg.org'
    password = getpass("Enter password: ")
    garmin = garminconnect.Garmin(email, password)
    garmin.login()
    garmin.garth.dump(GARTH_HOME)

print(garth.DailyStress.list("2023-11-01", 2))

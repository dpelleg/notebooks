#!/usr/bin/env python3
"""
pip3 install garth requests readchar

export EMAIL=<your garmin email>
export PASSWORD=<your garmin password>

"""
import datetime
import json
import logging
import os
import sys
from getpass import getpass

import readchar
import requests
from garth.exc import GarthHTTPError

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

# Configure debug logging
# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables if defined
email = os.getenv("EMAIL")
password = os.getenv("PASSWORD")
tokenstore = os.getenv("GARMINTOKENS") or "~/.garminconnect"
api = None

# Example selections and settings
today = datetime.date.today()
startdate = today - datetime.timedelta(days=7)  # Select past week
start = 0
limit = 100
start_badge = 1  # Badge related calls calls start counting at 1
activitytype = ""  # Possible values are: cycling, running, swimming, multi_sport, fitness_equipment, hiking, walking, other
activityfile = "MY_ACTIVITY.fit"  # Supported file types are: .fit .gpx .tcx
weight = 89.6
weightunit = 'kg'

menu_options = {
    "1": "Get full name",
    "2": "Get unit system",
    "3": f"Get activity data for '{today.isoformat()}'",
    "4": f"Get activity data for '{today.isoformat()}' (compatible with garminconnect-ha)",
    "5": f"Get body composition data for '{today.isoformat()}' (compatible with garminconnect-ha)",
    "6": f"Get body composition data for from '{startdate.isoformat()}' to '{today.isoformat()}' (to be compatible with garminconnect-ha)",
    "7": f"Get stats and body composition data for '{today.isoformat()}'",
    "8": f"Get steps data for '{today.isoformat()}'",
    "9": f"Get heart rate data for '{today.isoformat()}'",
    "0": f"Get training readiness data for '{today.isoformat()}'",
    "-": f"Get daily step data for '{startdate.isoformat()}' to '{today.isoformat()}'",
    "/": f"Get body battery data for '{startdate.isoformat()}' to '{today.isoformat()}'",
    "!": f"Get floors data for '{startdate.isoformat()}'",
    "?": f"Get blood pressure data for '{startdate.isoformat()}' to '{today.isoformat()}'",
    ".": f"Get training status data for '{today.isoformat()}'",
    "a": f"Get resting heart rate data for {today.isoformat()}'",
    "b": f"Get hydration data for '{today.isoformat()}'",
    "c": f"Get sleep data for '{today.isoformat()}'",
    "d": f"Get stress data for '{today.isoformat()}'",
    "e": f"Get respiration data for '{today.isoformat()}'",
    "f": f"Get SpO2 data for '{today.isoformat()}'",
    "g": f"Get max metric data (like vo2MaxValue and fitnessAge) for '{today.isoformat()}'",
    "h": "Get personal record for user",
    "i": "Get earned badges for user",
    "j": f"Get adhoc challenges data from start '{start}' and limit '{limit}'",
    "k": f"Get available badge challenges data from '{start_badge}' and limit '{limit}'",
    "l": f"Get badge challenges data from '{start_badge}' and limit '{limit}'",
    "m": f"Get non completed badge challenges data from '{start_badge}' and limit '{limit}'",
    "n": f"Get activities data from start '{start}' and limit '{limit}'",
    "o": "Get last activity",
    "p": f"Download activities data by date from '{startdate.isoformat()}' to '{today.isoformat()}'",
    "r": f"Get all kinds of activities data from '{start}'",
    "s": f"Upload activity data from file '{activityfile}'",
    "t": "Get all kinds of Garmin device info",
    "u": "Get active goals",
    "v": "Get future goals",
    "w": "Get past goals",
    "y": "Get all Garmin device alarms",
    "x": f"Get Heart Rate Variability data (HRV) for '{today.isoformat()}'",
    "z": f"Get progress summary from '{startdate.isoformat()}' to '{today.isoformat()}' for all metrics",
    "A": "Get gear, the defaults, activity types and statistics",
    "B": f"Get weight-ins from '{startdate.isoformat()}' to '{today.isoformat()}'",
    "C": f"Get daily weigh-ins for '{today.isoformat()}'",
    "D": f"Delete all weigh-ins for '{today.isoformat()}'",
    "E": f"Add a weigh-in of {weight}{weightunit} on '{today.isoformat()}'",
    "F": f"Get virtual challenges/expeditions from '{startdate.isoformat()}' to '{today.isoformat()}'",
    "G": f"Get hill score data from '{startdate.isoformat()}' to '{today.isoformat()}'",
    "H": f"Get endurance score data from '{startdate.isoformat()}' to '{today.isoformat()}'",
    "I": f"Get activities for date '{today.isoformat()}'",
    "J": "Get race predictions",
    "K": f"Get all day stress data for '{today.isoformat()}'",
    "L": f"Add body composition for '{today.isoformat()}'",
    "M": "Set blood pressure '120,80,80,notes='Testing with example.py'",
    "N": "Get user profile/settings",
    "Z": "Remove stored login tokens (logout)",
    "q": "Exit",
}


def display_json(api_call, output):
    """Format API output for better readability."""

    dashed = "-" * 20
    header = f"{dashed} {api_call} {dashed}"
    footer = "-" * len(header)

    print(header)

    if isinstance(output, (int, str, dict, list)):
        print(json.dumps(output, indent=4))
    else:
        print(output)

    print(footer)

def display_text(output):
    """Format API output for better readability."""

    dashed = "-" * 60
    header = f"{dashed}"
    footer = "-" * len(header)

    print(header)
    print(json.dumps(output, indent=4))
    print(footer)


def get_credentials():
    """Get user credentials."""

    email = input("Login e-mail: ")
    password = getpass("Enter password: ")

    return email, password


def init_api(email, password):
    """Initialize Garmin API with your credentials."""

    try:
        garmin = Garmin()
        garmin.login(tokenstore)
    except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError):
        # Session is expired. You'll need to log in again
        print(
            "Login tokens not present, login with your Garmin Connect credentials to generate them.\n"
            f"They will be stored in '{tokenstore}' for future use.\n"
        )
        try:
            # Ask for credentials if not set as environment variables
            if not email or not password:
                email, password = get_credentials()

            garmin = Garmin(email, password)
            garmin.login()
            # Save tokens for next login
            garmin.garth.dump(tokenstore)

        except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError, requests.exceptions.HTTPError) as err:
            logger.error(err)
            return None

    return garmin

device_to_match = None
device_to_match = '3331454858'
# Main program loop
# Init API
if not api:
    api = init_api(email, password)

if api:
    # Display menu
    acts = api.get_activities(start, 10000)
    for act in acts:
        aid = str(act['activityId'])
        atime = act['startTimeLocal']
        atype = act['activityType']['typeKey']
        adev = str(act['deviceId'])
        if device_to_match is None:
            print(json.dumps(act))
        else:
            if adev == device_to_match:
                print(" ".join([aid, atime, atype, adev]))

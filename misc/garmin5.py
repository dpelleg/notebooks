import json

with open('acts_all.txt') as f:
    for line in f:
        act = json.loads(line)
        print(f"{act['startTimeLocal']} {act['deviceId']}")

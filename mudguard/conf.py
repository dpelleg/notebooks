import json

conffile = 'conf.json'

with open(conffile) as json_file:
    conf = json.load(json_file)

if __name__ == "__main__":
    print(conf)

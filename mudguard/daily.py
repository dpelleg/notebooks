import os
import sys
import subprocess
import conf

# change dir to the script's dir
os.chdir(sys.path[0])

subprocess.run(["python3", "./download_weather.py"])

nosegs = len(sys.argv) > 1 and sys.argv[1] == 'no_segments'
if !nosegs:
    subprocess.run(["python3", "./get_all_segments.py"])

subprocess.run(["python3", "./genrides.py"], check=True)
srcfile = "{}out/rides.html".format(conf.conf['datadir'])
subproces.run("mv {} ../../mysite/static/rides.html".format(srcfile))
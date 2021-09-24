
cd /home/mudguard/notebooks/mudguard

./get_all_segments.py

python ./genrides.py && mv data/out/rides.html mysite/static/rides.html



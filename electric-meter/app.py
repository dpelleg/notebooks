from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import os
import time
import re
from functools import wraps
from ratelimit import limits, sleep_and_retry
from electric_meter import *
from datetime import datetime
import locale
import gzip
import shutil

locale.setlocale(locale.LC_ALL, 'he_IL')

app = Flask(__name__)

def compress_and_delete_file(input_path):
    # Check if the file exists
    if not os.path.exists(input_path):
        return

    output_path = input_path + '.gz'
    with open(input_path, 'rb') as f_in, gzip.open(output_path, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    os.remove(input_path)

# Rate limiting decorators
# Limit to 100 calls per hour (3600 seconds)
@sleep_and_retry
@limits(calls=100, period=3600)
def rate_limit(key):
    return True

# Limit to 5 calls per 5 minutes (300 seconds) per IP
@sleep_and_retry
@limits(calls=5, period=300)
def ip_rate_limit(key):
    return True

def generate_unique_filename(filename):
    timestamp = int(time.time())
    random_string = os.urandom(4).hex()
    process_id = os.getpid()
    _, extension = os.path.splitext(filename)
    unique_filename = f"{timestamp}_{process_id}_{random_string}{extension}"
    return unique_filename

# Function to validate num_people
def is_valid_num_people(input_string):
    return input_string.isdigit()

# Function to validate city
def is_valid_city(input_string):
    return re.match(r'^[a-zA-Zא-ת\s\']+$', input_string) is not None

# Function to sanitize user inputs
def sanitize_input(input_string):
    # Remove HTML and JavaScript tags
    sanitized_string = re.sub('<[^<]+?>', '', input_string)
    return sanitized_string

# Function to check the validity of the uploaded CSV file
def is_valid_csv(file):
    try:
        return file_contains_header(file)
    except Exception as e:
        if app.debug:
            app.logger.warning(e)
    return False

def str_month_and_year(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%B %Y')
    except ValueError:
        return "Invalid date format"

# Route for the upload form page
@app.route('/', methods=['GET', 'POST'])
def upload_form():
    if request.method == 'POST':
        #num_people = sanitize_input(request.form.get('num_people'))
        num_people = sanitize_input('12')
        #city = sanitize_input(request.form.get('city'))
        city = sanitize_input('Tel Aviv')
        file = request.files.get('csv_file')

        # Validate num_people and city for empty or malicious input
        if not num_people or not city:
            return "Invalid input. Please provide valid values."

        # Validate num_people is numeric
        if not is_valid_num_people(num_people):
            return "Invalid input for number of people. Please provide a numeric value."

        # Validate city contains only letters and allowed characters
        if not is_valid_city(city):
            return "Invalid input for city. Please provide a valid city name."

        if file and file.filename.endswith((".csv", ".xlsx")):
            # Perform rate limiting
            ip = request.remote_addr
            if not rate_limit(ip) or not ip_rate_limit(ip):
                return "Rate limit exceeded. Please try again later."

            # Save uploaded file
            file_name = generate_unique_filename(secure_filename(file.filename))
            file_path = os.path.join('uploads', file_name)
            file.save(file_path)

            # Check validity of CSV
            if not is_valid_csv(file_path):
                return "Invalid CSV file. Please upload a valid file."

            # Save form parameters
            form_data = {
                #'num_people': num_people,
                #'city': city,
                'meter_file': file_name,
                'timestamp': time.time(),
                'form_version': '1.0'
            }

            # Append form_data to the JSON file
            with open('uploads/uploads.json', 'a') as json_file:
                json.dump(form_data, json_file)
                json_file.write('\n')

            # Call function to compute costs
            try:
                meter = read_data(file_path)
                costs, conf = compute_costs(meter)
                result = style_table(costs)
                result = result.to_html()
                # format into readable units
                kwh_rate = 100*conf['kwh_rate']     # Agorot to Shekel
                kwh_rate_date = str_month_and_year(conf['kwh_rate_date'])
                taoz_rate_date = str_month_and_year(conf['taoz_rate_date'])

                compress_and_delete_file(file_path)

                return render_template('result.html',
                    result=result,
                    kwh_rate=kwh_rate,
                    kwh_rate_date=kwh_rate_date,
                    taoz_rate_date=taoz_rate_date,
                    taoz_summer_low=conf['taoz']['summer']['low_price'],
                    taoz_summer_high=conf['taoz']['summer']['high_price'],
                    taoz_winter_low=conf['taoz']['winter']['low_price'],
                    taoz_winter_high=conf['taoz']['winter']['high_price'],
                    taoz_transition_low=conf['taoz']['transition']['low_price'],
                    taoz_transition_high=conf['taoz']['transition']['high_price'],
                    )
            except Exception as e:
                if app.debug:
                    app.logger.warning(e)
                return render_template('noresult.html', msg=str(e))

    return render_template('upload_form.html')

if __name__ == '__main__':
    with open('data/secrets.json', 'r') as json_file:
        conf = json.load(json_file)

    debug = conf.get('debug', False)

    app.run(debug=debug)

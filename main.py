import sys
import io, os, base64

import datetime
import time

import matplotlib
import matplotlib.pyplot as plt

import numpy as np
import requests

from flask import Flask, render_template, request, Markup

from geopy.geocoders import Nominatim

from haversine import haversine, Unit

# global variable
app = Flask(__name__)
app.secret_key = 'secret123' # Give your secret key


geolocator = Nominatim(user_agent="ISS Locator") # Calling globally Geolocator to extract lat/long

# get path directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Get the location of ISS
def get_space_station_location():

    space_station_longitude = None
    space_station_latitude = None
    try:
        r = requests.get(url='https://api.wheretheiss.at/v1/satellites/25544')
        space_station_location = (r.json())

        space_station_longitude = float(space_station_location['longitude'])
        space_station_latitude = float(space_station_location['latitude'])

    except:
        #log error
        print("Request Not working")

    return(space_station_longitude, space_station_latitude)

# Initialize scientist info
def get_scientist_onboard():
    scient_no = None
    scient_names = None
    try:
        r = requests.get(url='http://api.open-notify.org/astros.json')
        scientist_info = (r.json())
        scient_no = str(scientist_info["number"])
        scient_names = scientist_info['people']
    except:
        # Log error
        print("Request not working")
    return(scient_no, scient_names)

# Convert geo(lat/lon) to pixels
def translate_geo_to_pixels(longitude, latitude, max_x_px, max_y_px):
    # y is -90 to +90
    # x is -180 to +180
    scale_x = abs(((longitude + 180) / 360) * max_x_px)
    scale_y = abs(((latitude - 90) / 180) * max_y_px) # subtract as y scale is flipped
    
    return scale_x, scale_y

# Home page
@app.route('/')
def index():
   return render_template("locate_iss.html")

# Get Scientist info onboard
@app.route('/onboard', methods=["GET", "POST"])
def scientist_onboard():
    if request.method == 'POST':
        # Get the location of ISS
        iss_scientist = get_scientist_onboard()
        numbers = iss_scientist[0]
        scientists = iss_scientist[1]
    return render_template('scientist.html', number=numbers, scientist=scientists)


# Plotting marker(ISS) on image(worldmap)
@app.route("/disttance", methods=["GET","POST"])
def ISS_tracker():

    # set an initial plot size
    plt.figure(figsize=(14,6))

    # Load the image from webdriver
    img = os.path.join(BASE_DIR, 'static//images//world_mapf.jpg')
    img = plt.imread(img)
    img = plt.imshow(img)

    if request.method == 'POST':
        # Get the location of ISS
        iss_location = get_space_station_location()

        try:
            # Retrieving Address from Lat/lon
            iss_lat = str(iss_location[1])
            iss_lon = str(iss_location[0])
            latlong = [iss_lat, iss_lon]
            print(latlong)
            cod = ", ".join(latlong)
            print(cod)
            location = geolocator.reverse(cod, language='en')
            print(location)
            Addres = location.address
            print(Addres)
        except:
            print('Loop Break')
            Addres = 'Unknown Locale(Sea,Oceans)'

        # Translate the geo coordinates to pixels
        translated_iss_location = translate_geo_to_pixels(
                                                        iss_location[0],
                                                        iss_location[1],
                                                        2416, 1208)
        # Add  position to plot
        plt.scatter(x=[translated_iss_location[0]], y=[translated_iss_location[1]], c='red', s=300, marker='P')

    plt.axis('off')
    img = io.BytesIO()
    plt.savefig(img, format='jpg')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()

    return render_template('distance.html', latlongs=cod,
        forecast_plot = Markup('<img src="data:image/jpg;base64,{}" style="width:100%; vertical-align:top">'.format(plot_url)),
        adress=Addres)

# Prediction passover your location
@app.route("/pasover", methods=["GET","POST"])
def pasover():
    cityname = None
    predictions = None
    if request.method == 'POST':
        try:
            # User input city/country
            cityname = request.form['city']
            print(cityname)

            # Using Geolocator to extract lat/lon
            # Geolocator for lat/long
            location = geolocator.geocode(cityname)
            lat = location.latitude
            lon = location.longitude

            # request url to fetch predictions
            base_url_pass='http://api.open-notify.org/iss-pass.json'
            url1 = base_url_pass + '?lat=' + str(lat) + '&lon=' + str(lon)
            r = requests.get(url1)
            data = (r.json())
            predictions = data['response']
            print(predictions)

        except:
            #Log error
            print('Not Getting values')

    # return 'The credentials for %s are %s' % (cityname, predictions)
    return render_template('pasover.html', cityname=cityname, prediction=predictions)

@app.route("/usrdist", methods=["GET","POST"])
def usrdist():
    cityname = None
    usr_loc = None
    miles = None
    kms = None
    Addres = None
    cod = None
    if request.method == 'POST':
        try:
            # User input city/country
            cityname = request.form['city']
            print(cityname)
            # To extract user's city/country lat/lon for iss distance calculation
            location = geolocator.geocode(cityname)
            lat = location.latitude
            lon = location.longitude
            # Iss Lat/lon for distance calculation
            iss_locat = get_space_station_location()
            iss_lon = iss_locat[0]
            iss_lat = iss_locat[1]
            
            # To extract ISS location name converting lat/lon to string
            iss_lat_str = str(iss_locat[1])
            iss_lon_str = str(iss_locat[0])

            #Extracting ISS address from lat/lon if over land returns city/country name else unknown locale
            latlong_iss = [iss_lat_str, iss_lon_str]
            print(latlong_iss)
            cod = ", ".join(latlong_iss)
            location = None
            try:
                location = geolocator.reverse(cod, language='en')
                Addres = location.address
            except:
                print('Loop Break')
                Addres = 'Unknown Locale(Sea,Oceans)'
            
            # create var to cal distance between user and ISS
            usr_loc = (lat, lon)
            # ISS LAT/LON
            iss_loc = (iss_lat, iss_lon)
            # Using Haversine to calculate the distance between two coordinates
            miles = haversine(iss_loc, usr_loc, unit=Unit.MILES)
            miles = round(miles,2)
            print(miles)

            kms = haversine(iss_loc, usr_loc)
            kms = round(kms,2)
            print(kms)
        except:
            print("there is an error")
            pass
        
    # return 'The credentials for %s are %s' % (cityname, predictions)
    return render_template('usrdisthome.html', citynames=cityname,  usr_lo=usr_loc, iss_lo=cod,
                            iss_address=Addres, miless=miles, kilo=kms)

@app.template_filter('ctime')
def timectime(s):
    # timestamp = datetime.datetime.fromtimestamp(s)
    local_time = time.localtime(s)
    return(time.strftime("Time/Date: %H:%M:%S / %d-%m-%Y", local_time))
    # return(timestamp.strftime("%Y-%m-%d %H:%M:%S")

@app.template_filter('dtime')
def timedtime(seconds):
    seconds = seconds % (24 * 3600) 
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return("%d:%02d:%02d" % (hour, minutes, seconds))

if __name__ == '__main__':
    app.run(debug=True)
from skyfield.api import load, Topos, EarthSatellite
import ephem
from datetime import datetime
import os
import requests

TLE_FILE = 'iss.tle'
TLE_URL = 'https://www.celestrak.com/NORAD/elements/stations.txt'

def download_tle():
    print("Downloading latest TLE from Celestrak...")
    response = requests.get(TLE_URL)
    tle_lines = response.text.splitlines()
    for i, line in enumerate(tle_lines):
        if 'ISS (ZARYA)' in line:
            with open(TLE_FILE, 'w') as file:
                file.write('\n'.join(tle_lines[i:i + 3]) + '\n')
            print("TLE saved to", TLE_FILE)
            return
    raise ValueError("ISS TLE not found in data")

# Step 1: Get TLE data (reuse existing file if available)
if not os.path.exists(TLE_FILE):
    download_tle()

with open(TLE_FILE) as file:
    tle = file.readlines()

# Skyfield Calculation
ts = load.timescale()
satellite = EarthSatellite(tle[1].strip(), tle[2].strip(), tle[0].strip(), ts)

# Observer Location
latitude = 46.4667081
longitude = 6.8616259
altitude = 500

observer_sf = Topos(latitude_degrees=latitude, longitude_degrees=longitude, elevation_m=altitude)
t = ts.now()
difference = satellite - observer_sf
topocentric = difference.at(t)
alt_sf, az_sf, distance_sf = topocentric.altaz()

print("\n--- Skyfield Results ---")
print(f"Azimuth: {az_sf.degrees:.2f}°")
print(f"Elevation: {alt_sf.degrees:.2f}°")
print(f"Distance: {distance_sf.km:.2f} km")

# PyEphem Calculation
iss = ephem.readtle(tle[0].strip(), tle[1].strip(), tle[2].strip())

observer_ephem = ephem.Observer()
observer_ephem.lat = str(latitude)
observer_ephem.lon = str(longitude)
observer_ephem.elev = altitude
observer_ephem.date = datetime.utcnow()

iss.compute(observer_ephem)

# Convert radians to degrees for PyEphem
az_ephem = iss.az * (180 / 3.14159)
alt_ephem = iss.alt * (180 / 3.14159)

print("\n--- PyEphem Results ---")
print(f"Azimuth: {az_ephem:.2f}°")
print(f"Elevation: {alt_ephem:.2f}°")
print(f"Distance: {iss.range / 1000:.2f} km")

# Compare Results
print("\n--- Difference ---")
print(f"Azimuth difference: {abs(az_sf.degrees - az_ephem):.2f}°")
print(f"Elevation difference: {abs(alt_sf.degrees - alt_ephem):.2f}°")
print(f"Distance difference: {abs(distance_sf.km - iss.range / 1000):.2f} km")

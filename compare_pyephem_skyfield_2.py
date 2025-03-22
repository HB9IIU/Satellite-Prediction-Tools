
# === Merged Code to Compare PyEphem and Skyfield Results ===

# ============================= PyEphem Code =============================
import ephem
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from datetime import timezone  # FIXED import here
import requests


# === Configurations ===
TLE_FILE = 'iss.tle'
LATITUDE = '46.4667'
LONGITUDE = '6.8616'
ALTITUDE = 550
MAX_PASSES = 20
MIN_ELEVATION =0.0
LOCAL_TIMEZONE = ZoneInfo("Europe/Zurich")


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



# === Step 1: Load TLE ===
with open(TLE_FILE) as file:
    tle_lines = file.readlines()

# ✅ Create ISS object from TLE
iss = ephem.readtle(tle_lines[0].strip(), tle_lines[1].strip(), tle_lines[2].strip())

# ✅ Create Observer
observer = ephem.Observer()
observer.lat = LATITUDE
observer.lon = LONGITUDE
observer.elev = ALTITUDE
observer.date = datetime.utcnow()

# === Step 2: Find Next Passes ===
passes_pyephem = []
for _ in range(MAX_PASSES):
    next_pass = observer.next_pass(iss)

    rise_time, rise_az, max_alt_time, max_alt, set_time, set_az = next_pass
    duration_seconds = (set_time.datetime() - rise_time.datetime()).total_seconds()
    minutes = int(duration_seconds // 60)
    seconds = int(duration_seconds % 60)

    if max_alt * (180 / 3.14159) >= MIN_ELEVATION:
        passes_pyephem.append({
            'rise_time': rise_time,
            'duration': f"{minutes:02}:{seconds:02}",
            'max_elevation': max_alt * (180 / 3.14159),
            'rise_azimuth': rise_az * (180 / 3.14159),
            'set_time': set_time,
            'set_azimuth': set_az * (180 / 3.14159),
            'max_alt_time': max_alt_time
        })

    observer.date = set_time + ephem.minute

# ============================= Skyfield Code =============================
from skyfield.api import load, Topos, EarthSatellite

# === Step 1: Load TLE ===
ts = load.timescale()
with open(TLE_FILE) as file:
    tle = file.readlines()

satellite = EarthSatellite(tle[1].strip(), tle[2].strip(), tle[0].strip(), ts)
observer = Topos(latitude_degrees=float(LATITUDE), longitude_degrees=float(LONGITUDE), elevation_m=int(ALTITUDE))

# === Step 2: Find Next Passes ===
passes_skyfield = []
t0 = ts.now()
while len(passes_skyfield) < MAX_PASSES:
    t, events = satellite.find_events(observer, t0, t0 + timedelta(days=10), altitude_degrees=MIN_ELEVATION)
    rise_time, max_alt_time, set_time = None, None, None
    max_altitude = 0

    for ti, event in zip(t, events):
        if event == 0:
            rise_time = ti.utc_datetime().replace(tzinfo=timezone.utc)
            t0 = ti + timedelta(seconds=1)
        elif event == 1:
            max_alt_time = ti.utc_datetime().replace(tzinfo=timezone.utc)
            alt, az, dist = (satellite - observer).at(ti).altaz()
            max_altitude = alt.degrees
        elif event == 2:
            set_time = ti.utc_datetime().replace(tzinfo=timezone.utc)
            if rise_time and set_time and max_altitude >= MIN_ELEVATION:
                duration = (set_time - rise_time).seconds
                passes_skyfield.append({
                    'aos_time': rise_time,
                    'max_time': max_alt_time,
                    'los_time': set_time,
                    'duration': duration,
                    'max_altitude': round(max_altitude),
                    'aos_azimuth': round((satellite - observer).at(t[0]).altaz()[1].degrees),
                    'los_azimuth': round((satellite - observer).at(t[2]).altaz()[1].degrees)
                })
            if len(passes_skyfield) >= MAX_PASSES:
                break
    t0 = t[-1] + timedelta(minutes=1)

# ============================= Combined Output =============================
from prettytable import PrettyTable

# Create tables
pyephem_table = PrettyTable()
skyfield_table = PrettyTable()
headers = ["DATE", "AOS", "TCA", "LOS", "DUR", "MEL"]
pyephem_table.field_names = headers
skyfield_table.field_names = headers

# Fill PyEphem table
for p in passes_pyephem:
    date = ephem.localtime(p['rise_time']).astimezone(LOCAL_TIMEZONE).strftime('%d.%m')
    aos = ephem.localtime(p['rise_time']).astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    tca = ephem.localtime(p['max_alt_time']).astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    los = ephem.localtime(p['set_time']).astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    dur = p['duration']
    mel = f"{p['max_elevation']:.1f}"
    pyephem_table.add_row([date, aos, tca, los, dur, mel])

# Fill Skyfield table
for p in passes_skyfield:
    date = p['aos_time'].astimezone(LOCAL_TIMEZONE).strftime('%d.%m')
    aos = p['aos_time'].astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    tca = p['max_time'].astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    los = p['los_time'].astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    dur = f"{p['duration'] // 60}:{p['duration'] % 60:02d}"
    mel = f"{p['max_altitude']:.1f}"
    skyfield_table.add_row([date, aos, tca, los, dur, mel])

# Print side by side
print("--- Comparison of PyEphem and Skyfield Results ---")
pyephem_lines = pyephem_table.get_string().split("\n")
skyfield_lines = skyfield_table.get_string().split("\n")
for ephem_line, skyfield_line in zip(pyephem_lines, skyfield_lines):
    print(f"{ephem_line:<70} {skyfield_line:<70}")

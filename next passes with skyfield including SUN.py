import ephem
from skyfield.api import load, Topos, EarthSatellite
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo
import requests, os

# === Configurations ===
TLE_FILE = 'iss.tle'
LATITUDE = '46.4667'
LONGITUDE = '6.8616'
ALTITUDE = 500
MAX_PASSES = 50
MIN_ELEVATION = 0
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

# Step 1: Get TLE data (reuse existing file if available)
if not os.path.exists(TLE_FILE):
    download_tle()

# === Step 1: Load TLE ===
ts = load.timescale()
with open(TLE_FILE) as file:
    tle = file.readlines()

# ✅ Use EarthSatellite for inline TLE data
satellite = EarthSatellite(tle[1].strip(), tle[2].strip(), tle[0].strip(), ts)

# ✅ Create Observer
observer = Topos(latitude_degrees=float(LATITUDE), longitude_degrees=float(LONGITUDE), elevation_m=int(ALTITUDE))

# === Use pyephem to compute Sun elevation ===
ephem_observer = ephem.Observer()
ephem_observer.lat = LATITUDE
ephem_observer.lon = LONGITUDE
ephem_observer.elev = ALTITUDE

def compute_sun_elevation(rise_time):
    ephem_observer.date = rise_time
    sun = ephem.Sun(ephem_observer)
    sun_altitude = sun.alt * (180 / 3.14159)  # Convert from radians to degrees
    return round(sun_altitude, 1)

# === Define Visibility Probability ===
def get_visibility(sun_altitude, max_altitude):
    if sun_altitude > 0:
        return "NO"  # Too bright
    elif -6 < sun_altitude <= 0:
        return "Unlikely"
    elif -12 < sun_altitude <= -6:
        return "Possible" if max_altitude > 20 else "Unlikely"
    elif -18 < sun_altitude <= -12:
        return "Likely" if max_altitude > 30 else "Possible"
    else:
        return "YES" if max_altitude > 30 else "Unlikely (too low)"

# === Step 2: Find Next Passes ===
def find_next_passes():
    t0 = ts.now()
    passes = []
    while len(passes) < MAX_PASSES:
        t, events = satellite.find_events(observer, t0, t0 + timedelta(days=10), altitude_degrees=MIN_ELEVATION)
        rise_time, max_alt_time, set_time = None, None, None
        max_altitude = 0

        for ti, event in zip(t, events):
            if event == 0:  # AOS (rise)
                rise_time = ti.utc_datetime().replace(tzinfo=timezone.utc)
                t0 = ti + timedelta(seconds=1)
            elif event == 1:  # MAX ALTITUDE
                max_alt_time = ti.utc_datetime().replace(tzinfo=timezone.utc)
                alt, az, dist = (satellite - observer).at(ti).altaz()
                max_altitude = alt.degrees
            elif event == 2:  # LOS (set)
                set_time = ti.utc_datetime().replace(tzinfo=timezone.utc)
                if rise_time and set_time and max_altitude >= MIN_ELEVATION:
                    duration = (set_time - rise_time).seconds
                    sun_altitude = compute_sun_elevation(rise_time)
                    visibility = get_visibility(sun_altitude, max_altitude)

                    passes.append({
                        'aos_time': rise_time,
                        'max_time': max_alt_time,
                        'los_time': set_time,
                        'duration': duration,
                        'max_altitude': round(max_altitude),
                        'aos_azimuth': round((satellite - observer).at(t[0]).altaz()[1].degrees),
                        'los_azimuth': round((satellite - observer).at(t[2]).altaz()[1].degrees),
                        'sun_elevation': sun_altitude,
                        'visibility': visibility
                    })
                if len(passes) >= MAX_PASSES:
                    break
        t0 = t[-1] + timedelta(minutes=1)
    return passes

passes = find_next_passes()

# === Step 3: Display Results in Table ===
print("\n--- Next 10 Visible Passes ---")
print(f"{'DATE':<10} {'AOS':<10} {'TCA':<10} {'LOS':<10} {'DUR':<6} {'MEL':<6} {'SUN':<6} {'VISIBILITY':<15}")
print("=" * 95)
for p in passes:
    date = p['aos_time'].astimezone(LOCAL_TIMEZONE).strftime('%d.%m')
    aos = p['aos_time'].astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    tca = p['max_time'].astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    los = p['los_time'].astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    dur = f"{p['duration'] // 60}:{p['duration'] % 60:02d}"
    mel = f"{p['max_altitude']:.1f}"
    sun = f"{p['sun_elevation']:.1f}"
    visibility = p['visibility']

    print(f"{date:<10} {aos:<10} {tca:<10} {los:<10} {dur:<6} {mel:<6} {sun:<6} {visibility:<15}")

print("\n✅ Done! Next 10 visible passes calculated.")


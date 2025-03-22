from skyfield.api import load, Topos, EarthSatellite
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo
import requests, os


# === Configurations ===
TLE_FILE = 'iss.tle'
LATITUDE = 46.4667
LONGITUDE = 6.8616
ALTITUDE = 500
MAX_PASSES = 12
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
observer = Topos(latitude_degrees=LATITUDE, longitude_degrees=LONGITUDE, elevation_m=ALTITUDE)


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
                    passes.append({
                        'aos_time': rise_time,
                        'max_time': max_alt_time,
                        'los_time': set_time,
                        'duration': duration,
                        'max_altitude': round(max_altitude),
                        'aos_azimuth': round((satellite - observer).at(t[0]).altaz()[1].degrees),
                        'los_azimuth': round((satellite - observer).at(t[2]).altaz()[1].degrees)
                    })
                if len(passes) >= MAX_PASSES:
                    break
        t0 = t[-1] + timedelta(minutes=1)
    return passes


passes = find_next_passes()


# === Step 3: Display Results (European NASA Style) ===
def azimuth_to_cardinal(azimuth):
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = int((azimuth + 22.5) // 45) % 8
    return directions[index]


print("\n--- Next 10 Visible Passes (European NASA Style) ---")
for i, p in enumerate(passes, start=1):
    local_aos_time = p['aos_time'].astimezone(LOCAL_TIMEZONE).strftime('%d.%m.%Y %H:%M:%S')
    utc_aos_time = p['aos_time'].strftime('%H:%M:%S')
    local_los_time = p['los_time'].astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    utc_los_time = p['los_time'].strftime('%H:%M:%S')

    max_height = p['max_altitude']
    appears_cardinal = azimuth_to_cardinal(p['aos_azimuth'])
    disappears_cardinal = azimuth_to_cardinal(p['los_azimuth'])

    print(f"{i}. AOS: {local_aos_time} ({utc_aos_time} UTC), "
          f"Visible: {p['duration'] // 60} min, "
          f"Max Height: {max_height}°, "
          f"Appears: {p['aos_azimuth']}° above {appears_cardinal}, "
          f"Disappears: {p['los_azimuth']}° above {disappears_cardinal}")

# === Step 4: Display Results in Table ===
print("\n--- Next 10 Visible Passes (Table Format) ---")
print(f"{'DATE':<10} {'AOS':<6} {'TCA':<6} {'LOS':<6} {'DUR':<6} {'MEL':<6}")
print("=" * 45)
for p in passes:
    date = p['aos_time'].astimezone(LOCAL_TIMEZONE).strftime('%d.%m')
    aos = p['aos_time'].astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    tca = p['max_time'].astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    los = p['los_time'].astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')

    # ✅ Format duration as MM:SS
    dur = f"{p['duration'] // 60}:{p['duration'] % 60:02d}"
    mel = f"{p['max_altitude']:.1f}"

    print(f"{date:<10} {aos:<6} {tca:<6} {los:<6} {dur:<6} {mel:<6}")

print("\n✅ Done! Next 10 visible passes calculated.")

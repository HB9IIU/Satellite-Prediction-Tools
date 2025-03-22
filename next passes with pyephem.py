import ephem
import os
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# === Configurations ===
TLE_FILE = 'iss.tle'
LATITUDE = '46.4667'
LONGITUDE = '6.8616'
ALTITUDE = 500
MAX_PASSES = 12
MIN_ELEVATION = 10.0
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

# === Step 2: Load TLE ===
with open(TLE_FILE) as file:
    tle_lines = file.readlines()

# ✅ Create ISS object from TLE
iss = ephem.readtle(tle_lines[0].strip(), tle_lines[1].strip(), tle_lines[2].strip())

# ✅ Create Observer
observer = ephem.Observer()
observer.lat = LATITUDE
observer.lon = LONGITUDE
observer.elev = ALTITUDE
observer.date = datetime.utcnow()  # Use current UTC time

# === Step 2: Find Next Passes ===
passes = []
print("\nCalculating next visible passes...")

for _ in range(MAX_PASSES):
    # Find next pass
    next_pass = observer.next_pass(iss)

    rise_time, rise_az, max_alt_time, max_alt, set_time, set_az = next_pass

    # Calculate duration in seconds
    duration_seconds = (set_time.datetime() - rise_time.datetime()).total_seconds()

    # Convert duration to minutes and seconds
    minutes = int(duration_seconds // 60)
    seconds = int(duration_seconds % 60)

    if max_alt * (180 / 3.14159) >= MIN_ELEVATION:
        passes.append({
            'rise_time': rise_time,
            'duration': f"{minutes:02}:{seconds:02}",  # Store duration in MM:SS format
            'max_elevation': max_alt * (180 / 3.14159),
            'rise_azimuth': rise_az * (180 / 3.14159),
            'set_time': set_time,
            'set_azimuth': set_az * (180 / 3.14159),
            'max_alt_time': max_alt_time  # Keep ephem.Date for conversion later
        })

    # Step observer forward
    observer.date = set_time + ephem.minute

# === Step 3: Display Results (European NASA Style) ===
def azimuth_to_cardinal(azimuth):
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = int((azimuth + 22.5) // 45) % 8
    return directions[index]


print("\n--- Next 10 Visible Passes (European NASA Style) ---")
for i, p in enumerate(passes, start=1):
    # Convert UTC to local time using ephem.localtime
    local_aos_time = ephem.localtime(p['rise_time']).astimezone(LOCAL_TIMEZONE).strftime('%d.%m.%Y %H:%M:%S')
    utc_aos_time = p['rise_time'].datetime().strftime('%H:%M:%S')  # .datetime() gives us a Python datetime object
    local_los_time = ephem.localtime(p['set_time']).astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    utc_los_time = p['set_time'].datetime().strftime('%H:%M:%S')  # .datetime() gives us a Python datetime object

    max_height = p['max_elevation']
    appears_cardinal = azimuth_to_cardinal(p['rise_azimuth'])
    disappears_cardinal = azimuth_to_cardinal(p['set_azimuth'])

    print(f"{i}. AOS: {local_aos_time} ({utc_aos_time} UTC), "
          f"Visible: {p['duration']} min, "
          f"Max Height: {max_height:.1f}°, "
          f"Appears: {p['rise_azimuth']:.1f}° above {appears_cardinal}, "
          f"Disappears: {p['set_azimuth']:.1f}° above {disappears_cardinal}")

# === Step 4: Display Results in Table Format ===
print("\n--- Next 10 Visible Passes (Table Format) ---")
print(f"{'DATE':<10} {'AOS':<6} {'TCA':<6} {'LOS':<6} {'DUR':<6} {'MEL':<6}")
print("=" * 45)
for p in passes:
    # Convert UTC to local time for table display with seconds
    date = ephem.localtime(p['rise_time']).astimezone(LOCAL_TIMEZONE).strftime('%d.%m')
    aos = ephem.localtime(p['rise_time']).astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')
    tca = ephem.localtime(p['max_alt_time']).astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')  # TCA as time
    los = ephem.localtime(p['set_time']).astimezone(LOCAL_TIMEZONE).strftime('%H:%M:%S')

    # ✅ Duration is already formatted in MM:SS
    mel = f"{p['max_elevation']:.1f}"

    print(f"{date:<10} {aos:<6} {tca:<6} {los:<6} {p['duration']:<6} {mel:<6}")

print("\n✅ Done! Next 10 visible passes calculated.")

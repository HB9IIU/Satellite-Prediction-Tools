import ephem
from datetime import datetime, timedelta

# === Configurations ===
TLE_FILE = 'iss.tle'
LATITUDE = '46.4667'
LONGITUDE = '6.8616'
ALTITUDE = 500
MAX_PASSES = 10
MIN_ELEVATION = 10.0

# === Step 1: Load TLE ===
with open(TLE_FILE) as file:
    tle = file.readlines()

# ✅ Create ISS object from TLE
iss = ephem.readtle(tle[0].strip(), tle[1].strip(), tle[2].strip())

# ✅ Create Observer
observer = ephem.Observer()
observer.lat = LATITUDE
observer.lon = LONGITUDE
observer.elev = ALTITUDE
observer.date = datetime.utcnow()

# === Step 2: Find Next Passes ===
passes = []
print("\nCalculating next visible passes...")

for _ in range(MAX_PASSES):
    # Find next pass
    next_pass = observer.next_pass(iss)

    rise_time, rise_az, max_alt_time, max_alt, set_time, set_az = next_pass

    duration = (set_time.datetime() - rise_time.datetime()).seconds // 60

    if max_alt * (180 / 3.14159) >= MIN_ELEVATION:
        passes.append({
            'rise_time': rise_time.datetime(),
            'duration': duration,
            'max_elevation': max_alt * (180 / 3.14159),
            'rise_azimuth': rise_az * (180 / 3.14159),
            'set_time': set_time.datetime(),
            'set_azimuth': set_az * (180 / 3.14159)
        })

    # Step observer forward
    observer.date = set_time + ephem.minute


# === Step 3: Display Results ===
def azimuth_to_cardinal(azimuth):
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = int((azimuth + 22.5) // 45) % 8
    return directions[index]


print("\n--- Next 10 Visible Passes ---")
for i, p in enumerate(passes, start=1):
    start_time = p['rise_time'].strftime('%a %b %d %I:%M %p')
    set_time = p['set_time'].strftime('%I:%M %p')
    appears_cardinal = azimuth_to_cardinal(p['rise_azimuth'])
    disappears_cardinal = azimuth_to_cardinal(p['set_azimuth'])

    print(f"{i}. Time: {start_time}, Duration: {p['duration']} min, "
          f"Max Height: {p['max_elevation']:.1f}°, "
          f"Appears: {int(p['rise_azimuth'])}° above {appears_cardinal}, "
          f"Disappears: {int(p['set_azimuth'])}° above {disappears_cardinal}")

# === Done ===
print("\n✅ Done! Next 10 visible passes calculated.")

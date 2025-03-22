import ephem
from datetime import datetime
from zoneinfo import ZoneInfo

# === Configurations ===
LATITUDE = '46.4667'
LONGITUDE = '6.8616'
ALTITUDE = 500
LOCAL_TIMEZONE = ZoneInfo("Europe/Zurich")

# ✅ Create Observer
observer = ephem.Observer()
observer.lat = LATITUDE
observer.lon = LONGITUDE
observer.elev = ALTITUDE
observer.date = datetime.utcnow()

# ✅ Compute Sun Position
sun = ephem.Sun(observer)

# ✅ Get Altitude and Azimuth
altitude = sun.alt * (180 / 3.14159)   # Convert from radians to degrees
azimuth = sun.az * (180 / 3.14159)     # Convert from radians to degrees

# ✅ Print Results
local_time = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC")).astimezone(LOCAL_TIMEZONE).strftime('%d.%m.%Y %H:%M:%S')
print(f"\n--- Sun Position at {local_time} ---")
print(f"Altitude: {altitude:.2f}°")
print(f"Azimuth: {azimuth:.2f}°")

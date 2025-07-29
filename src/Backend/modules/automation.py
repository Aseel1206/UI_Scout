import time
import math
from pymavlink import mavutil
from modules.mavlink_commands import *
from modules.distcalc import *

alti = 30  # Altitude to fly at (in meters)
drop_time = 5  # seconds to wait for drop
accuracy = 1.5  # meters to accept proximity

def distance_lat_lon(lat1, lon1, lat2, lon2):
    '''Calculate distance between two GPS coordinates in meters'''
    dLat = math.radians(lat2) - math.radians(lat1)
    dLon = math.radians(lon2) - math.radians(lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371000 * c

def automation(lati, longi, target_no, the_connection):
    logging.getLogger().status(f"Repositioning to target: {target_no}")

    # Get current GPS for logging
    gps = the_connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
    logging.getLogger().status(f"GPS during calculation: {gps}")

    calculated_distance = distance_lat_lon(lati/1e7, longi/1e7, gps.lat/1e7, gps.lon/1e7)
    gps = the_connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
    logging.getLogger().status(f"GPS before shifting to guided: {gps}")
    current_alt = gps.relative_alt / 1000.0
    logging.getLogger().status(f"Current altitude: {current_alt:.2f} m")

    # ARM the drone
    logging.getLogger().status("Arming the drone...")
    arm()
    time.sleep(1)

    # Switch to GUIDED mode
    logging.getLogger().status("Switching to GUIDED mode...")
    guided()
    time.sleep(2)

    # ✅ Critical: TAKEOFF command
    logging.getLogger().status("Sending takeoff command...")
    the_connection.mav.command_long_send(
        the_connection.target_system,
        the_connection.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        0, 0, 0, 0,
        0, 0,
        alti
    )
    time.sleep(6)  # give time to lift off

    # ✅ Now send go-to command
    logging.getLogger().status("Sending position target...")
    the_connection.mav.set_position_target_global_int_send(
        0,
        the_connection.target_system,
        the_connection.target_component,
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
        0b0000111111111000,
        int(lati),
        int(longi),
        alti,
        0, 0, 0,
        0, 0, 0,
        0, 0
    )

    logging.getLogger().status(f"Real distance to target: {calculated_distance:.2f} meters")
    logging.getLogger().status(f"Target LAT: {lati / 1e7}")
    logging.getLogger().status(f"Target LON: {longi / 1e7}")

    # ✅ Loop until drone reaches target
    try:
        while True:
            msg = the_connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
            current_lat = msg.lat / 1e7
            current_lon = msg.lon / 1e7
            distance = distance_lat_lon(current_lat, current_lon, lati / 1e7, longi / 1e7)

            logging.getLogger().status(f"Distance to target: {distance:.2f} meters")

            if distance <= accuracy:
                logging.getLogger().status("Target reached. Dropping payload...")
                drop(target_no)
                time.sleep(drop_time)
                logging.getLogger().status(f"Dropped at lat={current_lat}, lon={current_lon}")
                auto()
                break
    except Exception as e:
        logging.getLogger().status(f"Automation failed: {str(e)}")

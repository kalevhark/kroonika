# This script allows you to download map tiles for a specific area (Bounding Box)
# and specific zoom levels from the Estonian Land Board (Maa-amet) TMS server.

# Prerequisites

# You will need the requests library:

# pip install requests

# Python Script

import os
import math
import requests
import time

# --- CONFIGURATION ---
# Base URL for Estonian Land Board TMS (Global Mercator)
BASE_URL = "https://tiles.maaamet.ee/tm/tms/1.0.0/foto@GMC/{z}/{x}/{y}.png"

# Define the area to download (Latitude/Longitude)
# Example: Valga Town center
LAT_MIN, LON_MIN = 57.730, 25.900 
LAT_MAX, LON_MAX = 57.830, 26.150

# Zoom levels to download (e.g., from 14 to 16)
ZOOM_LEVELS = range(4, 19)

# Directory to save tiles
OUTPUT_DIR = "maaamet_tiles"

# Headers to be polite to the server
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TileDownloader/1.0"
}

def latlon_to_xyz(lat, lon, zoom):
    """Converts Lat/Lon to standard XYZ tile coordinates."""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return x, y

def xyz_to_tms_y(y, zoom):
    """Converts standard XYZ Y-coordinate to TMS Y-coordinate (inverted Y)."""
    return (2 ** zoom) - 1 - y

def download_tiles():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    for zoom in ZOOM_LEVELS:
        print(f"\nProcessing Zoom Level: {zoom}")
        
        # Find the tile range for the BBox
        x_min, y_max_xyz = latlon_to_xyz(LAT_MIN, LON_MIN, zoom)
        x_max, y_min_xyz = latlon_to_xyz(LAT_MAX, LON_MAX, zoom)
        
        # Ensure coordinates are in correct order
        x_start, x_end = min(x_min, x_max), max(x_min, x_max)
        y_start_xyz, y_end_xyz = min(y_min_xyz, y_max_xyz), max(y_min_xyz, y_max_xyz)

        for x in range(x_start, x_end + 1):
            # Create subdirectory for X
            tile_path = os.path.join(OUTPUT_DIR, str(zoom), str(x))
            if not os.path.exists(tile_path):
                os.makedirs(tile_path)

            for y_xyz in range(y_start_xyz, y_end_xyz + 1):
                # IMPORTANT: Maa-amet uses TMS Y-coordinate (bottom-up)
                # Standard web maps use XYZ (top-down). We must invert Y.
                y_tms = xyz_to_tms_y(y_xyz, zoom)
                
                url = BASE_URL.format(z=zoom, x=x, y=y_tms)
                file_name = os.path.join(tile_path, f"{y_tms}.png")

                if os.path.exists(file_name):
                    continue

                try:
                    response = requests.get(url, headers=HEADERS, timeout=10)
                    if response.status_code == 200:
                        with open(file_name, "wb") as f:
                            f.write(response.content)
                        print(f"Downloaded: {zoom}/{x}/{y_tms}")
                        # Sleep briefly to avoid hammering the server
                        time.sleep(0.1)
                    else:
                        print(f"Skipped: {zoom}/{x}/{y_tms} (Status: {response.status_code})")
                except Exception as e:
                    print(f"Error downloading {url}: {e}")

if __name__ == "__main__":
    start_time = time.time()
    download_tiles()
    end_time = time.time()
    print(f"\nFinished! Total time: {end_time - start_time:.2f} seconds.")


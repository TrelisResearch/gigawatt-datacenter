import requests

def check_open_meteo_wind_heights():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 52.52,
        "longitude": 13.41,
        "hourly": "windspeed_10m,windspeed_50m,windspeed_100m,windspeed_180m",
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    available_heights = []
    for key in data.get("hourly", {}).keys():
        if key.startswith("windspeed_"):
            height = key.split("_")[1]
            available_heights.append(height)
    
    print("Available wind speed heights from Open-Meteo:")
    print(", ".join(available_heights))
    
    if "50m" in available_heights:
        print("\nOpen-Meteo provides 50m wind data!")
    else:
        print("\nOpen-Meteo does not provide 50m wind data.")
        print("Consider using 100m data and interpolating if needed.")
        print("\nAlternative API suggestion:")
        print("NREL's WIND Toolkit API (https://www.nrel.gov/grid/wind-toolkit.html)")
        print("It provides wind speed data at multiple heights, including 50m.")
        print("Note: NREL's API requires registration and has usage limits.")

if __name__ == "__main__":
    check_open_meteo_wind_heights()

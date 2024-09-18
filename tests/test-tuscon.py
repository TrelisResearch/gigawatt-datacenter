import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import requests

def fetch_open_meteo_data(latitude, longitude, start_date, end_date):
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "windspeed_10m,windspeed_100m,windspeed_180m,temperature_2m,pressure_msl"
    }
    
    response = requests.get(base_url, params=params)
    data = response.json()
    
    df = pd.DataFrame(data['hourly'])
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    
    return df

def analyze_wind_data(df):
    # Calculate daily average wind speeds
    daily_wind_speeds = df[['windspeed_10m', 'windspeed_100m', 'windspeed_180m']].resample('D').mean()
    
    # Calculate monthly average wind speeds
    monthly_wind_speeds = df[['windspeed_10m', 'windspeed_100m', 'windspeed_180m']].resample('M').mean()
    
    # Calculate overall statistics
    overall_stats = df[['windspeed_10m', 'windspeed_100m', 'windspeed_180m']].describe()
    
    return daily_wind_speeds, monthly_wind_speeds, overall_stats

def plot_wind_data(daily_wind_speeds, monthly_wind_speeds):
    # Plot daily wind speeds
    plt.figure(figsize=(12, 6))
    daily_wind_speeds.plot()
    plt.title('Daily Average Wind Speeds in Tucson')
    plt.xlabel('Date')
    plt.ylabel('Wind Speed (m/s)')
    plt.legend(['10m', '100m', '180m'])
    plt.savefig('tucson_daily_wind_speeds.png')
    plt.close()
    
    # Plot monthly wind speeds
    plt.figure(figsize=(12, 6))
    monthly_wind_speeds.plot(kind='bar')
    plt.title('Monthly Average Wind Speeds in Tucson')
    plt.xlabel('Month')
    plt.ylabel('Wind Speed (m/s)')
    plt.legend(['10m', '100m', '180m'])
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('tucson_monthly_wind_speeds.png')
    plt.close()
    
    # Plot wind speed distribution
    plt.figure(figsize=(12, 6))
    sns.histplot(data=daily_wind_speeds, kde=True)
    plt.title('Wind Speed Distribution in Tucson')
    plt.xlabel('Wind Speed (m/s)')
    plt.ylabel('Frequency')
    plt.savefig('tucson_wind_speed_distribution.png')
    plt.close()

def main():
    latitude = 32.31
    longitude = -111.08
    start_date = "2022-01-01"
    end_date = "2022-12-31"
    
    print("Fetching wind data for Tucson...")
    df = fetch_open_meteo_data(latitude, longitude, start_date, end_date)
    
    print("Analyzing wind data...")
    daily_wind_speeds, monthly_wind_speeds, overall_stats = analyze_wind_data(df)
    
    print("Plotting wind data...")
    plot_wind_data(daily_wind_speeds, monthly_wind_speeds)
    
    print("\nOverall Wind Speed Statistics:")
    print(overall_stats)
    
    print("\nAnalysis complete. Check the generated PNG files for visualizations.")

if __name__ == "__main__":
    main()

from windpowerlib import ModelChain, WindTurbine
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests

# Cities: Cork, Waterford, Dublin (with their respective coordinates)
locations = {
    'Cork': {'latitude': 51.89, 'longitude': -8.47, 'name': 'Cork'},
    'Waterford': {'latitude': 52.26, 'longitude': -7.12, 'name': 'Waterford'},
    'Dublin': {'latitude': 53.35, 'longitude': -6.26, 'name': 'Dublin'},
    'San Antonio': {'latitude': 29.22, 'longitude': -98.75, 'name': 'San Antonio'},
    'Tucson': {'latitude': 32.43, 'longitude': -111.1, 'name': 'Tucson'},
    'Galway': {'latitude': 53.27, 'longitude': -9.05, 'name': 'Galway'},
    'Donegal': {'latitude': 54.65, 'longitude': -8.12, 'name': 'Donegal'}
}

city_name = 'San Antonio'  # Change this to 'Waterford' or 'Dublin' as needed

# Get the location information for the selected city
latitude = locations[city_name]['latitude']
longitude = locations[city_name]['longitude']
city = locations[city_name]['name']

def fetch_open_meteo_data(latitude, longitude, start_date, end_date):
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={latitude}&longitude={longitude}&start_date={start_date}&end_date={end_date}&hourly=windspeed_10m,temperature_2m,pressure_msl"
    response = requests.get(url)
    data = response.json()
    
    # Print diagnostic information
    print(f"API URL: {url}")
    print(f"First few wind speed values: {data['hourly']['windspeed_10m'][:5]}")
    
    df = pd.DataFrame({
        ('wind_speed', 10): data['hourly']['windspeed_10m'],
        ('temperature', 2): [t + 273.15 for t in data['hourly']['temperature_2m']],  # Convert to Kelvin
        ('pressure', 0): data['hourly']['pressure_msl'],
        ('roughness_length', 0): [0.1] * len(data['hourly']['time']),  # Estimate roughness length
    })
    df.index = pd.to_datetime(data['hourly']['time'])
    
    return df

# Fetch real weather data
start_date = "2022-01-01"
end_date = "2022-12-31"
weather = fetch_open_meteo_data(latitude, longitude, start_date, end_date)

# After fetching weather data
print(f"Average wind speed for {city_name}: {weather[('wind_speed', 10)].mean():.2f} m/s")

# Specification of wind turbine
turbine = WindTurbine(turbine_type='E-126/7500', hub_height=135)

# ModelChain setup and run
mc = ModelChain(turbine).run_model(weather)
turbine.power_output = mc.power_output

# After calculating power output
print(f"Total energy output for {city_name}: {turbine.power_output.sum() / 1e6:.2f} MWh")

# Calculate daily energy output
daily_output = turbine.power_output.resample('D').sum() / 1e6  # Convert to MWh

# Sort daily output for analysis
sorted_daily_output = daily_output.sort_values()

# Print some statistics about the daily output
print(f"Daily output statistics for {city_name}:")
print(sorted_daily_output.describe())

# Define energy usage and other requirements
cutoff_day = 50  # This could be adjusted based on seasonality and your use case
daily_usage = 2400  # Adjust according to actual daily usage (in MWh)
demand_in_MW = 100  # Demand in MW

# Print diagnostic information
print(f"\nDiagnostic Information:")
print(f"Daily usage: {daily_usage} MWh")
print(f"Cutoff day value: {sorted_daily_output.iloc[cutoff_day]:.2f} MWh")
print(f"Calculation: {daily_usage} / {sorted_daily_output.iloc[cutoff_day]:.2f}")

# Calculate required wind turbines
if sorted_daily_output.iloc[0] > 0:
    required_turbines_no_generators = round(daily_usage / sorted_daily_output.iloc[0])
else:
    required_turbines_no_generators = float('inf')
    print("Warning: There are days with zero wind output. Infinite turbines would be required without generators.")

required_turbines_with_generators = round(daily_usage / sorted_daily_output.iloc[cutoff_day])

# Calculate generator input and fraction
annual_demand = 365 * daily_usage
generator_input = (50 * demand_in_MW * 24) - sum(sorted_daily_output.iloc[:cutoff_day]) * required_turbines_with_generators
generator_fraction = generator_input / annual_demand

# Calculate average capacity factor (with generators)
total_energy_output = sum(sorted_daily_output) * required_turbines_with_generators  # Total energy in MWh
total_capacity = turbine.nominal_power * required_turbines_with_generators / 1e6  # Total capacity in MW
capacity_factor = total_energy_output / (total_capacity * 24 * 365)

# Print results
print(f'\nWind Turbine Requirements for {city_name}:')
print(f'Turbine Type: {turbine.turbine_type}')
print(f'Rated Power: {turbine.nominal_power/1e3:.2f} MW')
print(f'Average Capacity Factor (with generators): {capacity_factor:.2%}')
if required_turbines_no_generators != float('inf'):
    print('Required Wind Turbines (no generators): ', required_turbines_no_generators)
    print(f'Total Installed Capacity (no generators): {required_turbines_no_generators * turbine.nominal_power/1e6:.2f} GW')
else:
    print('Required Wind Turbines (no generators): Infinite (due to days with no wind)')
print('Required Wind Turbines (with generators): ', required_turbines_with_generators)
print(f'Total Installed Capacity (with generators): {required_turbines_with_generators * turbine.nominal_power/1e6:.2f} GW')
print(f'Fraction handled by generators: {generator_fraction:.2%}')

# Plotting
scaled_daily_output = sorted_daily_output * required_turbines_with_generators
generator_output = np.maximum(daily_usage - scaled_daily_output, 0)

fig, ax = plt.subplots(figsize=(12, 6))

ax.bar(range(len(scaled_daily_output)), scaled_daily_output, label='Wind Output', color='blue')
ax.bar(range(len(generator_output)), generator_output, bottom=scaled_daily_output, 
       label='Generator Output', color='gray')

ax.set_xlabel('Days (sorted by wind output)')
ax.set_ylabel('Energy Output (MWh)')
ax.set_title(f'Daily Energy Output in {city_name}: Wind vs Generator')
ax.legend()
ax.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()
plt.show()
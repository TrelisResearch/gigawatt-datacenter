from pvlib import pvsystem, modelchain, location, iotools
import pandas as pd

# Cities: Cork, Waterford, Dublin (with their respective coordinates)
locations = {
    'Cork': {'latitude': 51.89, 'longitude': -8.47, 'name': 'Cork'},
    'Waterford': {'latitude': 52.26, 'longitude': -7.12, 'name': 'Waterford'},
    'Dublin': {'latitude': 53.35, 'longitude': -6.26, 'name': 'Dublin'},
    'San Antonio': {'latitude': 29.22, 'longitude': -98.75, 'name': 'San Antonio'},
    'Tuscon': {'latitude': 32.43, 'longitude': -111.1, 'name': 'Tuscon'}
}

# Choose a city here (Cork, Waterford, or Dublin)
city_name = 'San Antonio'  # Change this to 'Waterford' or 'Dublin' as needed

# Get the location information for the selected city
latitude = locations[city_name]['latitude']
longitude = locations[city_name]['longitude']
city = locations[city_name]['name']

# Adjust solar array parameters (same as before, can be modified)
array_kwargs_tracker = dict(
    module_parameters=dict(pdc0=1, gamma_pdc=-0.004),
    temperature_model_parameters=dict(a=-3.56, b=-0.075, deltaT=3)
)

# Setting to display all columns
pd.set_option('display.max_columns', None)

# Defining the solar panel system with a single-axis tracker
arrays = [
    pvsystem.Array(pvsystem.SingleAxisTrackerMount(),
                   **array_kwargs_tracker),
]

# Create a location object using the selected coordinates
loc = location.Location(latitude, longitude)
system = pvsystem.PVSystem(arrays=arrays, inverter_parameters=dict(pdc0=1))

# Create a ModelChain object to simulate the solar energy output
mc = modelchain.ModelChain(system, loc, aoi_model='physical', spectral_model='no_loss')

# Fetching Typical Meteorological Year (TMY) weather data for the location
weather = iotools.get_pvgis_tmy(latitude, longitude)[0]

# Run the model with the fetched weather data
mc.run_model(weather)

# Getting the AC power results from the model (hourly output)
ac = mc.results.ac

# Variables for calculating daily solar energy output
daily_energy_sum = 0
hour_counter = 0
daily_output = []

# Ireland has a different solar profile, we may not want to trim as much data.
# However, we'll still exclude some start and end hours if needed.

# Looping over hourly data, trimming first 7 and last 17 hours
# This can be adjusted for Ireland based on actual solar profiles (optional trimming)
for hourly_output in ac[7:-17]:  
    if hour_counter < 24:
        daily_energy_sum += hourly_output
        hour_counter += 1
    else:
        daily_output.append(daily_energy_sum)
        daily_energy_sum = 0
        hour_counter = 0

# Once loop ends, append the last day's sum
if daily_energy_sum > 0:
    daily_output.append(daily_energy_sum)

# Sorting the daily output to analyze worst-case scenarios
daily_output.sort()

# Define energy usage and other requirements
cutoff_day = 50  # This could be adjusted based on seasonality and your use case
daily_usage = 2400  # Adjust according to actual daily usage (in kWh)
demand_in_MW = 100  # Demand in MW

# Output results for the required solar array sizes
# Calculate total annual energy demand
annual_demand = 365 * daily_usage

print(f'Solar Array Requirements for {city_name}:')
required_solar_array_no_generators = round(daily_usage / (daily_output[0]))
required_solar_array_with_generators = round(daily_usage / (daily_output[cutoff_day:][0]))
print('Required Solar Array (no generators): ', required_solar_array_no_generators)
print('Required Solar Array (with generators): ', required_solar_array_with_generators)


# Calculate generator input (50 worst days at full demand, minus solar contribution)
generator_input = (50 * demand_in_MW * 24) - sum(daily_output[:cutoff_day])*required_solar_array_with_generators

# Calculate fraction handled by generators
generator_fraction = generator_input / annual_demand

print('Fraction handled by generators: ', generator_fraction)

##--Add some plotting--##
import matplotlib.pyplot as plt
import numpy as np

# Daily output for the required solar array size
scaled_daily_output = np.array(daily_output) * required_solar_array_with_generators

# Create generator output data
generator_output = np.zeros_like(scaled_daily_output)
generator_output[:cutoff_day] = 2400 - scaled_daily_output[:cutoff_day]
generator_output = np.maximum(generator_output, 0)  # Ensure non-negative values

# Create the plot
fig, ax = plt.subplots(figsize=(12, 6))

# Plot solar output
ax.bar(range(len(scaled_daily_output)), scaled_daily_output, label='Solar Output', color='yellow')

# Plot generator output
ax.bar(range(len(generator_output)), generator_output, bottom=scaled_daily_output, 
       label='Generator Output', color='gray')

# Customize the plot
ax.set_xlabel('Days (sorted by solar output)')
ax.set_ylabel('Energy Output (MWh)')
ax.set_title(f'Daily Energy Output in {city_name}: Solar vs Generator')
ax.legend()

# Add grid for better readability
ax.grid(True, linestyle='--', alpha=0.7)

# Show the plot
plt.tight_layout()
plt.show()

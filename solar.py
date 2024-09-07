from pvlib import pvsystem, modelchain, location, iotools
import pandas as pd
import yfinance as yf

# Cities: Cork, Waterford, Dublin (with their respective coordinates)
locations = {
    'Cork': {'latitude': 51.89, 'longitude': -8.47, 'name': 'Cork'},
    'Waterford': {'latitude': 52.26, 'longitude': -7.12, 'name': 'Waterford'},
    'Dublin': {'latitude': 53.35, 'longitude': -6.26, 'name': 'Dublin'},
    'San Antonio': {'latitude': 29.22, 'longitude': -98.75, 'name': 'San Antonio'},
    'Tuscon': {'latitude': 32.43, 'longitude': -111.1, 'name': 'Tuscon'}
}

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
daily_usage = 2400  # Adjust according to actual daily usage (in MWh)
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

##--Add cost calculations--##

# Fetch 20-year Treasury rate
treasury_20y = yf.Ticker("^TYX")
rate_20y = treasury_20y.info['previousClose'] / 100  # Convert to decimal

# WACC calculation
equity_premium = 0.05  # 5% premium over 20-year Treasury rate
equity_return = rate_20y + equity_premium
debt_premium = 0.02  # 2% premium over 20-year Treasury rate
debt_return = rate_20y + debt_premium
debt_ratio = 0.6  # 60% debt financing
equity_ratio = 1 - debt_ratio
tax_rate = 0.21  # Assuming 21% corporate tax rate

wacc = (equity_return * equity_ratio) + (debt_return * debt_ratio * (1 - tax_rate))

# Project lifetime
project_lifetime = 20  # years

# Cost parameters
solar_cost_per_kw = 550  # $/kW
battery_cost_per_kwh = 250  # $/kWh
generator_cost_per_kw = 800  # $/kW

# Calculate system costs
def calculate_system_cost(solar_capacity, battery_capacity=0, generator_capacity=0):
    solar_cost = solar_capacity * solar_cost_per_kw
    battery_cost = battery_capacity * battery_cost_per_kwh
    generator_cost = generator_capacity * generator_cost_per_kw
    return solar_cost + battery_cost + generator_cost

# Pure solar case
pure_solar_capacity = required_solar_array_no_generators * 1000  # Convert to kW
pure_solar_cost = calculate_system_cost(pure_solar_capacity)

# Generator supported case
supported_solar_capacity = required_solar_array_with_generators * 1000  # Convert to kW
generator_capacity = demand_in_MW * 1000  # Convert to kW
supported_system_cost = calculate_system_cost(supported_solar_capacity, generator_capacity=generator_capacity)

# Calculate LCOE
def calculate_lcoe(system_cost, annual_energy_output):
    annual_cost = system_cost * (wacc * (1 + wacc)**project_lifetime) / ((1 + wacc)**project_lifetime - 1)
    return annual_cost / (annual_energy_output * 1000)  # Convert MWh to kWh

pure_solar_lcoe = calculate_lcoe(pure_solar_cost, annual_demand)
supported_system_lcoe = calculate_lcoe(supported_system_cost, annual_demand)

# Natural Gas Case
ng_efficiency = 0.35  # 35% efficiency for open cycle gas turbine
ng_price_per_mmbtu = 20  # €/MMBtu (typical European price)
ng_price_per_kwh = ng_price_per_mmbtu / 293.07  # Convert €/MMBtu to €/kWh
ng_opex_per_kwh = 0.02  # €/kWh for operation and maintenance

def calculate_ng_lcoe(demand_mwh):
    fuel_cost_per_kwh = ng_price_per_kwh / ng_efficiency
    total_cost_per_kwh = fuel_cost_per_kwh + ng_opex_per_kwh
    return total_cost_per_kwh

ng_lcoe = calculate_ng_lcoe(annual_demand)

# Print results
print("\nCost Analysis:")
print(f"20-year Treasury rate: {rate_20y:.4f}")
print(f"WACC: {wacc:.4f}")

print(f"\nNatural Gas System:")
# print(f"LCOE: €{ng_lcoe:.4f}/kWh")

# Convert to USD for comparison
usd_eur_rate = 1.1  # Assume 1 EUR = 1.1 USD
print(f"LCOE: ${ng_lcoe * usd_eur_rate:.4f}/kWh")

print(f"\nPure Solar System:")
print(f"Total cost: ${pure_solar_cost:,.0f}")
print(f"LCOE: ${pure_solar_lcoe:.4f}/kWh")
print(f"\nGenerator Supported System:")
print(f"Total cost: ${supported_system_cost:,.0f}")
print(f"LCOE: ${supported_system_lcoe:.4f}/kWh")

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
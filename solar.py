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

city_name = 'Waterford'  # Change this to 'Waterford' or 'Dublin' as needed

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
daily_output.sort() # in kWh / kW of solar array

# Define energy usage and other requirements
cutoff_day = 50  # This could be adjusted based on seasonality and your use case
demand_in_kw = 1000000  # Demand in kW (changed from 1000 MW)
daily_usage = 24000000  # Adjust according to actual daily usage (in kWh, changed from 24000 MWh)

# Calculate total annual energy demand
annual_demand = 365 * daily_usage  # in kWh (removed * 1000)

print(f'Solar Array Requirements for {city_name}:')
required_solar_array_no_generators = round(daily_usage / (daily_output[0]))  # in kW of solar array (removed * 1000)
required_solar_array_with_generators = round(daily_usage / (daily_output[cutoff_day:][0]))  # in kW of solar array (removed * 1000)
print('Required Solar Array (no generators): ', required_solar_array_no_generators)
print('Required Solar Array (with generators): ', required_solar_array_with_generators)

# Calculate generator input (50 worst days at full demand, minus solar contribution)
generator_energy = ((50 * demand_in_kw * 24) - sum(daily_output[:cutoff_day])*required_solar_array_with_generators)  # in kWh (removed * 1000)

# Calculate fraction handled by generators
generator_fraction = generator_energy / annual_demand

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

# Natural Gas parameters
ng_price_per_mmbtu = 20  # €/MMBtu (typical European price)
ng_price_per_kwh = ng_price_per_mmbtu / 293.07  # Convert €/MMBtu to €/kWh

# Open Cycle Gas Turbine (OCGT) parameters
ocgt_efficiency = 0.35  # 35% efficiency for open cycle gas turbine
ocgt_capex_per_kw = 800  # $/kW
ocgt_opex_per_kwh = 0.02  # €/kWh for operation and maintenance

# Combined Cycle Gas Turbine (CCGT) parameters
ccgt_efficiency = 0.60  # 60% efficiency for combined cycle gas turbine
ccgt_capex_per_kw = 1200  # $/kW
ccgt_opex_per_kwh = 0.015  # €/kWh for operation and maintenance

# Calculate system costs
def calculate_system_cost(solar_capacity, battery_capacity=0, generator_capacity=0):
    solar_cost = solar_capacity * solar_cost_per_kw
    battery_cost = battery_capacity * battery_cost_per_kwh
    generator_cost = generator_capacity * generator_cost_per_kw
    return solar_cost + battery_cost + generator_cost

# Pure solar case
pure_solar_capacity = required_solar_array_no_generators  # in kW of solar array
battery_capacity = demand_in_kw * 24  # 24 hours of storage in kWh (changed from demand_in_MW)
pure_solar_cost = calculate_system_cost(pure_solar_capacity, battery_capacity)

# Generator supported case
supported_solar_capacity = required_solar_array_with_generators  # in kW of solar array
generator_capacity = demand_in_kw  # Already in kW (changed from demand_in_MW * 1000)
supported_system_cost = calculate_system_cost(supported_solar_capacity, battery_capacity, generator_capacity)

# Calculate annual energy used (which is equal to the demand)
annual_energy_used = 365 * daily_usage  # in kWh (removed * 1000)

# Calculate annual energy generated for solar systems
pure_solar_energy_generated = sum(daily_output) * required_solar_array_no_generators  # in kWh
supported_solar_energy_generated = sum(daily_output) * required_solar_array_with_generators  # in kWh

# Solar energy used is the minimum of generated and demanded
pure_solar_energy_used = min(annual_energy_used, pure_solar_energy_generated)
supported_solar_energy_used = min(annual_energy_used - generator_energy, supported_solar_energy_generated)

# Calculate LCOE
def calculate_lcoe(system_cost, annual_energy_used, annual_generator_energy=0):
    annual_capital_cost = system_cost * (wacc * (1 + wacc)**project_lifetime) / ((1 + wacc)**project_lifetime - 1)
    annual_generator_fuel_cost = annual_generator_energy * (ng_price_per_kwh / ocgt_efficiency + ocgt_opex_per_kwh)
    total_annual_cost = annual_capital_cost + annual_generator_fuel_cost
    return total_annual_cost / annual_energy_used  # Removed * 1000

pure_solar_lcoe = calculate_lcoe(pure_solar_cost, annual_energy_used)
supported_system_lcoe = calculate_lcoe(supported_system_cost, annual_energy_used, generator_energy)

# Natural Gas Case (CCGT and OCGT)
def calculate_ng_lcoe(demand_kwh, efficiency, capex_per_kw, opex_per_kwh):
    capacity_kw = demand_in_kw
    
    capex = capacity_kw * capex_per_kw
    annual_capex = capex * (wacc * (1 + wacc)**project_lifetime) / ((1 + wacc)**project_lifetime - 1)
    
    fuel_cost_per_kwh = ng_price_per_kwh / efficiency
    annual_fuel_cost = demand_kwh * fuel_cost_per_kwh
    annual_opex = demand_kwh * opex_per_kwh
    
    total_annual_cost = annual_capex + annual_fuel_cost + annual_opex
    return total_annual_cost / demand_kwh

ocgt_lcoe = calculate_ng_lcoe(annual_energy_used, ocgt_efficiency, ocgt_capex_per_kw, ocgt_opex_per_kwh)
ccgt_lcoe = calculate_ng_lcoe(annual_energy_used, ccgt_efficiency, ccgt_capex_per_kw, ccgt_opex_per_kwh)

# Calculate capex per kW of rated capacity
def calculate_capex_per_kw(total_cost, rated_capacity_kw):
    return total_cost / rated_capacity_kw

# Pure solar case
pure_solar_capex_per_kw = calculate_capex_per_kw(pure_solar_cost, demand_in_kw)

# Generator supported case
supported_system_capex_per_kw = calculate_capex_per_kw(supported_system_cost, demand_in_kw)

# Natural gas cases (OCGT and CCGT)
ocgt_capex_per_kw = ocgt_capex_per_kw
ccgt_capex_per_kw = ccgt_capex_per_kw

# Print results
print("\nCost Analysis:")
print(f"20-year Treasury rate: {rate_20y:.4f}")
print(f"WACC: {wacc:.4f}")

# Convert to USD for comparison
usd_eur_rate = 1.1  # Assume 1 EUR = 1.1 USD

print(f"\nNatural Gas System (OCGT):")
print(f"LCOE: ${ocgt_lcoe * usd_eur_rate:.4f}/kWh")
print(f"Capex per kW: ${ocgt_capex_per_kw:.2f}/kW")

print(f"\nNatural Gas System (CCGT):")
print(f"LCOE: ${ccgt_lcoe * usd_eur_rate:.4f}/kWh")
print(f"Capex per kW: ${ccgt_capex_per_kw:.2f}/kW")

print(f"\nPure Solar System (with 24h battery storage):")
print(f"Total cost: ${pure_solar_cost:,.0f}")
print(f"LCOE: ${pure_solar_lcoe:.4f}/kWh")
print(f"Capex per kW: ${pure_solar_capex_per_kw:.2f}/kW")
print(f"Solar Capacity Factor: {pure_solar_energy_used / pure_solar_energy_generated:.2%}")

print(f"\nGenerator Supported System (with 24h battery storage):")
print(f"Total cost: ${supported_system_cost:,.0f}")
print(f"LCOE: ${supported_system_lcoe:.4f}/kWh")
print(f"Capex per kW: ${supported_system_capex_per_kw:.2f}/kW")
print(f"Solar Capacity Factor: {supported_solar_energy_used / supported_solar_energy_generated:.2%}")
print(f"Fraction of energy from solar: {supported_solar_energy_used / annual_energy_used:.2%}")

##--Add some plotting--##
import matplotlib.pyplot as plt
import numpy as np

# Daily output for the required solar array size
scaled_daily_output = np.array(daily_output) * required_solar_array_with_generators

# Create generator output data
generator_output = np.zeros_like(scaled_daily_output)
generator_output[:cutoff_day] = demand_in_kw * 24 - scaled_daily_output[:cutoff_day]
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
ax.set_ylabel('Energy Output (kWh)')
ax.set_title(f'Daily Energy Output in {city_name}: Solar vs Generator')
ax.legend()

# Add grid for better readability
ax.grid(True, linestyle='--', alpha=0.7)

# Show the plot
plt.tight_layout()
plt.show()
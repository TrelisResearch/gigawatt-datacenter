print("Running wind-solar.py")

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pvlib import pvsystem, modelchain, location, iotools
import requests
import yfinance as yf
from windpowerlib import ModelChain, WindTurbine, WindFarm

# Import necessary functions from solar.py
from solar import get_coordinates, calculate_system_cost, calculate_lcoe, calculate_ng_lcoe, calculate_capex_per_kw

# Constants and parameters
gamma = 1  # Ratio of rated solar to wind capacity
city_name = 'Boston'
country_name = 'United States'
demand_in_kw = 1000000
daily_usage = 24000000
cutoff_day = 50

# Get coordinates
coordinates = get_coordinates(city_name, country_name)
if coordinates:
    latitude, longitude = coordinates
else:
    raise ValueError(f"Could not find coordinates for {city_name}, {country_name}")

print(f"Coordinates for {city_name}: Latitude {latitude}, Longitude {longitude}")

# Solar energy calculation
def calculate_solar_energy(latitude, longitude):
    array_kwargs = dict(
        module_parameters=dict(pdc0=1, gamma_pdc=-0.004),
        temperature_model_parameters=dict(a=-3.56, b=-0.075, deltaT=3)
    )
    arrays = [pvsystem.Array(pvsystem.SingleAxisTrackerMount(), **array_kwargs)]
    loc = location.Location(latitude, longitude)
    system = pvsystem.PVSystem(arrays=arrays, inverter_parameters=dict(pdc0=1))
    mc = modelchain.ModelChain(system, loc, aoi_model='physical', spectral_model='no_loss')
    weather = iotools.get_pvgis_tmy(latitude, longitude)[0]
    mc.run_model(weather)
    return mc.results.ac

# Wind energy calculation
def calculate_wind_energy(latitude, longitude):
    weather_df = iotools.get_pvgis_tmy(latitude, longitude)[0]
    weather_df.index.name = 'timestamp'
    weather_df = weather_df.rename(columns={'temp_air': 'temperature', 'wind_speed': 'wind_speed'})
    weather_df['roughness_length'] = 0.1
    weather_df['pressure'] = 101325
    
    turbine_type = 'E-126/4200'
    turbine = WindTurbine(**WindTurbine.get_turbine_data(turbine_type))
    mc_wind = ModelChain(turbine).run_model(weather_df)
    return mc_wind.power_output

# Calculate hourly energy profiles
solar_hourly = calculate_solar_energy(latitude, longitude)
wind_hourly = calculate_wind_energy(latitude, longitude)

# Combine solar and wind profiles based on gamma
combined_hourly = gamma * solar_hourly + wind_hourly

# Calculate daily energy output
daily_output = combined_hourly.resample('D').sum().sort_values()

# Calculate required capacity
required_capacity = daily_usage / daily_output.iloc[cutoff_day]
solar_capacity = gamma * required_capacity
wind_capacity = required_capacity

print(f'Combined Wind-Solar System Requirements for {city_name}:')
print(f'Required Solar Capacity: {solar_capacity:.2f} kW')
print(f'Required Wind Capacity: {wind_capacity:.2f} kW')

# Calculate generator energy
generator_energy = (cutoff_day * demand_in_kw * 24) - (daily_output.iloc[:cutoff_day] * required_capacity).sum()
generator_fraction = generator_energy / (365 * daily_usage)

print(f'Fraction handled by generators: {generator_fraction:.4f}')

# Cost calculations
solar_cost_per_kw = 550
wind_cost_per_kw = 1300
battery_cost_per_kwh = 250
generator_cost_per_kw = 800

battery_capacity = demand_in_kw * 24
generator_capacity = demand_in_kw

system_cost = (solar_capacity * solar_cost_per_kw +
               wind_capacity * wind_cost_per_kw +
               battery_capacity * battery_cost_per_kwh +
               generator_capacity * generator_cost_per_kw)

# LCOE calculation
treasury_20y = yf.Ticker("^TYX")
rate_20y = treasury_20y.info['previousClose'] / 100
equity_premium = 0.05
equity_return = rate_20y + equity_premium
debt_premium = 0.02
debt_return = rate_20y + debt_premium
debt_ratio = 0.6
equity_ratio = 1 - debt_ratio
tax_rate = 0.21

wacc = (equity_return * equity_ratio) + (debt_return * debt_ratio * (1 - tax_rate))

project_lifetime = 20
annual_energy_used = 365 * daily_usage

lcoe = calculate_lcoe(system_cost, annual_energy_used, generator_energy)

print("\nCost Analysis:")
print(f"20-year Treasury rate: {rate_20y:.4f}")
print(f"WACC: {wacc:.4f}")
print(f"\nWind-Solar-Generator System:")
print(f"Total cost: ${system_cost:,.0f}")
print(f"LCOE: ${lcoe:.4f}/kWh")

# Capex breakdown chart
capex_components = [
    solar_capacity * solar_cost_per_kw,
    wind_capacity * wind_cost_per_kw,
    battery_capacity * battery_cost_per_kwh,
    generator_capacity * generator_cost_per_kw
]
labels = ['Solar Panels', 'Wind Turbines', 'Battery Storage', 'Generator']
colors = ['yellow', 'lightblue', 'lightgreen', 'lightgray']

fig, ax = plt.subplots(figsize=(10, 8))
wedges, texts, autotexts = ax.pie(capex_components, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
ax.set_title(f'Capex Breakdown for Wind-Solar-Generator System in {city_name}')
ax.legend(wedges, labels, title="Components", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
plt.text(0.5, -0.1, f'Total Capex: ${sum(capex_components):,.0f}', ha='center', transform=ax.transAxes)
plt.tight_layout()
plt.show()
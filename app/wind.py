from runtime_config import config
from windpowerlib import ModelChain, WindTurbine
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import math
from utils import calculate_wacc, calculate_lcoe, calculate_capex_per_kw
from functools import lru_cache

WIND_TURBINE = WindTurbine(turbine_type=config.WIND_TURBINE_TYPE, hub_height=config.WIND_TURBINE_HUB_HEIGHT)

# Cost analysis
WACC = calculate_wacc()

@lru_cache(maxsize=None)
def get_processed_weather_data(latitude, longitude, start_date, end_date):
    processed_weather_data = fetch_open_meteo_data(latitude, longitude, start_date, end_date)
    return processed_weather_data

def fetch_open_meteo_data(latitude, longitude, start_date, end_date):
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={latitude}&longitude={longitude}&start_date={start_date}&end_date={end_date}&hourly=windspeed_10m,windspeed_100m,temperature_2m,pressure_msl&wind_speed_unit=ms"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None
    data = response.json()
    
    print(f"API URL: {url}")
    print(f"Available variables: {data['hourly'].keys()}")
    
    df = pd.DataFrame({
        ('wind_speed', 10): data['hourly']['windspeed_10m'],
        ('temperature', 2): [t + 273.15 for t in data['hourly']['temperature_2m']],  # Convert to Kelvin
        ('pressure', 0): [p*100 for p in data['hourly']['pressure_msl']], # Convert to Pascals
        ('roughness_length', 0): [0.1] * len(data['hourly']['time']),  # Estimate roughness length
    })
    
    # Add wind speeds for other heights if available
    if 'windspeed_100m' in data['hourly']:
        df[('wind_speed', 100)] = data['hourly']['windspeed_100m']
    
    df.index = pd.to_datetime(data['hourly']['time'])
    
    return df

# Calculate system costs
def calculate_system_cost(wind_capacity, battery_capacity=0, gas_capacity=0):
    wind_cost = wind_capacity * config.WIND_COST_PER_KW
    battery_cost = battery_capacity * config.BATTERY_COST_PER_KWH
    gas_cost = gas_capacity * config.OCGT_CAPEX_PER_KW
    return wind_cost + battery_cost + gas_cost

def analyze_wind_energy(latitude, longitude, daily_usage, demand_in_kw, cutoff_day=None, wacc=WACC):
    if cutoff_day is None:
        cutoff_day = config.CUTOFF_DAY

    print(f"Analyzing wind energy for coordinates: Latitude {latitude}, Longitude {longitude}")

    # Fetch weather data
    weather = get_processed_weather_data(latitude, longitude, "2022-01-01", "2022-12-31")
    if weather is None:
        print("Failed to fetch weather data.")
        return {}

    # Select the wind speed column closest to the turbine's hub height
    available_heights = [10, 100]
    closest_height = min(available_heights, key=lambda x: abs(x - WIND_TURBINE.hub_height))
    
    print(f"Using wind speed data from {closest_height}m for {WIND_TURBINE.hub_height}m hub height")

    # Create a new DataFrame with the selected wind speed data
    weather_selected = pd.DataFrame({
        ('wind_speed', WIND_TURBINE.hub_height): weather[('wind_speed', closest_height)],
        ('temperature', 2): weather[('temperature', 2)],
        ('pressure', 0): weather[('pressure', 0)],
        ('roughness_length', 0): weather[('roughness_length', 0)]
    })

    # Print average wind speed
    print(f"Average wind speed for coordinates ({latitude}, {longitude}): {weather_selected[('wind_speed', WIND_TURBINE.hub_height)].mean():.2f} m/s")

    # ModelChain setup and run
    mc = ModelChain(WIND_TURBINE).run_model(weather_selected)
    WIND_TURBINE.power_output = mc.power_output

    # Calculate daily energy output
    daily_generated = WIND_TURBINE.power_output.resample('D').sum() / 1e6  # Convert to MWh

    # Sort daily output for analysis
    sorted_daily_generated = daily_generated.sort_values()

    # Print some statistics about the daily output
    print(f"Daily output statistics for coordinates ({latitude}, {longitude}):")
    print(sorted_daily_generated.describe())

    if cutoff_day >= len(sorted_daily_generated):
        print(f"cutoff_day ({cutoff_day}) exceeds the number of available data days ({len(sorted_daily_generated)}).")
        return {}

    # Calculate required wind turbines
    required_turbines = math.ceil(daily_usage / (sorted_daily_generated.iloc[cutoff_day] * 1000))

    # Calculate gas input and fraction
    annual_demand = 365 * daily_usage
    gas_input = max(0, (cutoff_day * demand_in_kw * 24) - sum(sorted_daily_generated.iloc[:cutoff_day]) * required_turbines * 1000)
    gas_fraction = gas_input / annual_demand if annual_demand > 0 else 0

    # Calculate average capacity factor
    wind_energy_rated = WIND_TURBINE.nominal_power * required_turbines / 1e3  # Total capacity in kW
    wind_energy_generated = sum(sorted_daily_generated) * required_turbines * 1000  # Total energy in kWh
    wind_energy_consumed = (sum(sorted_daily_generated.iloc[:cutoff_day]) + (365-cutoff_day)*sorted_daily_generated.iloc[cutoff_day]) * required_turbines * 1000
    wind_capacity_factor = wind_energy_consumed / (wind_energy_rated * 8760)
    wind_curtailment = (wind_energy_generated - wind_energy_consumed) / wind_energy_generated

    print(f'\nWind Turbine Requirements for coordinates ({latitude}, {longitude}):')
    print(f'Turbine Type: {WIND_TURBINE.turbine_type}')
    print(f'Rated Power: {WIND_TURBINE.nominal_power/1e3:.2f} kW')
    print(f'Wind Capacity Factor: {wind_capacity_factor:.2%}')
    print(f'Wind Curtailment: {wind_curtailment:.2%}')
    print('Required Wind Turbines: ', required_turbines)
    print(f'Total Installed Capacity: {required_turbines * WIND_TURBINE.nominal_power/1e3:.2f} kW')
    print(f'Fraction handled by gas: {gas_fraction:.2%}')

    # Wind + Gas case
    wind_capacity = required_turbines * WIND_TURBINE.nominal_power / 1e3  # in kW
    battery_capacity = demand_in_kw * config.WIND_BATTERY_STORAGE_HOURS  # Battery storage in kWh
    gas_capacity = demand_in_kw
    system_cost = calculate_system_cost(wind_capacity, battery_capacity, gas_capacity)

    # Calculate LCOE
    system_lcoe = calculate_lcoe(system_cost, annual_demand, gas_input)

    # Calculate capex per kW of rated capacity
    system_capex_per_kw = calculate_capex_per_kw(system_cost, demand_in_kw)

    # Print cost analysis results
    print("\nCost Analysis:")
    print(f"WACC: {WACC:.4f}")

    print(f"\nWind + Gas System (with {config.WIND_BATTERY_STORAGE_HOURS}h battery storage):")
    print(f"Total cost: ${system_cost:,.0f}")
    print(f"LCOE: ${system_lcoe:.4f}/kWh")
    print(f"Capex per kW: ${system_capex_per_kw:.2f}/kW")
    print(f"Fraction of energy from wind: {1 - gas_fraction:.2%}")
    
    results = {
        "lcoe": system_lcoe,
        "wind_fraction": 1 - gas_fraction,
        "gas_fraction": gas_fraction,
        "wind_capacity_factor": wind_capacity_factor,
        "wind_curtailment": wind_curtailment,
        "wind_capacity_gw": wind_capacity / 1e6,
        "gas_capacity_gw": gas_capacity / 1e6,
        "capex_per_kw": system_capex_per_kw,
        "energy_generated_data": {
            'wind_generated': sorted_daily_generated * required_turbines * 1000,
            'gas_generated': np.maximum(daily_usage - sorted_daily_generated * required_turbines * 1000, 0)
        },
        "capex_breakdown_data": {
            'components': ['Wind Turbines', 'Battery Storage', 'Gas'],
            'values': [
                wind_capacity * config.WIND_COST_PER_KW / 1e6,  # Convert to millions
                battery_capacity * config.BATTERY_COST_PER_KWH / 1e6,  # Convert to millions
                gas_capacity * config.OCGT_CAPEX_PER_KW / 1e6  # Convert to millions
            ]
        },
        "total_capex": system_cost / 1e6,  # Convert to millions
        "wacc": wacc,
        "number_of_turbines": required_turbines,  # Add this line
        "turbine_type": WIND_TURBINE.turbine_type,  # Add this line
        "turbine_nominal_power": WIND_TURBINE.nominal_power / 1e3  # Add this line, convert to MW
    }

    return results

def plot_energy_generated(sorted_daily_generated, required_turbines, daily_usage, location):
    scaled_daily_generated = sorted_daily_generated * required_turbines * 1000
    gas_generated = np.maximum(daily_usage - scaled_daily_generated, 0)

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.bar(range(len(scaled_daily_generated)), scaled_daily_generated, label='Wind Output', color='blue')
    ax.bar(range(len(gas_generated)), gas_generated, bottom=scaled_daily_generated, 
           label='Gas Output', color='gray')

    ax.set_xlabel('Days (sorted by wind output)')
    ax.set_ylabel('Energy Output (kWh)')
    ax.set_title(f'Daily Energy Output in {location}: Wind vs Gas')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.7)

    plt.tight_layout()
    plt.show()

def plot_capex_breakdown(wind_capacity, battery_capacity, gas_capacity, location):
    wind_capex = wind_capacity * config.WIND_COST_PER_KW
    battery_capex = battery_capacity * config.BATTERY_COST_PER_KWH
    gas_capex = gas_capacity * config.OCGT_CAPEX_PER_KW

    capex_components = [wind_capex, battery_capex, gas_capex]
    labels = ['Wind Turbines', 'Battery Storage', 'Gas']
    colors = ['skyblue', 'lightblue', 'lightgray']

    fig, ax = plt.subplots(figsize=(10, 8))

    wedges, texts, autotexts = ax.pie(capex_components, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)

    ax.set_title(f'Capex Breakdown for Wind + Gas System in {location}')

    ax.legend(wedges, labels,
              title="Components",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1))

    total_capex = sum(capex_components)
    plt.text(0.5, -0.1, f'Total Capex: ${total_capex:,.0f}', ha='center', transform=ax.transAxes)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    latitude = 53
    longitude = -8
    daily_usage = 24000000  # Daily usage in kWh (24 GWh)
    demand_in_kw = 1000000  # Demand in kW (1 GW)
    
    analyze_wind_energy(latitude, longitude, daily_usage, demand_in_kw)
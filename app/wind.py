from windpowerlib import ModelChain, WindTurbine
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import yfinance as yf
from utils import get_coordinates, calculate_wacc, calculate_lcoe, calculate_capex_per_kw
from config import *

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

# Calculate system costs
def calculate_system_cost(wind_capacity, battery_capacity=0, gas_capacity=0):
    wind_cost = wind_capacity * WIND_COST_PER_KW
    battery_cost = battery_capacity * BATTERY_COST_PER_KWH
    gas_cost = gas_capacity * OCGT_CAPEX_PER_KW
    return wind_cost + battery_cost + gas_cost

def analyze_wind_energy(latitude, longitude, daily_usage, demand_in_kw, cutoff_day=CUTOFF_DAY, start_date="2022-01-01", end_date="2022-12-31", plot=False):
    # Remove the get_coordinates function call
    print(f"Analyzing wind energy for coordinates: Latitude {latitude}, Longitude {longitude}")

    # Fetch weather data
    weather = fetch_open_meteo_data(latitude, longitude, start_date, end_date)

    # Print average wind speed
    print(f"Average wind speed for coordinates ({latitude}, {longitude}): {weather[('wind_speed', 10)].mean():.2f} m/s")

    # Specification of wind turbine
    turbine = WindTurbine(turbine_type='E-126/7500', hub_height=135)

    # ModelChain setup and run
    mc = ModelChain(turbine).run_model(weather)
    turbine.power_output = mc.power_output

    # Calculate daily energy output
    daily_output = turbine.power_output.resample('D').sum() / 1e6  # Convert to MWh

    # Sort daily output for analysis
    sorted_daily_output = daily_output.sort_values()

    # Print some statistics about the daily output
    print(f"Daily output statistics for coordinates ({latitude}, {longitude}):")
    print(sorted_daily_output.describe())

    # Calculate required wind turbines
    required_turbines = round(daily_usage / (sorted_daily_output.iloc[cutoff_day] * 1000))

    # Calculate gas input and fraction
    annual_demand = 365 * daily_usage
    gas_input = max(0, (cutoff_day * demand_in_kw * 24) - sum(sorted_daily_output.iloc[:cutoff_day]) * required_turbines * 1000)
    gas_fraction = gas_input / annual_demand if annual_demand > 0 else 0

    # Calculate average capacity factor
    wind_energy_rated = turbine.nominal_power * required_turbines / 1e3  # Total capacity in kW
    wind_energy_generated = sum(sorted_daily_output) * required_turbines * 1000  # Total energy in kWh
    wind_energy_consumed = (sum(sorted_daily_output.iloc[:cutoff_day]) + (365-cutoff_day)*sorted_daily_output.iloc[cutoff_day]) * required_turbines * 1000
    wind_capacity_factor = wind_energy_consumed / (wind_energy_rated * 8760)
    wind_curtailment = (wind_energy_generated - wind_energy_consumed) / wind_energy_generated

    print(f'\nWind Turbine Requirements for coordinates ({latitude}, {longitude}):')
    print(f'Turbine Type: {turbine.turbine_type}')
    print(f'Rated Power: {turbine.nominal_power/1e3:.2f} kW')
    print(f'Wind Capacity Factor: {wind_capacity_factor:.2%}')
    print(f'Wind Curtailment: {wind_curtailment:.2%}')
    print('Required Wind Turbines: ', required_turbines)
    print(f'Total Installed Capacity: {required_turbines * turbine.nominal_power/1e3:.2f} kW')
    print(f'Fraction handled by gas: {gas_fraction:.2%}')

    # Cost analysis
    wacc = calculate_wacc()

    # Wind + Gas case
    wind_capacity = required_turbines * turbine.nominal_power / 1e3  # in kW
    battery_capacity = demand_in_kw * WIND_BATTERY_STORAGE_HOURS  # Battery storage in kWh
    gas_capacity = demand_in_kw
    system_cost = calculate_system_cost(wind_capacity, battery_capacity, gas_capacity)

    # Calculate LCOE
    system_lcoe = calculate_lcoe(system_cost, annual_demand, gas_input)

    # Calculate capex per kW of rated capacity
    system_capex_per_kw = calculate_capex_per_kw(system_cost, demand_in_kw)

    # Print cost analysis results
    print("\nCost Analysis:")
    print(f"WACC: {wacc:.4f}")

    print(f"\nWind + Gas System (with {WIND_BATTERY_STORAGE_HOURS}h battery storage):")
    print(f"Total cost: ${system_cost:,.0f}")
    print(f"LCOE: ${system_lcoe:.4f}/kWh")
    print(f"Capex per kW: ${system_capex_per_kw:.2f}/kW")
    print(f"Fraction of energy from wind: {1 - gas_fraction:.2%}")
    
    if plot:
        plot_energy_output(sorted_daily_output, required_turbines, daily_usage, f"({latitude}, {longitude})")
        plot_capex_breakdown(wind_capacity, battery_capacity, gas_capacity, f"({latitude}, {longitude})")

    results = {
        "lcoe": system_lcoe,
        "wind_fraction": 1 - gas_fraction,
        "gas_fraction": gas_fraction,
        "wind_capacity_factor": wind_capacity_factor,
        "wind_curtailment": wind_curtailment,
        "wind_capacity_gw": wind_capacity / 1e6,
        "gas_capacity_gw": gas_capacity / 1e6,
        "capex_per_kw": system_capex_per_kw,
        "energy_output_data": {
            'wind_output': sorted_daily_output * required_turbines * 1000,
            'gas_output': np.maximum(daily_usage - sorted_daily_output * required_turbines * 1000, 0)
        },
        "capex_breakdown_data": {
            'components': ['Wind Turbines', 'Battery Storage', 'Gas'],
            'values': [
                wind_capacity * WIND_COST_PER_KW / 1e6,  # Convert to millions
                battery_capacity * BATTERY_COST_PER_KWH / 1e6,  # Convert to millions
                gas_capacity * OCGT_CAPEX_PER_KW / 1e6  # Convert to millions
            ]
        },
        "total_capex": system_cost / 1e6,  # Convert to millions
        "wacc": wacc
    }

        # Check if all arrays in energy_output_data have the same length
    wind_output_len = len(results['energy_output_data']['wind_output'])
    gas_output_len = len(results['energy_output_data']['gas_output'])
    if wind_output_len != gas_output_len:
        raise ValueError(f"Mismatch in energy output data lengths: wind_output ({wind_output_len}) != gas_output ({gas_output_len})")

    # Add this debugging code
    wind_output_len = len(results['energy_output_data']['wind_output'])
    gas_output_len = len(results['energy_output_data']['gas_output'])
    print(f"Wind output length: {wind_output_len}")
    print(f"Gas output length: {gas_output_len}")
    if wind_output_len != gas_output_len:
        raise ValueError(f"Mismatch in energy output data lengths: wind_output ({wind_output_len}) != gas_output ({gas_output_len})")

    return results

def plot_energy_output(sorted_daily_output, required_turbines, daily_usage, location):
    scaled_daily_output = sorted_daily_output * required_turbines * 1000
    gas_output = np.maximum(daily_usage - scaled_daily_output, 0)

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.bar(range(len(scaled_daily_output)), scaled_daily_output, label='Wind Output', color='blue')
    ax.bar(range(len(gas_output)), gas_output, bottom=scaled_daily_output, 
           label='Gas Output', color='gray')

    ax.set_xlabel('Days (sorted by wind output)')
    ax.set_ylabel('Energy Output (kWh)')
    ax.set_title(f'Daily Energy Output in {location}: Wind vs Gas')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.7)

    plt.tight_layout()
    plt.show()

def plot_capex_breakdown(wind_capacity, battery_capacity, gas_capacity, location):
    wind_capex = wind_capacity * WIND_COST_PER_KW
    battery_capex = battery_capacity * BATTERY_COST_PER_KWH
    gas_capex = gas_capacity * OCGT_CAPEX_PER_KW

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
    latitude = 29.22
    longitude = -98.75
    daily_usage = 24000000  # Daily usage in kWh (24 GWh)
    demand_in_kw = 1000000  # Demand in kW (1 GW)
    
    analyze_wind_energy(latitude, longitude, daily_usage, demand_in_kw, plot=True)
    
from windpowerlib import ModelChain, WindTurbine
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import yfinance as yf
from utils import get_coordinates, calculate_wacc, calculate_lcoe, calculate_capex_per_kw

# Cost parameters
wind_cost_per_kw = 1300  # $/kW
battery_cost_per_kwh = 250  # $/kWh
generator_cost_per_kw = 800  # $/kW

# Natural Gas parameters
ng_price_per_mmbtu = 20  # €/MMBtu (typical European price)
ng_price_per_kwh = ng_price_per_mmbtu / 293.07  # Convert €/MMBtu to €/kWh

# Open Cycle Gas Turbine (OCGT) parameters
ocgt_efficiency = 0.35  # 35% efficiency for open cycle gas turbine
ocgt_capex_per_kw = 800  # $/kW
ocgt_opex_per_kwh = 0.02  # €/kWh for operation and maintenance

# Project lifetime
project_lifetime = 20  # years

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

def analyze_wind_energy(city, country, daily_usage, demand_in_kw, cutoff_day=50, start_date="2022-01-01", end_date="2022-12-31"):
    # Get coordinates
    coordinates = get_coordinates(city, country)
    if coordinates is None:
        print(f"Could not find coordinates for {city}, {country}")
        return
    
    latitude, longitude = coordinates

    # Fetch weather data
    weather = fetch_open_meteo_data(latitude, longitude, start_date, end_date)

    # Print average wind speed
    print(f"Average wind speed for {city}: {weather[('wind_speed', 10)].mean():.2f} m/s")

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
    print(f"Daily output statistics for {city}:")
    print(sorted_daily_output.describe())

    # Calculate required wind turbines
    if sorted_daily_output.iloc[0] > 0:
        required_turbines_no_generators = round(daily_usage / (sorted_daily_output.iloc[0] * 1000))
    else:
        required_turbines_no_generators = float('inf')
        print("Warning: There are days with zero wind output. Infinite turbines would be required without generators.")

    required_turbines_with_generators = round(daily_usage / (sorted_daily_output.iloc[cutoff_day] * 1000))

    # Calculate generator input and fraction
    annual_demand = 365 * daily_usage
    generator_input = (50 * demand_in_kw * 24) - sum(sorted_daily_output.iloc[:cutoff_day]) * required_turbines_with_generators * 1000
    generator_fraction = generator_input / annual_demand

    # Calculate average capacity factor (with generators)
    total_energy_output = sum(sorted_daily_output) * required_turbines_with_generators * 1000  # Total energy in kWh
    total_capacity = turbine.nominal_power * required_turbines_with_generators / 1e3  # Total capacity in kW
    capacity_factor = total_energy_output / (total_capacity * 24 * 365)

    # Print results
    print(f'\nWind Turbine Requirements for {city}:')
    print(f'Turbine Type: {turbine.turbine_type}')
    print(f'Rated Power: {turbine.nominal_power/1e3:.2f} kW')
    print(f'Average Capacity Factor (with generators): {capacity_factor:.2%}')
    if required_turbines_no_generators != float('inf'):
        print('Required Wind Turbines (no generators): ', required_turbines_no_generators)
        print(f'Total Installed Capacity (no generators): {required_turbines_no_generators * turbine.nominal_power/1e3:.2f} kW')
    else:
        print('Required Wind Turbines (no generators): Infinite (due to days with no wind)')
    print('Required Wind Turbines (with generators): ', required_turbines_with_generators)
    print(f'Total Installed Capacity (with generators): {required_turbines_with_generators * turbine.nominal_power/1e3:.2f} kW')
    print(f'Fraction handled by generators: {generator_fraction:.2%}')

    # Cost analysis
    wacc = calculate_wacc()

    # Calculate system costs
    def calculate_system_cost(wind_capacity, battery_capacity=0, generator_capacity=0):
        wind_cost = wind_capacity * wind_cost_per_kw
        battery_cost = battery_capacity * battery_cost_per_kwh
        generator_cost = generator_capacity * generator_cost_per_kw
        return wind_cost + battery_cost + generator_cost

    # Pure wind case
    pure_wind_capacity = required_turbines_no_generators * turbine.nominal_power / 1e3  # in kW
    battery_capacity = demand_in_kw * 12  # 12 hours of storage in kWh
    pure_wind_cost = calculate_system_cost(pure_wind_capacity, battery_capacity)

    # Generator supported case
    supported_wind_capacity = required_turbines_with_generators * turbine.nominal_power / 1e3  # in kW
    generator_capacity = demand_in_kw
    supported_system_cost = calculate_system_cost(supported_wind_capacity, battery_capacity, generator_capacity)

    # Calculate annual energy used (which is equal to the demand)
    annual_energy_used = 365 * daily_usage  # in kWh

    # Calculate annual energy generated for wind systems
    pure_wind_energy_generated = sum(daily_output) * required_turbines_no_generators * 1e6  # in kWh
    supported_wind_energy_generated = sum(daily_output) * required_turbines_with_generators * 1e6  # in kWh

    # Wind energy used is the minimum of generated and demanded
    pure_wind_energy_used = min(annual_energy_used, pure_wind_energy_generated)
    supported_wind_energy_used = min(annual_energy_used - generator_input, supported_wind_energy_generated)

    # Calculate LCOE
    pure_wind_lcoe = calculate_lcoe(pure_wind_cost, annual_energy_used)
    supported_system_lcoe = calculate_lcoe(supported_system_cost, annual_energy_used, generator_input)

    # Natural Gas Case (OCGT)
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

    # Calculate capex per kW of rated capacity
    pure_wind_capex_per_kw = calculate_capex_per_kw(pure_wind_cost, demand_in_kw)
    supported_system_capex_per_kw = calculate_capex_per_kw(supported_system_cost, demand_in_kw)

    # Print cost analysis results
    print("\nCost Analysis:")
    print(f"WACC: {wacc:.4f}")

    # Convert to USD for comparison
    usd_eur_rate = 1.1  # Assume 1 EUR = 1.1 USD

    print(f"\nNatural Gas System (OCGT):")
    print(f"LCOE: ${ocgt_lcoe * usd_eur_rate:.4f}/kWh")
    print(f"Capex per kW: ${ocgt_capex_per_kw:.2f}/kW")

    print(f"\nPure Wind System (with 24h battery storage):")
    if required_turbines_no_generators != float('inf'):
        print(f"Total cost: ${pure_wind_cost:,.0f}")
        print(f"LCOE: ${pure_wind_lcoe:.4f}/kWh")
        print(f"Capex per kW: ${pure_wind_capex_per_kw:.2f}/kW")
        pure_wind_capacity_factor = pure_wind_energy_used / (pure_wind_capacity * 8760)
        print(f"Wind Capacity Factor: {pure_wind_capacity_factor:.2%}")
    else:
        print("Pure wind system is not feasible due to days with zero wind output.")

    print(f"\nGenerator Supported System (with 24h battery storage):")
    print(f"Total cost: ${supported_system_cost:,.0f}")
    print(f"LCOE: ${supported_system_lcoe:.4f}/kWh")
    print(f"Capex per kW: ${supported_system_capex_per_kw:.2f}/kW")
    supported_wind_capacity_factor = supported_wind_energy_used / (supported_wind_capacity * 8760)
    print(f"Wind Capacity Factor: {supported_wind_capacity_factor:.2%}")
    print(f"Fraction of energy from wind: {supported_wind_energy_used / annual_energy_used:.2%}")

    # Plotting
    plot_energy_output(sorted_daily_output, required_turbines_with_generators, daily_usage, city)
    plot_capex_breakdown(supported_wind_capacity, battery_capacity, generator_capacity, city)

def plot_energy_output(sorted_daily_output, required_turbines, daily_usage, city):
    scaled_daily_output = sorted_daily_output * required_turbines * 1000
    generator_output = np.maximum(daily_usage - scaled_daily_output, 0)

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.bar(range(len(scaled_daily_output)), scaled_daily_output, label='Wind Output', color='blue')
    ax.bar(range(len(generator_output)), generator_output, bottom=scaled_daily_output, 
           label='Generator Output', color='gray')

    ax.set_xlabel('Days (sorted by wind output)')
    ax.set_ylabel('Energy Output (kWh)')
    ax.set_title(f'Daily Energy Output in {city}: Wind vs Generator')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.7)

    plt.tight_layout()
    plt.show()

def plot_capex_breakdown(wind_capacity, battery_capacity, generator_capacity, city):
    wind_capex = wind_capacity * wind_cost_per_kw
    battery_capex = battery_capacity * battery_cost_per_kwh
    generator_capex = generator_capacity * generator_cost_per_kw

    capex_components = [wind_capex, battery_capex, generator_capex]
    labels = ['Wind Turbines', 'Battery Storage', 'Generator']
    colors = ['skyblue', 'lightblue', 'lightgray']

    fig, ax = plt.subplots(figsize=(10, 8))

    wedges, texts, autotexts = ax.pie(capex_components, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)

    ax.set_title(f'Capex Breakdown for Wind + Generator System in {city}')

    ax.legend(wedges, labels,
              title="Components",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1))

    total_capex = sum(capex_components)
    plt.text(0.5, -0.1, f'Total Capex: ${total_capex:,.0f}', ha='center', transform=ax.transAxes)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    city = "San Antonio"
    country = "United States"
    daily_usage = 24000000  # Daily usage in kWh (24 GWh)
    demand_in_kw = 1000000  # Demand in kW (1 GW)
    
    analyze_wind_energy(city, country, daily_usage, demand_in_kw)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from solar import simulate_solar_output, calculate_daily_output as calculate_solar_daily_output
from wind import fetch_open_meteo_data, WindTurbine, ModelChain
from utils import get_coordinates, calculate_wacc, calculate_lcoe, calculate_capex_per_kw

# Constants
SOLAR_COST_PER_KW = 550
WIND_COST_PER_KW = 1300
BATTERY_COST_PER_KWH = 250
GENERATOR_COST_PER_KW = 800
PROJECT_LIFETIME = 20

def simulate_wind_output(weather_data):
    turbine = WindTurbine(turbine_type='E-126/7500', hub_height=135)
    mc = ModelChain(turbine).run_model(weather_data)
    return mc.power_output / turbine.nominal_power  # Normalize to per kW output

def calculate_wind_daily_output(wind_output):
    return wind_output.resample('D').sum()  # Daily sum of kWh per kW of capacity

def analyze_wind_solar_system(city, country, demand_in_kw, daily_usage, gamma=0.5, cutoff_day=50):
    coordinates = get_coordinates(city, country)
    if coordinates is None:
        print(f"Could not find coordinates for {city}, {country}")
        return
    
    latitude, longitude = coordinates
    print(f"Coordinates: {latitude}, {longitude}")

    # Simulate solar output
    solar_output = simulate_solar_output(latitude, longitude)
    solar_daily = pd.Series(calculate_solar_daily_output(solar_output))
    print(f"Solar daily output (first 5 days): {solar_daily.head()}")

    # Fetch weather data and simulate wind output
    weather_data = fetch_open_meteo_data(latitude, longitude, "2022-01-01", "2022-12-31")
    wind_output = simulate_wind_output(weather_data)
    wind_daily = calculate_wind_daily_output(wind_output)
    print(f"Wind daily output (first 5 days): {wind_daily.head()}")

    # After simulating solar and wind output
    print(f"Number of days in solar data: {len(solar_daily)}")
    print(f"Number of days in wind data: {len(wind_daily)}")
    
    # Check for NaN or zero values
    print(f"Number of NaN values in solar data: {solar_daily.isna().sum()}")
    print(f"Number of zero values in solar data: {(solar_daily == 0).sum()}")
    print(f"Number of NaN values in wind data: {wind_daily.isna().sum()}")
    print(f"Number of zero values in wind data: {(wind_daily == 0).sum()}")

    # Ensure both series have the same length and index
    start_date = "2022-01-01"
    end_date = "2022-12-31"
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    solar_daily = pd.Series(solar_daily.values, index=date_range[:len(solar_daily)])
    wind_daily = wind_daily.reindex(date_range)

    print(f"Final number of days in solar data: {len(solar_daily)}")
    print(f"Final number of days in wind data: {len(wind_daily)}")

    # Combine daily outputs
    combined_daily = solar_daily * gamma + wind_daily * (1 - gamma)
    print(f"Number of days in combined data: {len(combined_daily)}")
    print(f"Number of NaN values in combined data: {combined_daily.isna().sum()}")
    print(f"Number of zero values in combined data: {(combined_daily == 0).sum()}")

    # Sort the combined daily output
    sorted_daily_output = combined_daily.sort_values(ascending=True)

    # Calculate system requirements
    print(f"Cutoff day value: {sorted_daily_output.iloc[cutoff_day]}")
    required_capacity = daily_usage / sorted_daily_output.iloc[cutoff_day]
    print(f"Required capacity: {required_capacity}")

    generator_energy = max(0, (50 * demand_in_kw * 24) - sum(sorted_daily_output.iloc[:cutoff_day]) * required_capacity)
    print(f"Generator energy: {generator_energy}")

    annual_demand = 365 * daily_usage
    generator_fraction = generator_energy / annual_demand
    print(f"Generator fraction: {generator_fraction}")

    # Calculate costs
    solar_capacity = required_capacity * gamma
    wind_capacity = required_capacity * (1 - gamma)
    battery_capacity = demand_in_kw * 24  # 24 hours of storage

    system_cost = (
        solar_capacity * SOLAR_COST_PER_KW +
        wind_capacity * WIND_COST_PER_KW +
        battery_capacity * BATTERY_COST_PER_KWH +
        demand_in_kw * GENERATOR_COST_PER_KW
    )
    print(f"System cost: {system_cost}")

    # Calculate LCOE
    wacc = calculate_wacc()
    lcoe = calculate_lcoe(system_cost, annual_demand, generator_energy)
    capex_per_kw = calculate_capex_per_kw(system_cost, demand_in_kw)

    # Calculate capacity factors
    solar_energy_output = sum(solar_daily) * solar_capacity
    wind_energy_output = sum(wind_daily) * wind_capacity
    solar_capacity_factor = solar_energy_output / (solar_capacity * 24 * 365)
    wind_capacity_factor = wind_energy_output / (wind_capacity * 24 * 365)

    # Print results
    print(f"\nWind-Solar Hybrid System Analysis for {city}:")
    print(f"Gamma (solar fraction): {gamma:.2f}")
    print(f"Total Required Capacity: {required_capacity:.2f} kW")
    print(f"Solar Capacity: {solar_capacity:.2f} kW")
    print(f"Wind Capacity: {wind_capacity:.2f} kW")
    print(f"Battery Capacity: {battery_capacity:.2f} kWh")
    print(f"Generator Capacity: {demand_in_kw:.2f} kW")
    print(f"Solar Capacity Factor: {solar_capacity_factor:.2%}")
    print(f"Wind Capacity Factor: {wind_capacity_factor:.2%}")
    print(f"Fraction handled by generator: {generator_fraction:.2%}")
    print(f"WACC: {wacc:.2%}")
    print(f"LCOE: ${lcoe:.4f}/kWh")
    print(f"CAPEX per kW: ${capex_per_kw:.2f}/kW")

    # Plot energy output
    plot_energy_output(solar_daily, wind_daily, required_capacity, demand_in_kw, cutoff_day, city, gamma)
    
    # Plot capex breakdown
    plot_capex_breakdown(solar_capacity, wind_capacity, battery_capacity, demand_in_kw, city)

def plot_energy_output(solar_daily, wind_daily, required_capacity, demand_in_kw, cutoff_day, city, gamma):
    solar_output = solar_daily.fillna(0) * required_capacity * gamma
    wind_output = wind_daily.fillna(0) * required_capacity * (1 - gamma)
    combined_output = solar_output + wind_output
    
    sorted_indices = combined_output.argsort()
    
    solar_output_sorted = solar_output.iloc[sorted_indices]
    wind_output_sorted = wind_output.iloc[sorted_indices]
    combined_output_sorted = combined_output.iloc[sorted_indices]
    generator_output = np.maximum(demand_in_kw * 24 - combined_output_sorted, 0)

    # Ensure we're only plotting 365 days
    num_days = 365
    solar_output_sorted = solar_output_sorted[:num_days]
    wind_output_sorted = wind_output_sorted[:num_days]
    combined_output_sorted = combined_output_sorted[:num_days]
    generator_output = generator_output[:num_days]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(range(num_days), solar_output_sorted, label='Solar Output', color='yellow')
    ax.bar(range(num_days), wind_output_sorted, bottom=solar_output_sorted, label='Wind Output', color='skyblue')
    ax.bar(range(num_days), generator_output, bottom=combined_output_sorted, 
           label='Generator Output', color='gray')
    ax.axhline(y=demand_in_kw * 24, color='r', linestyle='--', label='Daily Demand')
    ax.set_xlabel('Days (sorted by combined output)')
    ax.set_ylabel('Energy Output (kWh)')
    ax.set_title(f'Daily Energy Output in {city}: Solar, Wind, and Generator')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_xlim(0, num_days - 1)  # Set x-axis limits explicitly
    plt.tight_layout()
    plt.show()

def plot_capex_breakdown(solar_capacity, wind_capacity, battery_capacity, generator_capacity, city):
    solar_capex = solar_capacity * SOLAR_COST_PER_KW
    wind_capex = wind_capacity * WIND_COST_PER_KW
    battery_capex = battery_capacity * BATTERY_COST_PER_KWH
    generator_capex = generator_capacity * GENERATOR_COST_PER_KW

    capex_components = [solar_capex, wind_capex, battery_capex, generator_capex]
    labels = ['Solar Panels', 'Wind Turbines', 'Battery Storage', 'Generator']
    colors = ['yellow', 'skyblue', 'lightblue', 'lightgray']

    fig, ax = plt.subplots(figsize=(10, 8))
    wedges, texts, autotexts = ax.pie(capex_components, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax.set_title(f'Capex Breakdown for Wind-Solar Hybrid System in {city}')
    ax.legend(wedges, labels, title="Components", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    total_capex = sum(capex_components)
    plt.text(0.5, -0.1, f'Total Capex: ${total_capex:,.0f}', ha='center', transform=ax.transAxes)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    city = "Waterford"
    country = "Ireland"
    demand_in_kw = 1000000  # 1 GW
    daily_usage = 24000000  # 24 GWh
    gamma = 0.5  # Equal split between wind and solar
    
    analyze_wind_solar_system(city, country, demand_in_kw, daily_usage, gamma)
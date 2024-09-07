from pvlib import pvsystem, modelchain, location, iotools
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from utils import get_coordinates, calculate_wacc, calculate_lcoe, calculate_capex_per_kw

# Constants
SOLAR_COST_PER_KW = 550
BATTERY_COST_PER_KWH = 250
GENERATOR_COST_PER_KW = 800
SOLAR_PANEL_EFFICIENCY = 0.2
SOLAR_PANEL_DENSITY = 0.4
PROJECT_LIFETIME = 20

def get_location_data(city_name, country_name, locations):
    if city_name in locations:
        latitude = locations[city_name]['latitude']
        longitude = locations[city_name]['longitude']
        city = locations[city_name]['name']
    else:
        coordinates = get_coordinates(city_name, country_name)
        if coordinates:
            latitude, longitude = coordinates
            city = city_name
        else:
            raise ValueError(f"Could not find coordinates for {city_name}, {country_name}")
    
    return latitude, longitude, city

def simulate_solar_output(latitude, longitude):
    array_kwargs_tracker = dict(
        module_parameters=dict(pdc0=1, gamma_pdc=-0.004),
        temperature_model_parameters=dict(a=-3.56, b=-0.075, deltaT=3)
    )

    arrays = [
        pvsystem.Array(pvsystem.SingleAxisTrackerMount(),
                       **array_kwargs_tracker),
    ]

    loc = location.Location(latitude, longitude)
    system = pvsystem.PVSystem(arrays=arrays, inverter_parameters=dict(pdc0=1))
    mc = modelchain.ModelChain(system, loc, aoi_model='physical', spectral_model='no_loss')
    weather = iotools.get_pvgis_tmy(latitude, longitude)[0]
    mc.run_model(weather)

    return mc.results.ac

def calculate_daily_output(ac):
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

    if daily_energy_sum > 0:
        daily_output.append(daily_energy_sum)

    return sorted(daily_output)

def calculate_system_requirements(daily_output, daily_usage, demand_in_kw, cutoff_day):
    required_solar_array_no_generators = round(daily_usage / (daily_output[0]))
    required_solar_array_with_generators = round(daily_usage / (daily_output[cutoff_day:][0]))
    generator_energy = ((50 * demand_in_kw * 24) - sum(daily_output[:cutoff_day])*required_solar_array_with_generators)
    annual_demand = 365 * daily_usage
    generator_fraction = generator_energy / annual_demand

    return required_solar_array_no_generators, required_solar_array_with_generators, generator_energy, generator_fraction

def calculate_system_cost(solar_capacity, battery_capacity=0, generator_capacity=0):
    solar_cost = solar_capacity * SOLAR_COST_PER_KW
    battery_cost = battery_capacity * BATTERY_COST_PER_KWH
    generator_cost = generator_capacity * GENERATOR_COST_PER_KW
    return solar_cost + battery_cost + generator_cost

def calculate_solar_area(capacity_kw):
    area_m2 = (capacity_kw * 1000) / (SOLAR_PANEL_EFFICIENCY * SOLAR_PANEL_DENSITY * 1000)
    area_km2 = area_m2 / 1_000_000
    ireland_area_km2 = 84421
    percentage_of_ireland = (area_km2 / ireland_area_km2) * 100
    return area_km2, percentage_of_ireland

def plot_energy_output(daily_output, required_solar_array, demand_in_kw, cutoff_day, city_name):
    scaled_daily_output = np.array(daily_output) * required_solar_array
    generator_output = np.zeros_like(scaled_daily_output)
    generator_output[:cutoff_day] = demand_in_kw * 24 - scaled_daily_output[:cutoff_day]
    generator_output = np.maximum(generator_output, 0)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(range(len(scaled_daily_output)), scaled_daily_output, label='Solar Output', color='yellow')
    ax.bar(range(len(generator_output)), generator_output, bottom=scaled_daily_output, 
           label='Generator Output', color='gray')
    ax.set_xlabel('Days (sorted by solar output)')
    ax.set_ylabel('Energy Output (kWh)')
    ax.set_title(f'Daily Energy Output in {city_name}: Solar vs Generator')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()

def plot_capex_breakdown(solar_capacity, battery_capacity, generator_capacity, city_name):
    solar_capex = solar_capacity * SOLAR_COST_PER_KW
    battery_capex = battery_capacity * BATTERY_COST_PER_KWH
    generator_capex = generator_capacity * GENERATOR_COST_PER_KW

    capex_components = [solar_capex, battery_capex, generator_capex]
    labels = ['Solar Panels', 'Battery Storage', 'Generator']
    colors = ['yellow', 'lightblue', 'lightgray']

    fig, ax = plt.subplots(figsize=(10, 8))
    wedges, texts, autotexts = ax.pie(capex_components, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax.set_title(f'Capex Breakdown for Solar + Generator System in {city_name}')
    ax.legend(wedges, labels, title="Components", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    total_capex = sum(capex_components)
    plt.text(0.5, -0.1, f'Total Capex: ${total_capex:,.0f}', ha='center', transform=ax.transAxes)
    plt.tight_layout()
    plt.show()

def analyze_solar_system(city_name, country_name, demand_in_kw, daily_usage, cutoff_day=50):
    locations = {
        'Cork': {'latitude': 51.89, 'longitude': -8.47, 'name': 'Cork'},
        'Waterford': {'latitude': 52.26, 'longitude': -7.12, 'name': 'Waterford'},
        'Dublin': {'latitude': 53.35, 'longitude': -6.26, 'name': 'Dublin'},
        'San Antonio': {'latitude': 29.22, 'longitude': -98.75, 'name': 'San Antonio'},
        'Tuscon': {'latitude': 32.43, 'longitude': -111.1, 'name': 'Tuscon'}
    }

    latitude, longitude, city = get_location_data(city_name, country_name, locations)
    print(f"Coordinates for {city_name}: Latitude {latitude}, Longitude {longitude}")

    ac = simulate_solar_output(latitude, longitude)
    daily_output = calculate_daily_output(ac)

    required_solar_array_no_generators, required_solar_array_with_generators, generator_energy, generator_fraction = calculate_system_requirements(daily_output, daily_usage, demand_in_kw, cutoff_day)

    battery_capacity = demand_in_kw * 24
    pure_solar_cost = calculate_system_cost(required_solar_array_no_generators, battery_capacity)
    supported_system_cost = calculate_system_cost(required_solar_array_with_generators, battery_capacity, demand_in_kw)

    annual_energy_used = 365 * daily_usage
    pure_solar_energy_generated = sum(daily_output) * required_solar_array_no_generators
    supported_solar_energy_generated = sum(daily_output) * required_solar_array_with_generators

    pure_solar_energy_used = min(annual_energy_used, pure_solar_energy_generated)
    supported_solar_energy_used = min(annual_energy_used - generator_energy, supported_solar_energy_generated)

    wacc = calculate_wacc()
    pure_solar_lcoe = calculate_lcoe(pure_solar_cost, annual_energy_used)
    supported_system_lcoe = calculate_lcoe(supported_system_cost, annual_energy_used, generator_energy)

    pure_solar_capex_per_kw = calculate_capex_per_kw(pure_solar_cost, demand_in_kw)
    supported_system_capex_per_kw = calculate_capex_per_kw(supported_system_cost, demand_in_kw)

    print("\nCost Analysis:")
    print(f"WACC: {wacc:.4f}")

    print(f"\nPure Solar System (with 24h battery storage):")
    print(f"Total cost: ${pure_solar_cost:,.0f}")
    print(f"LCOE: ${pure_solar_lcoe:.4f}/kWh")
    print(f"Capex per kW: ${pure_solar_capex_per_kw:.2f}/kW")
    print(f"Solar Capacity Factor: {pure_solar_energy_used / pure_solar_energy_generated:.2%}")
    area_km2, percentage = calculate_solar_area(required_solar_array_no_generators)
    print(f"Required solar area: {area_km2:.2f} km² ({percentage:.2f}% of Ireland's land area)")

    print(f"\nGenerator Supported System (with 24h battery storage):")
    print(f"Total cost: ${supported_system_cost:,.0f}")
    print(f"LCOE: ${supported_system_lcoe:.4f}/kWh")
    print(f"Capex per kW: ${supported_system_capex_per_kw:.2f}/kW")
    print(f"Solar Capacity Factor: {supported_solar_energy_used / supported_solar_energy_generated:.2%}")
    print(f"Fraction of energy from solar: {supported_solar_energy_used / annual_energy_used:.2%}")
    area_km2, percentage = calculate_solar_area(required_solar_array_with_generators)
    print(f"Required solar area: {area_km2:.2f} km² ({percentage:.2f}% of Ireland's land area)")

    plot_energy_output(daily_output, required_solar_array_with_generators, demand_in_kw, cutoff_day, city_name)
    plot_capex_breakdown(required_solar_array_with_generators, battery_capacity, demand_in_kw, city_name)

if __name__ == "__main__":
    city_name = 'Boston'
    country_name = 'United States'
    demand_in_kw = 1000000
    daily_usage = 24000000
    analyze_solar_system(city_name, country_name, demand_in_kw, daily_usage)
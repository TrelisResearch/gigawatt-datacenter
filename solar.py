from config import *

from pvlib import pvsystem, modelchain, location, iotools
import numpy as np
from utils import get_coordinates, calculate_wacc, calculate_lcoe, calculate_capex_per_kw

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

    for hourly_output in ac:  # Modified this line
        if hour_counter < 24:
            daily_energy_sum += hourly_output
            hour_counter += 1
        else:
            daily_output.append(daily_energy_sum)
            daily_energy_sum = hourly_output
            hour_counter = 1

    if daily_energy_sum > 0:
        daily_output.append(daily_energy_sum)

    return sorted(daily_output)

def calculate_system_requirements(daily_output, daily_usage, demand_in_kw, cutoff_day):
    required_solar_array_no_gass = round(daily_usage / (daily_output[0]))
    required_solar_array_with_gass = round(daily_usage / (daily_output[cutoff_day:][0]))
    gas_energy = ((50 * demand_in_kw * 24) - sum(daily_output[:cutoff_day])*required_solar_array_with_gass)
    annual_demand = 365 * daily_usage
    gas_fraction = gas_energy / annual_demand

    return required_solar_array_no_gass, required_solar_array_with_gass, gas_energy, gas_fraction

def calculate_system_cost(solar_capacity, battery_capacity=0, gas_capacity=0):
    solar_cost = solar_capacity * SOLAR_COST_PER_KW
    battery_cost = battery_capacity * BATTERY_COST_PER_KWH
    gas_cost = gas_capacity * OCGT_CAPEX_PER_KW
    return solar_cost + battery_cost + gas_cost

def calculate_solar_area(capacity_kw):
    area_m2 = (capacity_kw * 1000) / (SOLAR_PANEL_EFFICIENCY * SOLAR_PANEL_DENSITY * 1000)
    area_km2 = area_m2 / 1_000_000
    ireland_area_km2 = 84421
    percentage_of_ireland = (area_km2 / ireland_area_km2) * 100
    return area_km2, percentage_of_ireland

def analyze_solar_system(city_name, country_name, demand_in_kw, daily_usage, cutoff_day=CUTOFF_DAY):
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

    required_solar_array_no_gass, required_solar_array_with_gass, gas_energy, gas_fraction = calculate_system_requirements(daily_output, daily_usage, demand_in_kw, CUTOFF_DAY)

    battery_capacity = demand_in_kw * SOLAR_BATTERY_STORAGE_HOURS
    pure_solar_cost = calculate_system_cost(required_solar_array_no_gass, battery_capacity)
    supported_system_cost = calculate_system_cost(required_solar_array_with_gass, battery_capacity, demand_in_kw)

    annual_energy_used = 365 * daily_usage
    pure_solar_energy_generated = sum(daily_output) * required_solar_array_no_gass
    supported_solar_energy_generated = sum(daily_output) * required_solar_array_with_gass

    pure_solar_energy_used = min(annual_energy_used, pure_solar_energy_generated)
    supported_solar_energy_used = min(annual_energy_used - gas_energy, supported_solar_energy_generated)

    wacc = calculate_wacc()
    pure_solar_lcoe = calculate_lcoe(pure_solar_cost, annual_energy_used)
    supported_system_lcoe = calculate_lcoe(supported_system_cost, annual_energy_used, gas_energy)

    pure_solar_capex_per_kw = calculate_capex_per_kw(pure_solar_cost, demand_in_kw)
    supported_system_capex_per_kw = calculate_capex_per_kw(supported_system_cost, demand_in_kw)

    # Calculate capacity factors
    pure_solar_capacity_factor = pure_solar_energy_used / (required_solar_array_no_gass * 24 * 365)
    supported_solar_capacity_factor = supported_solar_energy_used / (required_solar_array_with_gass * 24 * 365)

    print("\nCost Analysis:")
    print(f"WACC: {wacc:.4f}")

    print(f"\nPure Solar System (with {SOLAR_BATTERY_STORAGE_HOURS}h battery storage):")
    print(f"Total cost: ${pure_solar_cost:,.0f}")
    print(f"LCOE: ${pure_solar_lcoe:.4f}/kWh")
    print(f"Capex per kW: ${pure_solar_capex_per_kw:.2f}/kW")
    print(f"Solar Capacity Factor: {pure_solar_capacity_factor:.2%}")
    area_km2, percentage = calculate_solar_area(required_solar_array_no_gass)
    print(f"Required solar area: {area_km2:.2f} km² ({percentage:.2f}% of Ireland's land area)")

    print(f"\nGas Supported System (with {SOLAR_BATTERY_STORAGE_HOURS}h battery storage):")
    print(f"Total cost: ${supported_system_cost:,.0f}")
    print(f"LCOE: ${supported_system_lcoe:.4f}/kWh")
    print(f"Capex per kW: ${supported_system_capex_per_kw:.2f}/kW")
    print(f"Solar Capacity Factor: {supported_solar_capacity_factor:.2%}")
    print(f"Fraction of energy from solar: {supported_solar_energy_used / annual_energy_used:.2%}")
    area_km2, percentage = calculate_solar_area(required_solar_array_with_gass)
    print(f"Required solar area: {area_km2:.2f} km² ({percentage:.2f}% of Ireland's land area)")

    # Instead of plotting, return the data needed for plots
    energy_output_data = {
        'solar_output': np.array(daily_output) * required_solar_array_with_gass,
        'gas_output': np.maximum(demand_in_kw * 24 - np.array(daily_output) * required_solar_array_with_gass, 0)
    }
    
    capex_breakdown_data = {
        'components': ['Solar Panels', 'Battery Storage', 'Gas'],
        'values': [
            required_solar_array_with_gass * SOLAR_COST_PER_KW / 1e6,  # Convert to millions
            battery_capacity * BATTERY_COST_PER_KWH / 1e6,  # Convert to millions
            demand_in_kw * OCGT_CAPEX_PER_KW / 1e6  # Convert to millions
        ]
    }

    return {
        "lcoe": supported_system_lcoe,
        "solar_fraction": supported_solar_energy_used / annual_energy_used,
        "gas_fraction": gas_fraction,
        "capacity_factor": supported_solar_capacity_factor,
        "solar_area_km2": area_km2,
        "solar_area_percentage": percentage,
        "solar_capacity_gw": required_solar_array_with_gass / 1e6,
        "gas_capacity_gw": demand_in_kw / 1e6,
        "capex_per_kw": supported_system_capex_per_kw / 1e3,  # Convert to millions
        "energy_output_data": energy_output_data,
        "capex_breakdown_data": capex_breakdown_data,
        "total_capex": supported_system_cost / 1e6  # Convert to millions
    }

if __name__ == "__main__":
    city = "Waterford"
    country = "Ireland"
    demand_in_kw = 1000000  # 1 GW
    daily_usage = 24000000  # 24 GWh
    
    analyze_solar_system(city, country, demand_in_kw, daily_usage)
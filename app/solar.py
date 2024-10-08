from runtime_config import config

from pvlib import pvsystem, modelchain, location, iotools
import numpy as np
from utils import get_coordinates, calculate_wacc, calculate_lcoe, calculate_capex_per_kw
import matplotlib.pyplot as plt

WACC = calculate_wacc()

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

def simulate_solar_generated(latitude, longitude):
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

    # Calculate average annual insolation (GHI)
    average_annual_insolation = weather['ghi'].mean()

    return mc.results.ac, average_annual_insolation

def calculate_daily_generated(ac):
    daily_energy_sum = 0
    hour_counter = 0
    daily_generated = []

    for hourly_generated in ac:
        if hour_counter < 24:
            daily_energy_sum += hourly_generated
            hour_counter += 1
        else:
            daily_generated.append(daily_energy_sum)
            daily_energy_sum = hourly_generated
            hour_counter = 1

    if daily_energy_sum > 0:
        daily_generated.append(daily_energy_sum)

    return daily_generated

def calculate_system_requirements(daily_generated, daily_usage, demand_in_kw, cutoff_day):
    required_solar_array = round(daily_usage / (daily_generated[cutoff_day]))
    gas_energy_generated = np.sum(np.maximum(0, daily_usage - np.array(daily_generated[:cutoff_day]) * required_solar_array))
    gas_energy_consumed = gas_energy_generated
    solar_energy_generated = (sum(daily_generated[:cutoff_day]) + sum(daily_generated[cutoff_day:]))*required_solar_array
    solar_energy_consumed = (sum(daily_generated[:cutoff_day]) + daily_generated[cutoff_day]*(365-cutoff_day))*required_solar_array
    annual_demand = 365 * daily_usage
    gas_fraction = gas_energy_generated / annual_demand

    return required_solar_array, gas_energy_generated, solar_energy_generated, solar_energy_consumed, gas_energy_consumed, gas_fraction

def calculate_system_cost(solar_capacity, battery_capacity=0, gas_capacity=0, cutoff_day=None):
    solar_cost = solar_capacity * config.SOLAR_COST_PER_KW
    battery_cost = battery_capacity * config.BATTERY_COST_PER_KWH
    gas_cost = 0 if cutoff_day == 0 else gas_capacity * config.OCGT_CAPEX_PER_KW
    return solar_cost + battery_cost + gas_cost

def calculate_solar_area(capacity_kw):
    area_m2 = (capacity_kw * 1000) / (config.SOLAR_IRRADIANCE * config.SOLAR_PANEL_EFFICIENCY * config.SOLAR_PANEL_DENSITY)
    area_km2 = area_m2 / 1_000_000
    ireland_area_km2 = 84421
    percentage_of_ireland = (area_km2 / ireland_area_km2) * 100
    return area_km2, percentage_of_ireland

def analyze_solar_system(latitude, longitude, demand_in_kw, daily_usage, cutoff_day=None, wacc=WACC):
    if cutoff_day is None:
        cutoff_day = config.CUTOFF_DAY

    print(f"Analyzing solar system for coordinates: Latitude {latitude}, Longitude {longitude}")

    ac, average_annual_insolation = simulate_solar_generated(latitude, longitude)
    daily_generated_unsorted = calculate_daily_generated(ac)
    daily_generated = sorted(daily_generated_unsorted)

    required_solar_array, gas_energy_generated, solar_energy_generated, solar_energy_consumed, gas_energy_consumed, gas_fraction = calculate_system_requirements(daily_generated, daily_usage, demand_in_kw, cutoff_day)

    battery_capacity = demand_in_kw * config.SOLAR_BATTERY_STORAGE_HOURS
    system_cost = calculate_system_cost(required_solar_array, battery_capacity, demand_in_kw)

    annual_energy_consumed = 365 * daily_usage

    total_energy_generated = solar_energy_consumed + gas_energy_consumed
    if np.isclose(total_energy_generated, annual_energy_consumed, atol=1e-2):
        print("Energy balance check passed: Total energy generated equals annual energy consumed.")
    else:
        print("Energy balance check failed: Total energy generated does not equal annual energy consumed.")

    system_lcoe = calculate_lcoe(system_cost, annual_energy_consumed, gas_energy_consumed)
    system_capex_per_kw = calculate_capex_per_kw(system_cost, demand_in_kw)

    solar_capacity_factor = solar_energy_consumed / (required_solar_array * 24 * 365)

    solar_curtailment = (solar_energy_generated - solar_energy_consumed) / solar_energy_generated

    print("\nCost Analysis:")
    print(f"WACC: {wacc:.4f}")

    print(f"\nGas Supported System (with {config.SOLAR_BATTERY_STORAGE_HOURS}h battery storage):")
    print(f"Solar Capacity: {required_solar_array/1e6} GW")
    print(f"Solar Energy Generated: {solar_energy_generated/1e6} GWh")
    print(f"Solar Energy Consumed: {solar_energy_consumed/1e6} GWh")
    print(f"Total cost: ${system_cost:,.0f}")
    print(f"LCOE: ${system_lcoe:.4f}/kWh")
    print(f"Capex per kW: ${system_capex_per_kw:.2f}/kW")
    print(f"Solar Capacity Factor: {solar_capacity_factor:.2%}")
    print(f"Solar Curtailment: {solar_curtailment:.2%}")
    print(f"Fraction of energy from solar: {solar_energy_consumed / annual_energy_consumed:.2%}")
    area_km2, percentage = calculate_solar_area(required_solar_array)
    print(f"Required solar area: {area_km2:.2f} km² ({percentage:.2f}% of Ireland's land area)")

    energy_generated_data = {
        'solar_generated': np.array(daily_generated) * required_solar_array,
        'gas_generated': np.maximum(demand_in_kw * 24 - np.array(daily_generated) * required_solar_array, 0)
    }
    
    capex_breakdown_data = {
        'components': ['Solar Panels', 'Battery Storage', 'Gas'],
        'values': [
            required_solar_array * config.SOLAR_COST_PER_KW / 1e6,
            battery_capacity * config.BATTERY_COST_PER_KWH / 1e6,
            0 if cutoff_day == 0 else demand_in_kw * config.OCGT_CAPEX_PER_KW / 1e6
        ]
    }

    print(f"Average Annual Insolation: {average_annual_insolation:.2f} W/m²")

    return {
        "lcoe": system_lcoe,
        "solar_fraction": solar_energy_consumed / annual_energy_consumed,
        "gas_fraction": gas_fraction,
        "solar_capacity_factor": solar_capacity_factor,
        "solar_area_km2": area_km2,
        "solar_area_percentage": percentage,
        "solar_capacity_gw": required_solar_array / 1e6,
        "gas_capacity_gw": demand_in_kw / 1e6,
        "capex_per_kw": system_capex_per_kw,
        "energy_generated_data": energy_generated_data,
        "capex_breakdown_data": capex_breakdown_data,
        "total_capex": system_cost / 1e6,
        "wacc": wacc,
        "solar_curtailment": solar_curtailment,
        "average_annual_insolation": average_annual_insolation,
        "daily_generated_unsorted": daily_generated_unsorted,
        "daily_generated_sorted": daily_generated,
        "required_solar_array": required_solar_array
    }

if __name__ == "__main__":
    # latitude = 53
    # longitude = -8
    # Coordinates for Tucson, Arizona
    latitude = 32.2226
    longitude = -110.9747

    demand_in_kw = 1000000  # 1 GW
    daily_usage = 24000000  # 24 GWh
    
    result = analyze_solar_system(latitude, longitude, demand_in_kw, daily_usage)
    
    # Normalize the data by dividing by the required solar array capacity
    daily_generated_unsorted = np.array(result['daily_generated_unsorted'])
    daily_generated_sorted = np.array(result['daily_generated_sorted'])
    
    # Create separate plots for unsorted and sorted data
    fig1, ax1 = plt.subplots(figsize=(12, 8))
    ax1.bar(range(1, 366), daily_generated_unsorted)
    ax1.set_title('Daily Solar Energy Generated (Unsorted)', fontsize=18)
    ax1.set_xlabel('Day of Year', fontsize=18)
    ax1.set_ylabel('Energy (kWh) per kW rated', fontsize=18)
    ax1.tick_params(axis='both', which='major', labelsize=14)
    plt.tight_layout()
    plt.show()

    fig2, ax2 = plt.subplots(figsize=(12, 8))
    ax2.bar(range(1, 366), daily_generated_sorted)
    ax2.set_title('Daily Solar Energy Generated (Sorted)', fontsize=18)
    ax2.set_xlabel('Day (sorted by generation)', fontsize=18)
    ax2.set_ylabel('Energy (kWh) per kW rated', fontsize=18)
    ax2.tick_params(axis='both', which='major', labelsize=14)
    plt.tight_layout()
    plt.show()
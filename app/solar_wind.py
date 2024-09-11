from config import *
import pandas as pd
import numpy as np
from solar import simulate_solar_output, calculate_daily_output as calculate_solar_daily_output
from wind import fetch_open_meteo_data, WindTurbine, ModelChain
from utils import calculate_wacc, calculate_lcoe, calculate_capex_per_kw

def simulate_wind_output(weather_data):
    turbine = WindTurbine(turbine_type='E-126/7500', hub_height=135)
    mc = ModelChain(turbine).run_model(weather_data)
    return mc.power_output / turbine.nominal_power  # Normalize to per kW output

def calculate_wind_daily_output(wind_output):
    return wind_output.resample('D').sum()  # Daily sum of kWh per kW of capacity

def analyze_hybrid_system(latitude, longitude, demand_in_kw, daily_usage, cutoff_day=CUTOFF_DAY):
    # Remove the get_coordinates function call
    print(f"Analyzing hybrid system for coordinates: Latitude {latitude}, Longitude {longitude}")


    wacc = calculate_wacc()    # Simulate solar output

    solar_output = simulate_solar_output(latitude, longitude)
    solar_daily = pd.Series(calculate_solar_daily_output(solar_output))

    # Fetch weather data and simulate wind output
    weather_data = fetch_open_meteo_data(latitude, longitude, "2022-01-01", "2022-12-31")
    wind_output = simulate_wind_output(weather_data)
    wind_daily = calculate_wind_daily_output(wind_output)

    # Ensure both series have the same length and index
    start_date = "2022-01-01"
    end_date = "2022-12-31"
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    solar_daily = pd.Series(solar_daily.values, index=date_range[:len(solar_daily)])
    wind_daily = wind_daily.reindex(date_range)

    gamma_values = np.linspace(0, 1, 10)  # Increase the number of points for a smoother curve
    results = []

    for gamma in gamma_values:
        combined_daily = solar_daily * gamma + wind_daily * (1 - gamma)
        sorted_daily_output = combined_daily.sort_values(ascending=True)
        required_capacity = daily_usage / sorted_daily_output.iloc[cutoff_day]

        solar_capacity = required_capacity * gamma
        wind_capacity = required_capacity * (1 - gamma)

        solar_output = solar_daily * solar_capacity
        wind_output = wind_daily * wind_capacity
        combined_daily = solar_output + wind_output

        daily_demand = pd.Series([daily_usage] * len(combined_daily), index=combined_daily.index)
        
        used_solar = np.minimum(solar_output, daily_demand)
        used_wind = np.minimum(wind_output, daily_demand - used_solar)

        solar_energy_used = used_solar.sum()
        wind_energy_used = used_wind.sum()
        solar_capacity_factor = solar_energy_used / (solar_capacity * 8760) if solar_capacity > 0 else 0
        wind_capacity_factor = wind_energy_used / (wind_capacity * 8760) if wind_capacity > 0 else 0

        gas_energy = max(0, (cutoff_day * demand_in_kw * 24) - sum(sorted_daily_output.iloc[:cutoff_day]) * required_capacity)
        annual_demand = 365 * daily_usage
        gas_fraction = gas_energy / annual_demand

        battery_hours = SOLAR_BATTERY_STORAGE_HOURS * gamma + WIND_BATTERY_STORAGE_HOURS * (1 - gamma)
        battery_capacity = demand_in_kw * battery_hours

        system_cost = (
            solar_capacity * SOLAR_COST_PER_KW +
            wind_capacity * WIND_COST_PER_KW +
            battery_capacity * BATTERY_COST_PER_KWH +
            demand_in_kw * OCGT_CAPEX_PER_KW
        )

        lcoe = calculate_lcoe(system_cost, annual_demand, gas_energy)
        capex_per_kw = calculate_capex_per_kw(system_cost, demand_in_kw)

        results.append((lcoe, gamma, solar_capacity, wind_capacity, battery_capacity, solar_capacity_factor, wind_capacity_factor, capex_per_kw, gas_fraction))

    best_hybrid_result = min(results, key=lambda x: x[0])
    solar_only_result = next(result for result in results if result[1] == 1.0)
    wind_only_result = next(result for result in results if result[1] == 0.0)

    best_single_lcoe = min(solar_only_result[0], wind_only_result[0])
    lcoe_improvement = (best_single_lcoe - best_hybrid_result[0]) / best_single_lcoe

    if lcoe_improvement >= HYBRID_LCOE_THRESHOLD:
        best_result = best_hybrid_result
        system_type = "Hybrid"
    elif solar_only_result[0] <= wind_only_result[0]:
        best_result = solar_only_result
        system_type = "Solar + Gas"
    else:
        best_result = wind_only_result
        system_type = "Wind + Gas"

    (lcoe, gamma, solar_capacity, wind_capacity, battery_capacity, solar_capacity_factor, wind_capacity_factor, capex_per_kw, gas_fraction) = best_result

    total_capex = (solar_capacity * SOLAR_COST_PER_KW +
                   wind_capacity * WIND_COST_PER_KW +
                   battery_capacity * BATTERY_COST_PER_KWH +
                   demand_in_kw * OCGT_CAPEX_PER_KW) / 1e6  # Convert to millions
    print(f"\nBest result ({system_type}) for coordinates ({latitude}, {longitude}):")
    print(f"Gamma: {gamma:.4f}")
    print(f"LCOE: ${lcoe:.4f}/kWh")
    print(f"Solar capacity factor: {solar_capacity_factor:.4f}")
    print(f"Wind capacity factor: {wind_capacity_factor:.4f}")
    print(f"CAPEX per kW: ${capex_per_kw:.2f}/kW")
    print(f"Battery storage hours: {battery_hours:.2f}")

    if system_type == "Hybrid":
        print(f"LCOE improvement over best single source: {lcoe_improvement:.2%}")

    energy_output_data = {
        'solar_output': (solar_daily * solar_capacity).values,
        'wind_output': (wind_daily * wind_capacity).values,
        'gas_output': np.full(len(solar_daily), daily_usage) - (solar_daily * solar_capacity + wind_daily * wind_capacity).values
    }

    energy_output_data['gas_output'] = np.maximum(energy_output_data['gas_output'], 0)

    # Sort the combined output
    combined_output = energy_output_data['solar_output'] + energy_output_data['wind_output']
    sort_indices = np.argsort(combined_output)

    for key in energy_output_data:
        energy_output_data[key] = energy_output_data[key][sort_indices]

    capex_breakdown_data = {
        'components': ['Solar Panels', 'Wind Turbines', 'Battery Storage', 'Gas'],
        'values': [
            solar_capacity * SOLAR_COST_PER_KW / 1e6,
            wind_capacity * WIND_COST_PER_KW / 1e6,
            battery_capacity * BATTERY_COST_PER_KWH / 1e6,
            demand_in_kw * OCGT_CAPEX_PER_KW / 1e6
        ]
    }

    # Instead of creating a plot, just return the data
    lcoe_vs_solar_fraction_data = {
        'solar_fractions': [result[1] for result in results],
        'lcoe_values': [result[0] for result in results]
    }

    return {
        "lcoe": lcoe,
        "system_type": system_type,
        "solar_fraction": gamma,
        "wind_fraction": 1 - gamma,
        "gas_fraction": gas_fraction,
        "solar_capacity_factor": solar_capacity_factor,
        "wind_capacity_factor": wind_capacity_factor,
        "solar_capacity_gw": solar_capacity / 1e6,
        "wind_capacity_gw": wind_capacity / 1e6,
        "gas_capacity_gw": demand_in_kw / 1e6,
        "battery_capacity_gwh": battery_capacity / 1e6,
        "capex_per_kw": capex_per_kw,
        "energy_output_data": energy_output_data,
        "capex_breakdown_data": capex_breakdown_data,
        "total_capex": total_capex,
        "latitude": latitude,
        "longitude": longitude,
        "wacc": wacc,
        "lcoe_vs_solar_fraction_data": lcoe_vs_solar_fraction_data,
        "solar_curtailment": 0,
        "wind_curtailment": 0
    }

if __name__ == "__main__":
    latitude = 26.14
    longitude = -81.79
    demand_in_kw = 1000000  # 1 GW
    daily_usage = 24000000  # 24 GWh
    
    result = analyze_hybrid_system(latitude, longitude, demand_in_kw, daily_usage)
    # print(result)
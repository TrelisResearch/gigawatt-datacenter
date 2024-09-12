from runtime_config import config
import pandas as pd
import numpy as np
from solar import simulate_solar_generated, calculate_daily_generated as calculate_solar_daily_generated
from wind import fetch_open_meteo_data, WindTurbine, ModelChain
from utils import calculate_wacc, calculate_lcoe, calculate_capex_per_kw

def simulate_wind_generated(weather_data):
    turbine = WindTurbine(turbine_type=config.WIND_TURBINE_TYPE, hub_height=config.WIND_TURBINE_HUB_HEIGHT)
    
    # Select the wind speed column closest to the turbine's hub height
    available_heights = [int(col[1]) for col in weather_data.columns if col[0] == 'wind_speed']
    closest_height = min(available_heights, key=lambda x: abs(x - turbine.hub_height))
    
    # Create a new DataFrame with the selected wind speed data
    weather_selected = pd.DataFrame({
        ('wind_speed', turbine.hub_height): weather_data[('wind_speed', closest_height)],
        ('temperature', 2): weather_data[('temperature', 2)],
        ('pressure', 0): weather_data[('pressure', 0)],
        ('roughness_length', 0): weather_data[('roughness_length', 0)]
    })

    mc = ModelChain(turbine)
    mc.run_model(weather_selected)
    
    return mc.power_output / turbine.nominal_power  # Normalize to per kW output

def calculate_wind_daily_generated(wind_generated):
    return wind_generated.resample('D').sum()  # Daily sum of kWh per kW of capacity

def analyze_hybrid_system(latitude, longitude, demand_in_kw, daily_consumption, cutoff_day=None):
    if cutoff_day is None:
        cutoff_day = config.CUTOFF_DAY

    print(f"Analyzing hybrid system for coordinates: Latitude {latitude}, Longitude {longitude}")

    wacc = calculate_wacc()

    # Simulate solar output
    solar_generated = simulate_solar_generated(latitude, longitude)
    solar_daily = pd.Series(calculate_solar_daily_generated(solar_generated))

    # Fetch weather data and simulate wind output
    weather_data = fetch_open_meteo_data(latitude, longitude, "2022-01-01", "2022-12-31")
    wind_generated = simulate_wind_generated(weather_data)
    wind_daily = calculate_wind_daily_generated(wind_generated)

    # Ensure both series have the same length and index
    start_date = "2022-01-01"
    end_date = "2022-12-31"
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    solar_daily = pd.Series(solar_daily.values, index=date_range[:len(solar_daily)])
    wind_daily = wind_daily.reindex(date_range)
    if wind_daily.isna().any():
        print("There are days that are not well defined in the wind daily output.")

    gamma_values = np.linspace(0, 1, 5)  # Increase the number of points for a smoother curve
    results = []

    for gamma in gamma_values:
        combined_daily_normalized = solar_daily * gamma + wind_daily * (1 - gamma)
        sorted_combined_daily_normalized = combined_daily_normalized.sort_values(ascending=True)
        required_capacity = daily_consumption / sorted_combined_daily_normalized.iloc[cutoff_day]

        solar_capacity = required_capacity * gamma
        wind_capacity = required_capacity * (1 - gamma)

        solar_generated = solar_daily * solar_capacity
        wind_generated = wind_daily * wind_capacity
        combined_daily = solar_generated + wind_generated

        daily_consumption_series = pd.Series([daily_consumption] * len(combined_daily), index=combined_daily.index)
        
        solar_consumed = np.zeros_like(solar_generated.values)
        wind_consumed = np.zeros_like(wind_generated.values)
        
        # Sort days by combined generation
        combined_generation = solar_generated + wind_generated
        sorted_indices = np.argsort(combined_generation.values)

        for i, idx in enumerate(sorted_indices):
            if i < cutoff_day:
                # Before cutoff: consume all generation up to daily consumption
                solar_consumed[idx] = min(solar_generated.values[idx], daily_consumption)
                wind_consumed[idx] = min(wind_generated.values[idx], daily_consumption - solar_consumed[idx])
            else:
                # After cutoff: curtail generation ratably
                total_generated = solar_generated.values[idx] + wind_generated.values[idx]
                if total_generated > daily_consumption:
                    curtailment_factor = daily_consumption / total_generated
                    solar_consumed[idx] = solar_generated.values[idx] * curtailment_factor
                    wind_consumed[idx] = wind_generated.values[idx] * curtailment_factor
                else:
                    solar_consumed[idx] = solar_generated.values[idx]
                    wind_consumed[idx] = wind_generated.values[idx]

        solar_energy_consumed = solar_consumed.sum()
        wind_energy_consumed = wind_consumed.sum()
        solar_capacity_factor = solar_energy_consumed / (solar_capacity * 8760) if solar_capacity > 0 else 0
        wind_capacity_factor = wind_energy_consumed / (wind_capacity * 8760) if wind_capacity > 0 else 0

        # Calculate curtailment
        solar_curtailment = (solar_generated.sum() - solar_energy_consumed) / solar_generated.sum() if solar_generated.sum() > 0 else 0
        wind_curtailment = (wind_generated.sum() - wind_energy_consumed) / wind_generated.sum() if wind_generated.sum() > 0 else 0

        gas_energy = max(0, (cutoff_day * demand_in_kw * 24) - sum(sorted_combined_daily_normalized.iloc[:cutoff_day]) * required_capacity)
        annual_demand = 365 * daily_consumption
        gas_fraction = gas_energy / annual_demand

        battery_hours = config.SOLAR_BATTERY_STORAGE_HOURS * gamma + config.WIND_BATTERY_STORAGE_HOURS * (1 - gamma)
        battery_capacity = demand_in_kw * battery_hours

        system_cost = (
            solar_capacity * config.SOLAR_COST_PER_KW +
            wind_capacity * config.WIND_COST_PER_KW +
            battery_capacity * config.BATTERY_COST_PER_KWH +
            demand_in_kw * config.OCGT_CAPEX_PER_KW
        )

        lcoe = calculate_lcoe(system_cost, annual_demand, gas_energy)
        capex_per_kw = calculate_capex_per_kw(system_cost, demand_in_kw)

        results.append({
            "gamma": gamma,
            "lcoe": lcoe,
            "solar_capacity": solar_capacity,
            "wind_capacity": wind_capacity,
            "battery_capacity": battery_capacity,
            "solar_capacity_factor": solar_capacity_factor,
            "wind_capacity_factor": wind_capacity_factor,
            "solar_curtailment": solar_curtailment,
            "wind_curtailment": wind_curtailment,
            "capex_per_kw": capex_per_kw,
            "gas_fraction": gas_fraction
        })

    # Find the best result based on LCOE
    best_result = min(results, key=lambda x: x["lcoe"])

    # Print the best result
    print(f"\nBest result for coordinates ({latitude}, {longitude}):")
    print(f"Gamma: {best_result['gamma']:.4f}")
    print(f"LCOE: ${best_result['lcoe']:.4f}/kWh")
    print(f"Solar capacity factor: {best_result['solar_capacity_factor']:.4f}")
    print(f"Solar curtailment: {best_result['solar_curtailment']:.4f}")
    print(f"Wind capacity factor: {best_result['wind_capacity_factor']:.4f}")
    print(f"Wind curtailment: {best_result['wind_curtailment']:.4f}")
    print(f"CAPEX per kW: ${best_result['capex_per_kw']:.2f}/kW")
    print(f"Battery storage hours: {battery_hours:.2f}")

    best_hybrid_result = best_result
    solar_only_result = next(result for result in results if result["gamma"] == 1.0)
    wind_only_result = next(result for result in results if result["gamma"] == 0.0)

    best_single_lcoe = min(solar_only_result["lcoe"], wind_only_result["lcoe"])
    lcoe_improvement = (best_single_lcoe - best_hybrid_result["lcoe"]) / best_single_lcoe

    if lcoe_improvement >= config.HYBRID_LCOE_THRESHOLD:
        best_result = best_hybrid_result
        system_type = "Hybrid"
    elif solar_only_result["lcoe"] <= wind_only_result["lcoe"]:
        best_result = solar_only_result
        system_type = "Solar + Gas"
    else:
        best_result = wind_only_result
        system_type = "Wind + Gas"

    if system_type == "Hybrid":
        print(f"LCOE improvement over best single source: {lcoe_improvement:.2%}")

    energy_generated_data = {
        'solar_generated': (solar_daily * best_result["solar_capacity"]).values,
        'wind_generated': (wind_daily * best_result["wind_capacity"]).values,
        'gas_generated': np.full(len(solar_daily), daily_consumption) - (solar_daily * best_result["solar_capacity"] + wind_daily * best_result["wind_capacity"]).values
    }

    energy_generated_data['gas_generated'] = np.maximum(energy_generated_data['gas_generated'], 0)

    # Sort the combined output
    combined_generated = energy_generated_data['solar_generated'] + energy_generated_data['wind_generated']
    sort_indices = np.argsort(combined_generated)

    for key in energy_generated_data:
        energy_generated_data[key] = energy_generated_data[key][sort_indices]

    capex_breakdown_data = {
        'components': ['Solar Panels', 'Wind Turbines', 'Battery Storage', 'Gas'],
        'values': [
            best_result["solar_capacity"] * config.SOLAR_COST_PER_KW / 1e6,
            best_result["wind_capacity"] * config.WIND_COST_PER_KW / 1e6,
            best_result["battery_capacity"] * config.BATTERY_COST_PER_KWH / 1e6,
            demand_in_kw * config.OCGT_CAPEX_PER_KW / 1e6
        ]
    }

    total_capex = sum(capex_breakdown_data['values'])

    return {
        "lcoe": best_result['lcoe'],
        "system_type": system_type,
        "solar_fraction": best_result['gamma'],
        "wind_fraction": 1 - best_result['gamma'],
        "gas_fraction": best_result['gas_fraction'],
        "solar_capacity_factor": best_result['solar_capacity_factor'],
        "wind_capacity_factor": best_result['wind_capacity_factor'],
        "solar_capacity_gw": best_result['solar_capacity'] / 1e6,
        "solar_curtailment": best_result['solar_curtailment'],
        "wind_capacity_gw": best_result['wind_capacity'] / 1e6,
        "wind_curtailment": best_result['wind_curtailment'],
        "gas_capacity_gw": demand_in_kw / 1e6,
        "battery_capacity_gwh": best_result['battery_capacity'] / 1e6,
        "capex_per_kw": best_result['capex_per_kw'],
        "energy_generated_data": energy_generated_data,
        "capex_breakdown_data": capex_breakdown_data,
        "total_capex": total_capex,
        "latitude": latitude,
        "longitude": longitude,
        "wacc": wacc,
        "lcoe_vs_solar_fraction_data": {
            "solar_fractions": [r["gamma"] for r in results],
            "lcoe_values": [r["lcoe"] for r in results]
        },
    }

if __name__ == "__main__":
    latitude = 32.31
    longitude = -111.08
    demand_in_kw = 1000000  # 1 GW
    daily_consumption = 24000000  # 24 GWh
    
    result = analyze_hybrid_system(latitude, longitude, demand_in_kw, daily_consumption)
    print(result)
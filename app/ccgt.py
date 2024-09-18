from runtime_config import config
import matplotlib.pyplot as plt
from utils import calculate_wacc, calculate_capex_per_kw

def calculate_ccgt_costs(demand_kwh, demand_in_kw, capacity_factor, wacc=None):
    if wacc is None:
        wacc = calculate_wacc()
    
    capacity_kw = demand_in_kw / capacity_factor
    
    capex = capacity_kw * config.CCGT_CAPEX_PER_KW
    annual_capex = capex * (wacc * (1 + wacc)**config.PROJECT_LIFETIME) / ((1 + wacc)**config.PROJECT_LIFETIME - 1)
    
    fuel_cost_per_kwh = config.NG_PRICE_PER_KWH / config.CCGT_EFFICIENCY
    annual_fuel_cost = demand_kwh * fuel_cost_per_kwh
    annual_opex = demand_kwh * config.CCGT_OPEX_PER_KWH
    
    total_annual_cost = annual_capex + annual_fuel_cost + annual_opex
    lcoe = total_annual_cost / demand_kwh
    
    capex_per_kw = calculate_capex_per_kw(capex, demand_in_kw)
    
    return {
        'lcoe': lcoe,
        'capex_per_kw': capex_per_kw,
        'total_capex': capex,
        'capacity_gw': capacity_kw / 1e6,
        'annual_energy_used': demand_kwh,
        'wacc': wacc,
        'capacity_factor': capacity_factor,
        'cost_breakdown': {
            'components': ['Capital Cost', 'Fuel Cost', 'O&M Cost'],
            'values': [annual_capex, annual_fuel_cost, annual_opex]
        }
    }

def analyze_ccgt(daily_usage, demand_in_kw, capacity_factor):
    annual_energy_used = 365 * daily_usage  # in kWh
    results = calculate_ccgt_costs(annual_energy_used, demand_in_kw, capacity_factor)
    
    print("\nCost Analysis for CCGT:")
    print(f"WACC: {results['wacc']:.4f}")
    print(f"LCOE: ${results['lcoe']:.4f}/kWh")
    print(f"Capex per kW: ${results['capex_per_kw']:.2f}/kW")
    print(f"Total Capex: ${results['total_capex']:,.0f}")
    print(f"Capacity Factor: {results['capacity_factor']:.2f}")
    
    return results

def plot_ccgt_cost_breakdown(annual_energy_used):
    capex = (annual_energy_used / (24 * 365 * 0.9)) * config.CCGT_CAPEX_PER_KW
    annual_capex = capex * (wacc * (1 + wacc)**config.PROJECT_LIFETIME) / ((1 + wacc)**config.PROJECT_LIFETIME - 1)
    fuel_cost = annual_energy_used * (config.NG_PRICE_PER_KWH / config.CCGT_EFFICIENCY)
    opex = annual_energy_used * config.CCGT_OPEX_PER_KWH

    cost_components = [annual_capex, fuel_cost, opex]
    labels = ['Capital Cost', 'Fuel Cost', 'O&M Cost']
    colors = ['lightblue', 'lightgreen', 'lightsalmon']

    fig, ax = plt.subplots(figsize=(10, 8))

    wedges, texts, autotexts = ax.pie(cost_components, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)

    ax.set_title('Annual Cost Breakdown for CCGT')

    ax.legend(wedges, labels,
              title="Components",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1))

    total_annual_cost = sum(cost_components)
    plt.text(0.5, -0.1, f'Total Annual Cost: ${total_annual_cost:,.0f}', ha='center', transform=ax.transAxes)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    daily_usage = 24000000  # Daily usage in kWh (24 GWh)
    demand_in_kw = 1000000  # Demand in kW (1 GW)
    capacity_factor = 0.9
    analyze_ccgt(daily_usage, demand_in_kw, capacity_factor)
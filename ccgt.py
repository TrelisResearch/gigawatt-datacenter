from config import *

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from utils import calculate_wacc, calculate_capex_per_kw

# CCGT parameters
ccgt_efficiency = 0.60  # 60% efficiency for combined cycle gas turbine
ccgt_capex_per_kw = 1000  # $/kW
ccgt_opex_per_kwh = 0.01  # €/kWh for operation and maintenance

# Natural Gas parameters
ng_price_per_mmbtu = 20  # €/MMBtu (typical European price)
ng_price_per_kwh = ng_price_per_mmbtu / 293.07  # Convert €/MMBtu to €/kWh

# Project lifetime
project_lifetime = 20  # years

def calculate_ccgt_lcoe(demand_kwh, efficiency, capex_per_kw, opex_per_kwh):
    wacc = calculate_wacc()
    capacity_kw = demand_kwh / (24 * 365 * 0.9)  # Assuming 90% capacity factor
    
    capex = capacity_kw * capex_per_kw
    annual_capex = capex * (wacc * (1 + wacc)**PROJECT_LIFETIME) / ((1 + wacc)**PROJECT_LIFETIME - 1)
    
    fuel_cost_per_kwh = NG_PRICE_PER_KWH / efficiency
    annual_fuel_cost = demand_kwh * fuel_cost_per_kwh
    annual_opex = demand_kwh * opex_per_kwh
    
    total_annual_cost = annual_capex + annual_fuel_cost + annual_opex
    return total_annual_cost / demand_kwh

def analyze_ccgt(daily_usage, demand_in_kw):
    annual_energy_used = 365 * daily_usage  # in kWh
    ccgt_lcoe = calculate_ccgt_lcoe(annual_energy_used, CCGT_EFFICIENCY, CCGT_CAPEX_PER_KW, CCGT_OPEX_PER_KWH)
    ccgt_capex = demand_in_kw * CCGT_CAPEX_PER_KW
    ccgt_capex_per_kw_result = calculate_capex_per_kw(ccgt_capex, demand_in_kw)

    # Print cost analysis results
    print("\nCost Analysis for CCGT:")
    print(f"WACC: {calculate_wacc():.4f}")
    print(f"LCOE: ${ccgt_lcoe:.4f}/kWh")
    print(f"Capex per kW: ${ccgt_capex_per_kw_result:.2f}/kW")
    print(f"Total Capex: ${ccgt_capex:,.0f}")

    # Plotting
    plot_ccgt_cost_breakdown(annual_energy_used, ccgt_efficiency, ccgt_capex, ccgt_opex_per_kwh)

def plot_ccgt_cost_breakdown(annual_energy_used, efficiency, capex, opex_per_kwh):
    wacc = calculate_wacc()
    annual_capex = capex * (wacc * (1 + wacc)**project_lifetime) / ((1 + wacc)**project_lifetime - 1)
    fuel_cost = annual_energy_used * (ng_price_per_kwh / efficiency)
    opex = annual_energy_used * opex_per_kwh

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
    
    analyze_ccgt(daily_usage, demand_in_kw)
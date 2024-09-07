import yfinance as yf

def get_treasury_rate():
    # Fetch 20-year Treasury rate
    treasury_20y = yf.Ticker("^TYX")
    return treasury_20y.info['previousClose'] / 100  # Convert to decimal

def calculate_wacc(rate_20y):
    # WACC calculation
    equity_premium = 0.05  # 5% premium over 20-year Treasury rate
    equity_return = rate_20y + equity_premium
    debt_premium = 0.02  # 2% premium over 20-year Treasury rate
    debt_return = rate_20y + debt_premium
    debt_ratio = 0.6  # 60% debt financing
    equity_ratio = 1 - debt_ratio
    tax_rate = 0.21  # Assuming 21% corporate tax rate

    return (equity_return * equity_ratio) + (debt_return * debt_ratio * (1 - tax_rate))

# Project lifetime
project_lifetime = 20  # years

# Natural Gas parameters
ng_price_per_mmbtu = 20  # €/MMBtu (typical European price)
ng_price_per_kwh = ng_price_per_mmbtu / 293.07  # Convert €/MMBtu to €/kWh

# Combined Cycle Gas Turbine (CCGT) parameters
ccgt_efficiency = 0.60  # 60% efficiency for combined cycle gas turbine
ccgt_capex_per_kw = 1200  # $/kW
ccgt_opex_per_kwh = 0.015  # €/kWh for operation and maintenance

def calculate_ccgt_lcoe(demand_kwh, wacc):
    capacity_kw = demand_kwh / (24 * 365)  # Assuming constant demand throughout the year
    
    capex = capacity_kw * ccgt_capex_per_kw
    annual_capex = capex * (wacc * (1 + wacc)**project_lifetime) / ((1 + wacc)**project_lifetime - 1)
    
    fuel_cost_per_kwh = ng_price_per_kwh / ccgt_efficiency
    annual_fuel_cost = demand_kwh * fuel_cost_per_kwh
    annual_opex = demand_kwh * ccgt_opex_per_kwh
    
    total_annual_cost = annual_capex + annual_fuel_cost + annual_opex
    return total_annual_cost / demand_kwh

def main():
    rate_20y = get_treasury_rate()
    wacc = calculate_wacc(rate_20y)
    
    # Example usage
    annual_demand_kwh = 8760000000  # Example: 1GW constant demand for a year
    
    ccgt_lcoe = calculate_ccgt_lcoe(annual_demand_kwh, wacc)
    
    print(f"20-year Treasury rate: {rate_20y:.4f}")
    print(f"WACC: {wacc:.4f}")
    print(f"\nCombined Cycle Gas Turbine (CCGT) System:")
    print(f"LCOE: €{ccgt_lcoe:.4f}/kWh")
    print(f"Capex per kW: ${ccgt_capex_per_kw:.2f}/kW")

if __name__ == "__main__":
    main()
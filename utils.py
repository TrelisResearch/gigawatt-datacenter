import yfinance as yf
import requests

def get_coordinates(city, country):
    """
    Fetch latitude and longitude for a given city and country using the Nominatim API.
    """
    base_url = "https://nominatim.openstreetmap.org/search"
    params = {
        "city": city,
        "country": country,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "SolarScript/1.0"
    }

    response = requests.get(base_url, params=params, headers=headers)
    response.raise_for_status()

    data = response.json()
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"])
    else:
        return None

def calculate_wacc():
    treasury_20y = yf.Ticker("^TYX")
    rate_20y = treasury_20y.info['previousClose'] / 100
    equity_premium = 0.05
    equity_return = rate_20y + equity_premium
    debt_premium = 0.02
    debt_return = rate_20y + debt_premium
    debt_ratio = 0.6
    equity_ratio = 1 - debt_ratio
    tax_rate = 0.21

    return (equity_return * equity_ratio) + (debt_return * debt_ratio * (1 - tax_rate))

def calculate_lcoe(system_cost, annual_energy_used, annual_generator_energy=0, project_lifetime=20):
    wacc = calculate_wacc()
    ng_price_per_kwh = 20 / 293.07  # Convert €/MMBtu to €/kWh
    ocgt_efficiency = 0.35
    ocgt_opex_per_kwh = 0.02

    annual_capital_cost = system_cost * (wacc * (1 + wacc)**project_lifetime) / ((1 + wacc)**project_lifetime - 1)
    annual_generator_fuel_cost = annual_generator_energy * (ng_price_per_kwh / ocgt_efficiency + ocgt_opex_per_kwh)
    total_annual_cost = annual_capital_cost + annual_generator_fuel_cost
    return total_annual_cost / annual_energy_used

def calculate_capex_per_kw(total_cost, rated_capacity_kw):
    return total_cost / rated_capacity_kw
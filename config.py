# Cost parameters
SOLAR_COST_PER_KW = 550  # $/kW
WIND_COST_PER_KW = 1300  # $/kW
BATTERY_COST_PER_KWH = 250  # $/kWh
GENERATOR_COST_PER_KW = 800  # $/kW

# Solar parameters
SOLAR_PANEL_EFFICIENCY = 0.2
SOLAR_PANEL_DENSITY = 0.4

# Natural Gas parameters
NG_PRICE_PER_MMBTU = 20  # €/MMBtu (typical European price)
NG_PRICE_PER_KWH = NG_PRICE_PER_MMBTU / 293.07  # Convert €/MMBtu to €/kWh

# Open Cycle Gas Turbine (OCGT) parameters
OCGT_EFFICIENCY = 0.35  # 35% efficiency for open cycle gas turbine
OCGT_CAPEX_PER_KW = 800  # $/kW
OCGT_OPEX_PER_KWH = 0.02  # €/kWh for operation and maintenance

# Combined Cycle Gas Turbine (CCGT) parameters
CCGT_EFFICIENCY = 0.60  # 60% efficiency for combined cycle gas turbine
CCGT_CAPEX_PER_KW = 1000  # $/kW
CCGT_OPEX_PER_KWH = 0.01  # €/kWh for operation and maintenance

# Project lifetime
PROJECT_LIFETIME = 20  # years
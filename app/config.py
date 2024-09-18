# Cost parameters
SOLAR_COST_PER_KW = 350  # $/kW
WIND_COST_PER_KW = 1300  # $/kW
BATTERY_COST_PER_KWH = 250  # $/kWh

# Solar parameters
SOLAR_PANEL_EFFICIENCY = 0.2
SOLAR_PANEL_DENSITY = 0.4 # m2 of area per m2 of panels
SOLAR_IRRADIANCE = 1000  # W/m² (standard solar irradiance)

# Natural Gas parameters
NG_PRICE_PER_MMBTU = 12  # $/MMBtu (typical European price)
NG_PRICE_PER_KWH = NG_PRICE_PER_MMBTU / 293.07  # Convert $/MMBtu to $/kWh

# Open Cycle Gas Turbine (OCGT) parameters
OCGT_EFFICIENCY = 0.35  # 35% efficiency for open cycle gas turbine
OCGT_CAPEX_PER_KW = 800  # $/kW
OCGT_OPEX_PER_KWH = 0.02  # $/kWh for operation and maintenance

# Combined Cycle Gas Turbine (CCGT) parameters
CCGT_EFFICIENCY = 0.55  # 60% efficiency for combined cycle gas turbine
CCGT_CAPEX_PER_KW = 1200  # $/kW
CCGT_OPEX_PER_KWH = 0.01  # $/kWh for operation and maintenance
CCGT_CAPACITY_FACTOR = 0.7  # 70% capacity factor for CCGT plant

# Project lifetime
PROJECT_LIFETIME = 20  # years

# Battery storage parameters
SOLAR_BATTERY_STORAGE_HOURS = 24  # Hours of battery storage for pure solar system
WIND_BATTERY_STORAGE_HOURS = 12   # Hours of battery storage for pure wind system

# System design parameters
CUTOFF_DAY = 50  # Number of days the system should be able to handle without gas support

# Hybrid system threshold
HYBRID_LCOE_THRESHOLD = 0  # 0% LCOE improvement threshold for hybriding

# WACC parameters
EQUITY_PREMIUM = 0.05
DEBT_PREMIUM = 0.02
DEBT_RATIO = 0.6
EQUITY_RATIO = 0.4
TAX_RATE = 0.21

# Wind turbine parameters
WIND_TURBINE_TYPE = 'E-126/7500'
WIND_TURBINE_HUB_HEIGHT = 135
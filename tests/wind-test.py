import pandas as pd
import numpy as np
from windpowerlib import ModelChain, WindTurbine
import matplotlib.pyplot as plt

# Function to generate simulated weather data
def generate_weather_data(start_date, end_date):
    date_range = pd.date_range(start=start_date, end=end_date, freq='h')
    wind_speed_10m = np.random.weibull(2, len(date_range)) * 5
    wind_speed_80m = wind_speed_10m * 1.3
    wind_speed_135m = wind_speed_10m * 1.5  # Added wind speed at hub height
    temperature_2m = np.random.normal(15, 5, len(date_range)) + 273.15
    temperature_10m = temperature_2m - 0.1
    pressure = np.random.normal(101325, 100, len(date_range))
    roughness_length = np.random.uniform(0.1, 0.5, len(date_range))
    
    return pd.DataFrame({
        ('wind_speed', 10): wind_speed_10m,
        ('wind_speed', 80): wind_speed_80m,
        ('wind_speed', 135): wind_speed_135m,  # Added wind speed at hub height
        ('temperature', 2): temperature_2m,
        ('temperature', 10): temperature_10m,
        ('pressure', 0): pressure,
        ('roughness_length', 0): roughness_length
    }, index=date_range)

# Generate simulated weather data for one year
weather = generate_weather_data('2022-01-01', '2022-12-31')

print("Weather data sample (first 3 rows):")
print(weather[['wind_speed', 'temperature', 'pressure']].head(3))

# Specification of wind turbine
e126ep8 = WindTurbine(turbine_type='E-126/7500', hub_height=135)

# ModelChain setup and run
mc_e126ep8 = ModelChain(e126ep8)
mc_e126ep8.run_model(weather)

# Power output summary
power_output = mc_e126ep8.power_output
print("\nPower output summary:")
print(f"Mean power output: {power_output.mean():.2f} W")
print(f"Max power output: {power_output.max():.2f} W")

# Calculate and print daily energy output summary
daily_output = power_output.resample('D').sum() / 1e6  # Convert to MWh
print("\nDaily energy output summary (MWh):")
print(daily_output.describe())

# Print worst 5 days
print("\nWorst 5 days of energy output (MWh):")
print(daily_output.nsmallest(5))

# Print wind speed data used and hub height wind speed data
wind_speed_hub = mc_e126ep8.wind_speed_hub(weather)  # Pass the weather DataFrame
print(f"Wind speed data used (mean): {wind_speed_hub.mean():.2f} m/s")
print(f"Hub height wind speed data (mean): {weather[('wind_speed', 135)].mean():.2f} m/s")
print(f"Wind speed data at 10m (mean): {weather[('wind_speed', 10)].mean():.2f} m/s")
print(f"Wind speed data at 80m (mean): {weather[('wind_speed', 80)].mean():.2f} m/s")

# Print some additional information about the wind speeds
print(f"\nWind speed statistics:")
print(f"Min wind speed at hub: {wind_speed_hub.min():.2f} m/s")
print(f"Max wind speed at hub: {wind_speed_hub.max():.2f} m/s")
print(f"Median wind speed at hub: {wind_speed_hub.median():.2f} m/s")

# Print information about the turbine
print(f"\nTurbine Information:")
print(f"Hub height: {e126ep8.hub_height} m")
print(f"Rotor diameter: {e126ep8.rotor_diameter} m")
print(f"Nominal power: {e126ep8.nominal_power} W")

# Print information about which wind speed height was used
print(f"\nWind speed height used by the model: {e126ep8.hub_height} m")

# Compare the first few values of wind speed at hub height
print("\nComparing first 5 wind speed values:")
print("Model wind speed at hub:")
print(wind_speed_hub.head())
print("\nInput wind speed at 135m:")
print(weather[('wind_speed', 135)].head())

# Plot results
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

# Daily energy output
daily_output.plot(ax=ax1)
ax1.set_title('Daily Energy Output')
ax1.set_xlabel('Date')
ax1.set_ylabel('Energy (MWh)')

# Power curve
wind_speeds = np.arange(0, 30, 0.5)
power_curve = []
for ws in wind_speeds:
    # Create a weather DataFrame for a single wind speed
    weather_single = pd.DataFrame({
        ('wind_speed', e126ep8.hub_height): [ws],
        ('temperature', 2): [288.15],  # 15°C in Kelvin
        ('pressure', 0): [101325]  # Standard atmospheric pressure
    })
    mc_single = ModelChain(e126ep8)
    mc_single.run_model(weather_single)
    power_curve.append(mc_single.power_output[0])

ax2.plot(wind_speeds, power_curve)
ax2.set_title('Power Curve')
ax2.set_xlabel('Wind Speed (m/s)')
ax2.set_ylabel('Power Output (W)')

plt.tight_layout()
plt.show()

# Calculate capacity factor
capacity_factor = power_output.mean() / e126ep8.nominal_power
print(f"\nCapacity Factor: {capacity_factor:.2%}")
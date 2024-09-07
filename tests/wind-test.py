import pandas as pd
import numpy as np
from windpowerlib import ModelChain, WindTurbine

# Function to generate simulated weather data
def generate_weather_data(start_date, end_date):
    date_range = pd.date_range(start=start_date, end=end_date, freq='h')
    wind_speed_10m = np.random.weibull(2, len(date_range)) * 5
    wind_speed_80m = wind_speed_10m * 1.3
    temperature_2m = np.random.normal(15, 5, len(date_range)) + 273.15
    temperature_10m = temperature_2m - 0.1
    pressure = np.random.normal(101325, 100, len(date_range))
    roughness_length = np.random.uniform(0.1, 0.5, len(date_range))
    
    return pd.DataFrame({
        ('wind_speed', 10): wind_speed_10m,
        ('wind_speed', 80): wind_speed_80m,
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
mc_e126ep8 = ModelChain(e126ep8).run_model(weather)
e126ep8.power_output = mc_e126ep8.power_output

print("\nPower output summary:")
print(f"Mean power output: {e126ep8.power_output.mean():.2f} W")
print(f"Max power output: {e126ep8.power_output.max():.2f} W")

# Calculate and print daily energy output summary
daily_output = e126ep8.power_output.resample('D').sum() / 1e6  # Convert to MWh
print("\nDaily energy output summary (MWh):")
print(f"Mean: {daily_output.mean():.2f}")
print(f"Median: {daily_output.median():.2f}")
print(f"Min: {daily_output.min():.2f}")
print(f"Max: {daily_output.max():.2f}")

# Print worst 5 days
print("\nWorst 5 days of energy output (MWh):")
print(daily_output.nsmallest(5))

# Optional: Plot results if matplotlib is available
try:
    import matplotlib.pyplot as plt
    
    daily_output.plot(figsize=(10, 5))
    plt.title('Daily Energy Output')
    plt.xlabel('Date')
    plt.ylabel('Energy (MWh)')
    plt.show()
except ImportError:
    print("\nMatplotlib not available. Skipping plot.")
import yfinance as yf
import pprint

# Fetch 20-year Treasury rate data
treasury_20y = yf.Ticker("^TYX")

# Get info
info = treasury_20y.info

print("Full info dictionary:")
pprint.pprint(info)

print("\nRegular Market Price (20-year Treasury Rate):")
if 'regularMarketPrice' in info:
    print(f"{info['regularMarketPrice']}%")
else:
    print("regularMarketPrice not found in info")

# Additional potentially useful fields
useful_fields = ['shortName', 'longName', 'previousClose', 'open', 'dayHigh', 'dayLow']

print("\nOther potentially useful fields:")
for field in useful_fields:
    if field in info:
        print(f"{field}: {info[field]}")
    else:
        print(f"{field} not found in info")

# Get historical data
print("\nRecent historical data:")
history = treasury_20y.history(period="5d")
print(history)
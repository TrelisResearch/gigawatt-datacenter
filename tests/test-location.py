import requests
import unittest

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
        "User-Agent": "TestScript/1.0"  # It's good practice to identify your application
    }

    response = requests.get(base_url, params=params, headers=headers)
    response.raise_for_status()  # Raise an exception for HTTP errors

    data = response.json()
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"])
    else:
        return None

class TestGeocoding(unittest.TestCase):
    def test_valid_location(self):
        lat, lon = get_coordinates("Dublin", "Ireland")
        self.assertAlmostEqual(lat, 53.3498, delta=0.1)
        self.assertAlmostEqual(lon, -6.2603, delta=0.1)

    def test_invalid_location(self):
        result = get_coordinates("NonexistentCity", "NonexistentCountry")
        self.assertIsNone(result)

    def test_empty_input(self):
        with self.assertRaises(Exception):
            get_coordinates("", "")

if __name__ == "__main__":
    unittest.main()
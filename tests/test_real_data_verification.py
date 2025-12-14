"""
Property-based tests for real data verification.
"""

import pytest
import requests
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from unittest.mock import patch, Mock
from datetime import datetime, timedelta

from breathable_commute.weather_data import get_city_data, get_all_cities_data, CITY_COORDINATES
from breathable_commute.data_processor import process_all_cities_data
from config import config


@given(
    city_name=st.sampled_from(list(CITY_COORDINATES.keys())),
    mock_pm25=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False),
    mock_temperature=st.floats(min_value=-50.0, max_value=60.0, allow_nan=False, allow_infinity=False),
    mock_wind_speed=st.floats(min_value=0.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    mock_precipitation=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_real_data_verification_no_simulated_values(
    city_name, mock_pm25, mock_temperature, mock_wind_speed, mock_precipitation
):
    """
    **Feature: breathable-commute, Property 15: Real data verification**
    
    For any data displayed in the system, all values should come from Open-Meteo API 
    without any simulated or hardcoded values.
    
    **Validates: Requirements 4.4**
    """
    # Test that the system uses real API data, not simulated values
    lat, lon = CITY_COORDINATES[city_name]
    
    # Create mock response that simulates Open-Meteo API structure
    mock_air_quality_response = Mock()
    mock_air_quality_response.status_code = 200
    mock_air_quality_response.json.return_value = {
        "current": {
            "time": datetime.utcnow().isoformat(),
            "pm2_5": mock_pm25
        }
    }
    mock_air_quality_response.raise_for_status.return_value = None
    
    mock_weather_response = Mock()
    mock_weather_response.status_code = 200
    mock_weather_response.json.return_value = {
        "current": {
            "time": datetime.utcnow().isoformat(),
            "temperature_2m": mock_temperature,
            "wind_speed_10m": mock_wind_speed,
            "precipitation": mock_precipitation
        }
    }
    mock_weather_response.raise_for_status.return_value = None
    
    def mock_get(url, **kwargs):
        """Mock requests.get to return appropriate response based on URL."""
        if "air-quality" in url:
            return mock_air_quality_response
        elif "forecast" in url:
            return mock_weather_response
        else:
            raise ValueError(f"Unexpected URL: {url}")
    
    # Create a mock session that uses our mock_get function
    mock_session = Mock()
    mock_session.get = mock_get
    
    with patch('breathable_commute.weather_data._get_optimized_session', return_value=mock_session):
        # Get city data using the API client
        city_data = get_city_data(lat, lon, city_name)
        
        # Verify that the data comes from the API response, not hardcoded values
        assert city_data.pm25 == mock_pm25, "PM2.5 should come from API, not hardcoded"
        assert city_data.temperature == mock_temperature, "Temperature should come from API, not hardcoded"
        assert city_data.wind_speed == mock_wind_speed, "Wind speed should come from API, not hardcoded"
        assert city_data.precipitation == mock_precipitation, "Precipitation should come from API, not hardcoded"
        
        # Verify that coordinates match the expected city coordinates
        assert city_data.coordinates == (lat, lon), "Coordinates should match city location"
        
        # Verify that city name is correctly set
        assert city_data.city_name == city_name, "City name should be correctly set"
        
        # Verify that timestamp is recent (within last hour)
        time_diff = datetime.utcnow() - city_data.timestamp
        assert time_diff < timedelta(hours=1), "Timestamp should be recent, indicating real-time data"
        
        # Verify no obvious simulated patterns
        # Real data should not have perfect round numbers consistently
        if mock_pm25 != round(mock_pm25):
            assert city_data.pm25 != round(city_data.pm25, 0), "Real data should preserve decimal precision"
        
        # Verify data is within realistic ranges for Indian cities
        assert 0 <= city_data.pm25 <= 1000, "PM2.5 should be in realistic range"
        assert -100 <= city_data.temperature <= 60, "Temperature should be in realistic range for India"
        assert 0 <= city_data.wind_speed <= 200, "Wind speed should be in realistic range"
        assert 0 <= city_data.precipitation <= 200, "Precipitation should be in realistic range"


@given(
    num_requests=st.integers(min_value=1, max_value=5)
)
def test_real_data_verification_api_endpoints_used(num_requests):
    """
    **Feature: breathable-commute, Property 15: Real data verification**
    
    For any data request, the system should make actual HTTP requests to 
    Open-Meteo API endpoints, not use cached or simulated data.
    
    **Validates: Requirements 4.4**
    """
    # Track API calls to ensure real endpoints are used
    api_calls = []
    
    def mock_get(url, **kwargs):
        """Mock that tracks API calls and returns valid responses."""
        # Capture full URL with parameters
        if 'params' in kwargs:
            params = kwargs['params']
            param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{url}?{param_str}"
            api_calls.append(full_url)
        else:
            api_calls.append(url)
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        if "air-quality" in url:
            mock_response.json.return_value = {
                "current": {
                    "time": datetime.utcnow().isoformat(),
                    "pm2_5": 25.5
                }
            }
        elif "forecast" in url:
            mock_response.json.return_value = {
                "current": {
                    "time": datetime.utcnow().isoformat(),
                    "temperature_2m": 28.3,
                    "wind_speed_10m": 12.7,
                    "precipitation": 0.0
                }
            }
        
        mock_response.raise_for_status.return_value = None
        return mock_response
    
    # Create a mock session that uses our mock_get function
    mock_session = Mock()
    mock_session.get = mock_get
    
    with patch('breathable_commute.weather_data._get_optimized_session', return_value=mock_session):
        # Make multiple requests to verify API usage
        for _ in range(num_requests):
            city_data = get_city_data(28.6139, 77.2090, "New Delhi")
            
            # Verify data is returned
            assert city_data is not None
            assert city_data.city_name == "New Delhi"
        
        # Verify that actual API endpoints were called
        assert len(api_calls) == num_requests * 2, "Should make 2 API calls per city (air quality + weather)"
        
        # Verify correct Open-Meteo endpoints are used
        air_quality_calls = [call for call in api_calls if "air-quality" in call]
        weather_calls = [call for call in api_calls if "forecast" in call]
        
        assert len(air_quality_calls) == num_requests, "Should call air quality API for each request"
        assert len(weather_calls) == num_requests, "Should call weather API for each request"
        
        # Verify URLs contain Open-Meteo domains
        for call in api_calls:
            assert "open-meteo.com" in call, f"Should use Open-Meteo API, got: {call}"
        
        # Verify URLs contain correct parameters (requests.get with params adds them to URL)
        for call in air_quality_calls:
            assert "latitude=" in call and "longitude=" in call, f"Air quality API should include coordinates: {call}"
            assert "pm2_5" in call, f"Air quality API should request PM2.5 data: {call}"
        
        for call in weather_calls:
            assert "latitude=" in call and "longitude=" in call, f"Weather API should include coordinates: {call}"
            assert "temperature_2m" in call, f"Weather API should request temperature data: {call}"
            assert "wind_speed_10m" in call, f"Weather API should request wind speed data: {call}"
            assert "precipitation" in call, f"Weather API should request precipitation data: {call}"


def test_real_data_verification_no_hardcoded_responses():
    """
    **Feature: breathable-commute, Property 15: Real data verification**
    
    The system should not contain hardcoded weather data responses or 
    fallback to simulated values when API is available.
    
    **Validates: Requirements 4.4**
    """
    # Test that system doesn't use hardcoded fallback data
    request_count = 0
    
    def mock_get_with_varying_data(url, **kwargs):
        """Mock that returns different data each time to verify no hardcoding."""
        nonlocal request_count
        request_count += 1
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        # Return different values each time to prove data isn't hardcoded
        base_pm25 = 20.0 + (request_count * 5.3)  # Varying PM2.5
        base_temp = 25.0 + (request_count * 2.1)  # Varying temperature
        base_wind = 10.0 + (request_count * 1.7)  # Varying wind speed
        
        if "air-quality" in url:
            mock_response.json.return_value = {
                "current": {
                    "time": datetime.utcnow().isoformat(),
                    "pm2_5": base_pm25
                }
            }
        elif "forecast" in url:
            mock_response.json.return_value = {
                "current": {
                    "time": datetime.utcnow().isoformat(),
                    "temperature_2m": base_temp,
                    "wind_speed_10m": base_wind,
                    "precipitation": 0.0
                }
            }
        
        mock_response.raise_for_status.return_value = None
        return mock_response
    
    # Create a mock session that uses our mock_get_with_varying_data function
    mock_session = Mock()
    mock_session.get = mock_get_with_varying_data
    
    with patch('breathable_commute.weather_data._get_optimized_session', return_value=mock_session):
        # Get data multiple times
        data1 = get_city_data(28.6139, 77.2090, "New Delhi")
        data2 = get_city_data(19.0760, 72.8777, "Mumbai")
        data3 = get_city_data(12.9716, 77.5946, "Bengaluru")
        
        # Verify that data varies (not hardcoded)
        assert data1.pm25 != data2.pm25, "PM2.5 values should vary, indicating real API data"
        assert data1.temperature != data2.temperature, "Temperature values should vary"
        assert data2.wind_speed != data3.wind_speed, "Wind speed values should vary"
        
        # Verify all data is within expected ranges but not identical
        all_pm25 = [data1.pm25, data2.pm25, data3.pm25]
        all_temps = [data1.temperature, data2.temperature, data3.temperature]
        
        assert len(set(all_pm25)) > 1, "PM2.5 values should be different (not hardcoded)"
        assert len(set(all_temps)) > 1, "Temperature values should be different (not hardcoded)"
        
        # Verify reasonable variation (not random noise)
        pm25_range = max(all_pm25) - min(all_pm25)
        temp_range = max(all_temps) - min(all_temps)
        
        assert 0 < pm25_range < 100, "PM2.5 variation should be reasonable"
        assert 0 < temp_range < 50, "Temperature variation should be reasonable"


@given(
    city_name=st.sampled_from(list(CITY_COORDINATES.keys()))
)
def test_real_data_verification_api_configuration_used(city_name):
    """
    **Feature: breathable-commute, Property 15: Real data verification**
    
    For any city data request, the system should use configured API URLs 
    from the configuration system, not hardcoded URLs.
    
    **Validates: Requirements 4.4**
    """
    lat, lon = CITY_COORDINATES[city_name]
    
    # Track which URLs are actually called
    called_urls = []
    
    def mock_get(url, **kwargs):
        """Mock that tracks URLs and returns valid responses."""
        called_urls.append(url)
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        if "air-quality" in url:
            mock_response.json.return_value = {
                "current": {
                    "time": datetime.utcnow().isoformat(),
                    "pm2_5": 30.0
                }
            }
        elif "forecast" in url:
            mock_response.json.return_value = {
                "current": {
                    "time": datetime.utcnow().isoformat(),
                    "temperature_2m": 27.0,
                    "wind_speed_10m": 15.0,
                    "precipitation": 0.0
                }
            }
        
        mock_response.raise_for_status.return_value = None
        return mock_response
    
    # Create a mock session that uses our mock_get function
    mock_session = Mock()
    mock_session.get = mock_get
    
    with patch('breathable_commute.weather_data._get_optimized_session', return_value=mock_session):
        # Get city data
        city_data = get_city_data(lat, lon, city_name)
        
        # Verify that configured URLs are used
        assert len(called_urls) == 2, "Should make 2 API calls (air quality + weather)"
        
        # Verify URLs match configuration
        air_quality_url = config.open_meteo_air_quality_url
        weather_url = config.open_meteo_weather_url
        
        air_quality_calls = [url for url in called_urls if air_quality_url in url]
        weather_calls = [url for url in called_urls if weather_url in url]
        
        assert len(air_quality_calls) == 1, f"Should use configured air quality URL: {air_quality_url}"
        assert len(weather_calls) == 1, f"Should use configured weather URL: {weather_url}"
        
        # Verify no hardcoded URLs are used
        for url in called_urls:
            # Should not contain hardcoded domains different from config
            if "open-meteo" in url:
                assert (air_quality_url.split('/')[2] in url or 
                       weather_url.split('/')[2] in url), "Should use configured domain names"
        
        # Verify data is properly returned
        assert city_data is not None
        assert city_data.city_name == city_name
        assert isinstance(city_data.pm25, (int, float))
        assert isinstance(city_data.temperature, (int, float))


def test_real_data_verification_all_cities_integration():
    """
    **Feature: breathable-commute, Property 15: Real data verification**
    
    When processing all cities data, the system should fetch real data for 
    all Indian cities without using simulated or cached values.
    
    **Validates: Requirements 4.4**
    """
    api_call_count = 0
    cities_called = set()
    
    def mock_get(url, **kwargs):
        """Mock that tracks API calls for all cities."""
        nonlocal api_call_count
        api_call_count += 1
        
        # Extract coordinates from params to identify city
        if 'params' in kwargs and 'latitude' in kwargs['params'] and 'longitude' in kwargs['params']:
            lat = kwargs['params']['latitude']
            lon = kwargs['params']['longitude']
            
            # Find matching city
            for city, coords in CITY_COORDINATES.items():
                if abs(coords[0] - lat) < 0.01 and abs(coords[1] - lon) < 0.01:
                    cities_called.add(city)
                    break
        elif "latitude=" in url and "longitude=" in url:
            lat_start = url.find("latitude=") + 9
            lat_end = url.find("&", lat_start)
            lon_start = url.find("longitude=") + 10
            lon_end = url.find("&", lon_start)
            
            if lat_end == -1:
                lat_end = len(url)
            if lon_end == -1:
                lon_end = len(url)
                
            try:
                lat = float(url[lat_start:lat_end])
                lon = float(url[lon_start:lon_end])
                
                # Find matching city
                for city, coords in CITY_COORDINATES.items():
                    if abs(coords[0] - lat) < 0.01 and abs(coords[1] - lon) < 0.01:
                        cities_called.add(city)
                        break
            except ValueError:
                pass
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        if "air-quality" in url:
            mock_response.json.return_value = {
                "current": {
                    "time": datetime.utcnow().isoformat(),
                    "pm2_5": 25.0 + (api_call_count * 3.2)  # Varying data
                }
            }
        elif "forecast" in url:
            mock_response.json.return_value = {
                "current": {
                    "time": datetime.utcnow().isoformat(),
                    "temperature_2m": 28.0 + (api_call_count * 1.5),
                    "wind_speed_10m": 12.0 + (api_call_count * 0.8),
                    "precipitation": 0.0
                }
            }
        
        mock_response.raise_for_status.return_value = None
        return mock_response
    
    # Create a mock session that uses our mock_get function
    mock_session = Mock()
    mock_session.get = mock_get
    
    with patch('breathable_commute.weather_data._get_optimized_session', return_value=mock_session):
        # Get all cities data
        all_cities_data = get_all_cities_data()
        
        # Verify that data was fetched for all cities
        expected_cities = set(CITY_COORDINATES.keys())
        assert len(all_cities_data) == len(expected_cities), "Should fetch data for all cities"
        
        # Verify API calls were made for all cities
        assert cities_called == expected_cities, f"Should call API for all cities. Called: {cities_called}, Expected: {expected_cities}"
        
        # Verify correct number of API calls (2 per city: air quality + weather)
        expected_calls = len(expected_cities) * 2
        assert api_call_count == expected_calls, f"Should make {expected_calls} API calls, made {api_call_count}"
        
        # Verify all cities have different data (not hardcoded)
        pm25_values = [city.pm25 for city in all_cities_data]
        temp_values = [city.temperature for city in all_cities_data]
        
        assert len(set(pm25_values)) > 1, "PM2.5 values should vary between cities"
        assert len(set(temp_values)) > 1, "Temperature values should vary between cities"
        
        # Verify all data is within realistic ranges
        for city_data in all_cities_data:
            assert 0 <= city_data.pm25 <= 1000, f"PM2.5 for {city_data.city_name} should be realistic"
            assert -100 <= city_data.temperature <= 60, f"Temperature for {city_data.city_name} should be realistic"
            assert 0 <= city_data.wind_speed <= 200, f"Wind speed for {city_data.city_name} should be realistic"
            assert 0 <= city_data.precipitation <= 200, f"Precipitation for {city_data.city_name} should be realistic"
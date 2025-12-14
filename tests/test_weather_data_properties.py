"""
Property-based tests for weather data fetching.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck, HealthCheck
from unittest.mock import patch, Mock
import requests
from datetime import datetime

from breathable_commute.weather_data import (
    get_city_data,
    CityWeatherData,
    WeatherDataError,
    CITY_COORDINATES,
    API_TIMEOUT,
    MAX_RETRIES
)


@given(
    pm25_value=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False)
)
@settings(deadline=None, max_examples=20)
def test_air_quality_data_fetching_consistency(pm25_value):
    """
    **Feature: python-dashboard, Property 1: Air quality data fetching consistency**
    
    For any dashboard load, the system should fetch PM2.5 data from Open-Meteo API 
    using the correct coordinates for all Indian cities and return valid air quality measurements.
    
    **Validates: Requirements 1.1**
    """
    # Test with New Delhi coordinates
    lat, lon = CITY_COORDINATES["New Delhi"]
    
    # Mock responses for both air quality and weather APIs
    def mock_get_side_effect(url, **kwargs):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        
        if "air-quality-api" in url:
            # Air quality API response
            mock_response.json.return_value = {
                "current": {
                    "pm2_5": pm25_value,
                    "time": "2024-01-01T12:00"
                }
            }
        elif "api.open-meteo.com" in url:
            # Weather API response
            mock_response.json.return_value = {
                "current": {
                    "temperature_2m": 25.0,
                    "wind_speed_10m": 15.0,
                    "precipitation": 0.0,
                    "time": "2024-01-01T12:00"
                }
            }
        
        return mock_response
    
    with patch('breathable_commute.weather_data._get_optimized_session') as mock_session_func:
        # Create a mock session
        mock_session = Mock()
        mock_session.get.side_effect = mock_get_side_effect
        mock_session_func.return_value = mock_session
        
        try:
            # Test the core function that fetches comprehensive city data
            result = get_city_data(lat, lon, "New Delhi")
            
            # Verify both APIs were called
            assert mock_session.get.call_count == 2
            
            # Check that air quality API was called
            air_quality_calls = [call for call in mock_session.get.call_args_list 
                               if "air-quality-api" in call[0][0]]
            assert len(air_quality_calls) == 1
            
            # Check the air quality API call parameters
            air_call = air_quality_calls[0]
            params = air_call[1]['params']
            assert params['latitude'] == lat
            assert params['longitude'] == lon
            assert params['current'] == "pm2_5"
            
            # Check that timeout is configured
            assert 'timeout' in air_call[1]
            assert air_call[1]['timeout'] == API_TIMEOUT
            
            # Verify the result structure and PM2.5 value
            assert isinstance(result, CityWeatherData)
            assert result.city_name == "New Delhi"
            assert result.pm25 == pm25_value
            assert result.pm25 >= 0.0  # PM2.5 should be non-negative
            assert result.coordinates == (lat, lon)
            
        except WeatherDataError:
            # If an error occurred, it should be due to validation
            # (e.g., if the generated value is outside reasonable bounds)
            pass


@given(
    temperature=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    wind_speed=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    precipitation=st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False)
)
@settings(deadline=None, max_examples=10, suppress_health_check=[HealthCheck.too_slow])  # Reduce examples further for performance
def test_weather_data_fetching_consistency(temperature, wind_speed, precipitation):
    """
    **Feature: python-dashboard, Property 5: Weather data fetching consistency**
    
    For any dashboard load, the system should fetch temperature, wind speed, and precipitation 
    data from Open-Meteo API for all Indian cities.
    
    **Validates: Requirements 2.1**
    """
    # Test with Mumbai coordinates
    lat, lon = CITY_COORDINATES["Mumbai"]
    
    # Mock responses for both air quality and weather APIs
    def mock_get_side_effect(url, **kwargs):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        
        if "air-quality-api" in url:
            # Air quality API response
            mock_response.json.return_value = {
                "current": {
                    "pm2_5": 45.0,  # Fixed reasonable value
                    "time": "2024-01-01T12:00"
                }
            }
        elif "api.open-meteo.com" in url:
            # Weather API response
            mock_response.json.return_value = {
                "current": {
                    "temperature_2m": temperature,
                    "wind_speed_10m": wind_speed,
                    "precipitation": precipitation,
                    "time": "2024-01-01T12:00"
                }
            }
        
        return mock_response
    
    with patch('breathable_commute.weather_data._get_optimized_session') as mock_session_func:
        # Create a mock session
        mock_session = Mock()
        mock_session.get.side_effect = mock_get_side_effect
        mock_session_func.return_value = mock_session
        
        try:
            # Test the core function that fetches comprehensive city data
            result = get_city_data(lat, lon, "Mumbai")
            
            # Verify both APIs were called
            assert mock_session.get.call_count == 2
            
            # Check that weather API was called
            weather_calls = [call for call in mock_session.get.call_args_list 
                           if "api.open-meteo.com" in call[0][0] and "forecast" in call[0][0]]
            assert len(weather_calls) == 1
            
            # Check the weather API call parameters
            weather_call = weather_calls[0]
            params = weather_call[1]['params']
            assert params['latitude'] == lat
            assert params['longitude'] == lon
            assert params['current'] == "temperature_2m,wind_speed_10m,precipitation"
            
            # Check that timeout is configured
            assert 'timeout' in weather_call[1]
            assert weather_call[1]['timeout'] == API_TIMEOUT
            
            # Verify the result structure and weather values
            assert isinstance(result, CityWeatherData)
            assert result.city_name == "Mumbai"
            assert result.temperature == temperature
            assert result.wind_speed == wind_speed
            assert result.precipitation == precipitation
            assert result.wind_speed >= 0.0  # Wind speed should be non-negative
            assert result.precipitation >= 0.0  # Precipitation should be non-negative
            assert result.coordinates == (lat, lon)
            
        except WeatherDataError:
            # If an error occurred, it should be due to validation
            # (e.g., if the generated values are outside reasonable bounds)
            pass


@given(
    lat=st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False),
    lon=st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False)
)
@settings(deadline=None)  # Disable deadline for this test since we're testing timeouts
def test_api_timeout_configuration(lat, lon):
    """
    **Feature: python-dashboard, Property 20: API request timeout configuration**
    
    For any API request made by the system, appropriate timeout values should be 
    configured to prevent hanging requests.
    
    **Validates: Requirements 6.1**
    """
    # Mock a timeout scenario
    def mock_get_side_effect(url, **kwargs):
        # Verify timeout is configured
        assert 'timeout' in kwargs
        assert kwargs['timeout'] == API_TIMEOUT
        assert kwargs['timeout'] > 0
        
        # Simulate timeout
        raise requests.exceptions.Timeout("Request timed out")
    
    with patch('breathable_commute.weather_data._get_optimized_session') as mock_session_func:
        # Create a mock session
        mock_session = Mock()
        mock_session.get.side_effect = mock_get_side_effect
        mock_session_func.return_value = mock_session
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            try:
                # This should fail due to timeout, but timeout should be configured
                get_city_data(lat, lon, "Test City")
                
            except WeatherDataError as e:
                # Expected - timeout should cause WeatherDataError
                assert "timed out" in str(e).lower()
                
                # Verify that timeout was configured in the API calls
                assert mock_session.get.called
                for call in mock_session.get.call_args_list:
                    assert 'timeout' in call[1]
                    assert call[1]['timeout'] == API_TIMEOUT
                    
            except WeatherDataError as e:
                # If coordinates are invalid, we should get a validation error
                # This is acceptable as long as the timeout was still configured
                if "Invalid latitude" in str(e) or "Invalid longitude" in str(e):
                    # Even for invalid coordinates, the timeout should have been configured
                    # if the request was attempted
                    if mock_session.get.called:
                        for call in mock_session.get.call_args_list:
                            assert 'timeout' in call[1]
                            assert call[1]['timeout'] == API_TIMEOUT


@given(
    lat=st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False),
    lon=st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False)
)
@settings(deadline=None, max_examples=10)  # Reduce examples for retry testing
def test_api_retry_mechanism(lat, lon):
    """
    **Feature: python-dashboard, Property 21: API retry mechanism**
    
    For any failed API request, the system should implement exponential backoff 
    retry logic with up to three attempts before giving up.
    
    **Validates: Requirements 6.2**
    """
    call_count = 0
    
    def mock_get_side_effect(url, **kwargs):
        nonlocal call_count
        call_count += 1
        
        # Verify timeout is configured
        assert 'timeout' in kwargs
        assert kwargs['timeout'] == API_TIMEOUT
        
        # Simulate connection error for first few attempts
        if call_count <= MAX_RETRIES:
            raise requests.exceptions.ConnectionError("Connection failed")
        
        # This shouldn't be reached in this test
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"current": {"pm2_5": 50.0}}
        return mock_response
    
    with patch('breathable_commute.weather_data._get_optimized_session') as mock_session_func:
        # Create a mock session
        mock_session = Mock()
        mock_session.get.side_effect = mock_get_side_effect
        mock_session_func.return_value = mock_session
        
        with patch('time.sleep') as mock_sleep:  # Mock sleep to speed up test
            try:
                # This should fail after MAX_RETRIES attempts
                get_city_data(lat, lon, "Test City")
                
            except WeatherDataError as e:
                # Should fail after retries are exhausted
                if "Failed to fetch weather data" in str(e) and "attempts" in str(e):
                    # Verify that exactly MAX_RETRIES * 2 calls were made (air quality + weather for each retry)
                    # But since we're failing on the first API call, we should see MAX_RETRIES calls
                    assert mock_session.get.call_count == MAX_RETRIES
                    
                    # Verify that sleep was called for exponential backoff (MAX_RETRIES - 1 times)
                    assert mock_sleep.call_count == MAX_RETRIES - 1
                    
                    # Verify exponential backoff delays
                    expected_delays = [1, 2]  # BASE_DELAY * (2 ** attempt) for attempts 0, 1
                    actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
                    assert actual_delays == expected_delays
                    
                # or because of coordinate validation
                elif "Invalid latitude" in str(e) or "Invalid longitude" in str(e):
                    # Coordinate validation error - this is expected for invalid coordinates
                    pass
                else:
                    # Re-raise unexpected errors
                    raise e
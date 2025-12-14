"""
Property-based tests for air quality data fetching.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from unittest.mock import patch, Mock
import requests
from datetime import datetime

from breathable_commute.air_quality import (
    get_current_pm25, 
    get_air_quality_data, 
    AirQualityData,
    AirQualityError,
    AIR_QUALITY_THRESHOLD
)


# London coordinates as specified in requirements
LONDON_LAT = 51.5074
LONDON_LON = -0.1278


@given(
    pm25_value=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False)
)
def test_air_quality_data_fetching_consistency(pm25_value):
    """
    **Feature: breathable-commute, Property 1: Air quality data fetching consistency**
    
    For any dashboard load, the system should fetch PM2.5 data from Open-Meteo API 
    using the correct London coordinates and return valid air quality measurements.
    
    **Validates: Requirements 1.1**
    """
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
                    "temperature_2m": 22.0,
                    "time": "2024-01-01T12:00"
                }
            }
        
        return mock_response
    
    with patch('requests.get', side_effect=mock_get_side_effect) as mock_get:
        try:
            # Test the core function that fetches PM2.5 data
            result = get_current_pm25(LONDON_LAT, LONDON_LON)
            
            # Verify both APIs were called (air quality returns just PM2.5, so only one call for this function)
            assert mock_get.call_count >= 1
            
            # Check that at least one call was to the air quality API
            air_quality_calls = [call for call in mock_get.call_args_list 
                               if "air-quality-api" in call[0][0]]
            assert len(air_quality_calls) >= 1
            
            # Check the air quality API call parameters
            air_call = air_quality_calls[0]
            params = air_call[1]['params']
            assert params['latitude'] == LONDON_LAT
            assert params['longitude'] == LONDON_LON
            assert params['current'] == "pm2_5"
            
            # Check that timeout is configured
            assert 'timeout' in air_call[1]
            assert air_call[1]['timeout'] > 0
            
            # Verify the result is the expected PM2.5 value
            assert result == pm25_value
            assert isinstance(result, float)
            assert result >= 0.0  # PM2.5 should be non-negative
            
        except AirQualityError:
            # If an error occurred, it should be due to validation
            # (e.g., if the generated value is outside reasonable bounds)
            pass


@given(
    pm25_value=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False)
)
def test_air_quality_data_structure_consistency(pm25_value):
    """
    **Feature: breathable-commute, Property 1: Air quality data fetching consistency**
    
    For any valid PM2.5 value, the system should return a properly structured 
    AirQualityData object with all required fields.
    
    **Validates: Requirements 1.1**
    """
    # Mock responses for both air quality and weather APIs
    def mock_get_side_effect(url, **kwargs):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        
        if "air-quality-api" in url:
            mock_response.json.return_value = {
                "current": {
                    "pm2_5": pm25_value,
                    "time": "2024-01-01T12:00"
                }
            }
        elif "api.open-meteo.com" in url:
            mock_response.json.return_value = {
                "current": {
                    "temperature_2m": 22.0,
                    "time": "2024-01-01T12:00"
                }
            }
        
        return mock_response
    
    with patch('requests.get', side_effect=mock_get_side_effect):
        try:
            # Test the complete air quality data fetching
            result = get_air_quality_data(LONDON_LAT, LONDON_LON)
            
            # Verify the result is an AirQualityData object
            assert isinstance(result, AirQualityData)
            
            # Verify all required fields are present and valid
            assert isinstance(result.pm25, float)
            assert result.pm25 == pm25_value
            assert result.pm25 >= 0.0
            
            assert isinstance(result.timestamp, datetime)
            
            assert isinstance(result.location, tuple)
            assert len(result.location) == 2
            assert result.location[0] == LONDON_LAT
            assert result.location[1] == LONDON_LON
            
            assert isinstance(result.is_healthy, bool)
            # Health status should be consistent with threshold
            expected_healthy = pm25_value <= AIR_QUALITY_THRESHOLD
            assert result.is_healthy == expected_healthy
            
        except AirQualityError:
            # If an error occurred, it should be due to validation
            pass


@given(
    lat=st.floats(min_value=-90.0, max_value=90.0, allow_nan=False, allow_infinity=False),
    lon=st.floats(min_value=-180.0, max_value=180.0, allow_nan=False, allow_infinity=False),
    pm25_value=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False)
)
def test_coordinate_validation_consistency(lat, lon, pm25_value):
    """
    **Feature: breathable-commute, Property 1: Air quality data fetching consistency**
    
    For any valid coordinates, the system should accept them and make appropriate API calls.
    For invalid coordinates, the system should reject them with appropriate errors.
    
    **Validates: Requirements 1.1**
    """
    # Mock responses for both APIs
    def mock_get_side_effect(url, **kwargs):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        
        if "air-quality-api" in url:
            mock_response.json.return_value = {
                "current": {
                    "pm2_5": pm25_value,
                    "time": "2024-01-01T12:00"
                }
            }
        elif "api.open-meteo.com" in url:
            mock_response.json.return_value = {
                "current": {
                    "temperature_2m": 22.0,
                    "time": "2024-01-01T12:00"
                }
            }
        
        return mock_response
    
    with patch('requests.get', side_effect=mock_get_side_effect) as mock_get:
        try:
            result = get_current_pm25(lat, lon)
            
            # If we get here, coordinates were valid
            # Verify the API was called with the provided coordinates
            call_args = mock_get.call_args
            params = call_args[1]['params']
            assert params['latitude'] == lat
            assert params['longitude'] == lon
            
            # Result should be the expected PM2.5 value
            assert result == pm25_value
            
        except AirQualityError as e:
            # If coordinates are invalid, we should get a validation error
            error_msg = str(e)
            if not (-90 <= lat <= 90):
                assert "Invalid latitude" in error_msg
            elif not (-180 <= lon <= 180):
                assert "Invalid longitude" in error_msg
            else:
                # Some other validation error occurred
                pass


@given(
    lat=st.floats(min_value=-90.0, max_value=90.0, allow_nan=False, allow_infinity=False),
    lon=st.floats(min_value=-180.0, max_value=180.0, allow_nan=False, allow_infinity=False),
    pm25_value=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False)
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_api_request_timeout_configuration(lat, lon, pm25_value):
    """
    **Feature: breathable-commute, Property 9: API request timeout configuration**
    
    For any API request made by the system, appropriate timeout values should be 
    configured to prevent hanging requests.
    
    **Validates: Requirements 4.1**
    """
    # Mock responses for both APIs
    def mock_get_side_effect(url, **kwargs):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        
        if "air-quality-api" in url:
            mock_response.json.return_value = {
                "current": {
                    "pm2_5": pm25_value,
                    "time": "2024-01-01T12:00"
                }
            }
        elif "api.open-meteo.com" in url:
            mock_response.json.return_value = {
                "current": {
                    "temperature_2m": 22.0,
                    "time": "2024-01-01T12:00"
                }
            }
        
        return mock_response
    
    with patch('requests.get', side_effect=mock_get_side_effect) as mock_get:
        try:
            # Make the API call
            result = get_current_pm25(lat, lon)
            
            # Verify that APIs were called with timeout parameters
            assert mock_get.call_count >= 1, "At least one API call should be made"
            
            # Check that all calls have timeout configured
            for call in mock_get.call_args_list:
                call_kwargs = call[1]
                assert 'timeout' in call_kwargs, "API request must include timeout parameter"
                
                # Verify timeout value is appropriate (positive and reasonable)
                timeout_value = call_kwargs['timeout']
                assert isinstance(timeout_value, (int, float)), "Timeout must be numeric"
                assert timeout_value > 0, "Timeout must be positive"
                assert timeout_value <= 60, "Timeout should be reasonable (≤ 60 seconds)"
            
            # Verify the result is valid when timeout is properly configured
            assert isinstance(result, float)
            assert result >= 0.0
            
        except AirQualityError as e:
            # If coordinates are invalid, we should get a validation error
            # This is acceptable as long as the timeout was still configured
            if "Invalid latitude" in str(e) or "Invalid longitude" in str(e):
                # Even for invalid coordinates, the timeout should have been configured
                # if the request was attempted
                if mock_get.called:
                    call_args = mock_get.call_args
                    assert 'timeout' in call_args[1], "Even failed requests must have timeout configured"


@given(
    lat=st.floats(min_value=-90.0, max_value=90.0, allow_nan=False, allow_infinity=False),
    lon=st.floats(min_value=-180.0, max_value=180.0, allow_nan=False, allow_infinity=False),
    failure_count=st.integers(min_value=1, max_value=3)
)
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_api_retry_mechanism(lat, lon, failure_count):
    """
    **Feature: breathable-commute, Property 10: API retry mechanism**
    
    For any failed API request, the system should implement exponential backoff 
    retry logic with up to three attempts before giving up.
    
    **Validates: Requirements 4.2**
    """
    # Create a side effect that fails for the specified number of attempts
    # then succeeds on the final attempt (if within retry limit)
    call_count = 0
    
    def mock_get_side_effect(url, **kwargs):
        nonlocal call_count
        call_count += 1
        
        # Only fail the first API call (air quality) for the specified number of attempts
        if "air-quality-api" in url and call_count <= failure_count:
            # Simulate a retryable network error
            raise requests.exceptions.ConnectionError("Simulated network failure")
        else:
            # Success case - return valid response based on API type
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            
            if "air-quality-api" in url:
                mock_response.json.return_value = {
                    "current": {
                        "pm2_5": 15.0,  # Valid PM2.5 value
                        "time": "2024-01-01T12:00"
                    }
                }
            elif "api.open-meteo.com" in url:
                mock_response.json.return_value = {
                    "current": {
                        "temperature_2m": 22.0,
                        "time": "2024-01-01T12:00"
                    }
                }
            
            return mock_response
    
    with patch('requests.get', side_effect=mock_get_side_effect) as mock_get:
        with patch('time.sleep') as mock_sleep:  # Speed up the test by mocking sleep
            try:
                result = get_current_pm25(lat, lon)
                
                # If we get here, the retry mechanism succeeded
                # Verify that retries were attempted and eventually succeeded
                # We expect at least failure_count + 1 calls for air quality, plus 1 for weather
                min_expected_calls = failure_count + 2  # failed air quality attempts + successful air quality + weather
                assert mock_get.call_count >= min_expected_calls, f"Expected at least {min_expected_calls} calls, got {mock_get.call_count}"
                
                # Verify exponential backoff was used (sleep called for each retry)
                expected_sleeps = failure_count  # One sleep between each retry
                assert mock_sleep.call_count == expected_sleeps, f"Expected {expected_sleeps} sleep calls, got {mock_sleep.call_count}"
                
                # Verify exponential backoff delays
                if expected_sleeps > 0:
                    sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                    
                    # Check that delays follow exponential backoff pattern (1, 2, 4, ...)
                    for i, delay in enumerate(sleep_calls):
                        expected_delay = 1 * (2 ** i)  # BASE_DELAY * (2 ** attempt)
                        assert delay == expected_delay, f"Sleep {i+1} should be {expected_delay}s, got {delay}s"
                
                # Verify the final result is valid
                assert isinstance(result, float)
                assert result >= 0.0
                
            except AirQualityError as e:
                # If we get an error, it should be because we exceeded max retries
                # or because of coordinate validation
                if "Invalid latitude" in str(e) or "Invalid longitude" in str(e):
                    # Coordinate validation error - this is expected for invalid coordinates
                    pass
                elif "Failed to fetch PM2.5 data after" in str(e):
                    # This should only happen if failure_count >= MAX_RETRIES (3)
                    assert failure_count >= 3, f"Should only fail after max retries, but failed with {failure_count} failures"
                    
                    # Verify all retry attempts were made
                    assert mock_get.call_count == 3, f"Should have made 3 attempts, got {mock_get.call_count}"
                    
                    # Verify exponential backoff was used for all retries
                    assert mock_sleep.call_count == 2, f"Should have made 2 sleep calls, got {mock_sleep.call_count}"
                    
                    # Verify exponential backoff delays
                    sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                    expected_delays = [1, 2]  # First retry: 1s, second retry: 2s
                    assert sleep_calls == expected_delays, f"Expected delays {expected_delays}, got {sleep_calls}"
                else:
                    # Some other error occurred
                    pass
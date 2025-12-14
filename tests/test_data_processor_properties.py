"""
Property-based tests for data processing functionality.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from datetime import datetime
from typing import List
import pandas as pd

from breathable_commute.data_processor import (
    process_all_cities_data,
    DashboardData,
    ChartConfig,
    DataProcessingError,
    _check_hazardous_air_quality,
    _format_air_quality_display,
    _format_weather_display,
    HAZARDOUS_AIR_QUALITY_THRESHOLD,
    HEALTHY_AIR_QUALITY_THRESHOLD
)
from breathable_commute.weather_data import CityWeatherData
from breathable_commute.recommendation_engine import Recommendation


# Test data generators
@st.composite
def city_weather_data_strategy(draw, city_name=None):
    """Generate valid CityWeatherData objects."""
    if city_name is None:
        city_name = draw(st.sampled_from(["New Delhi", "Mumbai", "Bengaluru", "Hyderabad", "Test City"]))
    
    pm25 = draw(st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False))
    temperature = draw(st.floats(min_value=-10.0, max_value=50.0, allow_nan=False, allow_infinity=False))
    wind_speed = draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    precipitation = draw(st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False))
    lat = draw(st.floats(min_value=-90.0, max_value=90.0, allow_nan=False, allow_infinity=False))
    lon = draw(st.floats(min_value=-180.0, max_value=180.0, allow_nan=False, allow_infinity=False))
    
    return CityWeatherData(
        city_name=city_name,
        pm25=pm25,
        temperature=temperature,
        wind_speed=wind_speed,
        precipitation=precipitation,
        timestamp=datetime.now(),
        coordinates=(lat, lon)
    )


@st.composite
def cities_data_list_strategy(draw):
    """Generate non-empty list of valid CityWeatherData objects with unique city names."""
    num_cities = draw(st.integers(min_value=1, max_value=10))
    cities = []
    
    for i in range(num_cities):
        city_name = f"City_{i}"  # Ensure unique city names
        city_data = draw(city_weather_data_strategy(city_name=city_name))
        cities.append(city_data)
    
    return cities


@st.composite
def hazardous_pm25_strategy(draw):
    """Generate PM2.5 values above hazardous threshold."""
    return draw(st.floats(
        min_value=HAZARDOUS_AIR_QUALITY_THRESHOLD + 0.1, 
        max_value=500.0, 
        allow_nan=False, 
        allow_infinity=False
    ))


@st.composite
def healthy_pm25_strategy(draw):
    """Generate PM2.5 values below healthy threshold."""
    return draw(st.floats(
        min_value=0.0, 
        max_value=HEALTHY_AIR_QUALITY_THRESHOLD - 0.1, 
        allow_nan=False, 
        allow_infinity=False
    ))


@given(cities_data=cities_data_list_strategy())
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
def test_hazardous_air_quality_warning(cities_data):
    """
    **Feature: breathable-commute, Property 4: Hazardous air quality warning**
    **Validates: Requirements 1.4**
    
    For any PM2.5 value above 100 μg/m³, the system should display a warning 
    that air quality is hazardous and cycling should be avoided.
    """
    # Test the hazardous air quality warning function directly
    warnings = _check_hazardous_air_quality(cities_data)
    
    # Count cities with hazardous air quality
    hazardous_cities = [city for city in cities_data if city.pm25 > HAZARDOUS_AIR_QUALITY_THRESHOLD]
    
    # Property: Number of warnings should equal number of hazardous cities
    assert len(warnings) == len(hazardous_cities), (
        f"Expected {len(hazardous_cities)} warnings for hazardous cities, but got {len(warnings)}. "
        f"Hazardous cities: {[city.city_name for city in hazardous_cities]}, "
        f"PM2.5 values: {[city.pm25 for city in hazardous_cities]}"
    )
    
    # Property: Each warning should mention the specific city and PM2.5 value
    for i, city in enumerate(hazardous_cities):
        warning = warnings[i]
        assert city.city_name in warning, (
            f"Warning should mention city name '{city.city_name}', but got: {warning}"
        )
        assert str(city.pm25) in warning or f"{city.pm25:.1f}" in warning, (
            f"Warning should mention PM2.5 value {city.pm25}, but got: {warning}"
        )
        assert "HAZARDOUS" in warning.upper(), (
            f"Warning should contain 'HAZARDOUS', but got: {warning}"
        )
        assert str(HAZARDOUS_AIR_QUALITY_THRESHOLD) in warning, (
            f"Warning should mention threshold {HAZARDOUS_AIR_QUALITY_THRESHOLD}, but got: {warning}"
        )
    
    # Property: No warnings should be generated for cities below threshold
    safe_cities = [city for city in cities_data if city.pm25 <= HAZARDOUS_AIR_QUALITY_THRESHOLD]
    for city in safe_cities:
        for warning in warnings:
            assert city.city_name not in warning, (
                f"Safe city '{city.city_name}' (PM2.5: {city.pm25}) should not appear in warnings, "
                f"but found in: {warning}"
            )


@given(pm25=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False))
def test_air_quality_display_formatting(pm25):
    """
    **Feature: breathable-commute, Property 2: Air quality display formatting**
    **Validates: Requirements 1.2**
    
    For any valid PM2.5 value retrieved from the API, the system should display it 
    with correct units (μg/m³) and proper numerical formatting for all cities.
    """
    # Test the air quality display formatting function
    formatted_display = _format_air_quality_display(pm25)
    
    # Property: Display should contain the PM2.5 value
    pm25_str = f"{pm25:.1f}"
    assert pm25_str in formatted_display, (
        f"Formatted display should contain PM2.5 value {pm25_str}, but got: {formatted_display}"
    )
    
    # Property: Display should contain correct units
    assert "μg/m³" in formatted_display, (
        f"Formatted display should contain units 'μg/m³', but got: {formatted_display}"
    )
    
    # Property: Display should be in expected format
    expected_format = f"{pm25:.1f} μg/m³"
    assert formatted_display == expected_format, (
        f"Expected format '{expected_format}', but got: {formatted_display}"
    )
    
    # Property: Display should not contain invalid characters
    assert not any(char in formatted_display for char in ['nan', 'inf', 'None']), (
        f"Display should not contain invalid values, but got: {formatted_display}"
    )


@given(
    temperature=st.floats(min_value=-50.0, max_value=60.0, allow_nan=False, allow_infinity=False),
    wind_speed=st.floats(min_value=0.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    precipitation=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
)
def test_weather_data_display_formatting(temperature, wind_speed, precipitation):
    """
    **Feature: breathable-commute, Property 6: Weather data display formatting**
    **Validates: Requirements 2.2**
    
    For any valid weather data retrieved from the API, the system should display 
    temperature in Celsius, wind speed in km/h, and precipitation status with proper units.
    """
    # Test the weather display formatting function
    formatted_display = _format_weather_display(temperature, wind_speed, precipitation)
    
    # Property: Should return a dictionary with all required keys
    expected_keys = {'temperature', 'wind_speed', 'precipitation'}
    assert set(formatted_display.keys()) == expected_keys, (
        f"Expected keys {expected_keys}, but got: {set(formatted_display.keys())}"
    )
    
    # Property: Temperature should be formatted with Celsius units
    temp_display = formatted_display['temperature']
    temp_str = f"{temperature:.1f}"
    assert temp_str in temp_display, (
        f"Temperature display should contain value {temp_str}, but got: {temp_display}"
    )
    assert "°C" in temp_display, (
        f"Temperature display should contain '°C' units, but got: {temp_display}"
    )
    assert temp_display == f"{temperature:.1f}°C", (
        f"Expected temperature format '{temperature:.1f}°C', but got: {temp_display}"
    )
    
    # Property: Wind speed should be formatted with km/h units
    wind_display = formatted_display['wind_speed']
    wind_str = f"{wind_speed:.1f}"
    assert wind_str in wind_display, (
        f"Wind speed display should contain value {wind_str}, but got: {wind_display}"
    )
    assert "km/h" in wind_display, (
        f"Wind speed display should contain 'km/h' units, but got: {wind_display}"
    )
    assert wind_display == f"{wind_speed:.1f} km/h", (
        f"Expected wind speed format '{wind_speed:.1f} km/h', but got: {wind_display}"
    )
    
    # Property: Precipitation should be formatted with mm units
    precip_display = formatted_display['precipitation']
    precip_str = f"{precipitation:.1f}"
    assert precip_str in precip_display, (
        f"Precipitation display should contain value {precip_str}, but got: {precip_display}"
    )
    assert "mm" in precip_display, (
        f"Precipitation display should contain 'mm' units, but got: {precip_display}"
    )
    assert precip_display == f"{precipitation:.1f} mm", (
        f"Expected precipitation format '{precipitation:.1f} mm', but got: {precip_display}"
    )
    
    # Property: All displays should not contain invalid values
    for key, display in formatted_display.items():
        assert not any(invalid in display for invalid in ['nan', 'inf', 'None']), (
            f"Display for {key} should not contain invalid values, but got: {display}"
        )
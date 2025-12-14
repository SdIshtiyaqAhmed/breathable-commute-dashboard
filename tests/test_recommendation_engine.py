"""
Tests for the Breathable Commute Recommendation Engine.
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st

from breathable_commute.recommendation_engine import (
    generate_recommendation,
    Recommendation
)
from breathable_commute.weather_data import CityWeatherData


# Helper function to create test city data
def create_test_city_data(pm25: float, temperature: float, wind_speed: float = 10.0, 
                         precipitation: float = 0.0, city_name: str = "Test City") -> CityWeatherData:
    """Create test CityWeatherData for testing."""
    return CityWeatherData(
        city_name=city_name,
        pm25=pm25,
        temperature=temperature,
        wind_speed=wind_speed,
        precipitation=precipitation,
        timestamp=datetime.now(),
        coordinates=(28.6139, 77.2090)  # New Delhi coordinates
    )


@given(
    pm25=st.floats(min_value=0.0, max_value=49.9, allow_nan=False, allow_infinity=False),
    temperature=st.floats(min_value=-20.0, max_value=29.9, allow_nan=False, allow_infinity=False),
    wind_speed=st.floats(min_value=0.0, max_value=20.0, allow_nan=False, allow_infinity=False)
)
def test_green_status_recommendation_logic(pm25, temperature, wind_speed):
    """
    **Feature: python-dashboard, Property 12: Green status recommendation logic**
    **Validates: Requirements 4.1**
    
    For any city data where PM2.5 < 50 μg/m³ AND temperature < 30°C, 
    the system should display green status indicating great cycling conditions.
    """
    precipitation = 0.0  # No precipitation for green status test
    city_data = create_test_city_data(pm25, temperature, wind_speed, precipitation)
    recommendation = generate_recommendation(city_data)
    
    # Verify green status conditions
    assert recommendation.status == "green"
    assert recommendation.is_safe_for_cycling == True
    assert isinstance(recommendation.message, str)
    assert len(recommendation.message) > 0
    
    # Verify conditions data is properly stored
    assert recommendation.conditions["pm25"] == pm25
    assert recommendation.conditions["temperature"] == temperature
    assert recommendation.conditions["wind_speed"] == wind_speed
    assert recommendation.conditions["precipitation"] == precipitation


@given(
    pm25=st.one_of(
        st.floats(min_value=50.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=49.9, allow_nan=False, allow_infinity=False)
    ),
    temperature=st.floats(min_value=-20.0, max_value=35.0, allow_nan=False, allow_infinity=False),
    wind_speed=st.one_of(
        st.floats(min_value=20.1, max_value=100.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=20.0, allow_nan=False, allow_infinity=False)
    )
)
def test_yellow_status_recommendation_logic(pm25, temperature, wind_speed):
    """
    **Feature: python-dashboard, Property 13: Yellow status recommendation logic**
    **Validates: Requirements 4.2**
    
    For any city data where PM2.5 is 50-100 μg/m³ OR wind speed > 20 km/h, 
    the system should display yellow status with moderate conditions warning.
    """
    # Only test cases that should result in yellow status
    should_be_yellow = (50.0 <= pm25 <= 100.0) or (wind_speed > 20.0)
    should_not_be_red = pm25 <= 100.0 and temperature <= 35.0
    should_not_be_green = not (pm25 < 50.0 and temperature < 30.0 and wind_speed <= 20.0)
    
    if should_be_yellow and should_not_be_red and should_not_be_green:
        precipitation = 0.0  # No precipitation for yellow status test
        city_data = create_test_city_data(pm25, temperature, wind_speed, precipitation)
        recommendation = generate_recommendation(city_data)
        
        # Verify yellow status conditions
        assert recommendation.status == "yellow"
        assert recommendation.is_safe_for_cycling == False
        assert isinstance(recommendation.message, str)
        assert len(recommendation.message) > 0
        
        # Verify conditions data is properly stored
        assert recommendation.conditions["pm25"] == pm25
        assert recommendation.conditions["temperature"] == temperature
        assert recommendation.conditions["wind_speed"] == wind_speed
        assert recommendation.conditions["precipitation"] == precipitation


@given(
    pm25=st.one_of(
        st.floats(min_value=100.1, max_value=500.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    ),
    temperature=st.one_of(
        st.floats(min_value=35.1, max_value=50.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-20.0, max_value=35.0, allow_nan=False, allow_infinity=False)
    ),
    wind_speed=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
)
def test_red_status_recommendation_logic(pm25, temperature, wind_speed):
    """
    **Feature: python-dashboard, Property 14: Red status recommendation logic**
    **Validates: Requirements 4.3**
    
    For any city data where PM2.5 > 100 μg/m³ OR temperature > 35°C, 
    the system should display red status warning against outdoor exertion.
    """
    # Only test cases that should result in red status
    should_be_red = (pm25 > 100.0) or (temperature > 35.0)
    
    if should_be_red:
        precipitation = 0.0  # No precipitation for red status test
        city_data = create_test_city_data(pm25, temperature, wind_speed, precipitation)
        recommendation = generate_recommendation(city_data)
        
        # Verify red status conditions
        assert recommendation.status == "red"
        assert recommendation.is_safe_for_cycling == False
        assert isinstance(recommendation.message, str)
        assert len(recommendation.message) > 0
        
        # Verify conditions data is properly stored
        assert recommendation.conditions["pm25"] == pm25
        assert recommendation.conditions["temperature"] == temperature
        assert recommendation.conditions["wind_speed"] == wind_speed
        assert recommendation.conditions["precipitation"] == precipitation


@given(
    pm25=st.floats(min_value=0.0, max_value=49.9, allow_nan=False, allow_infinity=False),
    temperature=st.floats(min_value=-20.0, max_value=29.9, allow_nan=False, allow_infinity=False),
    wind_speed=st.floats(min_value=0.0, max_value=20.0, allow_nan=False, allow_infinity=False),
    precipitation=st.floats(min_value=0.1, max_value=50.0, allow_nan=False, allow_infinity=False)
)
def test_precipitation_factor_in_recommendations(pm25, temperature, wind_speed, precipitation):
    """
    **Feature: python-dashboard, Property 8: Precipitation factor in recommendations**
    **Validates: Requirements 2.4**
    
    For any detected precipitation (> 0mm), the system should factor this into cycling condition recommendations.
    """
    city_data = create_test_city_data(pm25, temperature, wind_speed, precipitation)
    recommendation = generate_recommendation(city_data)
    
    # When there's precipitation, status should not be green (should be yellow or red)
    # and cycling should not be considered safe
    assert recommendation.status != "green"
    assert recommendation.is_safe_for_cycling == False
    
    # Precipitation should be mentioned in the message or affect the status
    assert precipitation > 0.0
    assert recommendation.conditions["precipitation"] == precipitation
    
    # The message should reflect the precipitation impact
    assert isinstance(recommendation.message, str)
    assert len(recommendation.message) > 0
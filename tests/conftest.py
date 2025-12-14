"""
Pytest configuration and fixtures for testing.
"""

import pytest
from datetime import datetime
from breathable_commute.air_quality import AirQualityData
from breathable_commute.weather_data import CityWeatherData


@pytest.fixture
def sample_air_quality_data():
    """Sample air quality data for testing."""
    return AirQualityData(
        pm25=15.5,
        temperature=22.0,
        timestamp=datetime.now(),
        location=(51.5074, -0.1278),
        is_healthy=True
    )


@pytest.fixture
def sample_city_weather_data():
    """Sample city weather data for testing."""
    return CityWeatherData(
        city_name="New Delhi",
        pm25=45.2,
        temperature=28.5,
        wind_speed=15.3,
        precipitation=0.0,
        timestamp=datetime.now(),
        coordinates=(28.6139, 77.2090)
    )
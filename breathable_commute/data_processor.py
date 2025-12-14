"""
Data processing module for combining weather and air quality data from multiple Indian cities.
Enhanced with performance optimizations for concurrent users and responsive design support.
"""

import logging
import pandas as pd
import time
from dataclasses import dataclass
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from .weather_data import CityWeatherData, get_all_cities_data
from .recommendation_engine import generate_recommendation, Recommendation


# Configure logging
logger = logging.getLogger(__name__)

# Constants for air quality thresholds (μg/m³)
HEALTHY_AIR_QUALITY_THRESHOLD = 50.0
HAZARDOUS_AIR_QUALITY_THRESHOLD = 100.0

# Performance optimization constants (Requirements 7.4)
MAX_PROCESSING_WORKERS = 4  # Maximum workers for parallel processing
PROCESSING_TIMEOUT = 30  # Timeout for data processing operations


@dataclass
class DashboardData:
    """Combined dashboard data structure for weather dashboard."""
    cities_data: List[CityWeatherData]
    selected_city: str
    recommendation: Recommendation
    correlation_data: pd.DataFrame


@dataclass
class ChartConfig:
    """Chart configuration settings for Plotly visualizations."""
    bar_chart_colors: List[str] = None
    scatter_colors: Dict[str, str] = None
    healthy_threshold: float = 50.0  # PM2.5 μg/m³
    hazardous_threshold: float = 100.0  # PM2.5 μg/m³
    
    def __post_init__(self):
        if self.bar_chart_colors is None:
            self.bar_chart_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
        
        if self.scatter_colors is None:
            self.scatter_colors = {
                "New Delhi": "#1f77b4",
                "Mumbai": "#ff7f0e", 
                "Bengaluru": "#2ca02c",
                "Hyderabad": "#d62728"
            }


class DataProcessingError(Exception):
    """Custom exception for data processing errors."""
    pass


def _validate_cities_data(cities_data: List[CityWeatherData]) -> None:
    """
    Validate cities weather data structure and integrity.
    
    Args:
        cities_data: List of CityWeatherData objects to validate
        
    Raises:
        DataProcessingError: If cities data is invalid
    """
    if cities_data is None:
        raise DataProcessingError("Cities data cannot be None")
    
    if not isinstance(cities_data, list):
        raise DataProcessingError("Cities data must be a list")
    
    if len(cities_data) == 0:
        raise DataProcessingError("Cities data list cannot be empty")
    
    # Validate individual city data
    for i, city_data in enumerate(cities_data):
        if city_data is None:
            raise DataProcessingError(f"City data at index {i} cannot be None")
        
        if not city_data.city_name:
            raise DataProcessingError(f"City at index {i} missing required name")
        
        # Validate PM2.5 values
        if city_data.pm25 < 0:
            raise DataProcessingError(f"City {city_data.city_name} has invalid PM2.5 value: {city_data.pm25}")
        
        # Validate coordinates
        if city_data.coordinates is None or len(city_data.coordinates) != 2:
            raise DataProcessingError(f"City {city_data.city_name} missing valid coordinates")
        
        lat, lon = city_data.coordinates
        if not (-90 <= lat <= 90):
            raise DataProcessingError(f"City {city_data.city_name} has invalid latitude: {lat}")
        if not (-180 <= lon <= 180):
            raise DataProcessingError(f"City {city_data.city_name} has invalid longitude: {lon}")
        
        # Validate weather measurements
        if city_data.wind_speed < 0:
            raise DataProcessingError(f"City {city_data.city_name} has invalid wind speed: {city_data.wind_speed}")
        
        if city_data.precipitation < 0:
            raise DataProcessingError(f"City {city_data.city_name} has invalid precipitation: {city_data.precipitation}")


def _check_hazardous_air_quality(cities_data: List[CityWeatherData]) -> List[str]:
    """
    Check for hazardous air quality conditions and generate warnings.
    
    Args:
        cities_data: List of CityWeatherData objects
        
    Returns:
        List of warning messages for cities with hazardous air quality
    """
    warnings = []
    
    for city_data in cities_data:
        if city_data.pm25 > HAZARDOUS_AIR_QUALITY_THRESHOLD:
            warning_msg = (f"HAZARDOUS AIR QUALITY WARNING: {city_data.city_name} has PM2.5 level of "
                          f"{city_data.pm25:.1f} μg/m³, which exceeds the hazardous threshold of "
                          f"{HAZARDOUS_AIR_QUALITY_THRESHOLD} μg/m³. Cycling should be avoided.")
            warnings.append(warning_msg)
            logger.warning(warning_msg)
    
    return warnings


def _create_correlation_dataframe(cities_data: List[CityWeatherData]) -> pd.DataFrame:
    """
    Create an optimized pandas DataFrame for correlation analysis between wind speed and PM2.5.
    Enhanced with performance optimizations for concurrent users (Requirement 7.4).
    
    Args:
        cities_data: List of CityWeatherData objects
        
    Returns:
        DataFrame with city data for correlation analysis
    """
    start_time = time.time()
    
    # Use list comprehension for better performance
    data_rows = [
        {
            'city': city_data.city_name,
            'pm25': city_data.pm25,
            'temperature': city_data.temperature,
            'wind_speed': city_data.wind_speed,
            'precipitation': city_data.precipitation,
            'latitude': city_data.coordinates[0],
            'longitude': city_data.coordinates[1],
            'timestamp': city_data.timestamp
        }
        for city_data in cities_data
    ]
    
    # Create DataFrame with optimized dtypes for better performance
    df = pd.DataFrame(data_rows)
    
    # Optimize data types for memory efficiency and performance
    df = df.astype({
        'city': 'category',  # Use category for string data with limited values
        'pm25': 'float32',   # Use float32 instead of float64 for memory efficiency
        'temperature': 'float32',
        'wind_speed': 'float32',
        'precipitation': 'float32',
        'latitude': 'float32',
        'longitude': 'float32'
    })
    
    processing_time = time.time() - start_time
    logger.info(f"Created optimized correlation DataFrame with {len(df)} cities in {processing_time:.3f}s")
    return df


def _format_air_quality_display(pm25: float) -> str:
    """
    Format PM2.5 air quality value for display with proper units.
    
    Args:
        pm25: PM2.5 concentration value
        
    Returns:
        Formatted string with value and units
    """
    return f"{pm25:.1f} μg/m³"


def _format_weather_display(temperature: float, wind_speed: float, precipitation: float) -> Dict[str, str]:
    """
    Format weather data for display with proper units.
    
    Args:
        temperature: Temperature in Celsius
        wind_speed: Wind speed in km/h
        precipitation: Precipitation in mm
        
    Returns:
        Dictionary with formatted weather values
    """
    return {
        'temperature': f"{temperature:.1f}°C",
        'wind_speed': f"{wind_speed:.1f} km/h",
        'precipitation': f"{precipitation:.1f} mm"
    }


def process_all_cities_data(selected_city: str = "New Delhi") -> DashboardData:
    """
    Process and combine weather and air quality data for all Indian cities.
    Enhanced with performance optimizations for concurrent users (Requirements 7.4).
    
    This function implements the core business logic for the weather dashboard:
    - Fetches data for all four Indian cities from Open-Meteo API
    - Validates input data integrity and completeness
    - Checks for hazardous air quality conditions and generates warnings
    - Creates correlation DataFrame for wind vs PM2.5 analysis
    - Generates intelligent recommendations based on selected city
    
    Args:
        selected_city: Name of the city to generate recommendations for
        
    Returns:
        DashboardData object with processed and combined data for all cities
        
    Raises:
        DataProcessingError: If data fetching or processing fails
    """
    start_time = time.time()
    logger.info("Starting optimized multi-city dashboard data processing")
    
    try:
        # Fetch data for all cities with concurrent processing (Requirements 1.1, 2.1)
        cities_data = get_all_cities_data()
        
        # Validate all cities data
        _validate_cities_data(cities_data)
        
        # Use parallel processing for performance optimization (Requirement 7.4)
        with ThreadPoolExecutor(max_workers=MAX_PROCESSING_WORKERS) as executor:
            # Submit parallel tasks for data processing
            hazardous_check_future = executor.submit(_check_hazardous_air_quality, cities_data)
            correlation_future = executor.submit(_create_correlation_dataframe, cities_data)
            
            # Find selected city data for recommendations (can be done in parallel)
            selected_city_future = executor.submit(_find_selected_city_data, cities_data, selected_city)
            
            # Wait for all parallel tasks to complete
            hazardous_warnings = hazardous_check_future.result(timeout=PROCESSING_TIMEOUT)
            correlation_data = correlation_future.result(timeout=PROCESSING_TIMEOUT)
            selected_city_data = selected_city_future.result(timeout=PROCESSING_TIMEOUT)
        
        # Log hazardous warnings
        if hazardous_warnings:
            for warning in hazardous_warnings:
                logger.warning(warning)
        
        if selected_city_data is None:
            raise DataProcessingError(f"Selected city '{selected_city}' not found in cities data")
        
        # Generate recommendation for selected city
        recommendation = generate_recommendation(selected_city_data)
        
        # Create combined dashboard data
        dashboard_data = DashboardData(
            cities_data=cities_data,
            selected_city=selected_city,
            recommendation=recommendation,
            correlation_data=correlation_data
        )
        
        processing_time = time.time() - start_time
        logger.info(f"Optimized multi-city dashboard data processing complete in {processing_time:.3f}s: "
                   f"Cities={len(cities_data)}, "
                   f"Selected={selected_city}, "
                   f"Recommendation={recommendation.status}")
        
        return dashboard_data
        
    except Exception as e:
        error_msg = f"Failed to process cities data: {e}"
        logger.error(error_msg)
        raise DataProcessingError(error_msg)


def _find_selected_city_data(cities_data: List[CityWeatherData], selected_city: str) -> Optional[CityWeatherData]:
    """
    Find selected city data from the list of cities.
    Separated for parallel processing optimization.
    
    Args:
        cities_data: List of CityWeatherData objects
        selected_city: Name of the city to find
        
    Returns:
        CityWeatherData object for the selected city or None if not found
    """
    for city_data in cities_data:
        if city_data.city_name == selected_city:
            return city_data
    return None


def get_city_display_data(city_data: CityWeatherData) -> Dict[str, str]:
    """
    Format city weather data for display with proper units and formatting.
    
    Args:
        city_data: CityWeatherData object
        
    Returns:
        Dictionary with formatted display values
    """
    return {
        "city_name": city_data.city_name,
        "pm25_display": _format_air_quality_display(city_data.pm25),  # Requirement 1.2
        "weather_display": _format_weather_display(  # Requirement 2.2
            city_data.temperature, 
            city_data.wind_speed, 
            city_data.precipitation
        ),
        "coordinates": f"{city_data.coordinates[0]:.4f}, {city_data.coordinates[1]:.4f}",
        "timestamp": city_data.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    }


def get_dashboard_summary(dashboard_data: DashboardData) -> Dict[str, any]:
    """
    Generate a summary of dashboard data for display purposes.
    
    Args:
        dashboard_data: DashboardData object
        
    Returns:
        Dictionary with summary information
    """
    selected_city_data = None
    for city_data in dashboard_data.cities_data:
        if city_data.city_name == dashboard_data.selected_city:
            selected_city_data = city_data
            break
    
    if selected_city_data is None:
        raise DataProcessingError(f"Selected city '{dashboard_data.selected_city}' not found")
    
    return {
        "selected_city": dashboard_data.selected_city,
        "pm25_value": selected_city_data.pm25,
        "temperature_value": selected_city_data.temperature,
        "wind_speed_value": selected_city_data.wind_speed,
        "precipitation_value": selected_city_data.precipitation,
        "pm25_display": _format_air_quality_display(selected_city_data.pm25),
        "weather_display": _format_weather_display(
            selected_city_data.temperature,
            selected_city_data.wind_speed,
            selected_city_data.precipitation
        ),
        "recommendation_status": dashboard_data.recommendation.status,
        "recommendation_message": dashboard_data.recommendation.message,
        "total_cities": len(dashboard_data.cities_data),
        "healthy_threshold": HEALTHY_AIR_QUALITY_THRESHOLD,
        "hazardous_threshold": HAZARDOUS_AIR_QUALITY_THRESHOLD,
        "timestamp": selected_city_data.timestamp
    }
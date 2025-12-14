"""
Air quality data client for fetching PM2.5 data from Open-Meteo API.
"""

import time
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Tuple, Optional
import requests


# Configure logging
logger = logging.getLogger(__name__)

# Constants
AIR_QUALITY_THRESHOLD = 25.0  # μg/m³
API_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
BASE_DELAY = 1  # seconds for exponential backoff


@dataclass
class AirQualityData:
    """Air quality data structure."""
    pm25: float  # PM2.5 concentration in μg/m³
    temperature: float  # Temperature in Celsius
    timestamp: datetime
    location: Tuple[float, float]  # (latitude, longitude)
    is_healthy: bool  # True if PM2.5 <= 25


class AirQualityError(Exception):
    """Custom exception for air quality data fetching errors."""
    pass


def _validate_coordinates(lat: float, lon: float) -> None:
    """
    Validate latitude and longitude coordinates.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        
    Raises:
        AirQualityError: If coordinates are invalid
    """
    if not (-90 <= lat <= 90):
        raise AirQualityError(f"Invalid latitude: {lat}. Must be between -90 and 90.")
    if not (-180 <= lon <= 180):
        raise AirQualityError(f"Invalid longitude: {lon}. Must be between -180 and 180.")


def _validate_pm25_value(pm25: float) -> None:
    """
    Validate PM2.5 value.
    
    Args:
        pm25: PM2.5 concentration value
        
    Raises:
        AirQualityError: If PM2.5 value is invalid
    """
    if pm25 < 0:
        raise AirQualityError(f"Invalid PM2.5 value: {pm25}. Must be non-negative.")
    if pm25 > 1000:  # Reasonable upper bound for PM2.5
        raise AirQualityError(f"Suspicious PM2.5 value: {pm25}. Exceeds reasonable limit.")


def _make_air_quality_request(lat: float, lon: float) -> dict:
    """
    Make an API request to Open-Meteo for air quality data.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        
    Returns:
        Air quality API response as dictionary
        
    Raises:
        AirQualityError: If request fails or response is invalid
    """
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "pm2_5"
    }
    
    try:
        response = requests.get(url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        # Validate response structure
        if "current" not in data:
            error_msg = "Invalid API response: missing 'current' field"
            logger.error(error_msg)
            raise AirQualityError(error_msg)
        
        current = data["current"]
        if "pm2_5" not in current:
            error_msg = "Invalid API response: missing 'pm2_5' field"
            logger.error(error_msg)
            raise AirQualityError(error_msg)
        
        pm25_value = current["pm2_5"]
        if pm25_value is None:
            error_msg = "API returned null PM2.5 value"
            logger.error(error_msg)
            raise AirQualityError(error_msg)
        
        return data
        
    except requests.exceptions.Timeout as e:
        error_msg = f"API request timed out after {API_TIMEOUT} seconds"
        logger.error(error_msg)
        raise AirQualityError(error_msg)
    except requests.exceptions.ConnectionError as e:
        error_msg = "Failed to connect to Open-Meteo API"
        logger.error(f"{error_msg}: {e}")
        raise AirQualityError(error_msg)
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error from Open-Meteo API: {e}"
        logger.error(error_msg)
        raise AirQualityError(error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"Request error: {e}"
        logger.error(error_msg)
        raise AirQualityError(error_msg)
    except ValueError as e:
        error_msg = f"Invalid JSON response: {e}"
        logger.error(error_msg)
        raise AirQualityError(error_msg)


def _make_weather_request(lat: float, lon: float) -> dict:
    """
    Make an API request to Open-Meteo for weather data.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        
    Returns:
        Weather API response as dictionary
        
    Raises:
        AirQualityError: If request fails or response is invalid
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m"
    }
    
    try:
        response = requests.get(url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        # Validate response structure
        if "current" not in data:
            error_msg = "Invalid weather API response: missing 'current' field"
            logger.error(error_msg)
            raise AirQualityError(error_msg)
        
        current = data["current"]
        if "temperature_2m" not in current:
            error_msg = "Invalid weather API response: missing 'temperature_2m' field"
            logger.error(error_msg)
            raise AirQualityError(error_msg)
        
        temperature_value = current["temperature_2m"]
        if temperature_value is None:
            error_msg = "Weather API returned null temperature value"
            logger.error(error_msg)
            raise AirQualityError(error_msg)
        
        return data
        
    except requests.exceptions.Timeout as e:
        error_msg = f"Weather API request timed out after {API_TIMEOUT} seconds"
        logger.error(error_msg)
        raise AirQualityError(error_msg)
    except requests.exceptions.ConnectionError as e:
        error_msg = "Failed to connect to Open-Meteo weather API"
        logger.error(f"{error_msg}: {e}")
        raise AirQualityError(error_msg)
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error from Open-Meteo weather API: {e}"
        logger.error(error_msg)
        raise AirQualityError(error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"Weather request error: {e}"
        logger.error(error_msg)
        raise AirQualityError(error_msg)
    except ValueError as e:
        error_msg = f"Invalid JSON response from weather API: {e}"
        logger.error(error_msg)
        raise AirQualityError(error_msg)
        
    except requests.exceptions.Timeout as e:
        error_msg = f"API request timed out after {API_TIMEOUT} seconds"
        logger.error(error_msg)
        raise AirQualityError(error_msg)
    except requests.exceptions.ConnectionError as e:
        error_msg = "Failed to connect to Open-Meteo API"
        logger.error(f"{error_msg}: {e}")
        raise AirQualityError(error_msg)
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error from Open-Meteo API: {e}"
        logger.error(error_msg)
        raise AirQualityError(error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"Request error: {e}"
        logger.error(error_msg)
        raise AirQualityError(error_msg)
    except ValueError as e:
        error_msg = f"Invalid JSON response: {e}"
        logger.error(error_msg)
        raise AirQualityError(error_msg)


def get_current_pm25(lat: float, lon: float) -> float:
    """
    Fetch current PM2.5 data from Open-Meteo API with retry logic.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        
    Returns:
        Current PM2.5 concentration in μg/m³
        
    Raises:
        AirQualityError: If API request fails after all retries or data is invalid
    """
    pm25, _ = get_current_air_data(lat, lon)
    return pm25


def get_current_air_data(lat: float, lon: float) -> Tuple[float, float]:
    """
    Fetch current PM2.5 and temperature data from Open-Meteo API with retry logic.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        
    Returns:
        Tuple of (PM2.5 concentration in μg/m³, temperature in Celsius)
        
    Raises:
        AirQualityError: If API request fails after all retries or data is invalid
    """
    _validate_coordinates(lat, lon)
    
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Fetching air quality and weather data for coordinates ({lat}, {lon}), attempt {attempt + 1}")
            
            # Fetch air quality data (PM2.5)
            air_data = _make_air_quality_request(lat, lon)
            pm25_value = float(air_data["current"]["pm2_5"])
            _validate_pm25_value(pm25_value)
            
            # Fetch weather data (temperature)
            weather_data = _make_weather_request(lat, lon)
            temperature_value = float(weather_data["current"]["temperature_2m"])
            
            logger.info(f"Successfully fetched data: PM2.5={pm25_value} μg/m³, Temperature={temperature_value}°C")
            return pm25_value, temperature_value
            
        except AirQualityError as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            
            # Don't retry for validation errors (coordinates, PM2.5 values)
            if "Invalid latitude" in str(e) or "Invalid longitude" in str(e) or "Invalid PM2.5 value" in str(e):
                raise e
            
            # Exponential backoff for retryable errors
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
        except Exception as e:
            # Catch any other exceptions (like raw ConnectionError from mocks) and convert to AirQualityError
            error_msg = f"Unexpected error during API request: {e}"
            logger.error(error_msg)
            last_error = AirQualityError(error_msg)
            
            # Exponential backoff for retryable errors
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
    
    # All retries exhausted
    logger.error(f"All {MAX_RETRIES} attempts failed. Last error: {last_error}")
    raise AirQualityError(f"Failed to fetch PM2.5 data after {MAX_RETRIES} attempts: {last_error}")


def get_air_quality_data(lat: float, lon: float) -> AirQualityData:
    """
    Fetch complete air quality data including health assessment.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        
    Returns:
        AirQualityData object with PM2.5 value, temperature, and health assessment
        
    Raises:
        AirQualityError: If API request fails or data is invalid
    """
    pm25, temperature = get_current_air_data(lat, lon)
    
    return AirQualityData(
        pm25=pm25,
        temperature=temperature,
        timestamp=datetime.now(),
        location=(lat, lon),
        is_healthy=pm25 <= AIR_QUALITY_THRESHOLD
    )
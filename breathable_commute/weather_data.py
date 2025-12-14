"""
Weather data client for fetching comprehensive weather and air quality data from Open-Meteo API.
"""

import time
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Tuple, Optional, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import concurrent.futures
import threading


# Configure logging
logger = logging.getLogger(__name__)

# Constants
API_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
BASE_DELAY = 1  # seconds for exponential backoff
MAX_CONCURRENT_REQUESTS = 10  # Maximum concurrent API requests for performance optimization
CONNECTION_POOL_SIZE = 20  # Connection pool size for concurrent users

# City coordinates as specified in requirements
CITY_COORDINATES = {
    "New Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Bengaluru": (12.9716, 77.5946),
    "Hyderabad": (17.3850, 78.4867)
}


@dataclass
class CityWeatherData:
    """Complete weather and air quality data structure for a city."""
    city_name: str
    pm25: float  # PM2.5 concentration in μg/m³
    temperature: float  # Temperature in Celsius
    wind_speed: float  # Wind speed in km/h
    precipitation: float  # Precipitation in mm
    timestamp: datetime
    coordinates: Tuple[float, float]  # (latitude, longitude)


class WeatherDataError(Exception):
    """Custom exception for weather data fetching errors."""
    pass


# Global session with connection pooling for concurrent users (Requirement 7.4)
_session_lock = threading.Lock()
_global_session = None


def _get_optimized_session() -> requests.Session:
    """
    Get or create an optimized requests session with connection pooling.
    
    Returns:
        Configured requests session optimized for concurrent users
    """
    global _global_session
    
    with _session_lock:
        if _global_session is None:
            _global_session = requests.Session()
            
            # Configure retry strategy for reliability
            retry_strategy = Retry(
                total=MAX_RETRIES,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS"],  # Updated from method_whitelist
                backoff_factor=BASE_DELAY
            )
            
            # Configure HTTP adapter with connection pooling
            adapter = HTTPAdapter(
                pool_connections=CONNECTION_POOL_SIZE,
                pool_maxsize=CONNECTION_POOL_SIZE,
                max_retries=retry_strategy,
                pool_block=False  # Don't block when pool is full
            )
            
            _global_session.mount("http://", adapter)
            _global_session.mount("https://", adapter)
            
            # Set default headers for better performance
            _global_session.headers.update({
                'User-Agent': 'BreathableCommute/1.0',
                'Accept': 'application/json',
                'Connection': 'keep-alive'
            })
            
            logger.info("Initialized optimized session with connection pooling")
    
    return _global_session


def _validate_coordinates(lat: float, lon: float) -> None:
    """
    Validate latitude and longitude coordinates.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        
    Raises:
        WeatherDataError: If coordinates are invalid
    """
    if not (-90 <= lat <= 90):
        raise WeatherDataError(f"Invalid latitude: {lat}. Must be between -90 and 90.")
    if not (-180 <= lon <= 180):
        raise WeatherDataError(f"Invalid longitude: {lon}. Must be between -180 and 180.")


def _validate_weather_data(pm25: float, temperature: float, wind_speed: float, precipitation: float) -> None:
    """
    Validate weather measurement values.
    
    Args:
        pm25: PM2.5 concentration value
        temperature: Temperature value
        wind_speed: Wind speed value
        precipitation: Precipitation value
        
    Raises:
        WeatherDataError: If any measurement is invalid
    """
    if pm25 < 0:
        raise WeatherDataError(f"Invalid PM2.5 value: {pm25}. Must be non-negative.")
    if pm25 > 1000:  # Reasonable upper bound for PM2.5
        raise WeatherDataError(f"Suspicious PM2.5 value: {pm25}. Exceeds reasonable limit.")
    
    if temperature < -100 or temperature > 60:  # Reasonable temperature bounds
        raise WeatherDataError(f"Invalid temperature: {temperature}°C. Outside reasonable range.")
    
    if wind_speed < 0:
        raise WeatherDataError(f"Invalid wind speed: {wind_speed}. Must be non-negative.")
    if wind_speed > 200:  # Reasonable upper bound for wind speed
        raise WeatherDataError(f"Suspicious wind speed: {wind_speed} km/h. Exceeds reasonable limit.")
    
    if precipitation < 0:
        raise WeatherDataError(f"Invalid precipitation: {precipitation}. Must be non-negative.")


def _make_air_quality_request(lat: float, lon: float) -> dict:
    """
    Make an API request to Open-Meteo for air quality data.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        
    Returns:
        Air quality API response as dictionary
        
    Raises:
        WeatherDataError: If request fails or response is invalid
    """
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "pm2_5"
    }
    
    try:
        session = _get_optimized_session()
        response = session.get(url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        # Validate response structure
        if "current" not in data:
            error_msg = "Invalid API response: missing 'current' field"
            logger.error(error_msg)
            raise WeatherDataError(error_msg)
        
        current = data["current"]
        if "pm2_5" not in current:
            error_msg = "Invalid API response: missing 'pm2_5' field"
            logger.error(error_msg)
            raise WeatherDataError(error_msg)
        
        pm25_value = current["pm2_5"]
        if pm25_value is None:
            error_msg = "API returned null PM2.5 value"
            logger.error(error_msg)
            raise WeatherDataError(error_msg)
        
        return data
        
    except requests.exceptions.Timeout as e:
        error_msg = f"Air quality API request timed out after {API_TIMEOUT} seconds"
        logger.error(error_msg)
        raise WeatherDataError(error_msg)
    except requests.exceptions.ConnectionError as e:
        error_msg = "Failed to connect to Open-Meteo air quality API"
        logger.error(f"{error_msg}: {e}")
        raise WeatherDataError(error_msg)
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error from Open-Meteo air quality API: {e}"
        logger.error(error_msg)
        raise WeatherDataError(error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"Air quality request error: {e}"
        logger.error(error_msg)
        raise WeatherDataError(error_msg)
    except ValueError as e:
        error_msg = f"Invalid JSON response from air quality API: {e}"
        logger.error(error_msg)
        raise WeatherDataError(error_msg)


def _make_weather_request(lat: float, lon: float) -> dict:
    """
    Make an API request to Open-Meteo for weather data.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        
    Returns:
        Weather API response as dictionary
        
    Raises:
        WeatherDataError: If request fails or response is invalid
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,precipitation"
    }
    
    try:
        session = _get_optimized_session()
        response = session.get(url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        # Validate response structure
        if "current" not in data:
            error_msg = "Invalid weather API response: missing 'current' field"
            logger.error(error_msg)
            raise WeatherDataError(error_msg)
        
        current = data["current"]
        required_fields = ["temperature_2m", "wind_speed_10m", "precipitation"]
        
        for field in required_fields:
            if field not in current:
                error_msg = f"Invalid weather API response: missing '{field}' field"
                logger.error(error_msg)
                raise WeatherDataError(error_msg)
            
            if current[field] is None:
                error_msg = f"Weather API returned null {field} value"
                logger.error(error_msg)
                raise WeatherDataError(error_msg)
        
        return data
        
    except requests.exceptions.Timeout as e:
        error_msg = f"Weather API request timed out after {API_TIMEOUT} seconds"
        logger.error(error_msg)
        raise WeatherDataError(error_msg)
    except requests.exceptions.ConnectionError as e:
        error_msg = "Failed to connect to Open-Meteo weather API"
        logger.error(f"{error_msg}: {e}")
        raise WeatherDataError(error_msg)
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error from Open-Meteo weather API: {e}"
        logger.error(error_msg)
        raise WeatherDataError(error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"Weather request error: {e}"
        logger.error(error_msg)
        raise WeatherDataError(error_msg)
    except ValueError as e:
        error_msg = f"Invalid JSON response from weather API: {e}"
        logger.error(error_msg)
        raise WeatherDataError(error_msg)


def get_city_data(lat: float, lon: float, city_name: str = "Unknown") -> CityWeatherData:
    """
    Fetch comprehensive weather and air quality data for a city with retry logic.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        city_name: Name of the city (optional)
        
    Returns:
        CityWeatherData object with complete weather and air quality information
        
    Raises:
        WeatherDataError: If API request fails after all retries or data is invalid
    """
    _validate_coordinates(lat, lon)
    
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Fetching weather data for {city_name} at coordinates ({lat}, {lon}), attempt {attempt + 1}")
            
            # Fetch air quality data (PM2.5)
            air_data = _make_air_quality_request(lat, lon)
            pm25_value = float(air_data["current"]["pm2_5"])
            
            # Fetch weather data (temperature, wind speed, precipitation)
            weather_data = _make_weather_request(lat, lon)
            current_weather = weather_data["current"]
            
            temperature_value = float(current_weather["temperature_2m"])
            wind_speed_value = float(current_weather["wind_speed_10m"])
            precipitation_value = float(current_weather["precipitation"])
            
            # Validate all measurements
            _validate_weather_data(pm25_value, temperature_value, wind_speed_value, precipitation_value)
            
            logger.info(f"Successfully fetched data for {city_name}: PM2.5={pm25_value} μg/m³, "
                       f"Temperature={temperature_value}°C, Wind={wind_speed_value} km/h, "
                       f"Precipitation={precipitation_value} mm")
            
            return CityWeatherData(
                city_name=city_name,
                pm25=pm25_value,
                temperature=temperature_value,
                wind_speed=wind_speed_value,
                precipitation=precipitation_value,
                timestamp=datetime.now(),
                coordinates=(lat, lon)
            )
            
        except WeatherDataError as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} failed for {city_name}: {e}")
            
            # Don't retry for validation errors (coordinates, measurement values)
            if any(keyword in str(e) for keyword in ["Invalid latitude", "Invalid longitude", 
                                                   "Invalid PM2.5", "Invalid temperature", 
                                                   "Invalid wind speed", "Invalid precipitation"]):
                raise e
            
            # Exponential backoff for retryable errors
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                
        except Exception as e:
            # Catch any other exceptions and convert to WeatherDataError
            error_msg = f"Unexpected error during API request for {city_name}: {e}"
            logger.error(error_msg)
            last_error = WeatherDataError(error_msg)
            
            # Exponential backoff for retryable errors
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
    
    # All retries exhausted
    logger.error(f"All {MAX_RETRIES} attempts failed for {city_name}. Last error: {last_error}")
    raise WeatherDataError(f"Failed to fetch weather data for {city_name} after {MAX_RETRIES} attempts: {last_error}")


def get_all_cities_data() -> List[CityWeatherData]:
    """
    Fetch weather data for all predefined Indian cities with concurrent processing
    for improved performance with multiple users (Requirement 7.4).
    
    Returns:
        List of CityWeatherData objects for all cities
        
    Raises:
        WeatherDataError: If any city data fetch fails
    """
    cities_data = []
    
    # Use concurrent processing for better performance with multiple cities
    def fetch_city_data(city_info):
        city_name, (lat, lon) = city_info
        return get_city_data(lat, lon, city_name)
    
    try:
        # Use ThreadPoolExecutor for concurrent API requests (Requirement 7.4)
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
            # Submit all city data requests concurrently
            future_to_city = {
                executor.submit(fetch_city_data, city_info): city_info[0] 
                for city_info in CITY_COORDINATES.items()
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_city):
                city_name = future_to_city[future]
                try:
                    city_data = future.result(timeout=API_TIMEOUT * 2)  # Allow extra time for concurrent requests
                    cities_data.append(city_data)
                    logger.debug(f"Successfully fetched data for {city_name}")
                except Exception as e:
                    error_msg = f"Failed to fetch data for {city_name}: {e}"
                    logger.error(error_msg)
                    raise WeatherDataError(error_msg)
        
        # Sort cities by name for consistent ordering
        cities_data.sort(key=lambda x: x.city_name)
        
        logger.info(f"Successfully fetched data for {len(cities_data)} cities concurrently")
        return cities_data
        
    except Exception as e:
        if isinstance(e, WeatherDataError):
            raise
        error_msg = f"Failed to fetch cities data concurrently: {e}"
        logger.error(error_msg)
        raise WeatherDataError(error_msg)
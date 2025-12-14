"""
Recommendation Engine for Breathable Commute Dashboard.
Provides cycling recommendations based on air quality and weather conditions.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any
from breathable_commute.weather_data import CityWeatherData


# Configure logging
logger = logging.getLogger(__name__)


class RecommendationError(Exception):
    """Raised when recommendation generation fails."""
    pass


@dataclass
class Recommendation:
    """Recommendation data structure as specified in design document."""
    status: str  # "green", "yellow", "red"
    message: str  # Recommendation text
    conditions: Dict[str, Any]  # Supporting data
    is_safe_for_cycling: bool


def generate_recommendation(city_data: CityWeatherData) -> Recommendation:
    """
    Generate cycling recommendation based on scientific thresholds.
    
    Logic as per requirements:
    - Green status: PM2.5 < 50 AND temp < 30°C
    - Yellow status: PM2.5 50-100 OR wind > 20 km/h  
    - Red status: PM2.5 > 100 OR temp > 35°C
    - Precipitation factor included in recommendations
    
    Args:
        city_data: CityWeatherData object with weather and air quality measurements
        
    Returns:
        Recommendation object with status and cycling advice
    """
    pm25 = city_data.pm25
    temperature = city_data.temperature
    wind_speed = city_data.wind_speed
    precipitation = city_data.precipitation
    
    logger.info(f"Generating recommendation for {city_data.city_name}: "
               f"PM2.5={pm25} μg/m³, Temp={temperature}°C, Wind={wind_speed} km/h, "
               f"Precipitation={precipitation} mm")
    
    # Determine status based on scientific thresholds
    if pm25 > 100 or temperature > 35:
        # Red status - hazardous conditions
        status = "red"
        is_safe = False
        
        if pm25 > 100 and temperature > 35:
            message = f"Hazardous conditions: High pollution (PM2.5: {pm25:.1f} μg/m³) and extreme heat ({temperature:.1f}°C). Avoid outdoor exertion."
        elif pm25 > 100:
            message = f"Hazardous air quality: PM2.5 level of {pm25:.1f} μg/m³ is dangerous. Avoid cycling and outdoor activities."
        else:
            message = f"Extreme heat warning: Temperature of {temperature:.1f}°C is too hot for safe cycling. Stay indoors or use air-conditioned transport."
            
    elif pm25 >= 50 or wind_speed > 20:
        # Yellow status - moderate conditions
        status = "yellow"
        is_safe = False
        
        conditions = []
        if pm25 >= 50:
            conditions.append(f"moderate pollution (PM2.5: {pm25:.1f} μg/m³)")
        if wind_speed > 20:
            conditions.append(f"high winds ({wind_speed:.1f} km/h)")
            
        message = f"Moderate conditions with {' and '.join(conditions)}. Short cycling trips may be acceptable with precautions."
        
    else:
        # Green status - good conditions
        status = "green"
        is_safe = True
        message = f"Great cycling conditions! PM2.5 is low ({pm25:.1f} μg/m³) and temperature is comfortable ({temperature:.1f}°C)."
    
    # Factor in precipitation
    if precipitation > 0:
        if status == "green":
            status = "yellow"
            is_safe = False
            message = f"Good air quality and temperature, but precipitation detected ({precipitation:.1f} mm). Consider covered transport or wait for rain to stop."
        else:
            message += f" Additionally, precipitation ({precipitation:.1f} mm) makes cycling conditions more challenging."
    
    conditions_data = {
        "pm25": pm25,
        "temperature": temperature,
        "wind_speed": wind_speed,
        "precipitation": precipitation,
        "city": city_data.city_name,
        "timestamp": city_data.timestamp.isoformat()
    }
    
    recommendation = Recommendation(
        status=status,
        message=message,
        conditions=conditions_data,
        is_safe_for_cycling=is_safe
    )
    
    logger.info(f"Generated {status} recommendation for {city_data.city_name}: {is_safe}")
    return recommendation


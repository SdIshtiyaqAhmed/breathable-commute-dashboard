"""
Health check functionality for API connectivity verification.
"""

import logging
import requests
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

from config import config


logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    service_name: str
    is_healthy: bool
    response_time_ms: float
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class HealthChecker:
    """Performs health checks on external APIs and services."""
    
    def __init__(self):
        self.timeout = config.health_check_timeout
    
    def check_open_meteo_api(self) -> HealthCheckResult:
        """
        Check connectivity to Open-Meteo API.
        
        Returns:
            HealthCheckResult: Result of the health check
        """
        service_name = "Open-Meteo API"
        start_time = datetime.utcnow()
        
        try:
            # Make a simple request to the air quality API using New Delhi coordinates
            response = requests.get(
                config.open_meteo_air_quality_url,
                params={
                    'latitude': config.new_delhi_coords[0],
                    'longitude': config.new_delhi_coords[1],
                    'current': 'pm2_5'
                },
                timeout=self.timeout
            )
            
            end_time = datetime.utcnow()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            response.raise_for_status()
            
            # Check if response has expected structure
            data = response.json()
            if 'current' not in data:
                raise ValueError("Invalid API response structure")
            
            logger.info(f"Open-Meteo API health check passed ({response_time_ms:.1f}ms)")
            
            return HealthCheckResult(
                service_name=service_name,
                is_healthy=True,
                response_time_ms=response_time_ms,
                timestamp=start_time
            )
            
        except requests.exceptions.Timeout:
            error_msg = f"API request timed out after {self.timeout}s"
            logger.warning(f"Open-Meteo API health check failed: {error_msg}")
            
            return HealthCheckResult(
                service_name=service_name,
                is_healthy=False,
                response_time_ms=self.timeout * 1000,
                error_message=error_msg,
                timestamp=start_time
            )
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.warning(f"Open-Meteo API health check failed: {error_msg}")
            
            end_time = datetime.utcnow()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return HealthCheckResult(
                service_name=service_name,
                is_healthy=False,
                response_time_ms=response_time_ms,
                error_message=error_msg,
                timestamp=start_time
            )
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Open-Meteo API health check failed: {error_msg}")
            
            end_time = datetime.utcnow()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return HealthCheckResult(
                service_name=service_name,
                is_healthy=False,
                response_time_ms=response_time_ms,
                error_message=error_msg,
                timestamp=start_time
            )
    
    def check_weather_api(self) -> HealthCheckResult:
        """
        Check connectivity to Open-Meteo Weather API.
        
        Returns:
            HealthCheckResult: Result of the health check
        """
        service_name = "Open-Meteo Weather API"
        start_time = datetime.utcnow()
        
        try:
            # Make a simple request to the weather API using New Delhi coordinates
            response = requests.get(
                config.open_meteo_weather_url,
                params={
                    'latitude': config.new_delhi_coords[0],
                    'longitude': config.new_delhi_coords[1],
                    'current': 'temperature_2m,wind_speed_10m,precipitation'
                },
                timeout=self.timeout
            )
            
            end_time = datetime.utcnow()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            response.raise_for_status()
            
            # Check if response has expected structure
            data = response.json()
            if 'current' not in data:
                raise ValueError("Invalid API response structure")
            
            logger.info(f"Open-Meteo Weather API health check passed ({response_time_ms:.1f}ms)")
            
            return HealthCheckResult(
                service_name=service_name,
                is_healthy=True,
                response_time_ms=response_time_ms,
                timestamp=start_time
            )
            
        except requests.exceptions.Timeout:
            error_msg = f"API request timed out after {self.timeout}s"
            logger.warning(f"Open-Meteo Weather API health check failed: {error_msg}")
            
            return HealthCheckResult(
                service_name=service_name,
                is_healthy=False,
                response_time_ms=self.timeout * 1000,
                error_message=error_msg,
                timestamp=start_time
            )
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.warning(f"Open-Meteo Weather API health check failed: {error_msg}")
            
            end_time = datetime.utcnow()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return HealthCheckResult(
                service_name=service_name,
                is_healthy=False,
                response_time_ms=response_time_ms,
                error_message=error_msg,
                timestamp=start_time
            )
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Open-Meteo Weather API health check failed: {error_msg}")
            
            end_time = datetime.utcnow()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return HealthCheckResult(
                service_name=service_name,
                is_healthy=False,
                response_time_ms=response_time_ms,
                error_message=error_msg,
                timestamp=start_time
            )
    
    def check_all_services(self) -> List[HealthCheckResult]:
        """
        Perform health checks on all external services.
        
        Returns:
            List[HealthCheckResult]: Results for all services
        """
        results = []
        
        if config.health_check_enabled:
            logger.info("Starting health checks for all services")
            
            # Check Open-Meteo Air Quality API
            results.append(self.check_open_meteo_api())
            
            # Check Open-Meteo Weather API
            results.append(self.check_weather_api())
            
            # Log summary
            healthy_count = sum(1 for result in results if result.is_healthy)
            total_count = len(results)
            
            if healthy_count == total_count:
                logger.info(f"All {total_count} services are healthy")
            else:
                unhealthy_count = total_count - healthy_count
                logger.warning(f"{unhealthy_count} of {total_count} services are unhealthy")
        
        else:
            logger.info("Health checks are disabled")
        
        return results
    
    def get_health_summary(self) -> Dict[str, any]:
        """
        Get a summary of system health status.
        
        Returns:
            Dict containing health summary information
        """
        results = self.check_all_services()
        
        healthy_services = [r for r in results if r.is_healthy]
        unhealthy_services = [r for r in results if not r.is_healthy]
        
        avg_response_time = (
            sum(r.response_time_ms for r in results) / len(results)
            if results else 0
        )
        
        return {
            'overall_healthy': len(unhealthy_services) == 0,
            'total_services': len(results),
            'healthy_services': len(healthy_services),
            'unhealthy_services': len(unhealthy_services),
            'average_response_time_ms': avg_response_time,
            'service_details': [
                {
                    'name': r.service_name,
                    'healthy': r.is_healthy,
                    'response_time_ms': r.response_time_ms,
                    'error': r.error_message,
                    'timestamp': r.timestamp.isoformat()
                }
                for r in results
            ],
            'timestamp': datetime.utcnow().isoformat()
        }


# Global health checker instance
health_checker = HealthChecker()


def verify_api_connectivity() -> Tuple[bool, List[HealthCheckResult]]:
    """
    Verify connectivity to all required APIs at startup.
    
    Returns:
        Tuple of (all_healthy, results_list)
    """
    logger.info("Verifying API connectivity at startup")
    
    results = health_checker.check_all_services()
    all_healthy = all(result.is_healthy for result in results)
    
    if all_healthy:
        logger.info("All APIs are accessible and responding correctly")
    else:
        unhealthy_services = [r.service_name for r in results if not r.is_healthy]
        logger.warning(f"Some APIs are not accessible: {', '.join(unhealthy_services)}")
    
    return all_healthy, results
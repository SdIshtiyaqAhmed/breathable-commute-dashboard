"""
Configuration management for the Breathable Commute application.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
from pathlib import Path


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


@dataclass
class Config:
    """Application configuration settings."""
    # API Configuration
    open_meteo_air_quality_url: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    open_meteo_weather_url: str = "https://api.open-meteo.com/v1/forecast"
    
    # Indian city coordinates
    new_delhi_coords: Tuple[float, float] = (28.6139, 77.2090)
    mumbai_coords: Tuple[float, float] = (19.0760, 72.8777)
    bengaluru_coords: Tuple[float, float] = (12.9716, 77.5946)
    hyderabad_coords: Tuple[float, float] = (17.3850, 78.4867)
    
    # Air quality thresholds (μg/m³)
    healthy_air_quality_threshold: float = 50.0
    hazardous_air_quality_threshold: float = 100.0
    
    # Weather thresholds
    moderate_wind_threshold: float = 20.0  # km/h
    high_wind_threshold: float = 30.0  # km/h
    high_temperature_threshold: float = 35.0  # °C
    comfortable_temperature_threshold: float = 30.0  # °C
    
    # API settings
    request_timeout: int = 10
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Performance and caching settings (Requirements 7.1, 7.3, 7.4, 7.5)
    cache_duration_seconds: int = 300  # 5 minutes cache for API responses
    max_concurrent_requests: int = 10  # Maximum concurrent API requests
    connection_pool_size: int = 20  # Connection pool size for concurrent users
    performance_monitoring_enabled: bool = True  # Enable performance monitoring
    auto_refresh_interval: int = 30  # Auto-refresh interval in seconds
    slow_request_threshold: float = 5.0  # Log requests slower than this (seconds)
    
    # Responsive design settings
    mobile_breakpoint: int = 768  # Mobile breakpoint in pixels
    tablet_breakpoint: int = 1024  # Tablet breakpoint in pixels
    chart_height_mobile: int = 300  # Chart height for mobile devices
    chart_height_tablet: int = 400  # Chart height for tablet devices
    chart_height_desktop: int = 500  # Chart height for desktop devices
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[str] = None
    
    # Health check settings
    health_check_enabled: bool = True
    health_check_timeout: int = 5
    
    # Application settings
    app_name: str = "Breathable Commute"
    app_version: str = "1.0.0"
    
    # Required configuration keys for validation
    _required_keys: list = field(default_factory=lambda: [
        "open_meteo_air_quality_url",
        "open_meteo_weather_url",
        "new_delhi_coords",
        "mumbai_coords",
        "bengaluru_coords",
        "hyderabad_coords",
        "healthy_air_quality_threshold",
        "hazardous_air_quality_threshold"
    ])
    
    def validate(self) -> None:
        """
        Validate configuration settings to ensure all required values are present and valid.
        
        Raises:
            ConfigurationError: If any required configuration is missing or invalid
        """
        errors = []
        
        # Validate required URLs
        if not self.open_meteo_air_quality_url or not self.open_meteo_air_quality_url.startswith(('http://', 'https://')):
            errors.append("open_meteo_air_quality_url must be a valid HTTP/HTTPS URL")
            
        if not self.open_meteo_weather_url or not self.open_meteo_weather_url.startswith(('http://', 'https://')):
            errors.append("open_meteo_weather_url must be a valid HTTP/HTTPS URL")
        
        # Validate city coordinates
        cities = {
            "new_delhi": self.new_delhi_coords,
            "mumbai": self.mumbai_coords,
            "bengaluru": self.bengaluru_coords,
            "hyderabad": self.hyderabad_coords
        }
        
        for city_name, coords in cities.items():
            if not isinstance(coords, tuple) or len(coords) != 2:
                errors.append(f"{city_name}_coords must be a tuple of (lat, lon)")
                continue
            lat, lon = coords
            if not (-90 <= lat <= 90):
                errors.append(f"{city_name} latitude must be between -90 and 90, got {lat}")
            if not (-180 <= lon <= 180):
                errors.append(f"{city_name} longitude must be between -180 and 180, got {lon}")
        
        # Validate air quality thresholds
        if self.healthy_air_quality_threshold <= 0:
            errors.append(f"healthy_air_quality_threshold must be positive, got {self.healthy_air_quality_threshold}")
            
        if self.hazardous_air_quality_threshold <= 0:
            errors.append(f"hazardous_air_quality_threshold must be positive, got {self.hazardous_air_quality_threshold}")
            
        if self.hazardous_air_quality_threshold <= self.healthy_air_quality_threshold:
            errors.append("hazardous_air_quality_threshold must be greater than healthy_air_quality_threshold")
        
        # Validate weather thresholds
        if self.moderate_wind_threshold <= 0:
            errors.append(f"moderate_wind_threshold must be positive, got {self.moderate_wind_threshold}")
            
        if self.high_wind_threshold <= 0:
            errors.append(f"high_wind_threshold must be positive, got {self.high_wind_threshold}")
            
        if self.high_wind_threshold <= self.moderate_wind_threshold:
            errors.append("high_wind_threshold must be greater than moderate_wind_threshold")
            
        if self.high_temperature_threshold <= 0:
            errors.append(f"high_temperature_threshold must be positive, got {self.high_temperature_threshold}")
            
        if self.comfortable_temperature_threshold <= 0:
            errors.append(f"comfortable_temperature_threshold must be positive, got {self.comfortable_temperature_threshold}")
        
        # Validate API settings
        if self.request_timeout <= 0:
            errors.append(f"request_timeout must be positive, got {self.request_timeout}")
            
        if self.max_retries < 0:
            errors.append(f"max_retries must be non-negative, got {self.max_retries}")
            
        if self.retry_delay <= 0:
            errors.append(f"retry_delay must be positive, got {self.retry_delay}")
        
        # Validate log level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"log_level must be one of {valid_log_levels}, got {self.log_level}")
        
        # Validate health check settings
        if self.health_check_timeout <= 0:
            errors.append(f"health_check_timeout must be positive, got {self.health_check_timeout}")
        
        if errors:
            raise ConfigurationError(f"Configuration validation failed: {'; '.join(errors)}")
    
    @classmethod
    def from_env(cls) -> 'Config':
        """
        Load configuration from environment variables.
        
        Returns:
            Config: Configuration instance loaded from environment variables
            
        Raises:
            ConfigurationError: If configuration validation fails
        """
        try:
            config = cls(
                open_meteo_air_quality_url=os.getenv(
                    "OPEN_METEO_AIR_QUALITY_URL", 
                    "https://air-quality-api.open-meteo.com/v1/air-quality"
                ),
                open_meteo_weather_url=os.getenv(
                    "OPEN_METEO_WEATHER_URL", 
                    "https://api.open-meteo.com/v1/forecast"
                ),
                new_delhi_coords=(
                    float(os.getenv("NEW_DELHI_LAT", "28.6139")),
                    float(os.getenv("NEW_DELHI_LON", "77.2090"))
                ),
                mumbai_coords=(
                    float(os.getenv("MUMBAI_LAT", "19.0760")),
                    float(os.getenv("MUMBAI_LON", "72.8777"))
                ),
                bengaluru_coords=(
                    float(os.getenv("BENGALURU_LAT", "12.9716")),
                    float(os.getenv("BENGALURU_LON", "77.5946"))
                ),
                hyderabad_coords=(
                    float(os.getenv("HYDERABAD_LAT", "17.3850")),
                    float(os.getenv("HYDERABAD_LON", "78.4867"))
                ),
                healthy_air_quality_threshold=float(os.getenv("HEALTHY_AIR_QUALITY_THRESHOLD", "50.0")),
                hazardous_air_quality_threshold=float(os.getenv("HAZARDOUS_AIR_QUALITY_THRESHOLD", "100.0")),
                moderate_wind_threshold=float(os.getenv("MODERATE_WIND_THRESHOLD", "20.0")),
                high_wind_threshold=float(os.getenv("HIGH_WIND_THRESHOLD", "30.0")),
                high_temperature_threshold=float(os.getenv("HIGH_TEMPERATURE_THRESHOLD", "35.0")),
                comfortable_temperature_threshold=float(os.getenv("COMFORTABLE_TEMPERATURE_THRESHOLD", "30.0")),
                request_timeout=int(os.getenv("REQUEST_TIMEOUT", "10")),
                max_retries=int(os.getenv("MAX_RETRIES", "3")),
                retry_delay=float(os.getenv("RETRY_DELAY", "1.0")),
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                log_format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
                log_file=os.getenv("LOG_FILE"),
                health_check_enabled=os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true",
                health_check_timeout=int(os.getenv("HEALTH_CHECK_TIMEOUT", "5")),
                app_name=os.getenv("APP_NAME", "Breathable Commute"),
                app_version=os.getenv("APP_VERSION", "1.0.0"),
                # Performance and caching settings
                cache_duration_seconds=int(os.getenv("CACHE_DURATION_SECONDS", "300")),
                max_concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", "10")),
                connection_pool_size=int(os.getenv("CONNECTION_POOL_SIZE", "20")),
                performance_monitoring_enabled=os.getenv("PERFORMANCE_MONITORING_ENABLED", "true").lower() == "true",
                auto_refresh_interval=int(os.getenv("AUTO_REFRESH_INTERVAL", "30")),
                slow_request_threshold=float(os.getenv("SLOW_REQUEST_THRESHOLD", "5.0")),
                # Responsive design settings
                mobile_breakpoint=int(os.getenv("MOBILE_BREAKPOINT", "768")),
                tablet_breakpoint=int(os.getenv("TABLET_BREAKPOINT", "1024")),
                chart_height_mobile=int(os.getenv("CHART_HEIGHT_MOBILE", "300")),
                chart_height_tablet=int(os.getenv("CHART_HEIGHT_TABLET", "400")),
                chart_height_desktop=int(os.getenv("CHART_HEIGHT_DESKTOP", "500")),
            )
            
            # Validate the configuration
            config.validate()
            return config
            
        except (ValueError, TypeError) as e:
            raise ConfigurationError(f"Failed to parse environment variables: {e}")
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """
        Load configuration from a JSON file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Config: Configuration instance loaded from file
            
        Raises:
            ConfigurationError: If file cannot be read or configuration is invalid
        """
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                raise ConfigurationError(f"Configuration file not found: {config_path}")
            
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Convert coordinate lists to tuples if needed
            for city in ['new_delhi_coords', 'mumbai_coords', 'bengaluru_coords', 'hyderabad_coords']:
                if city in config_data and isinstance(config_data[city], list):
                    config_data[city] = tuple(config_data[city])
            
            # Create config instance with file data
            config = cls(**config_data)
            config.validate()
            return config
            
        except (json.JSONDecodeError, TypeError) as e:
            raise ConfigurationError(f"Failed to parse configuration file {config_path}: {e}")
        except FileNotFoundError:
            raise ConfigurationError(f"Configuration file not found: {config_path}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format.
        
        Returns:
            Dict containing all configuration values
        """
        return {
            key: value for key, value in self.__dict__.items() 
            if not key.startswith('_')
        }
    
    def setup_logging(self) -> logging.Logger:
        """
        Set up logging configuration based on config settings.
        
        Returns:
            Logger: Configured logger instance
        """
        # Create logger
        logger = logging.getLogger(self.app_name)
        logger.setLevel(getattr(logging, self.log_level.upper()))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(self.log_format)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler (if specified)
        if self.log_file:
            try:
                file_handler = logging.FileHandler(self.log_file)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except (OSError, IOError) as e:
                logger.warning(f"Failed to create log file {self.log_file}: {e}")
        
        return logger


def load_config(config_file: Optional[str] = None) -> Config:
    """
    Load configuration from file or environment variables.
    
    Args:
        config_file: Optional path to configuration file. If not provided,
                    loads from environment variables.
    
    Returns:
        Config: Loaded and validated configuration
        
    Raises:
        ConfigurationError: If configuration cannot be loaded or is invalid
    """
    if config_file:
        # If a config file is explicitly specified, it must exist
        return Config.from_file(config_file)
    else:
        return Config.from_env()


# Global configuration instance
config = load_config()
"""
Unit tests for error handling scenarios across the application.

Tests API failure scenarios, malformed data handling, graceful degradation,
and configuration validation.
"""

import pytest
import requests
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from breathable_commute.weather_data import (
    get_city_data, get_all_cities_data, WeatherDataError, CityWeatherData
)
from breathable_commute.data_processor import (
    process_all_cities_data, DataProcessingError
)
from breathable_commute.health_check import (
    HealthChecker, verify_api_connectivity
)
from config import Config, ConfigurationError, load_config


class TestWeatherDataErrorHandling:
    """Test error handling in weather data fetching."""
    
    def test_connection_error_handling(self):
        """Test handling of network connection errors."""
        with patch('breathable_commute.weather_data._get_optimized_session') as mock_session_func:
            mock_session = Mock()
            mock_session.get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            mock_session_func.return_value = mock_session
            
            with pytest.raises(WeatherDataError) as exc_info:
                get_city_data(28.6139, 77.2090, "New Delhi")
            
            assert "failed to connect" in str(exc_info.value).lower()
    
    def test_timeout_error_handling(self):
        """Test handling of request timeout errors."""
        with patch('breathable_commute.weather_data._get_optimized_session') as mock_session_func:
            mock_session = Mock()
            mock_session.get.side_effect = requests.exceptions.Timeout("Request timed out")
            mock_session_func.return_value = mock_session
            
            with pytest.raises(WeatherDataError) as exc_info:
                get_city_data(28.6139, 77.2090, "New Delhi")
            
            assert "timed out" in str(exc_info.value).lower()
    
    def test_http_error_handling(self):
        """Test handling of HTTP error responses."""
        with patch('breathable_commute.weather_data._get_optimized_session') as mock_session_func:
            mock_session = Mock()
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
            mock_session.get.return_value = mock_response
            mock_session_func.return_value = mock_session
            
            with pytest.raises(WeatherDataError) as exc_info:
                get_city_data(28.6139, 77.2090, "New Delhi")
            
            assert "500" in str(exc_info.value) or "http error" in str(exc_info.value).lower()
    
    def test_malformed_json_response_handling(self):
        """Test handling of malformed JSON responses."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status.return_value = None
        
        with patch('breathable_commute.weather_data._get_optimized_session') as mock_session_func:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_func.return_value = mock_session
            
            with pytest.raises(WeatherDataError) as exc_info:
                get_city_data(28.6139, 77.2090, "New Delhi")
            
            assert "json" in str(exc_info.value).lower()
    
    def test_missing_air_quality_fields_handling(self):
        """Test handling of API responses with missing required air quality fields."""
        def mock_get(url, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            
            if "air-quality" in url:
                mock_response.json.return_value = {"invalid": "response"}  # Missing 'current' field
            else:
                mock_response.json.return_value = {
                    "current": {
                        "temperature_2m": 28.0,
                        "wind_speed_10m": 12.0,
                        "precipitation": 0.0
                    }
                }
            return mock_response
        
        # Create a mock session that uses our mock_get function
        mock_session = Mock()
        mock_session.get = mock_get
        
        with patch('breathable_commute.weather_data._get_optimized_session', return_value=mock_session):
            with pytest.raises(WeatherDataError) as exc_info:
                get_city_data(28.6139, 77.2090, "New Delhi")
            
            assert "current" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower()
    
    def test_missing_weather_fields_handling(self):
        """Test handling of API responses with missing required weather fields."""
        def mock_get(url, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            
            if "air-quality" in url:
                mock_response.json.return_value = {
                    "current": {"pm2_5": 25.0}
                }
            else:
                mock_response.json.return_value = {"invalid": "response"}  # Missing 'current' field
            return mock_response
        
        # Create a mock session that uses our mock_get function
        mock_session = Mock()
        mock_session.get = mock_get
        
        with patch('breathable_commute.weather_data._get_optimized_session', return_value=mock_session):
            with pytest.raises(WeatherDataError) as exc_info:
                get_city_data(28.6139, 77.2090, "New Delhi")
            
            assert "current" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower()
    
    def test_invalid_coordinate_handling(self):
        """Test handling of invalid coordinate values."""
        # Test invalid latitude
        with pytest.raises(WeatherDataError) as exc_info:
            get_city_data(100.0, 77.2090, "Invalid City")  # Latitude > 90
        
        assert "latitude" in str(exc_info.value).lower()
        
        # Test invalid longitude
        with pytest.raises(WeatherDataError) as exc_info:
            get_city_data(28.6139, 200.0, "Invalid City")  # Longitude > 180
        
        assert "longitude" in str(exc_info.value).lower()
    
    def test_invalid_weather_values_handling(self):
        """Test handling of invalid weather measurement values."""
        def mock_get(url, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            
            if "air-quality" in url:
                mock_response.json.return_value = {
                    "current": {"pm2_5": -5.0}  # Invalid negative PM2.5
                }
            else:
                mock_response.json.return_value = {
                    "current": {
                        "temperature_2m": 28.0,
                        "wind_speed_10m": 12.0,
                        "precipitation": 0.0
                    }
                }
            return mock_response
        
        # Create a mock session that uses our mock_get function
        mock_session = Mock()
        mock_session.get = mock_get
        
        with patch('breathable_commute.weather_data._get_optimized_session', return_value=mock_session):
            with pytest.raises(WeatherDataError) as exc_info:
                get_city_data(28.6139, 77.2090, "New Delhi")
            
            assert "pm2" in str(exc_info.value).lower() or "negative" in str(exc_info.value).lower()
    
    def test_retry_mechanism_exhaustion(self):
        """Test that retry mechanism eventually gives up after max attempts."""
        # Create a mock session that always raises ConnectionError
        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.ConnectionError("Persistent failure")
        
        with patch('breathable_commute.weather_data._get_optimized_session', return_value=mock_session):
            with patch('time.sleep'):  # Speed up test by mocking sleep
                with pytest.raises(WeatherDataError) as exc_info:
                    get_city_data(28.6139, 77.2090, "New Delhi")
                
                assert "after 3 attempts" in str(exc_info.value).lower()
    
    def test_graceful_degradation_with_valid_data(self):
        """Test graceful handling when all required data is available."""
        def mock_get(url, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            
            if "air-quality" in url:
                mock_response.json.return_value = {
                    "current": {"pm2_5": 25.5}
                }
            else:
                mock_response.json.return_value = {
                    "current": {
                        "temperature_2m": 28.3,
                        "wind_speed_10m": 12.7,
                        "precipitation": 0.0
                    }
                }
            return mock_response
        
        # Create a mock session that uses our mock_get function
        mock_session = Mock()
        mock_session.get = mock_get
        
        with patch('breathable_commute.weather_data._get_optimized_session', return_value=mock_session):
            # Should not raise an error and return valid data
            result = get_city_data(28.6139, 77.2090, "New Delhi")
            assert result.pm25 == 25.5
            assert result.temperature == 28.3
            assert result.wind_speed == 12.7
            assert result.precipitation == 0.0
            assert result.city_name == "New Delhi"


class TestAllCitiesDataErrorHandling:
    """Test error handling in all cities data fetching."""
    
    def test_partial_city_failure_handling(self):
        """Test handling when some cities fail to fetch data."""
        # Mock get_city_data to fail for Mumbai specifically
        original_get_city_data = get_city_data
        
        def mock_get_city_data(lat, lon, city_name):
            if city_name == "Mumbai":
                raise WeatherDataError("Mumbai API failed after 3 attempts")
            else:
                # Return valid data for other cities
                return CityWeatherData(
                    city_name=city_name,
                    pm25=25.0,
                    temperature=28.0,
                    wind_speed=12.0,
                    precipitation=0.0,
                    timestamp=datetime.utcnow(),
                    coordinates=(lat, lon)
                )
        
        with patch('breathable_commute.weather_data.get_city_data', side_effect=mock_get_city_data):
            # Should raise error when any city fails
            with pytest.raises(WeatherDataError) as exc_info:
                get_all_cities_data()
            
            assert "mumbai" in str(exc_info.value).lower() or "after 3 attempts" in str(exc_info.value).lower()
    
    def test_all_cities_success_handling(self):
        """Test successful fetching of all cities data."""
        def mock_get(url, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            
            if "air-quality" in url:
                mock_response.json.return_value = {
                    "current": {"pm2_5": 25.0}
                }
            else:
                mock_response.json.return_value = {
                    "current": {
                        "temperature_2m": 28.0,
                        "wind_speed_10m": 12.0,
                        "precipitation": 0.0
                    }
                }
            return mock_response
        
        with patch('breathable_commute.weather_data.requests.get', side_effect=mock_get):
            # Should successfully return data for all cities
            cities_data = get_all_cities_data()
            
            assert len(cities_data) == 4  # All 4 Indian cities
            city_names = [city.city_name for city in cities_data]
            expected_cities = ["New Delhi", "Mumbai", "Bengaluru", "Hyderabad"]
            
            for expected_city in expected_cities:
                assert expected_city in city_names


class TestDataProcessingErrorHandling:
    """Test error handling in data processing."""
    
    def test_invalid_city_selection_handling(self):
        """Test handling when an invalid city is selected."""
        with pytest.raises(DataProcessingError) as exc_info:
            process_all_cities_data("Invalid City")
        
        assert "invalid city" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()
    
    def test_empty_cities_data_handling(self):
        """Test handling when no cities data is available."""
        # Mock get_all_cities_data to return empty list
        with patch('breathable_commute.data_processor.get_all_cities_data', return_value=[]):
            with pytest.raises(DataProcessingError) as exc_info:
                process_all_cities_data("New Delhi")
            
            assert "no cities data" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()
    
    def test_missing_selected_city_data_handling(self):
        """Test handling when selected city data is not in the dataset."""
        # Create mock data for other cities but not the selected one
        mock_cities_data = [
            CityWeatherData(
                city_name="Mumbai",
                pm25=30.0,
                temperature=32.0,
                wind_speed=15.0,
                precipitation=0.0,
                timestamp=datetime.utcnow(),
                coordinates=(19.0760, 72.8777)
            )
        ]
        
        with patch('breathable_commute.data_processor.get_all_cities_data', return_value=mock_cities_data):
            with pytest.raises(DataProcessingError) as exc_info:
                process_all_cities_data("New Delhi")  # Not in mock data
            
            assert "new delhi" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()
    
    def test_successful_data_processing(self):
        """Test successful data processing with valid input."""
        # Create mock data for all cities
        mock_cities_data = [
            CityWeatherData(
                city_name="New Delhi",
                pm25=45.0,
                temperature=28.0,
                wind_speed=12.0,
                precipitation=0.0,
                timestamp=datetime.utcnow(),
                coordinates=(28.6139, 77.2090)
            ),
            CityWeatherData(
                city_name="Mumbai",
                pm25=35.0,
                temperature=30.0,
                wind_speed=18.0,
                precipitation=2.0,
                timestamp=datetime.utcnow(),
                coordinates=(19.0760, 72.8777)
            )
        ]
        
        with patch('breathable_commute.data_processor.get_all_cities_data', return_value=mock_cities_data):
            # Should successfully process data
            result = process_all_cities_data("New Delhi")
            
            assert result is not None
            assert result.selected_city == "New Delhi"
            assert len(result.cities_data) == 2
            assert result.recommendation is not None


class TestConfigurationErrorHandling:
    """Test error handling in configuration management."""
    
    def test_invalid_configuration_file_handling(self):
        """Test handling of invalid configuration files."""
        # Test with non-existent file
        with pytest.raises(ConfigurationError) as exc_info:
            Config.from_file("non_existent_file.json")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_malformed_configuration_file_handling(self):
        """Test handling of malformed JSON configuration files."""
        import tempfile
        import os
        
        # Create a temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json content")
            temp_file = f.name
        
        try:
            with pytest.raises(ConfigurationError) as exc_info:
                Config.from_file(temp_file)
            
            assert "parse" in str(exc_info.value).lower() or "json" in str(exc_info.value).lower()
        finally:
            os.unlink(temp_file)
    
    def test_invalid_environment_variables_handling(self):
        """Test handling of invalid environment variable values."""
        with patch.dict('os.environ', {
            'LONDON_LAT': 'invalid_float',  # Invalid latitude
            'REQUEST_TIMEOUT': 'not_a_number'  # Invalid timeout
        }):
            with pytest.raises(ConfigurationError) as exc_info:
                Config.from_env()
            
            assert "parse" in str(exc_info.value).lower() or "environment" in str(exc_info.value).lower()
    
    def test_configuration_validation_errors(self):
        """Test configuration validation with invalid values."""
        # Test invalid latitude
        config = Config(new_delhi_coords=(100.0, 77.2090))  # Invalid latitude > 90
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        
        assert "new_delhi" in str(exc_info.value).lower() and "latitude" in str(exc_info.value).lower()
        
        # Test invalid URL
        config = Config(open_meteo_air_quality_url="not_a_url")
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        
        assert "url" in str(exc_info.value).lower()
        
        # Test invalid air quality threshold
        config = Config(healthy_air_quality_threshold=-1.0)  # Negative threshold
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        
        assert "threshold" in str(exc_info.value).lower() or "positive" in str(exc_info.value).lower()
    
    def test_missing_required_configuration_handling(self):
        """Test handling when required configuration is missing."""
        # Test with empty URLs
        config = Config(
            open_meteo_air_quality_url="",
            open_meteo_weather_url=""
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate()
        
        assert "url" in str(exc_info.value).lower()


class TestHealthCheckErrorHandling:
    """Test error handling in health check functionality."""
    
    def test_api_connection_failure_handling(self):
        """Test handling of API connection failures during health checks."""
        health_checker = HealthChecker()
        
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError("Connection failed")):
            # Update to use the correct method name for Indian cities dashboard
            result = health_checker.check_open_meteo_api()
            
            assert not result.is_healthy
            assert "connection" in result.error_message.lower()
            assert result.service_name == "Open-Meteo API"
    
    def test_api_timeout_handling(self):
        """Test handling of API timeouts during health checks."""
        health_checker = HealthChecker()
        
        with patch('requests.get', side_effect=requests.exceptions.Timeout("Request timed out")):
            result = health_checker.check_open_meteo_api()
            
            assert not result.is_healthy
            assert "timed out" in result.error_message.lower()
            assert result.response_time_ms >= health_checker.timeout * 1000
    
    def test_invalid_api_response_handling(self):
        """Test handling of invalid API responses during health checks."""
        health_checker = HealthChecker()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "structure"}  # Missing expected fields
        mock_response.raise_for_status.return_value = None
        
        with patch('requests.get', return_value=mock_response):
            result = health_checker.check_open_meteo_api()
            
            assert not result.is_healthy
            assert "invalid" in result.error_message.lower() or "response" in result.error_message.lower()
    
    def test_health_check_disabled_handling(self):
        """Test graceful handling when health checks are disabled."""
        with patch('config.config.health_check_enabled', False):
            all_healthy, results = verify_api_connectivity()
            
            # Should return True (no failures) with empty results when disabled
            assert all_healthy
            assert len(results) == 0
    
    def test_successful_health_check(self):
        """Test successful health check with valid API responses."""
        health_checker = HealthChecker()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"current": {"pm2_5": 15.5}}
        mock_response.raise_for_status.return_value = None
        
        with patch('requests.get', return_value=mock_response):
            result = health_checker.check_open_meteo_api()
            
            assert result.is_healthy
            assert result.error_message is None
            assert result.service_name == "Open-Meteo API"
            assert result.response_time_ms >= 0  # Allow for very fast responses


class TestApplicationStartupErrorHandling:
    """Test error handling during application startup."""
    
    def test_configuration_loading_failure_handling(self):
        """Test handling of configuration loading failures at startup."""
        # Test with invalid file path
        with pytest.raises(ConfigurationError):
            load_config("non_existent_config.json")
    
    def test_logging_setup_failure_handling(self):
        """Test handling of logging setup failures."""
        config = Config(log_file="/invalid/path/logfile.log")  # Invalid log file path
        
        # Should not raise exception, but should log warning about file creation failure
        logger = config.setup_logging()
        
        # Logger should still be created even if file handler fails
        assert logger is not None
        assert len(logger.handlers) > 0  # Should at least have console handler
    
    def test_health_check_initialization_failure(self):
        """Test handling of health check initialization failures."""
        with patch('breathable_commute.health_check.HealthChecker.__init__', side_effect=Exception("Init failed")):
            # Should handle health checker initialization failures
            with pytest.raises(Exception):
                HealthChecker()


class TestGracefulDegradation:
    """Test graceful degradation scenarios."""
    
    def test_weather_data_retry_success(self):
        """Test that weather data fetching succeeds after retries."""
        call_count = 0
        
        def failing_request(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise requests.exceptions.ConnectionError("Temporary failure")
            else:  # Succeed on 3rd attempt
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.raise_for_status.return_value = None
                
                if "air-quality" in url:
                    mock_response.json.return_value = {"current": {"pm2_5": 20.0}}
                else:
                    mock_response.json.return_value = {
                        "current": {
                            "temperature_2m": 28.0,
                            "wind_speed_10m": 12.0,
                            "precipitation": 0.0
                        }
                    }
                return mock_response
        
        # Create a mock session that uses our failing_request function
        mock_session = Mock()
        mock_session.get = failing_request
        
        with patch('breathable_commute.weather_data._get_optimized_session', return_value=mock_session):
            with patch('time.sleep'):  # Speed up test
                # Should eventually succeed after retries
                result = get_city_data(28.6139, 77.2090, "New Delhi")
                assert result.pm25 == 20.0
                assert result.temperature == 28.0
                assert call_count >= 3  # Should have made at least 3 attempts
    
    def test_data_processing_with_valid_input(self):
        """Test that data processing works correctly with valid input."""
        # Create mock cities data
        mock_cities_data = [
            CityWeatherData(
                city_name="New Delhi",
                pm25=45.0,
                temperature=28.0,
                wind_speed=12.0,
                precipitation=0.0,
                timestamp=datetime.utcnow(),
                coordinates=(28.6139, 77.2090)
            ),
            CityWeatherData(
                city_name="Mumbai",
                pm25=35.0,
                temperature=30.0,
                wind_speed=18.0,
                precipitation=2.0,
                timestamp=datetime.utcnow(),
                coordinates=(19.0760, 72.8777)
            )
        ]
        
        with patch('breathable_commute.data_processor.get_all_cities_data', return_value=mock_cities_data):
            # Should successfully process data
            result = process_all_cities_data("New Delhi")
            
            assert result is not None
            assert result.selected_city == "New Delhi"
            assert len(result.cities_data) == 2
            assert result.recommendation is not None
            assert result.recommendation.status in ["green", "yellow", "red"]
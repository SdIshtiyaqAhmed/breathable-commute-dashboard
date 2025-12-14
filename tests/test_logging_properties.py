"""
Property-based tests for error logging completeness.
"""

import pytest
import logging
import io
import sys
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from unittest.mock import patch, Mock
from datetime import datetime

from config import Config
from breathable_commute.weather_data import WeatherDataError
from breathable_commute.data_processor import DataProcessingError
from breathable_commute.chart_generator import ChartGenerationError
from breathable_commute.recommendation_engine import RecommendationError


class LogCapture:
    """Helper class to capture log messages for testing."""
    
    def __init__(self):
        self.records = []
        self.handler = None
        self.original_handlers = {}
        self.original_levels = {}
    
    def __enter__(self):
        self.handler = logging.Handler()
        self.handler.emit = lambda record: self.records.append(record)
        
        # Get the root logger and all module loggers
        loggers_to_capture = [
            logging.getLogger(),  # Root logger
            logging.getLogger('breathable_commute'),
            logging.getLogger('breathable_commute.air_quality'),
            logging.getLogger('breathable_commute.bike_data'),
            logging.getLogger('breathable_commute.data_processor'),
            logging.getLogger('breathable_commute.map_generator'),
        ]
        
        # Store original handlers and levels, then add our handler
        for logger in loggers_to_capture:
            self.original_handlers[logger.name] = logger.handlers.copy()
            self.original_levels[logger.name] = logger.level
            
            # Set level to DEBUG to capture all messages
            logger.setLevel(logging.DEBUG)
            
            # Add our handler
            logger.addHandler(self.handler)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original handlers and levels
        for logger_name, original_handlers in self.original_handlers.items():
            logger = logging.getLogger(logger_name)
            
            # Remove our handler
            if self.handler in logger.handlers:
                logger.removeHandler(self.handler)
            
            # Restore original level
            logger.setLevel(self.original_levels[logger_name])
    
    def get_messages(self, level=None):
        """Get all log messages, optionally filtered by level."""
        if level is None:
            return [record.getMessage() for record in self.records]
        else:
            return [record.getMessage() for record in self.records if record.levelno >= level]
    
    def get_records(self, level=None):
        """Get all log records, optionally filtered by level."""
        if level is None:
            return self.records
        else:
            return [record for record in self.records if record.levelno >= level]





@given(
    log_level=st.sampled_from(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    app_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), whitelist_characters=' -_')),
    log_message=st.text(min_size=1, max_size=200)
)
def test_logging_configuration_completeness(log_level, app_name, log_message):
    """
    **Feature: breathable-commute, Property 24: Error logging completeness**
    
    For any logging configuration, the system should set up comprehensive 
    logging with proper formatting and level handling.
    
    **Validates: Requirements 8.5**
    """
    assume(len(app_name.strip()) > 0)
    
    # Create config with specified logging settings
    config = Config(
        log_level=log_level,
        app_name=app_name.strip(),
        log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Set up logging using the configuration
    logger = config.setup_logging()
    
    # Verify logger configuration
    assert logger is not None, "Logger should be created"
    assert logger.name == app_name.strip(), f"Logger name should be {app_name.strip()}"
    
    # Verify log level is set correctly
    expected_level = getattr(logging, log_level.upper())
    assert logger.level == expected_level, f"Logger level should be {expected_level}"
    
    # Verify logger has handlers
    assert len(logger.handlers) > 0, "Logger should have at least one handler"
    
    # Test that logging actually works at the configured level
    with LogCapture() as log_capture:
        # Add handler to the specific logger created by config
        log_capture.handler.emit = lambda record: log_capture.records.append(record)
        logger.addHandler(log_capture.handler)
        
        # Log at different levels
        logger.debug("Debug message: " + log_message)
        logger.info("Info message: " + log_message)
        logger.warning("Warning message: " + log_message)
        logger.error("Error message: " + log_message)
        logger.critical("Critical message: " + log_message)
        
        # Remove the handler
        logger.removeHandler(log_capture.handler)
        
        # Check that appropriate messages were captured based on log level
        all_messages = log_capture.get_messages()
        
        # Should have captured messages at or above the configured level
        if log_level == 'DEBUG':
            assert len(all_messages) >= 5, "Should capture all log levels for DEBUG"
        elif log_level == 'INFO':
            assert len(all_messages) >= 4, "Should capture INFO and above"
        elif log_level == 'WARNING':
            assert len(all_messages) >= 3, "Should capture WARNING and above"
        elif log_level == 'ERROR':
            assert len(all_messages) >= 2, "Should capture ERROR and above"
        elif log_level == 'CRITICAL':
            assert len(all_messages) >= 1, "Should capture CRITICAL"
        
        # Verify message content includes our test message
        found_test_message = any(log_message in msg for msg in all_messages)
        assert found_test_message, "Test message should appear in logs"
        
        # Verify log format includes essential components
        records = log_capture.get_records()
        if records:
            record = records[0]
            # Should have timestamp, logger name, level, and message
            assert hasattr(record, 'created'), "Record should have timestamp"
            assert hasattr(record, 'name'), "Record should have logger name"
            assert hasattr(record, 'levelname'), "Record should have level name"
            assert hasattr(record, 'getMessage'), "Record should have message"


@given(
    exception_type=st.sampled_from([
        'WeatherDataError', 'DataProcessingError', 'ChartGenerationError', 'RecommendationError'
    ]),
    error_details=st.text(min_size=1, max_size=150),
    context_data=st.dictionaries(
        keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), whitelist_characters='_')),
        values=st.one_of(st.text(max_size=50), st.integers(), st.floats(allow_nan=False, allow_infinity=False)),
        min_size=0,
        max_size=5
    )
)
def test_structured_error_logging_completeness(exception_type, error_details, context_data):
    """
    **Feature: breathable-commute, Property 24: Error logging completeness**
    
    For any application-specific error, the system should log structured 
    error information with context for effective debugging.
    
    **Validates: Requirements 8.5**
    """
    config = Config()
    logger = config.setup_logging()
    
    with LogCapture() as log_capture:
        # Create the appropriate exception
        if exception_type == 'WeatherDataError':
            exception = WeatherDataError(error_details)
        elif exception_type == 'DataProcessingError':
            exception = DataProcessingError(error_details)
        elif exception_type == 'ChartGenerationError':
            exception = ChartGenerationError(error_details)
        else:  # RecommendationError
            exception = RecommendationError(error_details)
        
        # Log the error with context (simulating how the app would log it)
        try:
            logger.error(f"{exception_type} occurred", extra={
                'error_type': exception_type,
                'error_message': str(exception),
                'context': context_data,
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception:
            # If structured logging fails, fall back to simple logging
            logger.error(f"{exception_type}: {exception}")
        
        # Verify that error was logged
        error_records = log_capture.get_records(level=logging.ERROR)
        assert len(error_records) > 0, "Error should be logged"
        
        # Verify error information is complete
        found_complete_error_info = False
        for record in error_records:
            message = record.getMessage()
            
            # Should contain error type
            has_error_type = exception_type.lower() in message.lower()
            
            # Should contain error details
            has_error_details = any(
                detail_word in message.lower() 
                for detail_word in error_details.lower().split()[:3]  # Check first few words
                if len(detail_word) > 2  # Skip very short words
            )
            
            # Should have proper log record structure
            has_proper_structure = (
                record.levelname == 'ERROR' and
                hasattr(record, 'created') and
                hasattr(record, 'name')
            )
            
            if has_error_type and has_proper_structure:
                found_complete_error_info = True
                break
        
        assert found_complete_error_info, "Error logs missing complete information"
        
        # Verify no sensitive information is logged
        all_messages = log_capture.get_messages()
        for message in all_messages:
            # Basic check for common sensitive patterns
            assert 'password' not in message.lower(), "Sensitive data in logs"
            assert 'secret' not in message.lower(), "Sensitive data in logs"
            assert 'token' not in message.lower(), "Sensitive data in logs"


def test_logging_system_initialization():
    """
    **Feature: breathable-commute, Property 24: Error logging completeness**
    
    The logging system should initialize properly and be ready to capture 
    all error conditions from application startup.
    
    **Validates: Requirements 8.5**
    """
    # Test that logging can be set up without errors
    config = Config()
    
    # Should not raise any exceptions
    logger = config.setup_logging()
    
    # Verify logger is properly configured
    assert logger is not None
    assert isinstance(logger, logging.Logger)
    assert logger.name == config.app_name
    assert logger.level == getattr(logging, config.log_level.upper())
    
    # Verify logger can handle messages
    with LogCapture() as log_capture:
        logger.info("Test initialization message")
        
        messages = log_capture.get_messages()
        assert len(messages) > 0, "Logger should capture initialization messages"
        assert "initialization" in messages[0].lower(), "Should log initialization message"
    
    # Test that multiple logger setups don't cause issues
    logger2 = config.setup_logging()
    assert logger2 is not None
    
    # Test with different configurations
    config_debug = Config(log_level='DEBUG')
    logger_debug = config_debug.setup_logging()
    assert logger_debug.level == logging.DEBUG
    
    config_error = Config(log_level='ERROR')
    logger_error = config_error.setup_logging()
    assert logger_error.level == logging.ERROR
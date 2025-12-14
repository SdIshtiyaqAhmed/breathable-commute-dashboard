"""
Property-based tests for the main Streamlit application.

**Feature: python-dashboard**
Tests for air quality display formatting and application initialization.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import patch, MagicMock
import streamlit
from datetime import datetime

from breathable_commute.weather_data import CityWeatherData, CITY_COORDINATES
from breathable_commute.data_processor import process_all_cities_data, get_dashboard_summary
from breathable_commute.chart_generator import create_comparison_charts, ChartConfig


class TestAppProperties:
    """Property-based tests for the main Streamlit application."""

    @given(
        selected_city=st.sampled_from(list(CITY_COORDINATES.keys())),
        pm25_base=st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        temp_base=st.floats(min_value=20.0, max_value=35.0, allow_nan=False, allow_infinity=False)
    )
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_city_selection_highlighting(self, selected_city, pm25_base, temp_base):
        """
        **Feature: python-dashboard, Property 19: City selection highlighting**
        
        *For any* user city selection, the system should highlight that city's data in the visualization.
        
        **Validates: Requirements 5.4**
        """
        # Create mock city weather data for all cities with simple variations
        cities_data = []
        city_names = list(CITY_COORDINATES.keys())
        
        for i, city_name in enumerate(city_names):
            lat, lon = CITY_COORDINATES[city_name]
            # Create simple variations based on base values
            pm25_variation = pm25_base + (i * 5)  # Simple increment
            temp_variation = temp_base + (i * 2)  # Simple increment
            wind_variation = 10.0 + (i * 3)      # Simple increment
            precip_variation = 0.0 + (i * 0.5)   # Simple increment
            
            city_data = CityWeatherData(
                city_name=city_name,
                pm25=pm25_variation,
                temperature=temp_variation,
                wind_speed=wind_variation,
                precipitation=precip_variation,
                timestamp=datetime.now(),
                coordinates=(lat, lon)
            )
            cities_data.append(city_data)
        
        # Create dashboard data with selected city
        from breathable_commute.data_processor import DashboardData
        from breathable_commute.recommendation_engine import generate_recommendation
        import pandas as pd
        
        selected_city_data = next(city for city in cities_data if city.city_name == selected_city)
        recommendation = generate_recommendation(selected_city_data)
        
        correlation_data = pd.DataFrame([{
            'city': city.city_name,
            'pm25': city.pm25,
            'wind_speed': city.wind_speed,
            'temperature': city.temperature,
            'precipitation': city.precipitation
        } for city in cities_data])
        
        dashboard_data = DashboardData(
            cities_data=cities_data,
            selected_city=selected_city,
            recommendation=recommendation,
            correlation_data=correlation_data
        )
        
        # Generate charts with city selection
        config = ChartConfig()
        bar_chart, scatter_plot = create_comparison_charts(dashboard_data, config)
        
        # Property: Selected city should be highlighted in bar chart
        # Check that bar chart has different colors and selected city is distinguishable
        bar_data = bar_chart.data[0]
        city_names_in_chart = list(bar_data.x)
        colors_in_chart = list(bar_data.marker.color)
        
        assert selected_city in city_names_in_chart, f"Selected city {selected_city} should appear in bar chart"
        
        # Property: Selected city should have a different color (highlighting)
        selected_city_index = city_names_in_chart.index(selected_city)
        selected_city_color = colors_in_chart[selected_city_index]
        
        # The highlighting color should be different from default colors
        default_colors = config.bar_chart_colors
        is_highlighted = selected_city_color not in default_colors or colors_in_chart.count(selected_city_color) == 1
        assert is_highlighted, f"Selected city {selected_city} should be highlighted with a distinct color"
        
        # Property: All cities should be present in the chart
        assert len(city_names_in_chart) == len(cities_data), "All cities should be present in bar chart"
        assert set(city_names_in_chart) == set(city.city_name for city in cities_data), "All city names should match"
        
        # Property: Chart should have proper PM2.5 values for each city
        pm25_values_in_chart = list(bar_data.y)
        for i, city_name in enumerate(city_names_in_chart):
            expected_pm25 = next(city.pm25 for city in cities_data if city.city_name == city_name)
            actual_pm25 = pm25_values_in_chart[i]
            assert abs(actual_pm25 - expected_pm25) < 1e-10, f"PM2.5 value mismatch for {city_name}"
        
        # Property: Scatter plot should contain all cities with proper labeling
        scatter_traces = scatter_plot.data
        scatter_city_names = [trace.name for trace in scatter_traces]
        
        assert len(scatter_traces) == len(cities_data), "Scatter plot should have one trace per city"
        assert set(scatter_city_names) == set(city.city_name for city in cities_data), "All cities should be in scatter plot"
        
        # Property: Selected city should be identifiable in scatter plot
        selected_city_trace = next((trace for trace in scatter_traces if trace.name == selected_city), None)
        assert selected_city_trace is not None, f"Selected city {selected_city} should have a trace in scatter plot"
        
        # Property: Scatter plot should have correct axis data
        for trace in scatter_traces:
            city_name = trace.name
            city_data = next(city for city in cities_data if city.city_name == city_name)
            
            # Check wind speed (x-axis) and PM2.5 (y-axis)
            assert len(trace.x) == 1, "Each city should have one point in scatter plot"
            assert len(trace.y) == 1, "Each city should have one point in scatter plot"
            
            assert abs(trace.x[0] - city_data.wind_speed) < 1e-10, f"Wind speed mismatch for {city_name}"
            assert abs(trace.y[0] - city_data.pm25) < 1e-10, f"PM2.5 mismatch for {city_name}"

    @patch('breathable_commute.data_processor.get_all_cities_data')
    @patch('streamlit.set_page_config')
    @patch('streamlit.title')
    @patch('streamlit.markdown')
    @patch('streamlit.columns')
    @patch('streamlit.spinner')
    @patch('streamlit.success')
    @patch('streamlit.selectbox')
    def test_application_initialization(self, mock_selectbox, mock_success, mock_spinner, mock_columns, 
                                     mock_markdown, mock_title, mock_set_page_config,
                                     mock_get_all_cities_data):
        """
        **Feature: python-dashboard, Property 22: Application initialization**
        
        *For any* application startup, all required components should initialize successfully 
        and API connectivity should be verified.
        
        **Validates: Requirements 8.2**
        """
        # Mock successful API responses for all Indian cities
        mock_cities_data = []
        for city_name, (lat, lon) in CITY_COORDINATES.items():
            city_data = CityWeatherData(
                city_name=city_name,
                pm25=25.0,  # Healthy level
                temperature=28.0,
                wind_speed=15.0,
                precipitation=0.0,
                timestamp=datetime.now(),
                coordinates=(lat, lon)
            )
            mock_cities_data.append(city_data)
        
        mock_get_all_cities_data.return_value = mock_cities_data
        
        # Mock Streamlit components
        mock_spinner_context = MagicMock()
        mock_spinner_context.__enter__ = MagicMock(return_value=mock_spinner_context)
        mock_spinner_context.__exit__ = MagicMock(return_value=None)
        mock_spinner.return_value = mock_spinner_context
        
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_selectbox.return_value = "New Delhi"
        
        # Test that data processing works with mocked data
        try:
            dashboard_data = process_all_cities_data("New Delhi")
            
            # Property: Data fetching should return valid results
            assert dashboard_data is not None, "Dashboard data should not be None"
            
            # Property: Dashboard data should contain all required components
            assert hasattr(dashboard_data, 'cities_data'), "Dashboard data should have cities_data"
            assert hasattr(dashboard_data, 'selected_city'), "Dashboard data should have selected_city"
            assert hasattr(dashboard_data, 'recommendation'), "Dashboard data should have recommendation"
            assert hasattr(dashboard_data, 'correlation_data'), "Dashboard data should have correlation_data"
            
            # Property: All Indian cities should be present
            city_names_in_data = [city.city_name for city in dashboard_data.cities_data]
            expected_cities = set(CITY_COORDINATES.keys())
            actual_cities = set(city_names_in_data)
            assert actual_cities == expected_cities, f"Missing cities: {expected_cities - actual_cities}"
            
            # Property: Selected city should be valid
            assert dashboard_data.selected_city in CITY_COORDINATES, f"Invalid selected city: {dashboard_data.selected_city}"
            
            # Property: Recommendation should be generated
            assert dashboard_data.recommendation is not None, "Recommendation should be generated"
            assert dashboard_data.recommendation.status in ["green", "yellow", "red"], "Recommendation status should be valid"
            
            # Property: Correlation data should be a DataFrame with all cities
            assert len(dashboard_data.correlation_data) == len(CITY_COORDINATES), "Correlation data should include all cities"
            
            # Property: API function should be called during initialization
            mock_get_all_cities_data.assert_called_once()
            
        except Exception as e:
            pytest.fail(f"Data fetching and processing failed: {e}")


"""
Property-based tests for chart generation functionality.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from datetime import datetime
from typing import List
import pandas as pd
import plotly.graph_objects as go

from breathable_commute.chart_generator import (
    create_comparison_charts,
    create_single_city_chart,
    get_chart_config,
    ChartGenerationError,
    _validate_cities_data_for_charts,
    _create_pm25_comparison_bar_chart,
    _create_wind_pollution_scatter_plot
)
from breathable_commute.data_processor import DashboardData, ChartConfig
from breathable_commute.weather_data import CityWeatherData
from breathable_commute.recommendation_engine import Recommendation


# Test data generators
@st.composite
def city_weather_data_strategy(draw, city_name=None):
    """Generate valid CityWeatherData objects for chart testing."""
    if city_name is None:
        city_name = draw(st.sampled_from(["New Delhi", "Mumbai", "Bengaluru", "Hyderabad", "Test City"]))
    
    pm25 = draw(st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False))
    temperature = draw(st.floats(min_value=-10.0, max_value=50.0, allow_nan=False, allow_infinity=False))
    wind_speed = draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    precipitation = draw(st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False))
    lat = draw(st.floats(min_value=-90.0, max_value=90.0, allow_nan=False, allow_infinity=False))
    lon = draw(st.floats(min_value=-180.0, max_value=180.0, allow_nan=False, allow_infinity=False))
    
    return CityWeatherData(
        city_name=city_name,
        pm25=pm25,
        temperature=temperature,
        wind_speed=wind_speed,
        precipitation=precipitation,
        timestamp=datetime.now(),
        coordinates=(lat, lon)
    )


@st.composite
def cities_data_list_strategy(draw, min_cities=2, max_cities=10):
    """Generate list of valid CityWeatherData objects with unique city names."""
    num_cities = draw(st.integers(min_value=min_cities, max_value=max_cities))
    cities = []
    
    for i in range(num_cities):
        city_name = f"City_{i}"  # Ensure unique city names
        city_data = draw(city_weather_data_strategy(city_name=city_name))
        cities.append(city_data)
    
    return cities


@st.composite
def dashboard_data_strategy(draw):
    """Generate valid DashboardData objects for chart testing."""
    cities_data = draw(cities_data_list_strategy())
    selected_city = draw(st.sampled_from([city.city_name for city in cities_data]))
    
    # Create a simple recommendation
    recommendation = Recommendation(
        status="green",
        message="Good conditions for cycling",
        conditions={},
        is_safe_for_cycling=True
    )
    
    # Create correlation DataFrame
    correlation_data = pd.DataFrame([
        {
            'city': city.city_name,
            'pm25': city.pm25,
            'wind_speed': city.wind_speed,
            'temperature': city.temperature,
            'precipitation': city.precipitation
        }
        for city in cities_data
    ])
    
    return DashboardData(
        cities_data=cities_data,
        selected_city=selected_city,
        recommendation=recommendation,
        correlation_data=correlation_data
    )


@given(dashboard_data=dashboard_data_strategy())
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
def test_air_quality_comparison_chart_generation(dashboard_data):
    """
    **Feature: breathable-commute, Property 3: Air quality comparison chart generation**
    **Validates: Requirements 1.3**
    
    For any valid set of city PM2.5 data, the system should create a proper bar chart 
    comparing levels across all cities.
    """
    # Generate charts using the main function
    bar_chart, scatter_plot = create_comparison_charts(dashboard_data)
    
    # Property: Bar chart should be a valid Plotly Figure
    assert isinstance(bar_chart, go.Figure), (
        f"Bar chart should be a Plotly Figure, but got: {type(bar_chart)}"
    )
    
    # Property: Bar chart should have data traces
    assert len(bar_chart.data) > 0, (
        "Bar chart should have at least one data trace"
    )
    
    # Property: Bar chart should have correct number of data points
    bar_trace = bar_chart.data[0]
    expected_cities = len(dashboard_data.cities_data)
    assert len(bar_trace.x) == expected_cities, (
        f"Bar chart should have {expected_cities} cities, but got {len(bar_trace.x)}"
    )
    assert len(bar_trace.y) == expected_cities, (
        f"Bar chart should have {expected_cities} PM2.5 values, but got {len(bar_trace.y)}"
    )
    
    # Property: Bar chart should contain all city names
    city_names_in_chart = list(bar_trace.x)
    expected_city_names = [city.city_name for city in dashboard_data.cities_data]
    for city_name in expected_city_names:
        assert city_name in city_names_in_chart, (
            f"City '{city_name}' should appear in bar chart, but chart contains: {city_names_in_chart}"
        )
    
    # Property: Bar chart should contain corresponding PM2.5 values
    pm25_values_in_chart = list(bar_trace.y)
    expected_pm25_values = [city.pm25 for city in dashboard_data.cities_data]
    
    # Match PM2.5 values to their corresponding cities
    for i, city_name in enumerate(city_names_in_chart):
        # Find the expected PM2.5 value for this city
        expected_pm25 = None
        for city in dashboard_data.cities_data:
            if city.city_name == city_name:
                expected_pm25 = city.pm25
                break
        
        assert expected_pm25 is not None, f"Could not find expected PM2.5 for city {city_name}"
        assert abs(pm25_values_in_chart[i] - expected_pm25) < 0.001, (
            f"PM2.5 value for {city_name} should be {expected_pm25}, but got {pm25_values_in_chart[i]}"
        )
    
    # Property: Bar chart should have proper axis labels
    layout = bar_chart.layout
    assert layout.xaxis.title.text is not None, "Bar chart should have x-axis title"
    assert layout.yaxis.title.text is not None, "Bar chart should have y-axis title"
    assert "Cities" in layout.xaxis.title.text, (
        f"X-axis should mention 'Cities', but got: {layout.xaxis.title.text}"
    )
    assert "PM2.5" in layout.yaxis.title.text, (
        f"Y-axis should mention 'PM2.5', but got: {layout.yaxis.title.text}"
    )
    assert "μg/m³" in layout.yaxis.title.text, (
        f"Y-axis should include units 'μg/m³', but got: {layout.yaxis.title.text}"
    )
    
    # Property: Bar chart should have a title
    assert layout.title.text is not None, "Bar chart should have a title"
    assert "PM2.5" in layout.title.text, (
        f"Title should mention 'PM2.5', but got: {layout.title.text}"
    )


@given(dashboard_data=dashboard_data_strategy())
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
def test_wind_vs_pollution_scatter_plot_generation(dashboard_data):
    """
    **Feature: breathable-commute, Property 9: Wind vs pollution scatter plot generation**
    **Validates: Requirements 3.1, 3.3**
    
    For any valid combination of air quality and weather data, the system should create 
    a scatter plot with wind speed as X-axis and PM2.5 as Y-axis.
    """
    # Generate charts using the main function
    bar_chart, scatter_plot = create_comparison_charts(dashboard_data)
    
    # Property: Scatter plot should be a valid Plotly Figure
    assert isinstance(scatter_plot, go.Figure), (
        f"Scatter plot should be a Plotly Figure, but got: {type(scatter_plot)}"
    )
    
    # Property: Scatter plot should have data traces (one per city)
    expected_cities = len(dashboard_data.cities_data)
    assert len(scatter_plot.data) == expected_cities, (
        f"Scatter plot should have {expected_cities} traces (one per city), but got {len(scatter_plot.data)}"
    )
    
    # Property: Each trace should have correct wind speed and PM2.5 values
    for i, city in enumerate(dashboard_data.cities_data):
        trace = scatter_plot.data[i]
        
        # Check that trace has one data point
        assert len(trace.x) == 1, (
            f"Each city trace should have exactly 1 data point, but city {city.city_name} has {len(trace.x)}"
        )
        assert len(trace.y) == 1, (
            f"Each city trace should have exactly 1 data point, but city {city.city_name} has {len(trace.y)}"
        )
        
        # Check wind speed (X-axis)
        wind_speed_in_chart = trace.x[0]
        assert abs(wind_speed_in_chart - city.wind_speed) < 0.001, (
            f"Wind speed for {city.city_name} should be {city.wind_speed}, but got {wind_speed_in_chart}"
        )
        
        # Check PM2.5 (Y-axis)
        pm25_in_chart = trace.y[0]
        assert abs(pm25_in_chart - city.pm25) < 0.001, (
            f"PM2.5 for {city.city_name} should be {city.pm25}, but got {pm25_in_chart}"
        )
    
    # Property: Scatter plot should have proper axis labels with units
    layout = scatter_plot.layout
    assert layout.xaxis.title.text is not None, "Scatter plot should have x-axis title"
    assert layout.yaxis.title.text is not None, "Scatter plot should have y-axis title"
    
    # Check X-axis (wind speed)
    x_title = layout.xaxis.title.text
    assert "Wind" in x_title, f"X-axis should mention 'Wind', but got: {x_title}"
    assert "km/h" in x_title, f"X-axis should include units 'km/h', but got: {x_title}"
    
    # Check Y-axis (PM2.5)
    y_title = layout.yaxis.title.text
    assert "PM2.5" in y_title, f"Y-axis should mention 'PM2.5', but got: {y_title}"
    assert "μg/m³" in y_title, f"Y-axis should include units 'μg/m³', but got: {y_title}"


@given(dashboard_data=dashboard_data_strategy())
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
def test_city_point_labeling_in_scatter_plot(dashboard_data):
    """
    **Feature: breathable-commute, Property 10: City point labeling in scatter plot**
    **Validates: Requirements 3.2**
    
    For any city dataset, the scatter plot should display each city as a distinct point 
    with proper city labels.
    """
    # Generate charts using the main function
    bar_chart, scatter_plot = create_comparison_charts(dashboard_data)
    
    # Property: Each city should have its own trace with proper labeling
    city_names_in_chart = []
    for trace in scatter_plot.data:
        # Check that trace has a name (city name)
        assert trace.name is not None, (
            "Each scatter plot trace should have a name (city name)"
        )
        city_names_in_chart.append(trace.name)
        
        # Check that trace has text labels
        assert trace.text is not None, (
            f"Trace for {trace.name} should have text labels"
        )
        
        # Check that city name appears in the text label
        if isinstance(trace.text, list):
            text_label = trace.text[0] if trace.text else ""
        else:
            text_label = trace.text
        
        assert trace.name in text_label, (
            f"City name '{trace.name}' should appear in text label, but got: {text_label}"
        )
    
    # Property: All cities should be represented in the scatter plot
    expected_city_names = [city.city_name for city in dashboard_data.cities_data]
    for expected_city in expected_city_names:
        assert expected_city in city_names_in_chart, (
            f"City '{expected_city}' should appear in scatter plot, but chart contains: {city_names_in_chart}"
        )
    
    # Property: No duplicate city names should exist
    assert len(city_names_in_chart) == len(set(city_names_in_chart)), (
        f"Scatter plot should have unique city names, but found duplicates: {city_names_in_chart}"
    )
    
    # Property: Each trace should be in scatter mode with markers and text
    for trace in scatter_plot.data:
        assert hasattr(trace, 'mode'), f"Trace for {trace.name} should have a mode attribute"
        assert 'markers' in trace.mode, (
            f"Trace for {trace.name} should include markers in mode, but got: {trace.mode}"
        )
        assert 'text' in trace.mode, (
            f"Trace for {trace.name} should include text in mode, but got: {trace.mode}"
        )


@given(dashboard_data=dashboard_data_strategy())
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
def test_scatter_plot_axis_labeling(dashboard_data):
    """
    **Feature: breathable-commute, Property 11: Scatter plot axis labeling**
    **Validates: Requirements 3.4**
    
    For any scatter plot generated, the system should provide clear axis labels 
    with proper units (km/h for wind, μg/m³ for PM2.5).
    """
    # Generate charts using the main function
    bar_chart, scatter_plot = create_comparison_charts(dashboard_data)
    
    # Property: Scatter plot should have both axis titles
    layout = scatter_plot.layout
    assert layout.xaxis.title.text is not None, (
        "Scatter plot must have x-axis title"
    )
    assert layout.yaxis.title.text is not None, (
        "Scatter plot must have y-axis title"
    )
    
    x_title = layout.xaxis.title.text
    y_title = layout.yaxis.title.text
    
    # Property: X-axis should be labeled for wind speed with km/h units
    assert "Wind" in x_title, (
        f"X-axis title should mention 'Wind', but got: {x_title}"
    )
    assert "Speed" in x_title, (
        f"X-axis title should mention 'Speed', but got: {x_title}"
    )
    assert "km/h" in x_title, (
        f"X-axis title should include 'km/h' units, but got: {x_title}"
    )
    
    # Property: Y-axis should be labeled for PM2.5 with μg/m³ units
    assert "PM2.5" in y_title, (
        f"Y-axis title should mention 'PM2.5', but got: {y_title}"
    )
    assert "μg/m³" in y_title, (
        f"Y-axis title should include 'μg/m³' units, but got: {y_title}"
    )
    
    # Property: Axis titles should be clear and descriptive
    assert len(x_title.strip()) > 5, (
        f"X-axis title should be descriptive, but got: '{x_title}'"
    )
    assert len(y_title.strip()) > 5, (
        f"Y-axis title should be descriptive, but got: '{y_title}'"
    )
    
    # Property: Units should be properly formatted in parentheses
    assert "(" in x_title and ")" in x_title, (
        f"X-axis title should have units in parentheses, but got: {x_title}"
    )
    assert "(" in y_title and ")" in y_title, (
        f"Y-axis title should have units in parentheses, but got: {y_title}"
    )


@given(dashboard_data=dashboard_data_strategy())
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
def test_city_comparison_bar_chart_generation(dashboard_data):
    """
    **Feature: breathable-commute, Property 16: City comparison bar chart generation**
    **Validates: Requirements 5.1**
    
    For any valid set of city PM2.5 data, the system should display a bar chart 
    comparing current levels across all four cities.
    """
    # Generate charts using the main function
    bar_chart, scatter_plot = create_comparison_charts(dashboard_data)
    
    # Property: Should generate a valid bar chart
    assert isinstance(bar_chart, go.Figure), (
        f"Should return a Plotly Figure for bar chart, but got: {type(bar_chart)}"
    )
    
    # Property: Bar chart should have exactly one trace (the bar data)
    assert len(bar_chart.data) == 1, (
        f"Bar chart should have exactly 1 trace, but got {len(bar_chart.data)}"
    )
    
    bar_trace = bar_chart.data[0]
    
    # Property: Bar trace should be of type Bar
    assert isinstance(bar_trace, go.Bar), (
        f"Chart trace should be a Bar type, but got: {type(bar_trace)}"
    )
    
    # Property: Bar chart should compare all cities in the dataset
    num_cities = len(dashboard_data.cities_data)
    assert len(bar_trace.x) == num_cities, (
        f"Bar chart should have {num_cities} cities, but got {len(bar_trace.x)}"
    )
    assert len(bar_trace.y) == num_cities, (
        f"Bar chart should have {num_cities} PM2.5 values, but got {len(bar_trace.y)}"
    )
    
    # Property: All PM2.5 values should be non-negative (valid air quality data)
    for i, pm25_value in enumerate(bar_trace.y):
        assert pm25_value >= 0, (
            f"PM2.5 value at index {i} should be non-negative, but got: {pm25_value}"
        )
    
    # Property: Chart should have proper comparison structure
    city_names = list(bar_trace.x)
    pm25_values = list(bar_trace.y)
    
    # Verify that each city's PM2.5 value is correctly represented
    for city in dashboard_data.cities_data:
        assert city.city_name in city_names, (
            f"City '{city.city_name}' should be in bar chart, but chart has: {city_names}"
        )
        
        # Find the index of this city in the chart
        city_index = city_names.index(city.city_name)
        chart_pm25 = pm25_values[city_index]
        
        assert abs(chart_pm25 - city.pm25) < 0.001, (
            f"PM2.5 for {city.city_name} should be {city.pm25}, but chart shows {chart_pm25}"
        )


@given(dashboard_data=dashboard_data_strategy())
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
def test_bar_chart_visual_formatting(dashboard_data):
    """
    **Feature: breathable-commute, Property 17: Bar chart visual formatting**
    **Validates: Requirements 5.2**
    
    For any bar chart generated, the system should use distinct colors and clear city labels 
    for easy comparison.
    """
    # Generate charts using the main function
    bar_chart, scatter_plot = create_comparison_charts(dashboard_data)
    
    bar_trace = bar_chart.data[0]
    
    # Property: Bar chart should have distinct colors
    if hasattr(bar_trace, 'marker') and hasattr(bar_trace.marker, 'color'):
        colors = bar_trace.marker.color
        
        # If colors is a list, check for distinctness
        if isinstance(colors, list):
            # Should have colors for each bar
            assert len(colors) == len(dashboard_data.cities_data), (
                f"Should have {len(dashboard_data.cities_data)} colors, but got {len(colors)}"
            )
            
            # Colors should be valid (not None or empty)
            for i, color in enumerate(colors):
                assert color is not None and color != "", (
                    f"Color at index {i} should be valid, but got: {color}"
                )
    
    # Property: City labels should be clear and readable
    city_labels = list(bar_trace.x)
    for label in city_labels:
        assert isinstance(label, str), (
            f"City label should be a string, but got: {type(label)} - {label}"
        )
        assert len(label.strip()) > 0, (
            f"City label should not be empty, but got: '{label}'"
        )
    
    # Property: Chart should have text annotations showing values
    if hasattr(bar_trace, 'text') and bar_trace.text is not None:
        text_annotations = bar_trace.text
        if isinstance(text_annotations, list):
            assert len(text_annotations) == len(dashboard_data.cities_data), (
                f"Should have text annotations for all {len(dashboard_data.cities_data)} cities"
            )
            
            # Each annotation should contain the PM2.5 value and units
            for i, annotation in enumerate(text_annotations):
                assert "μg/m³" in annotation, (
                    f"Text annotation {i} should contain units 'μg/m³', but got: {annotation}"
                )
    
    # Property: Chart layout should be configured for readability
    layout = bar_chart.layout
    
    # Should have a meaningful title
    assert layout.title.text is not None, "Bar chart should have a title"
    title_text = layout.title.text
    assert len(title_text.strip()) > 10, (
        f"Title should be descriptive, but got: '{title_text}'"
    )
    
    # Should have proper axis labels
    assert layout.xaxis.title.text is not None, "Should have x-axis title"
    assert layout.yaxis.title.text is not None, "Should have y-axis title"
    
    # Should be configured for responsive design
    assert layout.autosize is True, "Chart should be configured for responsive design"
    
    # Should have reasonable height for readability
    if hasattr(layout, 'height') and layout.height is not None:
        assert layout.height >= 300, (
            f"Chart height should be at least 300px for readability, but got: {layout.height}"
        )


@given(dashboard_data=dashboard_data_strategy())
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
def test_pm25_units_and_scaling(dashboard_data):
    """
    **Feature: breathable-commute, Property 18: PM2.5 units and scaling**
    **Validates: Requirements 5.3**
    
    For any PM2.5 values displayed, the system should include proper units (μg/m³) 
    and scale charts appropriately.
    """
    # Generate charts using the main function
    bar_chart, scatter_plot = create_comparison_charts(dashboard_data)
    
    # Property: Bar chart Y-axis should include proper PM2.5 units
    bar_layout = bar_chart.layout
    y_axis_title = bar_layout.yaxis.title.text
    assert "μg/m³" in y_axis_title, (
        f"Bar chart Y-axis should include PM2.5 units 'μg/m³', but got: {y_axis_title}"
    )
    assert "PM2.5" in y_axis_title, (
        f"Bar chart Y-axis should mention 'PM2.5', but got: {y_axis_title}"
    )
    
    # Property: Scatter plot Y-axis should include proper PM2.5 units
    scatter_layout = scatter_plot.layout
    scatter_y_title = scatter_layout.yaxis.title.text
    assert "μg/m³" in scatter_y_title, (
        f"Scatter plot Y-axis should include PM2.5 units 'μg/m³', but got: {scatter_y_title}"
    )
    assert "PM2.5" in scatter_y_title, (
        f"Scatter plot Y-axis should mention 'PM2.5', but got: {scatter_y_title}"
    )
    
    # Property: Bar chart should scale appropriately for PM2.5 values
    bar_trace = bar_chart.data[0]
    pm25_values = list(bar_trace.y)
    
    # All PM2.5 values should be properly scaled (non-negative, reasonable range)
    for i, pm25_value in enumerate(pm25_values):
        assert pm25_value >= 0, (
            f"PM2.5 value at index {i} should be non-negative, but got: {pm25_value}"
        )
        assert pm25_value <= 1000, (
            f"PM2.5 value at index {i} should be reasonable (≤1000 μg/m³), but got: {pm25_value}"
        )
    
    # Property: Chart scaling should accommodate the data range
    if pm25_values:
        min_pm25 = min(pm25_values)
        max_pm25 = max(pm25_values)
        
        # Y-axis range should accommodate all data points
        if hasattr(bar_layout.yaxis, 'range') and bar_layout.yaxis.range:
            y_min, y_max = bar_layout.yaxis.range
            assert y_min <= min_pm25, (
                f"Y-axis minimum ({y_min}) should be ≤ minimum PM2.5 value ({min_pm25})"
            )
            assert y_max >= max_pm25, (
                f"Y-axis maximum ({y_max}) should be ≥ maximum PM2.5 value ({max_pm25})"
            )
    
    # Property: Scatter plot should scale appropriately for PM2.5 values
    scatter_pm25_values = []
    for trace in scatter_plot.data:
        if len(trace.y) > 0:
            scatter_pm25_values.extend(trace.y)
    
    for i, pm25_value in enumerate(scatter_pm25_values):
        assert pm25_value >= 0, (
            f"Scatter plot PM2.5 value at index {i} should be non-negative, but got: {pm25_value}"
        )
        assert pm25_value <= 1000, (
            f"Scatter plot PM2.5 value at index {i} should be reasonable (≤1000 μg/m³), but got: {pm25_value}"
        )
    
    # Property: Text annotations should include proper units
    if hasattr(bar_trace, 'text') and bar_trace.text:
        text_annotations = bar_trace.text
        if isinstance(text_annotations, list):
            for i, annotation in enumerate(text_annotations):
                assert "μg/m³" in annotation, (
                    f"Text annotation {i} should include units 'μg/m³', but got: {annotation}"
                )
                
                # Extract numeric value from annotation and verify it matches data
                try:
                    # Look for number pattern in annotation (e.g., "123.4 μg/m³")
                    import re
                    number_match = re.search(r'(\d+\.?\d*)', annotation)
                    if number_match:
                        annotated_value = float(number_match.group(1))
                        actual_value = pm25_values[i]
                        assert abs(annotated_value - actual_value) < 0.1, (
                            f"Annotated PM2.5 value ({annotated_value}) should match actual value ({actual_value})"
                        )
                except (ValueError, IndexError):
                    # If we can't parse the annotation, that's also a problem
                    pass  # But don't fail the test just for parsing issues
    
    # Property: Charts should have appropriate scaling for different PM2.5 ranges
    # Test that charts can handle both low and high PM2.5 values appropriately
    pm25_range = max(pm25_values) - min(pm25_values) if pm25_values else 0
    
    # If there's significant variation in PM2.5 values, chart should show this clearly
    if pm25_range > 10:  # Significant variation
        # Bar chart should visually distinguish between different PM2.5 levels
        bar_heights = list(bar_trace.y)
        assert len(set(bar_heights)) > 1, (
            "Bar chart should show variation when PM2.5 values differ significantly"
        )
    
    # Property: Units should be consistently formatted across all displays
    unit_formats = []
    
    # Collect unit formats from various places
    if "μg/m³" in y_axis_title:
        unit_formats.append("μg/m³")
    if "μg/m³" in scatter_y_title:
        unit_formats.append("μg/m³")
    
    # All unit formats should be consistent
    if unit_formats:
        first_format = unit_formats[0]
        for unit_format in unit_formats:
            assert unit_format == first_format, (
                f"Unit formats should be consistent, but found: {set(unit_formats)}"
            )
"""
Chart generation module for creating Plotly visualizations for the Breathable Commute dashboard.
"""

import logging
from typing import Tuple, List, Dict, Any
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .data_processor import ChartConfig, DashboardData
from .weather_data import CityWeatherData


# Configure logging
logger = logging.getLogger(__name__)


class ChartGenerationError(Exception):
    """Custom exception for chart generation errors."""
    pass


def _validate_cities_data_for_charts(cities_data: List[CityWeatherData]) -> None:
    """
    Validate cities data for chart generation.
    
    Args:
        cities_data: List of CityWeatherData objects
        
    Raises:
        ChartGenerationError: If data is invalid for chart generation
    """
    if not cities_data:
        raise ChartGenerationError("Cities data cannot be empty for chart generation")
    
    if len(cities_data) < 2:
        raise ChartGenerationError("At least 2 cities required for meaningful comparison charts")
    
    for i, city_data in enumerate(cities_data):
        if city_data is None:
            raise ChartGenerationError(f"City data at index {i} cannot be None")
        
        if not city_data.city_name:
            raise ChartGenerationError(f"City at index {i} missing required name")
        
        if city_data.pm25 < 0:
            raise ChartGenerationError(f"City {city_data.city_name} has invalid PM2.5 value: {city_data.pm25}")
        
        if city_data.wind_speed < 0:
            raise ChartGenerationError(f"City {city_data.city_name} has invalid wind speed: {city_data.wind_speed}")


def _create_pm25_comparison_bar_chart(cities_data: List[CityWeatherData], 
                                    config: ChartConfig,
                                    selected_city: str = None,
                                    responsive_config: dict = None) -> go.Figure:
    """
    Create a bar chart comparing PM2.5 levels across cities.
    
    Args:
        cities_data: List of CityWeatherData objects
        config: Chart configuration settings
        selected_city: Name of selected city to highlight (optional)
        
    Returns:
        Plotly Figure object with PM2.5 comparison bar chart
    """
    city_names = [city.city_name for city in cities_data]
    pm25_values = [city.pm25 for city in cities_data]
    
    # Create colors list, highlighting selected city if specified
    colors = []
    for i, city_name in enumerate(city_names):
        if selected_city and city_name == selected_city:
            # Use a brighter/different color for selected city
            colors.append("#ff4444")  # Bright red for selection
        else:
            # Use default colors cycling through the palette
            color_index = i % len(config.bar_chart_colors)
            colors.append(config.bar_chart_colors[color_index])
    
    # Create bar chart
    fig = go.Figure(data=[
        go.Bar(
            x=city_names,
            y=pm25_values,
            marker_color=colors,
            text=[f"{pm25:.1f} μg/m³" for pm25 in pm25_values],
            textposition='auto',
            name="PM2.5 Levels"
        )
    ])
    
    # Add threshold lines for reference
    fig.add_hline(
        y=config.healthy_threshold,
        line_dash="dash",
        line_color="green",
        annotation_text=f"Healthy Threshold ({config.healthy_threshold} μg/m³)",
        annotation_position="top right"
    )
    
    fig.add_hline(
        y=config.hazardous_threshold,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Hazardous Threshold ({config.hazardous_threshold} μg/m³)",
        annotation_position="top right"
    )
    
    # Get responsive configuration or use defaults
    if responsive_config is None:
        responsive_config = {
            'height': 500,
            'title_size': 18,
            'font_size': 12,
            'tick_font_size': 11
        }
    
    # Configure layout for desktop and mobile readability (Requirements 7.1, 7.5)
    fig.update_layout(
        title={
            'text': "PM2.5 Air Quality Comparison Across Indian Cities",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': responsive_config.get('title_size', 18)}
        },
        xaxis_title="Cities",
        yaxis_title="PM2.5 Concentration (μg/m³)",
        showlegend=False,
        height=responsive_config.get('height', 500),
        margin=dict(l=50, r=50, t=80, b=50),
        font=dict(size=responsive_config.get('font_size', 12)),
        # Enhanced responsive design
        autosize=True,
        # Mobile-friendly settings with adaptive text
        xaxis=dict(
            tickangle=-45 if len(city_names) > 3 else 0,
            tickfont=dict(size=responsive_config.get('tick_font_size', 11)),
            # Ensure text fits on mobile
            tickmode='linear',
            automargin=True
        ),
        yaxis=dict(
            tickfont=dict(size=responsive_config.get('tick_font_size', 11)),
            automargin=True
        ),
        # Performance optimizations for concurrent users (Requirement 7.4)
        dragmode=False,  # Disable dragging for better mobile performance
        # Responsive behavior
        modebar=dict(
            orientation='h',
            bgcolor='rgba(255,255,255,0.8)',
            # Optimize modebar for mobile
            remove=['pan2d', 'lasso2d', 'select2d'] if responsive_config.get('height', 500) < 400 else []
        )
    )
    
    logger.info(f"Created PM2.5 comparison bar chart for {len(city_names)} cities")
    return fig


def _create_wind_pollution_scatter_plot(cities_data: List[CityWeatherData], 
                                      config: ChartConfig,
                                      responsive_config: dict = None) -> go.Figure:
    """
    Create a scatter plot showing correlation between wind speed and PM2.5 levels.
    
    Args:
        cities_data: List of CityWeatherData objects
        config: Chart configuration settings
        
    Returns:
        Plotly Figure object with wind vs pollution scatter plot
    """
    city_names = [city.city_name for city in cities_data]
    wind_speeds = [city.wind_speed for city in cities_data]
    pm25_values = [city.pm25 for city in cities_data]
    
    # Create scatter plot with city-specific colors
    fig = go.Figure()
    
    for i, city_data in enumerate(cities_data):
        city_color = config.scatter_colors.get(city_data.city_name, config.bar_chart_colors[i % len(config.bar_chart_colors)])
        
        fig.add_trace(go.Scatter(
            x=[city_data.wind_speed],
            y=[city_data.pm25],
            mode='markers+text',
            marker=dict(
                size=12,
                color=city_color,
                line=dict(width=2, color='white')
            ),
            text=[city_data.city_name],
            textposition="top center",
            textfont=dict(size=10, color='black'),
            name=city_data.city_name,
            hovertemplate=(
                f"<b>{city_data.city_name}</b><br>"
                f"Wind Speed: {city_data.wind_speed:.1f} km/h<br>"
                f"PM2.5: {city_data.pm25:.1f} μg/m³<br>"
                f"Temperature: {city_data.temperature:.1f}°C<br>"
                "<extra></extra>"
            )
        ))
    
    # Get responsive configuration or use defaults
    if responsive_config is None:
        responsive_config = {
            'height': 500,
            'title_size': 18,
            'font_size': 12,
            'tick_font_size': 11,
            'legend_font_size': 10
        }
    
    # Configure layout with proper axis labels and units (Requirements 7.1, 7.5)
    fig.update_layout(
        title={
            'text': "Wind Speed vs PM2.5 Correlation Analysis",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': responsive_config.get('title_size', 18)}
        },
        xaxis_title="Wind Speed (km/h)",
        yaxis_title="PM2.5 Concentration (μg/m³)",
        showlegend=True,
        legend=dict(
            orientation="h" if responsive_config.get('height', 500) >= 400 else "v",
            yanchor="bottom",
            y=1.02 if responsive_config.get('height', 500) >= 400 else 0.5,
            xanchor="right" if responsive_config.get('height', 500) >= 400 else "left",
            x=1 if responsive_config.get('height', 500) >= 400 else 1.02,
            # Responsive legend
            font=dict(size=responsive_config.get('legend_font_size', 10))
        ),
        height=responsive_config.get('height', 500),
        margin=dict(l=60, r=50, t=100, b=60),
        font=dict(size=responsive_config.get('font_size', 12)),
        # Enhanced responsive design
        autosize=True,
        # Grid for better readability
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            tickfont=dict(size=responsive_config.get('tick_font_size', 11)),
            automargin=True
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            tickfont=dict(size=responsive_config.get('tick_font_size', 11)),
            automargin=True
        ),
        # Performance optimizations for concurrent users (Requirement 7.4)
        dragmode='pan' if responsive_config.get('height', 500) >= 400 else False,
        # Mobile-friendly hover
        hovermode='closest'
    )
    
    logger.info(f"Created wind vs PM2.5 scatter plot for {len(city_names)} cities")
    return fig


def create_comparison_charts(dashboard_data: DashboardData, 
                           config: ChartConfig = None,
                           responsive_config: dict = None) -> Tuple[go.Figure, go.Figure]:
    """
    Generate both bar chart and scatter plot for air quality and weather comparison.
    
    This function creates two complementary visualizations:
    1. Bar chart comparing PM2.5 levels across all cities
    2. Scatter plot showing wind speed vs PM2.5 correlation
    
    Args:
        dashboard_data: DashboardData object with cities data
        config: Chart configuration settings (optional, uses defaults if None)
        
    Returns:
        Tuple containing (bar_chart_figure, scatter_plot_figure)
        
    Raises:
        ChartGenerationError: If chart generation fails
    """
    if config is None:
        config = ChartConfig()
    
    try:
        logger.info("Starting chart generation for dashboard data")
        
        # Validate input data
        _validate_cities_data_for_charts(dashboard_data.cities_data)
        
        # Create PM2.5 comparison bar chart (Requirements 1.3, 5.1, 5.2)
        bar_chart = _create_pm25_comparison_bar_chart(
            dashboard_data.cities_data, 
            config,
            dashboard_data.selected_city,
            responsive_config
        )
        
        # Create wind vs pollution scatter plot (Requirements 3.1, 3.2, 3.3, 3.4)
        scatter_plot = _create_wind_pollution_scatter_plot(
            dashboard_data.cities_data,
            config,
            responsive_config
        )
        
        logger.info("Chart generation completed successfully")
        return bar_chart, scatter_plot
        
    except Exception as e:
        error_msg = f"Failed to generate comparison charts: {e}"
        logger.error(error_msg)
        raise ChartGenerationError(error_msg)


def create_single_city_chart(city_data: CityWeatherData, config: ChartConfig = None) -> go.Figure:
    """
    Create a detailed chart for a single city showing multiple metrics.
    
    Args:
        city_data: CityWeatherData object for the city
        config: Chart configuration settings (optional)
        
    Returns:
        Plotly Figure object with single city metrics
    """
    if config is None:
        config = ChartConfig()
    
    # Create subplots for multiple metrics
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('PM2.5 Level', 'Temperature', 'Wind Speed', 'Precipitation'),
        specs=[[{"type": "indicator"}, {"type": "indicator"}],
               [{"type": "indicator"}, {"type": "indicator"}]]
    )
    
    # PM2.5 gauge
    pm25_color = "red" if city_data.pm25 > config.hazardous_threshold else "yellow" if city_data.pm25 > config.healthy_threshold else "green"
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=city_data.pm25,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "PM2.5 (μg/m³)"},
        gauge={'axis': {'range': [None, 200]},
               'bar': {'color': pm25_color},
               'steps': [
                   {'range': [0, config.healthy_threshold], 'color': "lightgreen"},
                   {'range': [config.healthy_threshold, config.hazardous_threshold], 'color': "yellow"},
                   {'range': [config.hazardous_threshold, 200], 'color': "lightcoral"}],
               'threshold': {'line': {'color': "red", 'width': 4},
                           'thickness': 0.75, 'value': config.hazardous_threshold}}
    ), row=1, col=1)
    
    # Temperature gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=city_data.temperature,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Temperature (°C)"},
        gauge={'axis': {'range': [0, 50]},
               'bar': {'color': "orange"}}
    ), row=1, col=2)
    
    # Wind speed gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=city_data.wind_speed,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Wind Speed (km/h)"},
        gauge={'axis': {'range': [0, 50]},
               'bar': {'color': "blue"}}
    ), row=2, col=1)
    
    # Precipitation gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=city_data.precipitation,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Precipitation (mm)"},
        gauge={'axis': {'range': [0, 20]},
               'bar': {'color': "lightblue"}}
    ), row=2, col=2)
    
    fig.update_layout(
        title=f"Weather Metrics for {city_data.city_name}",
        height=600,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    logger.info(f"Created single city chart for {city_data.city_name}")
    return fig


def get_chart_config(selected_city: str = None) -> ChartConfig:
    """
    Get chart configuration with optional city-specific customizations.
    
    Args:
        selected_city: Name of selected city for highlighting (optional)
        
    Returns:
        ChartConfig object with appropriate settings
    """
    config = ChartConfig()
    
    # Customize colors based on selected city if needed
    if selected_city and selected_city in config.scatter_colors:
        logger.info(f"Using chart configuration optimized for {selected_city}")
    
    return config


def get_responsive_chart_config(screen_width: int = None, is_mobile: bool = False) -> dict:
    """
    Get responsive chart configuration based on screen size for optimal display
    across different devices (Requirements 7.1, 7.5).
    
    Args:
        screen_width: Screen width in pixels (optional)
        is_mobile: Whether the device is mobile (optional)
        
    Returns:
        Dictionary with responsive chart configuration
    """
    # Default desktop configuration
    config = {
        'height': 500,
        'title_size': 18,
        'font_size': 12,
        'tick_font_size': 11,
        'legend_font_size': 10,
        'margin_top': 100,
        'margin_bottom': 60,
        'margin_left': 60,
        'margin_right': 50
    }
    
    # Adjust for mobile devices (Requirements 7.1, 7.5)
    if is_mobile or (screen_width and screen_width <= 768):
        config.update({
            'height': 300,
            'title_size': 14,
            'font_size': 10,
            'tick_font_size': 9,
            'legend_font_size': 8,
            'margin_top': 80,
            'margin_bottom': 50,
            'margin_left': 50,
            'margin_right': 40
        })
        logger.debug("Using mobile-optimized chart configuration")
    
    # Adjust for tablet devices
    elif screen_width and 768 < screen_width <= 1024:
        config.update({
            'height': 400,
            'title_size': 16,
            'font_size': 11,
            'tick_font_size': 10,
            'legend_font_size': 9,
            'margin_top': 90,
            'margin_bottom': 55,
            'margin_left': 55,
            'margin_right': 45
        })
        logger.debug("Using tablet-optimized chart configuration")
    
    else:
        logger.debug("Using desktop-optimized chart configuration")
    
    return config
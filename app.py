"""
Main Streamlit dashboard application for Breathable Commute - Indian Cities Edition.

This application provides real-time air quality and weather information
for Indian commuters to make informed cycling decisions across New Delhi, Mumbai, Bengaluru, and Hyderabad.
"""

import streamlit as st
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import pandas as pd

from breathable_commute.weather_data import get_all_cities_data, CITY_COORDINATES, WeatherDataError
from breathable_commute.data_processor import process_all_cities_data, get_dashboard_summary, DataProcessingError
from breathable_commute.chart_generator import create_comparison_charts, ChartConfig, ChartGenerationError, get_responsive_chart_config
from breathable_commute.recommendation_engine import Recommendation
from breathable_commute.health_check import verify_api_connectivity
from config import config

# Set up logging using configuration
logger = config.setup_logging()
logger.info(f"Starting {config.app_name} v{config.app_version}")

# Verify API connectivity at startup if health checks are enabled
if config.health_check_enabled:
    try:
        all_healthy, health_results = verify_api_connectivity()
        if all_healthy:
            logger.info("All APIs are healthy and accessible")
        else:
            unhealthy_services = [r.service_name for r in health_results if not r.is_healthy]
            logger.warning(f"Some APIs are not accessible: {', '.join(unhealthy_services)}")
            # Continue running even if some APIs are unhealthy - graceful degradation
    except Exception as e:
        logger.error(f"Health check failed during startup: {e}")
        # Continue running - health checks are not critical for basic functionality

# Use configuration for cache duration and performance settings
CACHE_DURATION_SECONDS = config.cache_duration_seconds
PERFORMANCE_MONITORING_ENABLED = config.performance_monitoring_enabled
MAX_CONCURRENT_REQUESTS = config.max_concurrent_requests


def configure_page():
    """Configure Streamlit page settings with responsive design."""
    st.set_page_config(
        page_title="Breathable Commute - Indian Cities",
        page_icon="🚴‍♂️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Add enhanced responsive CSS for mobile devices and performance (Requirements 7.1, 7.3)
    st.markdown("""
    <style>
    /* Performance optimizations */
    .main .block-container {
        transition: all 0.3s ease;
    }
    
    /* Mobile-first responsive design (Requirement 7.1) */
    @media (max-width: 480px) {
        /* Extra small mobile devices */
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
            max-width: 100%;
        }
        
        /* Stack all content vertically */
        .stColumns > div {
            width: 100% !important;
            margin-bottom: 1rem;
        }
        
        /* Smaller chart height for very small screens */
        .js-plotly-plot {
            height: 300px !important;
        }
        
        /* Compact metrics display */
        .metric-value {
            font-size: 1.2rem !important;
        }
        
        /* Smaller recommendation box */
        .recommendation-box {
            padding: 15px;
            margin: 15px 0;
        }
        
        .recommendation-box h2 {
            font-size: 1.3rem !important;
        }
    }
    
    @media (max-width: 768px) {
        /* Standard mobile devices */
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 100%;
        }
        
        /* Stack metrics in 2x2 grid on mobile */
        .stColumns > div {
            width: 50% !important;
            min-width: 150px;
        }
        
        /* Adjust chart height for mobile */
        .js-plotly-plot {
            height: 400px !important;
        }
        
        /* Make buttons full width on mobile */
        .stButton > button {
            width: 100%;
            margin-bottom: 0.5rem;
        }
        
        /* Responsive sidebar */
        .css-1d391kg {
            width: 100% !important;
        }
        
        /* Compact header on mobile */
        h1 {
            font-size: 1.8rem !important;
        }
    }
    
    @media (min-width: 769px) and (max-width: 1024px) {
        /* Tablet responsive design */
        .js-plotly-plot {
            height: 450px !important;
        }
        
        /* Adjust columns for tablet */
        .stColumns > div {
            min-width: 200px;
        }
    }
    
    /* Desktop responsive design (Requirement 7.3) */
    @media (min-width: 1025px) {
        .js-plotly-plot {
            height: 500px !important;
        }
        
        /* Optimize for large screens */
        .main .block-container {
            max-width: 1200px;
            margin: 0 auto;
        }
    }
    
    /* Ensure charts are responsive across all screen sizes */
    .js-plotly-plot .plotly {
        width: 100% !important;
        height: auto !important;
    }
    
    /* Performance: GPU acceleration for animations */
    .js-plotly-plot, .recommendation-box, .stButton > button {
        transform: translateZ(0);
        will-change: transform;
    }
    
    /* Recommendation box styling with responsive design */
    .recommendation-box {
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
        text-align: center;
        border: 2px solid;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: box-shadow 0.3s ease;
    }
    
    .recommendation-box:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    .recommendation-green {
        background-color: #d4edda;
        border-color: #28a745;
        color: #155724;
    }
    
    .recommendation-yellow {
        background-color: #fff3cd;
        border-color: #ffc107;
        color: #856404;
    }
    
    .recommendation-red {
        background-color: #f8d7da;
        border-color: #dc3545;
        color: #721c24;
    }
    
    /* Loading indicators optimization */
    .stSpinner {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100px;
    }
    
    /* Responsive metrics layout */
    .metric-container {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        justify-content: space-around;
    }
    
    /* Performance: Reduce repaints */
    .stMetric {
        contain: layout style paint;
    }
    
    /* Accessibility improvements */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    
    /* High contrast mode support */
    @media (prefers-contrast: high) {
        .recommendation-box {
            border-width: 3px;
        }
    }
    </style>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=CACHE_DURATION_SECONDS, show_spinner=False, max_entries=50)
def fetch_all_cities_data() -> Optional[list]:
    """
    Cached wrapper for fetching all cities weather data with performance monitoring.
    
    Returns:
        List of CityWeatherData objects or None if error
    """
    try:
        start_time = time.time()
        cities_data = get_all_cities_data()
        fetch_time = time.time() - start_time
        
        # Performance monitoring (Requirement 7.4)
        if PERFORMANCE_MONITORING_ENABLED:
            logger.info(f"All cities data fetched in {fetch_time:.2f}s")
            if fetch_time > 5.0:  # Log slow requests
                logger.warning(f"Slow API response detected: {fetch_time:.2f}s")
        
        return cities_data
        
    except WeatherDataError as e:
        logger.error(f"Failed to fetch cities data: {e}")
        return None


@st.cache_data(ttl=CACHE_DURATION_SECONDS, show_spinner=False, max_entries=20)
def process_dashboard_data_cached(selected_city: str, cities_data_hash: str) -> Optional[tuple]:
    """
    Cached wrapper for processing dashboard data to improve performance.
    
    Args:
        selected_city: Selected city name
        cities_data_hash: Hash of cities data for cache invalidation
        
    Returns:
        Tuple of (dashboard_data, dashboard_summary) or None if error
    """
    try:
        start_time = time.time()
        
        # Process dashboard data
        dashboard_data = process_all_cities_data(selected_city)
        dashboard_summary = get_dashboard_summary(dashboard_data)
        
        processing_time = time.time() - start_time
        
        # Performance monitoring
        if PERFORMANCE_MONITORING_ENABLED:
            logger.info(f"Dashboard data processed in {processing_time:.2f}s for {selected_city}")
        
        return dashboard_data, dashboard_summary
        
    except DataProcessingError as e:
        logger.error(f"Failed to process dashboard data: {e}")
        return None


@st.cache_data(ttl=CACHE_DURATION_SECONDS * 2, show_spinner=False, max_entries=10)  # Cache charts longer
def generate_charts_cached(cities_data_hash: str, selected_city: str, is_mobile: bool = False) -> Optional[tuple]:
    """
    Cached wrapper for chart generation with responsive design support to improve performance.
    Enhanced for different screen sizes (Requirements 7.1, 7.5).
    
    Args:
        cities_data_hash: Hash of cities data for cache invalidation
        selected_city: Selected city for highlighting
        is_mobile: Whether to use mobile-optimized charts
        
    Returns:
        Tuple of (bar_chart, scatter_plot) or None if error
    """
    try:
        start_time = time.time()
        
        # Get dashboard data for chart generation
        dashboard_data = process_all_cities_data(selected_city)
        chart_config = ChartConfig()
        
        # Get responsive chart configuration (Requirements 7.1, 7.5)
        responsive_config = get_responsive_chart_config(is_mobile=is_mobile)
        
        bar_chart, scatter_plot = create_comparison_charts(dashboard_data, chart_config, responsive_config)
        
        chart_time = time.time() - start_time
        
        # Performance monitoring (Requirement 7.4)
        if PERFORMANCE_MONITORING_ENABLED:
            logger.info(f"Charts generated in {chart_time:.2f}s (mobile: {is_mobile})")
            if chart_time > config.slow_request_threshold:
                logger.warning(f"Slow chart generation detected: {chart_time:.2f}s")
        
        return bar_chart, scatter_plot
        
    except (DataProcessingError, ChartGenerationError) as e:
        logger.error(f"Failed to generate charts: {e}")
        return None


def get_cities_data_hash(cities_data: list) -> str:
    """
    Generate a hash of cities data for cache invalidation.
    
    Args:
        cities_data: List of CityWeatherData objects
        
    Returns:
        Hash string for cache key
    """
    if not cities_data:
        return "empty"
    
    # Create a simple hash based on PM2.5 values and timestamps
    import hashlib
    hash_input = ""
    for city in cities_data:
        hash_input += f"{city.city_name}:{city.pm25}:{city.timestamp.isoformat()}"
    
    return hashlib.md5(hash_input.encode()).hexdigest()[:8]


def display_header():
    """Display the main header and description."""
    st.title("🚴‍♂️ Breathable Commute Dashboard")
    st.markdown("""
    **Real-time air quality and weather data for Indian cyclists**
    
    This dashboard helps you make informed decisions about cycling in major Indian cities by showing:
    - Current PM2.5 air quality levels across New Delhi, Mumbai, Bengaluru, and Hyderabad
    - Weather conditions including temperature, wind speed, and precipitation
    - Intelligent recommendations based on scientific thresholds
    - Correlation analysis between wind patterns and air pollution
    """)


def display_city_selector() -> str:
    """
    Display city selector dropdown in sidebar.
    
    Returns:
        Selected city name
    """
    st.sidebar.header("🏙️ City Selection")
    
    city_names = list(CITY_COORDINATES.keys())
    selected_city = st.sidebar.selectbox(
        "Choose a city for detailed recommendations:",
        options=city_names,
        index=0,  # Default to New Delhi
        help="Select a city to see personalized cycling recommendations"
    )
    
    # Display city coordinates for reference
    if selected_city in CITY_COORDINATES:
        lat, lon = CITY_COORDINATES[selected_city]
        st.sidebar.caption(f"📍 Coordinates: {lat:.4f}, {lon:.4f}")
    
    return selected_city


def display_loading_indicators():
    """Display loading indicators while fetching data."""
    with st.spinner("🔄 Fetching real-time data from Open-Meteo API..."):
        col1, col2 = st.columns(2)
        with col1:
            st.info("🌬️ Getting air quality data (PM2.5)")
        with col2:
            st.info("🌡️ Getting weather data (temperature, wind, precipitation)")


def display_error_message(error_type: str, error_message: str, show_retry: bool = True):
    """
    Display user-friendly error messages with graceful degradation.
    
    Args:
        error_type: Type of error (e.g., "Data Fetching", "Chart Generation")
        error_message: Detailed error message
        show_retry: Whether to show retry button
    """
    logger.error(f"{error_type} error: {error_message}")
    
    st.error(f"❌ **{error_type} Error**")
    
    # Show user-friendly error message based on error type
    if "timeout" in error_message.lower():
        st.warning("⏱️ The request timed out. This might be due to slow network connectivity.")
    elif "connection" in error_message.lower():
        st.warning("🌐 Unable to connect to the data service. Please check your internet connection.")
    elif "http" in error_message.lower():
        st.warning("🔧 The data service is temporarily unavailable. Please try again later.")
    else:
        st.warning(f"⚠️ {error_message}")
    
    if show_retry:
        if st.button("🔄 Retry", key=f"retry_{error_type.lower().replace(' ', '_')}"):
            st.cache_data.clear()
            st.rerun()


def display_recommendation_box(recommendation: Recommendation):
    """
    Display colored recommendation box at the top (green/yellow/red status).
    
    Args:
        recommendation: Recommendation object with status and message
    """
    # Map status to colors and icons
    status_config = {
        "green": {
            "color": "#28a745",
            "bg_color": "#d4edda",
            "icon": "✅",
            "title": "Great Cycling Conditions!"
        },
        "yellow": {
            "color": "#ffc107", 
            "bg_color": "#fff3cd",
            "icon": "⚠️",
            "title": "Moderate Conditions"
        },
        "red": {
            "color": "#dc3545",
            "bg_color": "#f8d7da", 
            "icon": "🚫",
            "title": "Poor Cycling Conditions"
        }
    }
    
    config = status_config.get(recommendation.status, status_config["yellow"])
    
    # Create colored recommendation box
    st.markdown(f"""
    <div class="recommendation-box recommendation-{recommendation.status}">
        <h2 style="margin: 0 0 10px 0;">
            {config['icon']} {config['title']}
        </h2>
        <p style="font-size: 16px; margin: 0;">
            {recommendation.message}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Add expandable details
    with st.expander("📋 Detailed Conditions", expanded=False):
        conditions = recommendation.conditions
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🌫️ PM2.5 Level", f"{conditions['pm25']:.1f} μg/m³")
            st.metric("🌡️ Temperature", f"{conditions['temperature']:.1f}°C")
        
        with col2:
            st.metric("💨 Wind Speed", f"{conditions['wind_speed']:.1f} km/h")
            st.metric("🌧️ Precipitation", f"{conditions['precipitation']:.1f} mm")
        
        # Safety recommendation
        if recommendation.is_safe_for_cycling:
            st.success("✅ Conditions are suitable for cycling")
        else:
            st.warning("⚠️ Consider alternative transportation or wait for better conditions")


def display_metrics_overview(dashboard_summary: Dict[str, Any]):
    """
    Display key metrics in a responsive layout.
    
    Args:
        dashboard_summary: Dictionary with dashboard summary data
    """
    st.subheader("📊 Current Conditions Overview")
    
    # Responsive metrics layout
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pm25_value = dashboard_summary["pm25_value"]
        healthy_threshold = dashboard_summary["healthy_threshold"]
        
        if pm25_value <= healthy_threshold:
            st.metric(
                label="🌿 Air Quality (PM2.5)",
                value=f"{pm25_value:.1f} μg/m³",
                delta="Healthy",
                delta_color="normal"
            )
        else:
            st.metric(
                label="⚠️ Air Quality (PM2.5)",
                value=f"{pm25_value:.1f} μg/m³",
                delta="Unhealthy",
                delta_color="inverse"
            )
    
    with col2:
        temperature_value = dashboard_summary["temperature_value"]
        st.metric(
            label="🌡️ Temperature",
            value=f"{temperature_value:.1f}°C",
            delta="Current"
        )
    
    with col3:
        wind_speed_value = dashboard_summary["wind_speed_value"]
        st.metric(
            label="💨 Wind Speed",
            value=f"{wind_speed_value:.1f} km/h",
            delta="Current"
        )
    
    with col4:
        precipitation_value = dashboard_summary["precipitation_value"]
        if precipitation_value > 0:
            st.metric(
                label="🌧️ Precipitation",
                value=f"{precipitation_value:.1f} mm",
                delta="Active",
                delta_color="inverse"
            )
        else:
            st.metric(
                label="☀️ Precipitation",
                value="0.0 mm",
                delta="None",
                delta_color="normal"
            )


def optimize_data_processing(cities_data: list) -> list:
    """
    Optimize data processing for multiple cities to improve performance.
    
    Args:
        cities_data: List of CityWeatherData objects
        
    Returns:
        Optimized cities data list
    """
    if not cities_data:
        return cities_data
    
    # Sort cities by PM2.5 for better chart rendering performance
    try:
        optimized_data = sorted(cities_data, key=lambda x: x.pm25)
        logger.info(f"Optimized data processing for {len(optimized_data)} cities")
        return optimized_data
    except Exception as e:
        logger.warning(f"Data optimization failed, using original data: {e}")
        return cities_data


def get_plotly_config(is_mobile: bool = False) -> dict:
    """
    Get Plotly configuration optimized for performance and responsiveness.
    Enhanced for different screen sizes (Requirements 7.1, 7.5).
    
    Args:
        is_mobile: Whether to use mobile-optimized configuration
        
    Returns:
        Dictionary with Plotly configuration settings
    """
    base_config = {
        'responsive': True,
        'displayModeBar': True,
        'displaylogo': False,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'breathable_commute_chart',
            'height': config.chart_height_mobile if is_mobile else config.chart_height_desktop,
            'width': 600 if is_mobile else 700,
            'scale': 1
        }
    }
    
    # Mobile-optimized configuration (Requirements 7.1, 7.5)
    if is_mobile:
        base_config['modeBarButtonsToRemove'] = [
            'pan2d', 'lasso2d', 'select2d', 'autoScale2d', 'hoverClosestCartesian',
            'hoverCompareCartesian', 'toggleSpikelines', 'zoom2d', 'zoomIn2d', 'zoomOut2d'
        ]
    else:
        base_config['modeBarButtonsToRemove'] = [
            'pan2d', 'lasso2d', 'select2d', 'autoScale2d', 'hoverClosestCartesian',
            'hoverCompareCartesian', 'toggleSpikelines'
        ]
    
    return base_config


def detect_mobile_device() -> bool:
    """
    Detect if the user is on a mobile device based on user agent.
    Simple detection for responsive design optimization.
    
    Returns:
        True if mobile device detected, False otherwise
    """
    try:
        # Try to get user agent from Streamlit session state or headers
        # This is a simple heuristic - in production, you might use more sophisticated detection
        user_agent = st.session_state.get('user_agent', '').lower()
        mobile_indicators = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
        return any(indicator in user_agent for indicator in mobile_indicators)
    except:
        # Default to desktop if detection fails
        return False


def display_data_timestamp(timestamp: datetime):
    """
    Display when the data was last updated.
    
    Args:
        timestamp: Timestamp of the data
    """
    st.caption(f"📅 Data last updated: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")


def display_footer_info():
    """Display footer information about data sources and features."""
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **📡 Data Sources:**
        - Air Quality & Weather: [Open-Meteo API](https://open-meteo.com/)
        - Real-time data from meteorological stations
        - No simulated or artificial data used
        """)
    
    with col2:
        st.markdown("""
        **🔬 Scientific Thresholds:**
        - Healthy PM2.5: ≤ 50 μg/m³
        - Hazardous PM2.5: > 100 μg/m³
        - High wind: > 20 km/h
        - Extreme heat: > 35°C
        """)
    
    st.markdown("""
    **About:** This dashboard helps Indian cyclists make informed decisions by combining 
    real-time air quality measurements with weather data across major cities. 
    All recommendations are based on scientific health guidelines and meteorological data.
    
    **Features:**
    - 📱 Responsive design for mobile and desktop (Requirements 7.1, 7.5)
    - 💾 Smart caching with 5-minute intervals for performance (Requirement 7.4)
    - 🔄 Real-time data from Open-Meteo API
    - 📊 Interactive charts optimized for concurrent users (Requirement 7.4)
    - ⚡ Performance monitoring and optimization
    - 🎯 Adaptive loading based on network conditions
    """)


def main():
    """Main Streamlit application entry point."""
    # Configure page
    configure_page()
    
    # Display header
    display_header()
    
    # City selector in sidebar
    selected_city = display_city_selector()
    
    # Add refresh button in sidebar
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh Data", help="Clear cache and fetch fresh data"):
        st.cache_data.clear()
        st.rerun()
    
    # Add auto-refresh option
    auto_refresh = st.sidebar.checkbox(
        "🔄 Auto-refresh (30s)", 
        value=False, 
        help="Automatically refresh data every 30 seconds"
    )
    
    # Display loading indicators
    display_loading_indicators()
    
    # Performance monitoring start
    app_start_time = time.time()
    
    # Fetch and process data with enhanced caching and performance optimization
    try:
        # Fetch all cities data with caching (Requirement 7.4)
        cities_data = fetch_all_cities_data()
        
        if cities_data is None:
            display_error_message(
                "Data Fetching", 
                "Failed to fetch weather data from Open-Meteo API", 
                show_retry=True
            )
            return
        
        # Generate hash for cache invalidation
        cities_hash = get_cities_data_hash(cities_data)
        
        # Process dashboard data with caching for performance optimization
        processed_data = process_dashboard_data_cached(selected_city, cities_hash)
        
        if processed_data is None:
            display_error_message("Data Processing", "Failed to process dashboard data")
            return
            
        dashboard_data, dashboard_summary = processed_data
        
        # Clear loading indicators
        st.success("✅ Data loaded successfully!")
        
        # Display recommendation box prominently at the top
        display_recommendation_box(dashboard_data.recommendation)
        
        # Display metrics overview with responsive layout
        display_metrics_overview(dashboard_summary)
        
        # Detect mobile device for responsive design (Requirements 7.1, 7.5)
        is_mobile = detect_mobile_device()
        
        # Generate and display charts with responsive caching
        charts_result = generate_charts_cached(cities_hash, selected_city, is_mobile)
        
        if charts_result is not None:
            bar_chart, scatter_plot = charts_result
            
            # Display charts in responsive layout (Requirements 7.1, 7.5)
            st.subheader("📈 Air Quality Analysis")
            
            # Responsive chart layout - stack on mobile, side-by-side on desktop
            if is_mobile:
                # Stack charts vertically on mobile for better readability
                st.markdown("**PM2.5 Comparison Across Cities**")
                plotly_config = get_plotly_config(is_mobile=True)
                st.plotly_chart(bar_chart, use_container_width=True, key="pm25_comparison", config=plotly_config)
                
                # Add threshold reference
                chart_config = ChartConfig()
                st.caption(f"🟢 Healthy: ≤ {chart_config.healthy_threshold} μg/m³ | "
                          f"🔴 Hazardous: > {chart_config.hazardous_threshold} μg/m³")
                
                st.markdown("**Wind Speed vs PM2.5 Correlation**")
                st.plotly_chart(scatter_plot, use_container_width=True, key="wind_pollution_correlation", config=plotly_config)
                
                # Add correlation explanation
                st.caption("💡 Higher wind speeds may help disperse air pollution")
            else:
                # Side-by-side layout for desktop and tablet
                chart_col1, chart_col2 = st.columns([1, 1])
                
                with chart_col1:
                    st.markdown("**PM2.5 Comparison Across Cities**")
                    plotly_config = get_plotly_config(is_mobile=False)
                    st.plotly_chart(bar_chart, use_container_width=True, key="pm25_comparison", config=plotly_config)
                    
                    # Add threshold reference
                    chart_config = ChartConfig()
                    st.caption(f"🟢 Healthy: ≤ {chart_config.healthy_threshold} μg/m³ | "
                              f"🔴 Hazardous: > {chart_config.hazardous_threshold} μg/m³")
                
                with chart_col2:
                    st.markdown("**Wind Speed vs PM2.5 Correlation**")
                    st.plotly_chart(scatter_plot, use_container_width=True, key="wind_pollution_correlation", config=plotly_config)
                    
                    # Add correlation explanation
                    st.caption("💡 Higher wind speeds may help disperse air pollution")
        else:
            display_error_message("Chart Generation", "Failed to generate charts", show_retry=False)
        
        # Display timestamp
        display_data_timestamp(dashboard_summary["timestamp"])
        
        # Performance monitoring display (Requirement 7.4)
        if PERFORMANCE_MONITORING_ENABLED:
            total_time = time.time() - app_start_time
            if total_time > 3.0:  # Show performance info if loading took more than 3 seconds
                st.sidebar.info(f"⏱️ Page loaded in {total_time:.2f}s")
            
            # Display cache statistics in sidebar for debugging
            if st.sidebar.checkbox("Show Performance Stats", value=False):
                st.sidebar.markdown("**Cache Statistics:**")
                st.sidebar.text(f"Cache TTL: {CACHE_DURATION_SECONDS}s")
                st.sidebar.text(f"Total Load Time: {total_time:.2f}s")
        
        # Display footer information
        display_footer_info()
        
        # Auto-refresh functionality with performance consideration (Requirement 7.4)
        if auto_refresh:
            # Use configurable refresh interval based on performance
            refresh_interval = config.auto_refresh_interval if total_time < 2.0 else config.auto_refresh_interval * 2
            time.sleep(refresh_interval)
            st.rerun()
            
    except DataProcessingError as e:
        display_error_message("Data Processing", str(e))
    except Exception as e:
        logger.error(f"Unexpected error in main application: {e}")
        display_error_message("Application", f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
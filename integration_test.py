#!/usr/bin/env python3
"""
Integration test script for Breathable Commute Dashboard
Tests all components working together end-to-end
"""

import sys
import logging
from typing import Optional

# Configure logging for test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_configuration():
    """Test configuration loading"""
    try:
        from config import load_config
        config = load_config()
        logger.info("✅ Configuration loaded successfully")
        logger.info(f"   - Open-Meteo Air Quality URL: {config.open_meteo_air_quality_url}")
        logger.info(f"   - Open-Meteo Weather URL: {config.open_meteo_weather_url}")
        logger.info(f"   - Healthy Air Quality Threshold: {config.healthy_air_quality_threshold}")
        logger.info(f"   - Hazardous Air Quality Threshold: {config.hazardous_air_quality_threshold}")
        return True
    except Exception as e:
        logger.error(f"❌ Configuration loading failed: {e}")
        return False

def test_air_quality_client():
    """Test air quality data fetching"""
    try:
        from breathable_commute.air_quality import get_current_pm25
        pm25 = get_current_pm25(51.5074, -0.1278)
        if pm25 is not None and pm25 >= 0:
            logger.info(f"✅ Air quality data fetched successfully: {pm25} μg/m³")
            return True
        else:
            logger.warning("⚠️ Air quality data is None or invalid")
            return False
    except Exception as e:
        logger.error(f"❌ Air quality client failed: {e}")
        return False

def test_weather_data_client():
    """Test weather data fetching"""
    try:
        from breathable_commute.weather_data import get_city_data
        # Test with New Delhi coordinates
        city_data = get_city_data(28.6139, 77.2090)
        if city_data and city_data.pm25 >= 0:
            logger.info(f"✅ Weather data fetched successfully")
            logger.info(f"   - PM2.5: {city_data.pm25} μg/m³")
            logger.info(f"   - Temperature: {city_data.temperature}°C")
            return True
        else:
            logger.warning("⚠️ No weather data returned")
            return False
    except Exception as e:
        logger.error(f"❌ Weather data client failed: {e}")
        return False

def test_data_processing():
    """Test data processing integration"""
    try:
        from breathable_commute.data_processor import process_all_cities_data
        
        # Process data for all cities
        dashboard_data = process_all_cities_data("New Delhi")
        
        if dashboard_data and dashboard_data.cities_data:
            logger.info("✅ Data processing successful")
            logger.info(f"   - Cities processed: {len(dashboard_data.cities_data)}")
            logger.info(f"   - Selected city: {dashboard_data.selected_city}")
            logger.info(f"   - Recommendation: {dashboard_data.recommendation.status}")
            return True
        else:
            logger.warning("⚠️ Data processing returned no data")
            return False
    except Exception as e:
        logger.error(f"❌ Data processing failed: {e}")
        return False

def test_chart_generation():
    """Test chart generation"""
    try:
        from breathable_commute.data_processor import process_all_cities_data
        from breathable_commute.chart_generator import create_comparison_charts, ChartConfig
        
        # Get processed data
        dashboard_data = process_all_cities_data("New Delhi")
        
        if dashboard_data and dashboard_data.cities_data:
            # Generate charts with proper configuration
            config = ChartConfig()
            bar_chart, scatter_plot = create_comparison_charts(dashboard_data, config)
            if bar_chart and scatter_plot:
                logger.info("✅ Chart generation successful")
                logger.info(f"   - Bar chart traces: {len(bar_chart.data)}")
                logger.info(f"   - Scatter plot traces: {len(scatter_plot.data)}")
                return True
            else:
                logger.warning("⚠️ Chart generation returned empty figures")
                return False
        else:
            logger.warning("⚠️ Insufficient data for chart generation")
            return False
    except Exception as e:
        logger.error(f"❌ Chart generation failed: {e}")
        return False

def test_health_check():
    """Test health check functionality"""
    try:
        from breathable_commute.health_check import health_checker
        health_status = health_checker.get_health_summary()
        
        if health_status.get('overall_healthy', False):
            logger.info("✅ Health check passed")
            for service in health_status.get('service_details', []):
                name = service['name']
                healthy = service['healthy']
                logger.info(f"   - {name}: {'✅' if healthy else '❌'}")
            return True
        else:
            logger.warning("⚠️ Health check indicates issues")
            return False
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False

def test_application_startup():
    """Test application can be imported without errors"""
    try:
        import app
        logger.info("✅ Application startup successful")
        return True
    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        return False

def main():
    """Run all integration tests"""
    logger.info("🚀 Starting Breathable Commute Integration Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Configuration Loading", test_configuration),
        ("Air Quality Client", test_air_quality_client),
        ("Weather Data Client", test_weather_data_client),
        ("Data Processing", test_data_processing),
        ("Chart Generation", test_chart_generation),
        ("Health Check", test_health_check),
        ("Application Startup", test_application_startup),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 Integration Test Results:")
    logger.info("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
        if result:
            passed += 1
    
    logger.info("=" * 60)
    logger.info(f"📈 Summary: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 All integration tests passed! Application is ready for deployment.")
        return 0
    else:
        logger.warning(f"⚠️ {total - passed} test(s) failed. Please review before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
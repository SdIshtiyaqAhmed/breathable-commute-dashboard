# Breathable Commute Dashboard - Indian Cities Edition

A Streamlit-based web dashboard that helps Indian commuters make informed cycling decisions by analyzing real-time air quality and weather data across major Indian cities.

## Features

- **Real-time Air Quality**: PM2.5 measurements from Open-Meteo API with health warnings for New Delhi, Mumbai, Bengaluru, and Hyderabad
- **Weather Analysis**: Temperature, wind speed, and precipitation data for cycling condition assessment
- **Interactive Charts**: Bar charts comparing PM2.5 levels and scatter plots showing wind vs pollution correlation
- **Intelligent Recommendations**: Color-coded cycling recommendations based on scientific thresholds
- **Responsive Design**: Optimized for mobile and desktop devices across India
- **Error Handling**: Graceful degradation when APIs are unavailable
- **Performance**: Smart caching and optimization for concurrent users
- **Ethical Data**: Uses only real, verifiable data from Open-Meteo API without simulated values

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Internet connection for API access

### Local Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd breathable-commute
```

2. **Create and activate virtual environment:**
```bash
# On macOS/Linux
python -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env file with your preferred settings (optional)
```

5. **Run the application:**
```bash
streamlit run app.py
```

6. **Access the dashboard:**
   - Open your browser to `http://localhost:8501`
   - The dashboard will automatically fetch and display current data

### Docker Installation (Alternative)

1. **Build the Docker image:**
```bash
docker build -t breathable-commute .
```

2. **Run the container:**
```bash
docker run -p 8501:8501 breathable-commute
```

## Deployment

### Streamlit Cloud Deployment

1. **Fork/Upload to GitHub:**
   - Push your code to a GitHub repository
   - Ensure all files are committed and pushed

2. **Deploy to Streamlit Cloud:**
   - Visit [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub account
   - Select your repository and branch
   - Set the main file path to `app.py`
   - Configure secrets (see Environment Variables section below)

3. **Configure Secrets in Streamlit Cloud:**
   - Go to your app settings in Streamlit Cloud
   - Add environment variables in the "Secrets" section:
   ```toml
   # .streamlit/secrets.toml format
   OPEN_METEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
   OPEN_METEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
   NEW_DELHI_LAT = "28.6139"
   NEW_DELHI_LON = "77.2090"
   MUMBAI_LAT = "19.0760"
   MUMBAI_LON = "72.8777"
   BENGALURU_LAT = "12.9716"
   BENGALURU_LON = "77.5946"
   HYDERABAD_LAT = "17.3850"
   HYDERABAD_LON = "78.4867"
   HEALTHY_AIR_QUALITY_THRESHOLD = "50.0"
   HAZARDOUS_AIR_QUALITY_THRESHOLD = "100.0"
   REQUEST_TIMEOUT = "10"
   MAX_RETRIES = "3"
   RETRY_DELAY = "1.0"
   LOG_LEVEL = "INFO"
   ```

### Local Production Deployment

1. **Install production dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with production settings
```

3. **Run with production settings:**
```bash
# Basic production run
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

# With custom configuration
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

### Docker Deployment

1. **Create Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

2. **Build and run:**
```bash
docker build -t breathable-commute .
docker run -p 8501:8501 --env-file .env breathable-commute
```

### Heroku Deployment

1. **Create required files:**
   - `Procfile`: `web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`
   - `runtime.txt`: `python-3.9.19`

2. **Deploy to Heroku:**
```bash
heroku create your-app-name
heroku config:set PYTHON_VERSION=3.9.19
git push heroku main
```

## Environment Variables

The application uses environment variables for configuration. All variables have sensible defaults but can be customized:

### Required Variables
None - the application works with default values.

### Optional Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPEN_METEO_AIR_QUALITY_URL` | `https://air-quality-api.open-meteo.com/v1/air-quality` | Open-Meteo Air Quality API endpoint |
| `OPEN_METEO_WEATHER_URL` | `https://api.open-meteo.com/v1/forecast` | Open-Meteo Weather API endpoint |
| `NEW_DELHI_LAT` | `28.6139` | New Delhi latitude |
| `NEW_DELHI_LON` | `77.2090` | New Delhi longitude |
| `MUMBAI_LAT` | `19.0760` | Mumbai latitude |
| `MUMBAI_LON` | `72.8777` | Mumbai longitude |
| `BENGALURU_LAT` | `12.9716` | Bengaluru latitude |
| `BENGALURU_LON` | `77.5946` | Bengaluru longitude |
| `HYDERABAD_LAT` | `17.3850` | Hyderabad latitude |
| `HYDERABAD_LON` | `78.4867` | Hyderabad longitude |
| `HEALTHY_AIR_QUALITY_THRESHOLD` | `50.0` | PM2.5 threshold for healthy air (μg/m³) |
| `HAZARDOUS_AIR_QUALITY_THRESHOLD` | `100.0` | PM2.5 threshold for hazardous air (μg/m³) |
| `MODERATE_WIND_THRESHOLD` | `20.0` | Wind speed threshold for moderate conditions (km/h) |
| `HIGH_WIND_THRESHOLD` | `30.0` | Wind speed threshold for high wind conditions (km/h) |
| `REQUEST_TIMEOUT` | `10` | API request timeout in seconds |
| `MAX_RETRIES` | `3` | Maximum number of API retry attempts |
| `RETRY_DELAY` | `1.0` | Initial delay between retries in seconds |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Setting Environment Variables

**Local Development (.env file):**
```bash
cp .env.example .env
# Edit .env file with your values (optional - defaults work fine)
```

**Streamlit Cloud:**
Add variables in the app settings under "Secrets" section.

**Heroku:**
```bash
heroku config:set VARIABLE_NAME=value
```

**Docker:**
```bash
docker run --env-file .env -p 8501:8501 breathable-commute
```

## Development

### Setting Up Development Environment

1. **Clone and setup:**
```bash
git clone <repository-url>
cd breathable-commute
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Install development dependencies:**
```bash
pip install pytest pytest-cov hypothesis responses
```

### Running Tests

**All tests:**
```bash
pytest
```

**Specific test types:**
```bash
pytest tests/test_*_properties.py    # Property-based tests
pytest tests/test_error_handling.py  # Unit tests
pytest -v                           # Verbose output
pytest --cov=breathable_commute      # With coverage
```

**Test specific components:**
```bash
pytest tests/test_air_quality_properties.py
pytest tests/test_weather_data_properties.py
pytest tests/test_data_processor_properties.py
pytest tests/test_chart_generator_properties.py
```

### Code Quality

**Run linting:**
```bash
flake8 breathable_commute/ tests/
black breathable_commute/ tests/  # Code formatting
```

**Type checking:**
```bash
mypy breathable_commute/
```

### Project Structure

```
breathable-commute/
├── breathable_commute/           # Main application package
│   ├── __init__.py
│   ├── air_quality.py           # Air quality API client
│   ├── weather_data.py          # Weather data API client  
│   ├── data_processor.py        # Data processing and business logic
│   ├── chart_generator.py       # Plotly chart generation
│   ├── recommendation_engine.py # Cycling recommendations
│   └── health_check.py          # System health monitoring
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py             # Test configuration and fixtures
│   ├── test_*_properties.py    # Property-based tests
│   └── test_error_handling.py  # Unit tests
├── .kiro/                       # Kiro specification files
│   └── specs/
│       └── python-dashboard/
│           ├── requirements.md  # Feature requirements
│           ├── design.md        # System design
│           └── tasks.md         # Implementation tasks
├── .streamlit/                  # Streamlit configuration
│   └── config.toml
├── app.py                       # Main Streamlit application
├── config.py                    # Configuration management
├── integration_test.py          # End-to-end integration tests
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── .gitignore                   # Git ignore rules
├── Dockerfile                   # Docker configuration
├── docker-compose.yml           # Docker Compose configuration
├── deploy.sh                    # Deployment helper script
├── Procfile                     # Heroku deployment
├── runtime.txt                  # Python version specification
├── DEPLOYMENT.md                # Detailed deployment guide
└── README.md                    # This documentation
```

## API Dependencies

### Open-Meteo Air Quality API
- **Endpoint:** `https://air-quality-api.open-meteo.com/v1/air-quality`
- **Authentication:** None required
- **Rate Limits:** 10,000 requests per day
- **Documentation:** [open-meteo.com](https://open-meteo.com/en/docs/air-quality-api)

### Open-Meteo Weather API
- **Endpoint:** `https://api.open-meteo.com/v1/forecast`
- **Authentication:** None required  
- **Rate Limits:** 10,000 requests per day
- **Documentation:** [open-meteo.com](https://open-meteo.com/en/docs)

## Troubleshooting

### Common Issues

**"Module not found" errors:**
```bash
pip install -r requirements.txt
# Ensure virtual environment is activated
```

**API connection errors:**
- Check internet connection
- Verify API endpoints are accessible
- Check firewall/proxy settings

**Streamlit not starting:**
```bash
# Check if port is already in use
lsof -i :8501  # macOS/Linux
netstat -ano | findstr :8501  # Windows

# Try different port
streamlit run app.py --server.port 8502
```

**Performance issues:**
- Check API response times
- Monitor memory usage with large datasets
- Consider caching for production deployment

### Getting Help

1. Check the [Issues](https://github.com/your-repo/issues) page
2. Review API documentation for external services
3. Check Streamlit documentation for deployment issues
4. Verify environment variable configuration

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run the test suite: `pytest`
5. Submit a pull request

### Code Standards

- Follow PEP 8 style guidelines
- Add type hints to new functions
- Write tests for new functionality
- Update documentation for API changes
- Use meaningful commit messages

## License

MIT License - see LICENSE file for details.

## Ethical Data Approach

This dashboard is built with a commitment to ethical data practices:

- **Real Data Only**: All air quality and weather data comes from Open-Meteo API - no simulated or artificial data
- **Scientific Accuracy**: Recommendations based on established health guidelines and meteorological science
- **Transparency**: All data sources, thresholds, and algorithms are documented and verifiable
- **Privacy Respect**: No personal data collection or tracking of users
- **Open Source**: Code is available for review and contribution

## Scientific Correlations

The dashboard analyzes several key correlations for cycling safety:

1. **PM2.5 and Health**: Based on WHO air quality guidelines
   - Healthy: ≤ 50 μg/m³
   - Hazardous: > 100 μg/m³

2. **Wind Speed and Pollution Dispersion**: Higher wind speeds can help disperse air pollutants
   - Moderate wind: > 20 km/h may improve air quality
   - High wind: > 30 km/h may make cycling difficult

3. **Temperature and Exertion**: High temperatures increase health risks during physical activity
   - Comfortable: < 30°C
   - Extreme heat: > 35°C (avoid outdoor exertion)

4. **Precipitation Impact**: Rain affects both air quality and cycling safety
   - Positive: Can wash pollutants from air
   - Negative: Reduces visibility and road safety

## Acknowledgments

- [Open-Meteo](https://open-meteo.com/) for comprehensive weather and air quality data
- [Streamlit](https://streamlit.io/) for the web framework
- [Plotly](https://plotly.com/) for interactive visualizations
- [Hypothesis](https://hypothesis.readthedocs.io/) for property-based testing
- Indian meteorological community for scientific guidance
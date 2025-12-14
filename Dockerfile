# Breathable Commute - Indian Air Quality Dashboard
# Multi-stage build for optimized production image

FROM python:3.9-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 streamlit \
    && chown -R streamlit:streamlit /app

# Switch to non-root user
USER streamlit

# Set environment variables for Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# Environment variables for the application
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default configuration for Indian cities
ENV NEW_DELHI_LAT=28.6139
ENV NEW_DELHI_LON=77.2090
ENV MUMBAI_LAT=19.0760
ENV MUMBAI_LON=72.8777
ENV BENGALURU_LAT=12.9716
ENV BENGALURU_LON=77.5946
ENV HYDERABAD_LAT=17.3850
ENV HYDERABAD_LON=78.4867

# Air quality thresholds
ENV HEALTHY_AIR_QUALITY_THRESHOLD=50.0
ENV HAZARDOUS_AIR_QUALITY_THRESHOLD=100.0

# API configuration
ENV OPEN_METEO_AIR_QUALITY_URL=https://air-quality-api.open-meteo.com/v1/air-quality
ENV OPEN_METEO_WEATHER_URL=https://api.open-meteo.com/v1/forecast
ENV REQUEST_TIMEOUT=10
ENV MAX_RETRIES=3
ENV RETRY_DELAY=1.0

# Performance settings
ENV CACHE_DURATION_SECONDS=300
ENV MAX_CONCURRENT_REQUESTS=10
ENV CONNECTION_POOL_SIZE=20

# Logging configuration
ENV LOG_LEVEL=INFO
ENV HEALTH_CHECK_ENABLED=true
ENV HEALTH_CHECK_TIMEOUT=5

# Expose Streamlit port
EXPOSE 8501

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
# Deployment Guide

This guide provides detailed instructions for deploying the Breathable Commute dashboard to various platforms.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Streamlit Cloud](#streamlit-cloud)
4. [Docker Deployment](#docker-deployment)
5. [Heroku Deployment](#heroku-deployment)
6. [AWS/GCP/Azure](#cloud-platforms)
7. [Environment Configuration](#environment-configuration)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- Python 3.8 or higher
- pip package manager
- Git (for version control)
- Internet connection (for API access)

### Optional Tools
- Docker (for containerized deployment)
- Heroku CLI (for Heroku deployment)
- Cloud provider CLI tools (AWS CLI, gcloud, etc.)

## Local Development

### Quick Setup

1. **Clone and setup environment:**
```bash
git clone <repository-url>
cd breathable-commute
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env file if needed (optional - defaults work fine)
```

4. **Run the application:**
```bash
streamlit run app.py
```

5. **Access the dashboard:**
   - Open browser to `http://localhost:8501`

### Development Workflow

1. **Make changes to code**
2. **Run tests:**
```bash
pytest
```
3. **Test locally:**
```bash
streamlit run app.py
```
4. **Commit and push changes**

## Streamlit Cloud

Streamlit Cloud is the easiest way to deploy Streamlit applications.

### Step-by-Step Deployment

1. **Prepare your repository:**
   - Ensure all code is committed to GitHub
   - Verify `requirements.txt` is up to date
   - Check that `app.py` is in the root directory

2. **Deploy to Streamlit Cloud:**
   - Visit [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repository
   - Set main file path: `app.py`
   - Click "Deploy"

3. **Configure secrets (optional):**
   - Go to app settings
   - Click "Secrets"
   - Add environment variables:
   ```toml
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

4. **Access your app:**
   - Your app will be available at `https://your-app-name.streamlit.app`

### Streamlit Cloud Benefits
- ✅ Free hosting
- ✅ Automatic deployments from GitHub
- ✅ Built-in secrets management
- ✅ Easy sharing and collaboration
- ✅ No server management required

## Docker Deployment

Docker provides a consistent deployment environment across different platforms.

### Basic Docker Deployment

1. **Build the image:**
```bash
docker build -t breathable-commute .
```

2. **Run the container:**
```bash
docker run -p 8501:8501 breathable-commute
```

3. **Access the application:**
   - Open browser to `http://localhost:8501`

### Docker Compose Deployment

1. **Start services:**
```bash
docker-compose up -d
```

2. **View logs:**
```bash
docker-compose logs -f
```

3. **Stop services:**
```bash
docker-compose down
```

### Production Docker Setup

1. **Create production docker-compose.yml:**
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "80:8501"
    environment:
      - LOG_LEVEL=WARNING
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    depends_on:
      - app
```

## Heroku Deployment

Heroku provides easy deployment with automatic scaling.

### Prerequisites
- Heroku account
- Heroku CLI installed

### Deployment Steps

1. **Login to Heroku:**
```bash
heroku login
```

2. **Create Heroku app:**
```bash
heroku create your-app-name
```

3. **Set Python version:**
```bash
heroku config:set PYTHON_VERSION=3.9.19
```

4. **Deploy:**
```bash
git push heroku main
```

5. **Open your app:**
```bash
heroku open
```

### Heroku Configuration

The following files are required for Heroku deployment:

- `Procfile`: Defines how to run your app
- `runtime.txt`: Specifies Python version
- `requirements.txt`: Lists dependencies

### Setting Environment Variables on Heroku

```bash
heroku config:set LOG_LEVEL=INFO
heroku config:set PM25_THRESHOLD=25.0
# Add other variables as needed
```

## Cloud Platforms

### AWS Deployment

#### Using AWS App Runner

1. **Create apprunner.yaml:**
```yaml
version: 1.0
runtime: python3
build:
  commands:
    build:
      - pip install -r requirements.txt
run:
  runtime-version: 3.9
  command: streamlit run app.py --server.port 8080 --server.address 0.0.0.0
  network:
    port: 8080
    env: PORT
```

2. **Deploy via AWS Console:**
   - Go to AWS App Runner
   - Create service from source code
   - Connect GitHub repository
   - Configure build settings

#### Using ECS with Fargate

1. **Push image to ECR:**
```bash
aws ecr create-repository --repository-name breathable-commute
docker tag breathable-commute:latest <account-id>.dkr.ecr.<region>.amazonaws.com/breathable-commute:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/breathable-commute:latest
```

2. **Create ECS task definition and service**

### Google Cloud Platform

#### Using Cloud Run

1. **Build and deploy:**
```bash
gcloud run deploy breathable-commute \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Using App Engine

1. **Create app.yaml:**
```yaml
runtime: python39
service: default

env_variables:
  LOG_LEVEL: INFO
  PM25_THRESHOLD: 25.0

automatic_scaling:
  min_instances: 0
  max_instances: 10
```

2. **Deploy:**
```bash
gcloud app deploy
```

### Microsoft Azure

#### Using Container Instances

1. **Deploy container:**
```bash
az container create \
  --resource-group myResourceGroup \
  --name breathable-commute \
  --image breathable-commute:latest \
  --ports 8501 \
  --dns-name-label breathable-commute-app
```

## Environment Configuration

### Required Environment Variables

The application works with default values, but you can customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPEN_METEO_AIR_QUALITY_URL` | `https://air-quality-api.open-meteo.com/v1/air-quality` | Air quality API endpoint |
| `OPEN_METEO_WEATHER_URL` | `https://api.open-meteo.com/v1/forecast` | Weather API endpoint |
| `NEW_DELHI_LAT` | `28.6139` | New Delhi latitude |
| `NEW_DELHI_LON` | `77.2090` | New Delhi longitude |
| `MUMBAI_LAT` | `19.0760` | Mumbai latitude |
| `MUMBAI_LON` | `72.8777` | Mumbai longitude |
| `BENGALURU_LAT` | `12.9716` | Bengaluru latitude |
| `BENGALURU_LON` | `77.5946` | Bengaluru longitude |
| `HYDERABAD_LAT` | `17.3850` | Hyderabad latitude |
| `HYDERABAD_LON` | `78.4867` | Hyderabad longitude |
| `HEALTHY_AIR_QUALITY_THRESHOLD` | `50.0` | Healthy air quality threshold (μg/m³) |
| `HAZARDOUS_AIR_QUALITY_THRESHOLD` | `100.0` | Hazardous air quality threshold (μg/m³) |
| `REQUEST_TIMEOUT` | `10` | API timeout (seconds) |
| `MAX_RETRIES` | `3` | Max retry attempts |
| `RETRY_DELAY` | `1.0` | Retry delay (seconds) |
| `LOG_LEVEL` | `INFO` | Logging level |

### Platform-Specific Configuration

**Streamlit Cloud:**
- Use the Secrets section in app settings
- Format as TOML key-value pairs

**Heroku:**
```bash
heroku config:set VARIABLE_NAME=value
```

**Docker:**
```bash
docker run -e VARIABLE_NAME=value ...
# or use --env-file .env
```

**Kubernetes:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  LOG_LEVEL: "INFO"
  PM25_THRESHOLD: "25.0"
```

## Monitoring and Maintenance

### Health Checks

The application includes built-in health checks:

- **Endpoint:** `/_stcore/health`
- **Docker:** Automatic health checks configured
- **Kubernetes:** Readiness and liveness probes

### Logging

Configure logging levels:
- `DEBUG`: Detailed debugging information
- `INFO`: General information (default)
- `WARNING`: Warning messages only
- `ERROR`: Error messages only

### Performance Monitoring

Monitor these metrics:
- Response time for API calls
- Memory usage
- CPU utilization
- Error rates
- User sessions

### Maintenance Tasks

**Regular Updates:**
1. Update dependencies: `pip install -r requirements.txt --upgrade`
2. Run security scans: `pip audit`
3. Update base Docker images
4. Monitor API rate limits

**Backup Considerations:**
- No persistent data to backup
- Configuration files in version control
- Monitor API key usage and limits

## Troubleshooting

### Common Issues

**Application won't start:**
```bash
# Check Python version
python --version

# Verify dependencies
pip install -r requirements.txt

# Check for port conflicts
netstat -tulpn | grep 8501  # Linux
netstat -ano | findstr :8501  # Windows
```

**API connection errors:**
```bash
# Test API connectivity for Indian cities
curl "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=28.6139&longitude=77.2090&current=pm2_5"
curl "https://api.open-meteo.com/v1/forecast?latitude=28.6139&longitude=77.2090&current=temperature_2m,wind_speed_10m,precipitation"
```

**Memory issues:**
- Increase container memory limits
- Monitor memory usage patterns
- Consider caching strategies

**Performance problems:**
- Check API response times
- Monitor concurrent user load
- Optimize data processing

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
streamlit run app.py
```

### Getting Help

1. Check application logs
2. Verify environment configuration
3. Test API endpoints manually
4. Review platform-specific documentation
5. Check GitHub issues for known problems

### Support Resources

- **Streamlit Documentation:** [docs.streamlit.io](https://docs.streamlit.io)
- **Docker Documentation:** [docs.docker.com](https://docs.docker.com)
- **Heroku Documentation:** [devcenter.heroku.com](https://devcenter.heroku.com)
- **API Documentation:**
  - Open-Meteo Air Quality: [open-meteo.com/en/docs/air-quality-api](https://open-meteo.com/en/docs/air-quality-api)
  - Open-Meteo Weather: [open-meteo.com/en/docs](https://open-meteo.com/en/docs)

## Security Considerations

### API Security
- No API keys required for current APIs
- Monitor usage to avoid rate limiting
- Consider implementing request caching

### Application Security
- Run containers as non-root user
- Keep dependencies updated
- Use HTTPS in production
- Implement proper error handling

### Data Privacy
- No personal data is collected or stored
- All data comes from public APIs
- Consider GDPR compliance for EU users

## Performance Optimization

### Caching Strategies
- Implement API response caching
- Use Streamlit's built-in caching
- Consider Redis for distributed caching

### Scaling Considerations
- Horizontal scaling with load balancers
- Container orchestration with Kubernetes
- Auto-scaling based on traffic patterns

### Resource Optimization
- Optimize Docker image size
- Minimize memory usage
- Efficient data processing algorithms
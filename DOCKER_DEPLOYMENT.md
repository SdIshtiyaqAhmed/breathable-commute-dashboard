# Breathable Commute - Docker Deployment Guide

This guide covers deploying the Breathable Commute dashboard using Docker and Docker Compose.

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- 2GB+ available RAM
- Internet connection for API access

### Development Deployment

```bash
# Build and run in development mode
make dev
# OR
./docker-deploy.sh run dev

# Access the dashboard
open http://localhost:8501
```

### Production Deployment

```bash
# Build and run in production mode
make prod
# OR  
./docker-deploy.sh run prod

# Access the dashboard
open http://localhost
```

## 📋 Available Commands

### Using Makefile

```bash
# Development
make build          # Build Docker image
make run            # Run development server
make stop           # Stop containers
make logs           # View logs
make test           # Run tests
make shell          # Open container shell

# Production
make prod-build     # Build production image
make prod-run       # Run with nginx proxy
make prod-stop      # Stop production setup

# Maintenance
make clean          # Remove containers/images
make clean-all      # Remove everything including volumes
```

### Using Deployment Script

```bash
# Build
./docker-deploy.sh build dev     # Development build
./docker-deploy.sh build prod    # Production build

# Run
./docker-deploy.sh run dev       # Development mode
./docker-deploy.sh run prod      # Production mode

# Control
./docker-deploy.sh stop dev      # Stop development
./docker-deploy.sh restart prod  # Restart production
./docker-deploy.sh logs dev      # View logs

# Maintenance
./docker-deploy.sh test          # Run tests
./docker-deploy.sh health        # Health check
./docker-deploy.sh cleanup       # Clean up resources
```

## 🏗️ Architecture

### Development Setup
- **Streamlit App**: Direct access on port 8501
- **Configuration**: Environment variables from docker-compose.yml
- **Logging**: Console output with INFO level
- **Health Check**: Built-in Streamlit health endpoint

### Production Setup
- **Nginx Reverse Proxy**: Port 80/443 with SSL support
- **Streamlit App**: Backend service on port 8501
- **Configuration**: Optimized for production workloads
- **Logging**: Structured logging with log rotation
- **Health Check**: Multi-layer health monitoring
- **Security**: Rate limiting, security headers, CORS

## 🔧 Configuration

### Environment Variables

The application supports extensive configuration through environment variables:

#### Indian City Coordinates
```bash
NEW_DELHI_LAT=28.6139
NEW_DELHI_LON=77.2090
MUMBAI_LAT=19.0760
MUMBAI_LON=72.8777
BENGALURU_LAT=12.9716
BENGALURU_LON=77.5946
HYDERABAD_LAT=17.3850
HYDERABAD_LON=78.4867
```

#### Air Quality Thresholds (μg/m³)
```bash
HEALTHY_AIR_QUALITY_THRESHOLD=50.0
HAZARDOUS_AIR_QUALITY_THRESHOLD=100.0
```

#### Weather Thresholds
```bash
MODERATE_WIND_THRESHOLD=20.0
HIGH_WIND_THRESHOLD=30.0
HIGH_TEMPERATURE_THRESHOLD=35.0
COMFORTABLE_TEMPERATURE_THRESHOLD=30.0
```

#### API Configuration
```bash
OPEN_METEO_AIR_QUALITY_URL=https://air-quality-api.open-meteo.com/v1/air-quality
OPEN_METEO_WEATHER_URL=https://api.open-meteo.com/v1/forecast
REQUEST_TIMEOUT=10
MAX_RETRIES=3
RETRY_DELAY=1.0
```

#### Performance Settings
```bash
CACHE_DURATION_SECONDS=300
MAX_CONCURRENT_REQUESTS=10
CONNECTION_POOL_SIZE=20
PERFORMANCE_MONITORING_ENABLED=true
AUTO_REFRESH_INTERVAL=30
```

#### Logging Configuration
```bash
LOG_LEVEL=INFO
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_TIMEOUT=5
```

### Custom Configuration

Create a `.env` file in the project root to override default settings:

```bash
# .env file example
LOG_LEVEL=DEBUG
CACHE_DURATION_SECONDS=600
MAX_CONCURRENT_REQUESTS=20
HEALTHY_AIR_QUALITY_THRESHOLD=40.0
```

## 🔍 Monitoring & Health Checks

### Health Check Endpoints

- **Development**: `http://localhost:8501/_stcore/health`
- **Production**: `http://localhost/health` (nginx proxy)

### Container Health Monitoring

Both development and production setups include automatic health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "--fail", "http://localhost:8501/_stcore/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Logging

View real-time logs:

```bash
# Development logs
docker-compose logs -f breathable-commute

# Production logs (app + nginx)
docker-compose -f docker-compose.prod.yml logs -f
```

## 🔒 Security

### Production Security Features

1. **Non-root User**: Application runs as `streamlit` user (UID 1000)
2. **Rate Limiting**: Nginx configured with request rate limits
3. **Security Headers**: HSTS, X-Frame-Options, CSP headers
4. **SSL Ready**: HTTPS configuration template included
5. **Resource Limits**: CPU and memory limits in production

### SSL Configuration

For production HTTPS, uncomment the SSL server block in `nginx/nginx.conf` and:

1. Place SSL certificates in `nginx/ssl/`
2. Update server names in nginx configuration
3. Restart the production stack

```bash
# Create SSL directory
mkdir -p nginx/ssl

# Copy your certificates
cp your-cert.pem nginx/ssl/cert.pem
cp your-key.pem nginx/ssl/key.pem

# Update nginx.conf and restart
make prod-stop
make prod-run
```

## 🚨 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using the port
netstat -tulpn | grep :8501

# Stop conflicting services
sudo systemctl stop apache2  # or nginx, etc.
```

#### Container Won't Start
```bash
# Check container logs
docker-compose logs breathable-commute

# Check system resources
docker system df
docker system prune  # Clean up if needed
```

#### API Connection Issues
```bash
# Test API connectivity from container
docker-compose exec breathable-commute curl -I https://api.open-meteo.com/v1/forecast

# Check DNS resolution
docker-compose exec breathable-commute nslookup api.open-meteo.com
```

#### Health Check Failures
```bash
# Manual health check
curl -f http://localhost:8501/_stcore/health

# Check application logs
docker-compose logs -f breathable-commute
```

### Performance Issues

#### High Memory Usage
```bash
# Check container resource usage
docker stats breathable-commute-dashboard

# Adjust memory limits in docker-compose.prod.yml
deploy:
  resources:
    limits:
      memory: 2G  # Increase if needed
```

#### Slow API Responses
```bash
# Increase timeout values
REQUEST_TIMEOUT=20
MAX_RETRIES=5
RETRY_DELAY=2.0
```

## 📊 Monitoring & Metrics

### Container Metrics

```bash
# Real-time resource usage
docker stats

# Container inspection
docker inspect breathable-commute-dashboard

# System-wide Docker info
docker system df
docker system events
```

### Application Metrics

The application includes built-in performance monitoring when enabled:

```bash
PERFORMANCE_MONITORING_ENABLED=true
SLOW_REQUEST_THRESHOLD=5.0
```

## 🔄 Updates & Maintenance

### Updating the Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
./docker-deploy.sh restart prod
```

### Database/Cache Cleanup

```bash
# Clear application cache
docker-compose exec breathable-commute rm -rf /tmp/streamlit-cache

# Full cleanup and restart
make clean-all
make prod
```

### Backup Configuration

```bash
# Backup current configuration
cp docker-compose.prod.yml docker-compose.prod.yml.backup
cp nginx/nginx.conf nginx/nginx.conf.backup
```

## 📈 Scaling

### Horizontal Scaling

For high-traffic deployments, consider:

1. **Load Balancer**: Use multiple app instances behind nginx
2. **Container Orchestration**: Deploy with Docker Swarm or Kubernetes
3. **CDN**: Cache static assets with CloudFlare or similar
4. **API Caching**: Implement Redis for API response caching

### Example Multi-Instance Setup

```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  breathable-commute:
    # ... existing config
    deploy:
      replicas: 3
      
  nginx:
    # ... configure upstream with multiple backends
```

## 📞 Support

For deployment issues:

1. Check the troubleshooting section above
2. Review container logs: `docker-compose logs -f`
3. Verify configuration: `docker-compose config`
4. Test health endpoints manually
5. Check system resources and Docker daemon status

## 🎯 Production Checklist

Before deploying to production:

- [ ] SSL certificates configured
- [ ] Environment variables reviewed
- [ ] Resource limits set appropriately
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented
- [ ] Security headers verified
- [ ] Rate limiting tested
- [ ] Health checks validated
- [ ] Log rotation configured
- [ ] Update process documented
# 🐳 Breathable Commute - Docker Setup

Quick reference for Docker deployment of the Breathable Commute dashboard.

## 🚀 Quick Start

### Development
```bash
# Build and run
make dev

# Access dashboard
http://localhost:8501
```

### Production
```bash
# Build and run with nginx
make prod

# Access dashboard  
http://localhost
```

## 📁 Docker Files Overview

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build for optimized production image |
| `docker-compose.yml` | Development environment configuration |
| `docker-compose.prod.yml` | Production deployment with nginx |
| `.dockerignore` | Excludes unnecessary files from Docker context |
| `nginx/nginx.conf` | Nginx reverse proxy configuration |
| `Makefile` | Convenient commands for Docker operations |
| `docker-deploy.sh` | Comprehensive deployment script |

## 🔧 Key Features

### Security
- ✅ Non-root user (streamlit:1000)
- ✅ Multi-stage build for smaller images
- ✅ Security headers in nginx
- ✅ Rate limiting configured
- ✅ Health checks enabled

### Performance
- ✅ Optimized Python dependencies
- ✅ Nginx reverse proxy with caching
- ✅ Connection pooling
- ✅ Resource limits in production
- ✅ Gzip compression

### Monitoring
- ✅ Health check endpoints
- ✅ Structured logging
- ✅ Container metrics
- ✅ Log rotation

## 🌍 Environment Variables

The application is configured for Indian cities with these defaults:

```bash
# Cities
NEW_DELHI_LAT=28.6139    NEW_DELHI_LON=77.2090
MUMBAI_LAT=19.0760       MUMBAI_LON=72.8777
BENGALURU_LAT=12.9716    BENGALURU_LON=77.5946
HYDERABAD_LAT=17.3850    HYDERABAD_LON=78.4867

# Thresholds
HEALTHY_AIR_QUALITY_THRESHOLD=50.0
HAZARDOUS_AIR_QUALITY_THRESHOLD=100.0
```

## 📊 Validation

Run the validation script to check your Docker setup:

```bash
python validate-docker.py
```

## 📚 Full Documentation

See `DOCKER_DEPLOYMENT.md` for complete deployment guide including:
- Detailed configuration options
- SSL setup for production
- Troubleshooting guide
- Scaling recommendations
- Security best practices

## 🆘 Quick Troubleshooting

```bash
# Check container status
docker-compose ps

# View logs
make logs

# Health check
curl http://localhost:8501/_stcore/health

# Restart everything
make clean && make dev
```
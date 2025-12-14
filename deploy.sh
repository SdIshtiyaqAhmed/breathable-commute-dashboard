#!/bin/bash

# Breathable Commute Deployment Script
# This script helps deploy the application to various platforms

set -e

echo "🚀 Breathable Commute Deployment Helper"
echo "======================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to deploy locally
deploy_local() {
    echo "📦 Setting up local deployment..."
    
    # Check Python version
    python_version=$(python --version 2>&1 | awk '{print $2}')
    echo "Python version: $python_version"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python -m venv venv
    fi
    
    # Activate virtual environment
    echo "Activating virtual environment..."
    source venv/bin/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    # Copy environment file if it doesn't exist
    if [ ! -f ".env" ]; then
        echo "Creating .env file from template..."
        cp .env.example .env
        echo "⚠️  Please review and update .env file with your settings"
    fi
    
    # Run tests
    echo "Running tests..."
    pytest
    
    echo "✅ Local setup complete!"
    echo "Run 'streamlit run app.py' to start the application"
}

# Function to deploy with Docker
deploy_docker() {
    echo "🐳 Setting up Docker deployment..."
    
    if ! command_exists docker; then
        echo "❌ Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Build Docker image
    echo "Building Docker image..."
    docker build -t breathable-commute .
    
    # Run container
    echo "Starting container..."
    docker run -d \
        --name breathable-commute \
        -p 8501:8501 \
        --env-file .env \
        breathable-commute
    
    echo "✅ Docker deployment complete!"
    echo "Application available at http://localhost:8501"
}

# Function to deploy with Docker Compose
deploy_compose() {
    echo "🐳 Setting up Docker Compose deployment..."
    
    if ! command_exists docker-compose; then
        echo "❌ Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Start services
    echo "Starting services with Docker Compose..."
    docker-compose up -d
    
    echo "✅ Docker Compose deployment complete!"
    echo "Application available at http://localhost:8501"
}

# Function to prepare for Streamlit Cloud
prepare_streamlit_cloud() {
    echo "☁️  Preparing for Streamlit Cloud deployment..."
    
    # Check if secrets.toml exists
    if [ ! -f ".streamlit/secrets.toml" ]; then
        echo "Creating secrets.toml template..."
        cat > .streamlit/secrets.toml << EOF
# Streamlit Cloud Secrets Configuration
# Add your environment variables here

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
EOF
        echo "⚠️  Please update .streamlit/secrets.toml with your actual values"
    fi
    
    echo "✅ Streamlit Cloud preparation complete!"
    echo "📋 Next steps:"
    echo "   1. Push your code to GitHub"
    echo "   2. Go to https://share.streamlit.io"
    echo "   3. Connect your GitHub repository"
    echo "   4. Set main file path to 'app.py'"
    echo "   5. Configure secrets in Streamlit Cloud settings"
}

# Function to run tests
run_tests() {
    echo "🧪 Running test suite..."
    
    # Check if pytest is available
    if ! command_exists pytest; then
        echo "Installing pytest..."
        pip install pytest hypothesis
    fi
    
    # Run tests
    pytest -v
    
    echo "✅ Tests completed!"
}

# Function to check health
check_health() {
    echo "🏥 Checking application health..."
    
    # Check if application is running
    if curl -f http://localhost:8501/_stcore/health >/dev/null 2>&1; then
        echo "✅ Application is healthy and running!"
    else
        echo "❌ Application is not responding. Please check if it's running."
        exit 1
    fi
}

# Main menu
case "${1:-}" in
    "local")
        deploy_local
        ;;
    "docker")
        deploy_docker
        ;;
    "compose")
        deploy_compose
        ;;
    "streamlit-cloud")
        prepare_streamlit_cloud
        ;;
    "test")
        run_tests
        ;;
    "health")
        check_health
        ;;
    *)
        echo "Usage: $0 {local|docker|compose|streamlit-cloud|test|health}"
        echo ""
        echo "Commands:"
        echo "  local           - Set up local development environment"
        echo "  docker          - Deploy using Docker"
        echo "  compose         - Deploy using Docker Compose"
        echo "  streamlit-cloud - Prepare for Streamlit Cloud deployment"
        echo "  test            - Run test suite"
        echo "  health          - Check application health"
        echo ""
        echo "Examples:"
        echo "  ./deploy.sh local"
        echo "  ./deploy.sh docker"
        echo "  ./deploy.sh test"
        exit 1
        ;;
esac
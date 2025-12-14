#!/bin/bash

# Breathable Commute - Docker Deployment Script
# This script handles building and deploying the Breathable Commute dashboard

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="breathable-commute"
CONTAINER_NAME="breathable-commute-dashboard"
PORT="8501"
HEALTH_CHECK_URL="http://localhost:${PORT}/_stcore/health"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    log_success "Docker is available and running"
}

check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        log_warning "docker-compose not found, trying 'docker compose'"
        if ! docker compose version &> /dev/null; then
            log_error "Neither docker-compose nor 'docker compose' is available"
            exit 1
        fi
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    log_success "Docker Compose is available"
}

build_image() {
    log_info "Building Docker image: ${IMAGE_NAME}"
    
    if [ "$1" = "prod" ]; then
        docker build -t ${IMAGE_NAME}:latest .
    else
        ${DOCKER_COMPOSE} build
    fi
    
    log_success "Docker image built successfully"
}

run_container() {
    local mode=${1:-dev}
    
    log_info "Starting container in ${mode} mode"
    
    if [ "$mode" = "prod" ]; then
        ${DOCKER_COMPOSE} -f docker-compose.prod.yml up -d
        log_info "Production deployment started with nginx reverse proxy"
        log_info "Application available at: http://localhost"
    else
        ${DOCKER_COMPOSE} up -d
        log_info "Development deployment started"
        log_info "Application available at: http://localhost:${PORT}"
    fi
    
    log_success "Container started successfully"
}

stop_container() {
    local mode=${1:-dev}
    
    log_info "Stopping containers"
    
    if [ "$mode" = "prod" ]; then
        ${DOCKER_COMPOSE} -f docker-compose.prod.yml down
    else
        ${DOCKER_COMPOSE} down
    fi
    
    log_success "Containers stopped"
}

health_check() {
    local max_attempts=30
    local attempt=1
    local url=${1:-$HEALTH_CHECK_URL}
    
    log_info "Performing health check..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            log_success "Health check passed (attempt $attempt)"
            return 0
        fi
        
        log_info "Health check attempt $attempt/$max_attempts failed, retrying in 2 seconds..."
        sleep 2
        ((attempt++))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    return 1
}

run_tests() {
    log_info "Running tests in Docker container"
    
    if ! docker ps | grep -q ${CONTAINER_NAME}; then
        log_warning "Container not running, starting it first..."
        run_container dev
        sleep 10
    fi
    
    ${DOCKER_COMPOSE} exec breathable-commute python -m pytest tests/ -v
    
    log_success "Tests completed"
}

show_logs() {
    local mode=${1:-dev}
    
    if [ "$mode" = "prod" ]; then
        ${DOCKER_COMPOSE} -f docker-compose.prod.yml logs -f
    else
        ${DOCKER_COMPOSE} logs -f
    fi
}

cleanup() {
    log_info "Cleaning up Docker resources"
    
    # Stop and remove containers
    ${DOCKER_COMPOSE} down --remove-orphans 2>/dev/null || true
    ${DOCKER_COMPOSE} -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true
    
    # Remove images
    docker rmi ${IMAGE_NAME}:latest 2>/dev/null || true
    
    # Clean up unused resources
    docker system prune -f
    
    log_success "Cleanup completed"
}

show_usage() {
    echo "Breathable Commute - Docker Deployment Script"
    echo "============================================="
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build [dev|prod]     Build Docker image"
    echo "  run [dev|prod]       Run the application"
    echo "  stop [dev|prod]      Stop the application"
    echo "  restart [dev|prod]   Restart the application"
    echo "  logs [dev|prod]      Show application logs"
    echo "  test                 Run tests"
    echo "  health               Check application health"
    echo "  cleanup              Clean up Docker resources"
    echo "  help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build dev         Build development image"
    echo "  $0 run prod          Run in production mode"
    echo "  $0 restart dev       Restart development environment"
    echo "  $0 logs prod         Show production logs"
    echo ""
}

# Main script logic
main() {
    local command=${1:-help}
    local mode=${2:-dev}
    
    case $command in
        "build")
            check_docker
            check_docker_compose
            build_image $mode
            ;;
        "run")
            check_docker
            check_docker_compose
            build_image $mode
            run_container $mode
            sleep 5
            if [ "$mode" = "prod" ]; then
                health_check "http://localhost/health"
            else
                health_check
            fi
            ;;
        "stop")
            check_docker
            check_docker_compose
            stop_container $mode
            ;;
        "restart")
            check_docker
            check_docker_compose
            stop_container $mode
            build_image $mode
            run_container $mode
            sleep 5
            if [ "$mode" = "prod" ]; then
                health_check "http://localhost/health"
            else
                health_check
            fi
            ;;
        "logs")
            check_docker
            check_docker_compose
            show_logs $mode
            ;;
        "test")
            check_docker
            check_docker_compose
            run_tests
            ;;
        "health")
            if [ "$mode" = "prod" ]; then
                health_check "http://localhost/health"
            else
                health_check
            fi
            ;;
        "cleanup")
            check_docker
            check_docker_compose
            cleanup
            ;;
        "help"|*)
            show_usage
            ;;
    esac
}

# Run main function with all arguments
main "$@"
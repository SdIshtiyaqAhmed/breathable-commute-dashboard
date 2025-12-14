# Breathable Commute - Docker Management Makefile

.PHONY: help build run stop clean test logs shell prod-build prod-run prod-stop

# Default target
help:
	@echo "Breathable Commute - Docker Management"
	@echo "======================================"
	@echo ""
	@echo "Development Commands:"
	@echo "  build       Build the Docker image"
	@echo "  run         Run the application in development mode"
	@echo "  stop        Stop the running containers"
	@echo "  logs        Show application logs"
	@echo "  shell       Open a shell in the running container"
	@echo "  test        Run tests in Docker container"
	@echo ""
	@echo "Production Commands:"
	@echo "  prod-build  Build production image"
	@echo "  prod-run    Run in production mode with nginx"
	@echo "  prod-stop   Stop production containers"
	@echo ""
	@echo "Maintenance Commands:"
	@echo "  clean       Remove containers and images"
	@echo "  clean-all   Remove everything including volumes"
	@echo ""

# Development commands
build:
	@echo "Building Breathable Commute Docker image..."
	docker-compose build

run:
	@echo "Starting Breathable Commute in development mode..."
	docker-compose up -d
	@echo "Application available at: http://localhost:8501"

stop:
	@echo "Stopping development containers..."
	docker-compose down

logs:
	@echo "Showing application logs..."
	docker-compose logs -f breathable-commute

shell:
	@echo "Opening shell in running container..."
	docker-compose exec breathable-commute /bin/bash

test:
	@echo "Running tests in Docker container..."
	docker-compose exec breathable-commute python -m pytest tests/ -v

# Production commands
prod-build:
	@echo "Building production image..."
	docker build -t breathable-commute:latest .

prod-run:
	@echo "Starting production deployment..."
	docker-compose -f docker-compose.prod.yml up -d
	@echo "Production application available at: http://localhost"

prod-stop:
	@echo "Stopping production containers..."
	docker-compose -f docker-compose.prod.yml down

# Maintenance commands
clean:
	@echo "Cleaning up containers and images..."
	docker-compose down --rmi all --remove-orphans
	docker-compose -f docker-compose.prod.yml down --rmi all --remove-orphans

clean-all:
	@echo "Cleaning up everything including volumes..."
	docker-compose down --rmi all --volumes --remove-orphans
	docker-compose -f docker-compose.prod.yml down --rmi all --volumes --remove-orphans
	docker system prune -f

# Health check
health:
	@echo "Checking application health..."
	@curl -f http://localhost:8501/_stcore/health || echo "Application not responding"

# Quick development workflow
dev: build run
	@echo "Development environment ready!"
	@echo "Access the dashboard at: http://localhost:8501"

# Quick production workflow  
prod: prod-build prod-run
	@echo "Production environment ready!"
	@echo "Access the dashboard at: http://localhost"
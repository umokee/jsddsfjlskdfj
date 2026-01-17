#!/bin/bash
set -e

echo "🐳 Task Manager Docker Setup"
echo "=============================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.docker .env

    # Generate API key
    echo "🔑 Generating secure API key..."
    API_KEY=$(openssl rand -hex 32)

    # Replace API key in .env
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/your-secret-key-change-me-to-something-secure/$API_KEY/" .env
    else
        sed -i "s/your-secret-key-change-me-to-something-secure/$API_KEY/" .env
    fi

    echo "✅ Generated API key: $API_KEY"
    echo "   (saved to .env file)"
    echo ""
else
    echo "ℹ️  .env file already exists, using existing configuration"
    echo ""
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo ""
    echo "On NixOS, make sure Docker is enabled in configuration.nix:"
    echo ""
    echo "  virtualisation.docker.enable = true;"
    echo ""
    echo "Then run: sudo nixos-rebuild switch"
    exit 1
fi

# Check if port is available
PORT=$(grep PUBLIC_PORT .env | cut -d'=' -f2)
PORT=${PORT:-8080}

if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Warning: Port $PORT is already in use!"
    echo ""
    echo "To use a different port, edit .env file:"
    echo "  PUBLIC_PORT=8081"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Build and start containers
echo "🏗️  Building and starting containers..."
docker-compose up -d --build

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check health
BACKEND_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' taskmanager-backend 2>/dev/null || echo "starting")
FRONTEND_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' taskmanager-frontend 2>/dev/null || echo "starting")

echo "   Backend: $BACKEND_HEALTH"
echo "   Frontend: $FRONTEND_HEALTH"
echo ""

echo "✅ Task Manager is starting!"
echo ""
echo "📱 Access the application at: http://localhost:$PORT"
echo "🔑 API Key: $(grep TASK_MANAGER_API_KEY .env | cut -d'=' -f2)"
echo ""
echo "📊 Useful commands:"
echo "   docker-compose logs -f     # View logs"
echo "   docker-compose ps          # Check status"
echo "   docker-compose stop        # Stop containers"
echo "   docker-compose down        # Stop and remove containers"
echo ""
echo "📖 For more information, see DOCKER-SETUP.md"

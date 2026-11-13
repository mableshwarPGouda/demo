#!/bin/bash
set -e

echo "============================================================"
echo " Starting Frontend Deployment on EC2"
echo "============================================================"

# Read or prompt for Backend EC2 Public IP / URL
if [ -n "$1" ]; then
    BACKEND_INPUT="$1"
elif [ -n "$VITE_API_URL" ]; then
    BACKEND_INPUT="$VITE_API_URL"
else
    # Check if .env file already has a valid VITE_API_URL
    EXISTING_URL=$(grep -E "^VITE_API_URL=" .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' | tr -d "'" || true)
    if [ -n "$EXISTING_URL" ] && [[ "$EXISTING_URL" != *"<YOUR_BACKEND_EC2_PUBLIC_IP>"* ]]; then
        BACKEND_INPUT="$EXISTING_URL"
        echo "[Config] Found existing API URL in .env: $BACKEND_INPUT"
    else
        read -p "Enter Backend EC2 Public IP (e.g. 54.123.45.67 or http://54.123.45.67:5000): " USER_IP
        BACKEND_INPUT="$USER_IP"
    fi
fi

# Clean and normalize BACKEND_API_URL
BACKEND_INPUT=$(echo "$BACKEND_INPUT" | sed 's|/$||')
if [[ "$BACKEND_INPUT" =~ ^https?:// ]]; then
    if [[ "$BACKEND_INPUT" =~ /api$ ]]; then
        FULL_API_URL="$BACKEND_INPUT"
    elif [[ "$BACKEND_INPUT" =~ :5000$ ]]; then
        FULL_API_URL="${BACKEND_INPUT}/api"
    else
        FULL_API_URL="${BACKEND_INPUT}:5000/api"
    fi
else
    FULL_API_URL="http://${BACKEND_INPUT}:5000/api"
fi

echo "[Config] Configured Backend API URL: $FULL_API_URL"
echo "VITE_API_URL=$FULL_API_URL" > .env

# Check if Docker is installed and running
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "[Mode] Deploying via Docker container..."

    # Stop and remove existing container if running
    if [ "$(docker ps -aq -f name=medstock-frontend)" ]; then
        echo "[Docker] Stopping and removing existing medstock-frontend container..."
        docker stop medstock-frontend || true
        docker rm medstock-frontend || true
    fi

    echo "[Docker] Building frontend image with API URL: $FULL_API_URL..."
    docker build --build-arg VITE_API_URL="$FULL_API_URL" -t medstock-frontend:latest .

    echo "[Docker] Running frontend container on port 80..."
    docker run -d \
        --name medstock-frontend \
        --restart unless-stopped \
        -p 80:80 \
        medstock-frontend:latest

else
    echo "[Mode] Docker not found or inactive. Building locally and deploying with system Nginx..."

    if ! command -v npm >/dev/null 2>&1; then
        echo "[Error] Node.js / npm is required for local build. Please install Node.js 18+ or Docker."
        exit 1
    fi

    echo "[Build] Installing npm dependencies..."
    npm install

    echo "[Build] Compiling production dist/ bundle with Vite..."
    export VITE_API_URL="$FULL_API_URL"
    npm run build

    # Check if system Nginx is installed
    if command -v nginx >/dev/null 2>&1; then
        echo "[Nginx] Deploying build artifacts to /usr/share/nginx/html or /var/www/html..."
        TARGET_DIR="/usr/share/nginx/html"
        [ -d "/var/www/html" ] && TARGET_DIR="/var/www/html"

        sudo cp -r dist/* "$TARGET_DIR/"
        if [ -f nginx.conf ]; then
            sudo cp nginx.conf /etc/nginx/conf.d/default.conf 2>/dev/null || sudo cp nginx.conf /etc/nginx/sites-available/default 2>/dev/null || true
        fi
        sudo systemctl restart nginx || sudo service nginx restart || true
    else
        echo "[Warning] Nginx not found. dist/ built successfully. You can serve it with any static server or install nginx (sudo apt update && sudo apt install -y nginx)."
    fi
fi

echo "Waiting for web server to initialize..."
sleep 3

echo "============================================================"
echo " Running HTTP Response Verification..."
echo "============================================================"
if curl -s -I http://localhost | grep -E "HTTP/.* (200|304)" > /dev/null; then
    echo "SUCCESS: Frontend is live and serving HTTP 200 OK on port 80!"
    curl -s -I http://localhost | head -n 5
else
    echo "Check response header:"
    curl -s -I http://localhost || true
fi
echo "============================================================"

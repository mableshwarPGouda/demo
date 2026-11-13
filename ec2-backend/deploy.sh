#!/bin/bash
set -e

echo "============================================================"
echo " Starting Backend Deployment on EC2"
echo "============================================================"

# Ensure .env exists
if [ ! -f .env ]; then
    echo "[Info] .env not found. Creating from .env.example..."
    cp .env.example .env
fi

# Ensure SQLite database file exists for persistence
if [ ! -f medicine_tracker.db ]; then
    echo "[Info] Creating empty medicine_tracker.db file..."
    touch medicine_tracker.db
fi

# Check if Docker is installed and running
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "[Mode] Deploying via Docker container..."
    
    # Stop and remove existing container if running
    if [ "$(docker ps -aq -f name=medstock-backend)" ]; then
        echo "[Docker] Stopping and removing existing medstock-backend container..."
        docker stop medstock-backend || true
        docker rm medstock-backend || true
    fi

    echo "[Docker] Building backend image..."
    docker build -t medstock-backend:latest .

    echo "[Docker] Running container on port 5000 with database persistence..."
    docker run -d \
        --name medstock-backend \
        --restart unless-stopped \
        -p 5000:5000 \
        -v "$(pwd)/medicine_tracker.db:/app/medicine_tracker.db" \
        -e USE_SQLITE=True \
        -e SQLITE_DB_NAME=medicine_tracker.db \
        -e FRONTEND_URL="*" \
        medstock-backend:latest

else
    echo "[Mode] Docker not found or inactive. Deploying with system Python..."
    
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN=python3
    elif command -v python >/dev/null 2>&1; then
        PYTHON_BIN=python
    else
        echo "[Error] Neither python3 nor docker is installed. Please install one of them."
        exit 1
    fi

    # Set up virtual environment if needed
    if [ ! -d "venv" ]; then
        echo "[Python] Creating virtual environment..."
        $PYTHON_BIN -m venv venv || virtualenv venv
    fi

    echo "[Python] Activating virtual environment & installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    # Stop any previous gunicorn instance running on port 5000
    pkill -f "gunicorn.*app:app" || true

    echo "[Python] Starting Gunicorn in background on 0.0.0.0:5000..."
    nohup gunicorn --bind 0.0.0.0:5000 --workers 3 app:app > backend.log 2>&1 &
fi

echo "Waiting for backend service to initialize..."
sleep 5

echo "============================================================"
echo " Running Health-Check..."
echo "============================================================"
HEALTH_URL="http://127.0.0.1:5000/api/health"

if curl -s -f "$HEALTH_URL" > /dev/null; then
    echo "SUCCESS: Backend API is live and responding healthy!"
    echo "Response:"
    curl -s "$HEALTH_URL"
    echo ""
else
    echo "Checking fallback health / test on port 5000..."
    if curl -s "http://127.0.0.1:5000/api/medicines" > /dev/null; then
        echo "SUCCESS: Backend API endpoints are responding on port 5000."
    else
        echo "WARNING: Backend health check did not return 200 OK. Check logs using: docker logs medstock-backend (or cat backend.log)"
    fi
fi
echo "============================================================"

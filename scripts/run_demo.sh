#!/bin/bash
set -e

echo "Starting FrayFuse API backend..."
# Start uvicorn without --reload for the demo
python -m uvicorn api.main:app --port 8000 &
UVICORN_PID=$!

echo "Waiting for uvicorn to bind..."
sleep 3

echo "Health check:"
curl -s http://localhost:8000/health
echo ""

echo "API is live."
wait $UVICORN_PID

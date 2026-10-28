#!/bin/bash
# =====================================================
# SIH26190 Legal DMS - Quick Start Script
# Run this once to start the backend, then open index.html
# =====================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=8765

echo "=============================="
echo " MHA Legal DMS - Backend Start"
echo "=============================="
echo ""

# Kill any old instance on the same port
echo "[1] Checking for existing process on port $PORT..."
fuser -k ${PORT}/tcp 2>/dev/null && echo "    Cleared." || echo "    Port is free."

echo "[2] Starting backend server on port $PORT..."
cd "$SCRIPT_DIR"
python3 backend_server.py &
SERVER_PID=$!
sleep 1

# Quick health check via Python
python3 -c "
import urllib.request, json, sys
try:
    res = urllib.request.urlopen('http://localhost:${PORT}/api/health', timeout=3)
    data = json.loads(res.read())
    print(f'[3] Health check OK: {data}')
except Exception as e:
    print(f'[3] Health check FAILED: {e}')
    sys.exit(1)
"

echo ""
echo "✓ Backend is running (PID: $SERVER_PID)"
echo ""
echo "▶ Now open this file in your browser:"
echo "  file://$SCRIPT_DIR/index.html"
echo ""
echo "  API Base: http://localhost:$PORT"
echo "  To stop:  kill $SERVER_PID"
echo "=============================="

wait $SERVER_PID

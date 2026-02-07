#!/bin/bash

# CFIN Development Startup Script
# This script starts both the backend and frontend services for development
#
# Usage:
#   ./start-dev.sh
#
# What it does:
#   1. Kills any existing processes on port 8000
#   2. Starts the Python backend server on port 8000
#   3. Starts the Next.js frontend development server
#
# To stop: Press Ctrl+C (this will stop both servers)
#
# Note: Make sure you're in the cfin project root directory when running this script

set -e  # Exit on any error

echo "🚀 Starting CFIN Development Environment..."

# Step 1: Kill any existing processes on port 8000
echo "🔍 Checking for existing processes on port 8000..."
EXISTING_PIDS=$(lsof -i :8000 2>/dev/null | grep LISTEN | awk '{print $2}' || true)

if [ ! -z "$EXISTING_PIDS" ]; then
    echo "⚠️  Found existing processes on port 8000. Killing PIDs: $EXISTING_PIDS"
    echo "$EXISTING_PIDS" | xargs kill -9 2>/dev/null || true
    sleep 2  # Give processes time to die
    echo "✅ Port 8000 cleared"
else
    echo "✅ Port 8000 is available"
fi

# Step 2: Start the backend
echo "🐍 Starting backend server..."
cd /Users/alexcardell/AlexCoding_Local/cfin/backend

# Start backend in background
PYTHONPATH=$PYTHONPATH:/Users/alexcardell/AlexCoding_Local/cfin/backend python -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "✅ Backend started with PID: $BACKEND_PID"

# Give backend time to start
sleep 3

# Step 3: Start the frontend
echo "⚛️  Starting frontend development server..."
cd /Users/alexcardell/AlexCoding_Local/cfin/nextjs-fdas

# Run frontend in foreground (so we can see logs and stop with Ctrl+C)
echo "🌐 Frontend will start shortly..."
echo "📝 Use Ctrl+C to stop both servers"

# Trap to cleanup background processes when script exits
cleanup() {
    echo ""
    echo "🛑 Stopping development servers..."
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo "🐍 Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true
    fi
    echo "✅ Cleanup complete"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start frontend
npm run dev

# If we get here, npm run dev exited, so cleanup
cleanup

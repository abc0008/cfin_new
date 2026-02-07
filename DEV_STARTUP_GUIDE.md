# CFIN Development Startup Guide

## Quick Start

To start your CFIN development environment, run:

```bash
./start-dev.sh
```

## What the Script Does

The `start-dev.sh` script automates your development environment setup:

1. **🔍 Port Cleanup**: Checks for and kills any existing processes on port 8000
2. **🐍 Backend Startup**: Starts the Python FastAPI backend server with auto-reload
3. **⚛️ Frontend Startup**: Starts the Next.js development server

## Requirements

- Make sure you're in the cfin project root directory
- Ensure Python environment is properly set up for the backend
- Ensure Node.js dependencies are installed in the `nextjs-fdas` directory

## Usage

```bash
# From the cfin project root
cd /Users/alexcardell/AlexCoding_Local/cfin
./start-dev.sh
```

## Stopping the Servers

Press `Ctrl+C` to stop both servers. The script will automatically clean up background processes.

## Manual Commands (if needed)

If you prefer to run commands manually:

```bash
# Kill existing processes on port 8000
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Start backend
cd /Users/alexcardell/AlexCoding_Local/cfin/backend
PYTHONPATH=$PYTHONPATH:/Users/alexcardell/AlexCoding_Local/cfin/backend python -m uvicorn app.main:app --reload --port 8000

# Start frontend (in a new terminal)
cd /Users/alexcardell/AlexCoding_Local/cfin/nextjs-fdas
npm run dev
```

## Troubleshooting

- If the script fails to start, check that all dependencies are installed
- Ensure Python virtual environment is activated if you're using one
- Verify that port 8000 is not being used by other applications
- Make sure the script has executable permissions: `chmod +x start-dev.sh`

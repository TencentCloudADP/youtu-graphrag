#!/bin/bash

echo "🌟 Starting Youtu-GraphRAG Server..."
echo "=========================================="


# Check if required files exist
if [ ! -f "backend.py" ]; then
    echo "❌ backend.py not found. Please run this script from the project root directory."
    exit 1
fi

if [ ! -f "frontend/index.html" ]; then
    echo "❌ frontend/index.html not found."
    exit 1
fi

# Kill any existing backend processes
echo "🔄 Checking for existing processes..."
pkill -f backend.py 2>/dev/null || true

# Start the backend server
echo "🚀 Starting backend server..."
echo "🛑 Press Ctrl+C to stop the server"
echo "=========================================="

python backend.py

echo "👋 Youtu-GraphRAG server stopped."

#!/bin/bash

# Activate Python 3.10 environment
echo "🔄 Activating Python 3.10 environment..."
if command -v conda &> /dev/null; then
    # Initialize conda in the script
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate py310
    echo "✅ Python environment activated: $(python --version)"
else
    echo "⚠️ Conda not found. Please ensure Python 3.10 is available."
fi

# Load environment variables from .env file if exists
source .env 2>/dev/null

# Set default port if not defined in .env
PORT=${PORT:-8001}

# Disable tokenizers parallelism to avoid warnings
export TOKENIZERS_PARALLELISM=false

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
echo "📱 Access the application at: http://localhost:$PORT"
echo "🛑 Press Ctrl+C to stop the server"
echo "=========================================="

python backend.py

echo "👋 Youtu-GraphRAG server stopped."

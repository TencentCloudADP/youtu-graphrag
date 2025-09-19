#!/bin/bash

# Ensure shell is properly initialized for conda
echo "🔄 Initializing shell environment for Python 3.10..."

# Initialize shell environment variables for conda
if [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc"
elif [ -f "$HOME/.zshrc" ]; then
    source "$HOME/.zshrc"
fi

# Try to activate Python 3.10 environment
activate_python_env() {
    echo "🔄 Activating Python 3.10 environment..."
    
    # Try conda activation with multiple approaches
    if command -v conda &> /dev/null; then
        # Approach 1: Use conda info --base
        if BASE=$(conda info --base 2>/dev/null); then
            source "$BASE/etc/profile.d/conda.sh"
            conda activate py310 && echo "✅ Python environment activated: $(python --version)" && return 0
        fi
        
        # Approach 2: Try common conda base locations
        for CONDA_BASE in "$HOME/miniconda3" "$HOME/anaconda3" "/opt/miniconda3" "/opt/anaconda3"; do
            if [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
                source "$CONDA_BASE/etc/profile.d/conda.sh"
                conda activate py310 && echo "✅ Python environment activated: $(python --version)" && return 0
            fi
        done
        
        echo "⚠️ Conda found but couldn't activate py310 environment."
    else
        echo "⚠️ Conda not found in PATH."
    fi
    
    # Fallback: Check if Python 3.10 is available directly
    if python3.10 --version &> /dev/null; then
        PYTHON=python3.10
        echo "✅ Using Python 3.10 directly: $(python3.10 --version)"
        return 0
    elif python --version 2>&1 | grep -q "Python 3.1[0-9]"; then
        PYTHON=python
        echo "✅ Python 3.10+ found: $(python --version)"
        return 0
    fi
    
    echo "❌ Python 3.10 environment not found. Using default Python."
    PYTHON=python
    return 1
}

# Call the activation function
activate_python_env

# Set alias for Python if we found a specific version
if [ -n "$PYTHON" ]; then
    alias python="$PYTHON"
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

# Create necessary directories if they don't exist
mkdir -p data/uploaded output/graphs output/chunks schemas

# Use the correct Python command (either direct Python 3.10 or alias)
if [ -n "$PYTHON" ]; then
    $PYTHON backend.py
else
    python backend.py
fi

echo "👋 Youtu-GraphRAG server stopped."

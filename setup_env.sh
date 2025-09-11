#!/bin/bash

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📦 Installing requirements..."
pip install -r requirements.txt

# Download spaCy model
echo "🧠 Downloading spaCy English model..."
python -m spacy download en_core_web_lg # If using Chinese mode, the corresponding Chinese database should be used here.

# Download default HuggingFace models
echo "🧠 Downloading default retriever model..."
python3 -c "
from huggingface_hub import snapshot_download
import os

try:
    model_path = snapshot_download(
        repo_id='sentence-transformers/all-MiniLM-L6-v2',
        ignore_patterns=['*.bin', '*.onnx', '*.ot', '*.h5'],
        local_files_only=False
    )
except:
    os.environ['HF_ENDPOINT'] = 'hf-mirror.com'
    model_path = snapshot_download(
        repo_id='sentence-transformers/all-MiniLM-L6-v2',
        ignore_patterns=['*.bin', '*.onnx', '*.ot', '*.h5'],
        local_files_only=False
    )

print(f'Model has been downloaded to: {model_path}')
"

# Verify installation
echo "✅ Verifying installation..."
python -c "
import fastapi
import uvicorn
import torch
import sentence_transformers
import faiss
import spacy
print('✅ All dependencies installed successfully!')
print(f'FastAPI version: {fastapi.__version__}')
print(f'PyTorch version: {torch.__version__}')
print(f'Sentence Transformers version: {sentence_transformers.__version__}')
"

if [ $? -eq 0 ]; then
    echo "==========================================="
    echo "🎉 Environment setup completed successfully!"
    echo "🚀 You can now start the server with: ./start.sh"
    echo "==========================================="
else
    echo "❌ Installation verification failed. Please check the error messages above."
    exit 1
fi

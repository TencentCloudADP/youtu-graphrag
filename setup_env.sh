#!/bin/bash

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install huggingface_hub separately (required for model download)
echo "📦 Installing huggingface_hub..."
pip install huggingface_hub

# Install requirements
echo "📦 Installing requirements..."
pip install -r requirements.txt

# 确保spaCy版本与Python 3.12兼容
echo "🔄 Upgrading spaCy to Python 3.12 compatible version..."
pip install --upgrade spacy

# Download spaCy Chinese and English models
echo "🧠 Downloading spaCy Chinese and English models..."
python -m spacy download zh_core_web_lg # Chinese model for Chinese text processing
python -m spacy download en_core_web_lg # English model for English text processing

# Download default HuggingFace models using hf-mirror for better download speed
# 设置环境变量使用hf-mirror优先下载，提高速度和稳定性
export HF_ENDPOINT=https://hf-mirror.com
echo "🧠 Downloading default retriever model (using hf-mirror)..."

# 使用单独的Python脚本文件来避免导入问题
cat > download_model.py << 'EOF'
from huggingface_hub import snapshot_download
import os

# 确保使用镜像站点
hf_endpoint = os.environ.get('HF_ENDPOINT', 'hf-mirror.com')
os.environ['HF_ENDPOINT'] = hf_endpoint

# 下载模型时不忽略任何必要的文件，确保模型能正常加载
model_path = snapshot_download(
    repo_id='sentence-transformers/all-MiniLM-L6-v2',
    ignore_patterns=['*.bin', '*.onnx', '*.ot', '*.h5'],
    local_files_only=False
)

print('Model has been downloaded to: ' + model_path)
EOF

# 执行下载脚本
python download_model.py

# 清理临时文件
rm download_model.py

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

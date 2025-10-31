#!/bin/bash
# set pip mirrors to speedup
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
pip config set install.trusted-host mirrors.aliyun.com

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📦 Installing requirements..."
pip install -r requirements.txt

# Install Java for Apache Tika
echo "☕ Setting up Java runtime for Apache Tika..."
if ! command -v java &> /dev/null; then
    echo "⚠️  Java not found, attempting to install..."
    
    if command -v apt-get &> /dev/null; then
        echo "📦 Installing Java (Ubuntu/Debian)..."
        if [ "$EUID" -eq 0 ]; then
            apt-get update -qq
            apt-get install -y -qq default-jre > /dev/null 2>&1
        elif command -v sudo &> /dev/null; then
            sudo apt-get update -qq
            sudo apt-get install -y default-jre > /dev/null 2>&1
        fi
    elif command -v yum &> /dev/null; then
        echo "📦 Installing Java (CentOS/RHEL)..."
        if [ "$EUID" -eq 0 ]; then
            yum install -y -q java-11-openjdk > /dev/null 2>&1
        elif command -v sudo &> /dev/null; then
            sudo yum install -y java-11-openjdk > /dev/null 2>&1
        fi
    fi
    
    if command -v java &> /dev/null; then
        echo "✅ Java installed successfully: $(java -version 2>&1 | head -n 1)"
    else
        echo "⚠️  Failed to install Java. Apache Tika will not work."
        echo "ℹ️  Please install Java manually: sudo apt-get install default-jre"
    fi
else
    echo "✅ Java is already installed: $(java -version 2>&1 | head -n 1)"
fi
echo ""

# Install .doc file support dependencies (optional but recommended)
echo "📄 Setting up .doc file parsing support..."
echo "ℹ️  Using system-level 'antiword' for .doc files (lightweight & stable)"
echo ""

# Detect OS for system dependencies
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$ID
else
    OS_NAME="unknown"
fi

# Function to compile antiword from source
compile_antiword_from_source() {
    echo "🔨 Attempting to compile antiword from source..."
    
    # Check for required build tools
    if ! command -v gcc &> /dev/null || ! command -v make &> /dev/null; then
        echo "⚠️  Build tools (gcc, make) not found"
        echo "ℹ️  Install them first: sudo yum install gcc make"
        return 1
    fi
    
    local ANTIWORD_VERSION="0.37"
    local WORK_DIR="/tmp/antiword-build-$$"
    
    mkdir -p "$WORK_DIR" && cd "$WORK_DIR" || return 1
    
    echo "📥 Downloading antiword source code..."
    
    # Try multiple download sources
    if wget -q "http://archive.ubuntu.com/ubuntu/pool/universe/a/antiword/antiword_${ANTIWORD_VERSION}.orig.tar.gz" -O "antiword-${ANTIWORD_VERSION}.tar.gz" 2>/dev/null; then
        echo "✅ Downloaded from Ubuntu archive"
    elif wget -q "https://fossies.org/linux/misc/antiword-${ANTIWORD_VERSION}.tar.gz" 2>/dev/null; then
        echo "✅ Downloaded from fossies.org"
    else
        echo "❌ Failed to download antiword source"
        cd - > /dev/null
        rm -rf "$WORK_DIR"
        return 1
    fi
    
    echo "📦 Extracting source code..."
    tar -xzf "antiword-${ANTIWORD_VERSION}.tar.gz" 2>/dev/null || {
        echo "❌ Failed to extract antiword source"
        cd - > /dev/null
        rm -rf "$WORK_DIR"
        return 1
    }
    
    cd "antiword-${ANTIWORD_VERSION}" || return 1
    
    echo "🔧 Compiling antiword..."
    if make -f Makefile.Linux > /dev/null 2>&1; then
        echo "✅ Compilation successful"
    else
        echo "❌ Compilation failed"
        cd - > /dev/null
        rm -rf "$WORK_DIR"
        return 1
    fi
    
    echo "📦 Installing antiword..."
    if [ "$EUID" -eq 0 ]; then
        make -f Makefile.Linux global_install > /dev/null 2>&1
    elif command -v sudo &> /dev/null; then
        sudo make -f Makefile.Linux global_install > /dev/null 2>&1
    else
        echo "❌ Cannot install (no root/sudo access)"
        cd - > /dev/null
        rm -rf "$WORK_DIR"
        return 1
    fi
    
    # Verify installation
    if command -v antiword &> /dev/null; then
        echo "✅ antiword installed successfully from source"
        cd - > /dev/null
        rm -rf "$WORK_DIR"
        return 0
    else
        echo "❌ Installation verification failed"
        cd - > /dev/null
        rm -rf "$WORK_DIR"
        return 1
    fi
}

# Install antiword system package
ANTIWORD_INSTALLED=false

if command -v apt-get &> /dev/null; then
    echo "📦 Installing antiword (Ubuntu/Debian)..."
    
    if [ "$EUID" -eq 0 ]; then
        # Running as root, install directly
        apt-get update -qq
        apt-get install -y -qq antiword > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "✅ antiword installed successfully"
            ANTIWORD_INSTALLED=true
        else
            echo "⚠️  Failed to install antiword via apt-get"
        fi
    else
        # Not root, try with sudo
        if command -v sudo &> /dev/null; then
            echo "🔑 Installing antiword (requires sudo)..."
            sudo apt-get update -qq
            sudo apt-get install -y antiword > /dev/null 2>&1
            if [ $? -eq 0 ]; then
                echo "✅ antiword installed successfully"
                ANTIWORD_INSTALLED=true
            else
                echo "⚠️  Failed to install antiword via apt-get"
            fi
        else
            echo "⚠️  Cannot install antiword (no root/sudo access)"
        fi
    fi
elif command -v yum &> /dev/null; then
    echo "📦 Installing antiword (CentOS/RHEL/TencentOS)..."
    if [ "$EUID" -eq 0 ]; then
        yum install -y -q antiword > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "✅ antiword installed successfully"
            ANTIWORD_INSTALLED=true
        else
            echo "⚠️  antiword not available in yum repositories"
        fi
    elif command -v sudo &> /dev/null; then
        sudo yum install -y antiword > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "✅ antiword installed successfully"
            ANTIWORD_INSTALLED=true
        else
            echo "⚠️  antiword not available in yum repositories"
        fi
    else
        echo "⚠️  Cannot install antiword (no root/sudo access)"
    fi
else
    echo "⚠️  Unknown package manager"
fi

# If package installation failed, try compiling from source
if [ "$ANTIWORD_INSTALLED" = false ] && ! command -v antiword &> /dev/null; then
    echo ""
    echo "📌 Package manager installation failed, trying source compilation..."
    if compile_antiword_from_source; then
        ANTIWORD_INSTALLED=true
    else
        echo "⚠️  Source compilation also failed (non-fatal)"
        echo "ℹ️  .doc files will fall back to python-docx (less reliable)"
    fi
fi

echo ""
echo "📊 .doc File Parsing Support Status:"
# Check antiword
if command -v antiword &> /dev/null; then
    antiword_version=$(antiword -V 2>&1 | head -1 || echo "unknown")
    echo "   ✅ antiword: $antiword_version"
else
    echo "   ❌ antiword: Not installed"
fi

# Check python-docx (should be in requirements.txt)
if python3 -c "import docx" 2>/dev/null; then
    echo "   ✅ python-docx: Available (for .docx files)"
else
    echo "   ⚠️  python-docx: Not installed"
fi

# Check LibreOffice
if command -v soffice &> /dev/null || command -v libreoffice &> /dev/null; then
    echo "   ✅ LibreOffice: Available (best compatibility)"
else
    echo "   ⚠️  LibreOffice: Not installed (recommended for WPS/legacy docs)"
fi

# Check striprtf
if python3 -c "import striprtf" 2>/dev/null; then
    echo "   ✅ striprtf: Available (for RTF files)"
else
    echo "   ⚠️  striprtf: Not installed"
fi

# Check Apache Tika
if python3 -c "from tika import parser" 2>/dev/null; then
    echo "   ✅ Apache Tika: Available (universal parser, supports WPS/legacy formats)"
else
    echo "   ⚠️  Apache Tika: Not installed"
fi

echo ""
echo "ℹ️  Document Parsing Strategy:"
echo "   📄 .doc files:"
echo "      1. antiword - Fast for standard Word docs"
echo "      2. Apache Tika - Best for WPS/legacy formats (recommended)"
echo "      3. LibreOffice - Fallback converter"
echo "      4. textract - Additional fallback"
echo "   📄 .docx files: python-docx"
echo "   📄 .rtf files: striprtf → LibreOffice fallback"
echo "   📄 .pdf files: MinerU (preferred) → PyMuPDF fallback"
echo ""
echo "💡 Apache Tika can parse almost any document format including:"
echo "   • WPS Office documents"
echo "   • Legacy Microsoft Office formats"
echo "   • PDF, RTF, HTML, XML, and 100+ more formats"
echo ""

# Download spaCy model
echo "🧠 Checking spaCy Chinese model..."

# Check if Chinese model is already installed (preferred for this project)
if python -c "import spacy; spacy.load('zh_core_web_lg')" 2>/dev/null; then
    echo "✅ spaCy Chinese model (zh_core_web_lg) already installed"
elif python -c "import spacy; spacy.load('en_core_web_lg')" 2>/dev/null; then
    echo "✅ spaCy English model (en_core_web_lg) already installed"
    echo "💡 For better Chinese text processing, consider installing zh_core_web_lg:"
    echo "   python -m spacy download zh_core_web_lg"
else
    echo "📥 Downloading spaCy Chinese model (recommended for Chinese text)..."
    echo "ℹ️  This may take a few minutes depending on network speed (~600MB)..."
    
    # Try to download Chinese spaCy model with error handling
    if python -m spacy download zh_core_web_lg --quiet 2>/dev/null; then
        echo "✅ Chinese spaCy model downloaded successfully"
    else
        echo "⚠️  Chinese model download failed, trying English model as fallback..."
        
        # Fallback to English model
        if python -m spacy download en_core_web_lg --quiet 2>/dev/null; then
            echo "✅ English spaCy model downloaded successfully"
            echo "💡 Note: English model works but Chinese model (zh_core_web_lg) is better for Chinese text"
        else
            echo "⚠️  spaCy model download failed (network issue)"
            echo "ℹ️  You can install it manually later with:"
            echo "     python -m spacy download zh_core_web_lg  # For Chinese (recommended)"
            echo "     python -m spacy download en_core_web_lg  # For English (fallback)"
            echo ""
            echo "⚠️  Continuing setup without spaCy model (non-fatal)..."
        fi
    fi
fi

echo ""
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

# Setup MinerU configuration (magic-pdf.json)
echo "🔧 Setting up MinerU configuration..."
MAGIC_PDF_CONFIG="/root/magic-pdf.json"

if [ -f "$MAGIC_PDF_CONFIG" ]; then
    echo "⚠️  MinerU config already exists at $MAGIC_PDF_CONFIG"
    echo "📋 Current configuration:"
    cat "$MAGIC_PDF_CONFIG"
else
    echo "📝 Creating MinerU configuration file..."
    cat > "$MAGIC_PDF_CONFIG" << 'EOF'
{
  "models-dir": "/tmp/models",
  "device-mode": "cpu"
}
EOF
    
    if [ -f "$MAGIC_PDF_CONFIG" ]; then
        echo "✅ MinerU config created successfully at $MAGIC_PDF_CONFIG"
        echo "📋 Configuration content:"
        cat "$MAGIC_PDF_CONFIG"
        
        # Validate JSON format
        if python3 -c "import json; json.load(open('$MAGIC_PDF_CONFIG'))" 2>/dev/null; then
            echo "✅ JSON format validation passed"
        else
            echo "⚠️  Warning: JSON format validation failed"
        fi
        
        # Ensure proper permissions
        chmod 644 "$MAGIC_PDF_CONFIG" 2>/dev/null || true
        echo "✅ File permissions set to 644"
    else
        echo "⚠️  Warning: Failed to create MinerU config (non-fatal)"
        echo "ℹ️  You can create it manually later using: bash fix_magic_pdf_config.sh"
    fi
fi

echo ""
echo "ℹ️  MinerU Configuration Notes:"
echo "   - Models will be downloaded to: /tmp/models (~150-200MB on first use)"
echo "   - Running mode: CPU (change to 'cuda' for GPU support)"
echo "   - System will auto-fallback to PyMuPDF if MinerU fails"
echo ""



if [ $? -eq 0 ]; then
    echo "==========================================="
    echo "🎉 Environment setup completed successfully!"
    echo "🚀 You can now start the server with: ./start.sh"
    echo "==========================================="
else
    echo "❌ Installation verification failed. Please check the error messages above."
    exit 1
fi

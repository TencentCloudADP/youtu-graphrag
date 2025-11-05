# 🚀 Youtu-GraphRAG Full Guide

<div align="center">
  <img src="assets/logo.png" alt="Logo" width="100">
  
  **Complete Guide from Installation to Usage**
  
  [⬅️ Back to Home](README.md) | [🌐 返回中文主页](README-CN.md)
</div>

---

## 📋 Table of Contents
- <a href="#web-interface-quick-experience">💻 Web Interface Quick Experience</a>
- <a href="#command-line-usage">🛠️ Command Line Usage</a>
- <a href="#advanced-configuration">⚙️ Advanced Configuration</a>
- <a href="#troubleshooting">🔧 Troubleshooting</a>

---

<a id="web-interface-quick-experience"></a>
This approach relies on the Docker environment, which could be installed according to [official documentation](https://docs.docker.com/get-started/).

```bash
# 1. Clone Youtu-GraphRAG project
git clone https://github.com/TencentCloudADP/youtu-graphrag

# 2. Create .env according to .env.example
cd youtu-graphrag && cp .env.example .env
# Config your LLM api in .env as OpenAI API format
# LLM_MODEL=deepseek-chat
# LLM_BASE_URL=https://api.deepseek.com
# LLM_API_KEY=sk-xxxxxx

# 3. Build with dockerfile 
docker build -t youtu_graphrag:v1 .

# 4. Docker run
docker run -d -p 8000:8000 youtu_graphrag:v1

# 5. Visit http://localhost:8000
curl -v http://localhost:8000
```

> **💡 Note:** If you encounter `Segmentation fault: 11` errors when building large-scale knowledge graphs, please refer to the <a href="#troubleshooting">Troubleshooting section</a> below.

### 3-Minute Experience Process

#### 1️⃣ Try Demo Data Immediately
- Go to **Query Panel** tab
- Select **demo** dataset  
- Enter demo query: *"When was the person who Messi's goals in Copa del Rey compared to get signed by Barcelona?"*
- View detailed reasoning process and knowledge graph

#### 2️⃣ Upload Your Own Documents
- Go to **Upload Documents** tab
- Follow the JSON format example on the page
- Drag and drop files to upload

#### 3️⃣ Build Knowledge Graph
- Go to **Knowledge Tree Visualization** tab
- Select dataset → Click **Construct Graph**
- Watch real-time construction progress

#### 4️⃣ Query
- Return to **Query Panel** tab
- Select the constructed dataset
- Start natural language Q&A
- Retrieval results visualization

---

<a id="command-line-usage"></a>
## 🛠️ Command Line Usage

### Environment Preparation with Docker
```bash
# 1. Clone Youtu-GraphRAG project
git clone https://github.com/TencentCloudADP/youtu-graphrag

# 2. Create .env according to .env.example
cd youtu-graphrag && cp .env.example .env
# Config your LLM api in .env as OpenAI API format
# LLM_MODEL=deepseek-chat
# LLM_BASE_URL=https://api.deepseek.com
# LLM_API_KEY=sk-xxxxxx

# 3. Build with dockerfile
docker build -t youtu_graphrag:v1 .

# 4. Docker run
docker run -d -p 8000:8000 youtu_graphrag:v1
```

### Environment Preparation with Conda
```bash
# 1. Clone Youtu-GraphRAG project
git clone https://github.com/TencentCloudADP/youtu-graphrag

# 2. Create .env according to .env.example
cd youtu-graphrag && cp .env.example .env
# Config your LLM api in .env as OpenAI API format
LLM_MODEL=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=sk-xxxxxx

# 3. Create the conda environment.
conda create -n YouTuGraphRAG python=3.10
conda activate YouTuGraphRAG

# 4. Setup environment
# You can also use the bash ./setup_env.sh to do the same thing.
chmod +x setup_env.sh
./setup_env.sh

# 5. Start the web server (for web interface)
chmod +x start.sh
./start.sh
```

### Basic Usage
```bash
# 1. Run with default configuration
python main.py --datasets demo

# 2. Specify multiple datasets
python main.py --datasets hotpot 2wiki musique

# 3. Use custom configuration file
python main.py --config my_config.yaml --datasets demo

# 4. Runtime parameter override
python main.py --override '{"retrieval": {"top_k_filter": 50}, "triggers": {"mode": "noagent"}}' --datasets demo
```

### Specialized Functions
```bash
# 1. Build knowledge graph only
python main.py --override '{"triggers": {"constructor_trigger": true, "retrieve_trigger": false}}' --datasets demo

# 2. Execute retrieval only (skip construction)
python main.py --override '{"triggers": {"constructor_trigger": false, "retrieve_trigger": true}}' --datasets demo

# 3. Performance optimization configuration
python main.py --override '{"construction": {"max_workers": 64}, "embeddings": {"batch_size": 64}}' --datasets demo
```

---

<a id="advanced-configuration"></a>
## ⚙️ Advanced Configuration

### 🔧 Key Configuration Points

| Configuration Category | Key Parameters | Description |
|------------------------|----------------|-------------|
| **🤖 Mode** | `triggers.mode` | agent(intelligent)/noagent(basic) |
| **🏗️ Construction** | `construction.max_workers` | Graph construction concurrency |
| **🔍 Retrieval** | `retrieval.top_k_filter`, `recall_paths` | Retrieval parameters |
| **🧠 Agentic CoT** | `retrieval.agent.max_steps` | Iterative retrieval steps |
| **🌳 Community Detection** | `tree_comm.struct_weight` | Weight to control impacts from topology |
| **⚡ Performance** | `embeddings.batch_size` | Batch processing size |

### 🎛️ Configuration Parameter Override Examples

<details>
<summary><strong>Click to expand detailed configuration options</strong></summary>

```bash
# Retrieval related configuration
python main.py --override '{
  "retrieval": {
    "top_k_filter": 30,
    "chunk_similarity_threshold": 0.7,
    "batch_size": 32
  }
}' --datasets demo

# Construction related configuration
python main.py --override '{
  "construction": {
    "max_workers": 32,
    "chunk_size": 512,
    "overlap_size": 50
  }
}' --datasets demo

# Embedding related configuration
python main.py --override '{
  "embeddings": {
    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
    "batch_size": 16,
    "device": "cpu"
  }
}' --datasets demo

# LLM related configuration
python main.py --override '{
  "llm": {
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 1500
  }
}' --datasets demo
```

</details>

### 📊 Performance Optimization Recommendations

**CPU Optimization:**
```bash
# Suitable for CPU environment
python main.py --override '{
  "construction": {"max_workers": 4},
  "embeddings": {"batch_size": 8, "device": "cpu"}
}' --datasets demo
```

**GPU Optimization:**
```bash
# Suitable for GPU environment
python main.py --override '{
  "construction": {"max_workers": 16},
  "embeddings": {"batch_size": 64, "device": "cuda"}
}' --datasets demo
```

**Memory Optimization:**
```bash
# Suitable for low memory environment
python kt_rag.py --override '{
  "construction": {"max_workers": 2},
  "embeddings": {"batch_size": 4},
  "retrieval": {"top_k_filter": 10}
}' --datasets demo
```

---

<a id="troubleshooting"></a>
## 🔧 Troubleshooting

### ❌ FAISS Segmentation Fault When Building Indices

**Problem Description:**

When processing large-scale datasets (e.g., 7000+ nodes), the process may crash with a segmentation fault during the FAISS index building phase.

**Typical Error Logs:**
```log
[2025-10-20 17:28:55] INFO enhanced_kt_retriever:2199 - Indexed 6000/7107 nodes
[2025-10-20 17:28:55] INFO enhanced_kt_retriever:2199 - Indexed 7000/7107 nodes
[2025-10-20 17:28:55] INFO enhanced_kt_retriever:2206 - Time taken to build node text index: 0.00603795051574707 seconds
[2025-10-20 17:28:55] INFO enhanced_kt_retriever:2228 - Saved node text index with 6494 words to retriever/faiss_cache_new/test/node_text_index.pkl (size: 356795 bytes)
[2025-10-20 17:28:55] INFO enhanced_kt_retriever:2351 - Precomputing chunk embeddings for direct chunk retrieval...
[2025-10-20 17:28:55] INFO enhanced_kt_retriever:2574 - Loaded chunk embedding cache with 1014 entries from retriever/faiss_cache_new/test/chunk_embedding_cache.pt (file size: 1857728 bytes)
[2025-10-20 17:28:55] INFO enhanced_kt_retriever:2353 - Successfully loaded chunk embeddings from disk cache
[2025-10-20 17:28:55] INFO faiss_filter:856 - Building FAISS indices and embeddings...
./start.sh: line 27: 38579 Segmentation fault: 11  python backend.py
👋 Youtu-GraphRAG server stopped.
/opt/homebrew/Cellar/python@3.10/3.10.17/Frameworks/Python.framework/Versions/3.10/lib/python3.10/multiprocessing/resource_tracker.py:224: UserWarning: resource_tracker: There appear to be 1 leaked semaphore objects to clean up at shutdown
```

**Key Indicators:**
- Process crashes immediately after logging `Building FAISS indices and embeddings...`
- Error message shows `Segmentation fault: 11`
- Typically occurs when processing thousands of nodes

**Root Cause:**

This is caused by a conflict between OpenMP multi-threading and the FAISS library, leading to memory access violations. For detailed technical analysis, see: [Related Technical Blog](https://blog.gitcode.com/b2031d6f6292a3c43ce76451badb9766.html)

---

**Solutions:**

> ⚠️ **Important:** Only apply these fixes if you encounter the `Segmentation fault: 11` error described above. No configuration is needed for normal operation.

**Method 1: Temporary Setting (Quick Test)**
```bash
# For web server (using start.sh)
OMP_NUM_THREADS=1 ./start.sh

# For command line usage
OMP_NUM_THREADS=1 python main.py --datasets your_dataset

# Or export first
export OMP_NUM_THREADS=1
./start.sh  # or python main.py --datasets your_dataset
```

**Method 2: Persistent Setting (For Frequent Large Dataset Processing)**
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export OMP_NUM_THREADS=1' >> ~/.bashrc  # or ~/.zshrc
source ~/.bashrc  # or source ~/.zshrc

# Then use normally
./start.sh
# or
python main.py --datasets your_dataset
```

**Method 3: Modify Startup Script (Recommended for Web Service)**

Edit the `start.sh` file and add the environment variable before line 27 (`python backend.py`):

```bash
# Modify lines 22-28 of start.sh to:
echo "🚀 Starting backend server..."
echo "🛑 Press Ctrl+C to stop the server"
echo "=========================================="

# Fix FAISS segmentation fault for large datasets
export OMP_NUM_THREADS=1

python backend.py
```

Then start normally:
```bash
./start.sh
```

**Verification:**

After applying the fix, rebuild your knowledge graph. The FAISS index construction should complete successfully without crashes.

**Related Issue:** [#123](https://github.com/TencentCloudADP/youtu-graphrag/issues/123)

---

## 🎯 Quick Usage Selection

| Use Case | Recommended Method | Features |
|----------|-------------------|----------|
| 🌐 **Interactive Experience** | <a href="#web-interface-quick-experience">Web Interface</a> | Visual operation, real-time feedback |
| 💻 **Batch Processing** | <a href="#command-line-usage">Command Line</a> | Scriptable, efficient processing |
| 🔧 **Custom Development** | <a href="#advanced-configuration">Advanced Configuration</a> | Flexible configuration, performance tuning |

---


<div>
  
  **🌟 We sincerely welcome STAR/PR/ISSUE 🌟**
  
  <!-- [⬅️ Back to Home](README.md) • [📖 Project Documentation](README-CN.md) • [🌐 Web Usage](WEB_USAGE.md) -->
  [⬅️ Back to Home](README.md) | [🌐 返回中文主页](README-CN.md)
  
</div>
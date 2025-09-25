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
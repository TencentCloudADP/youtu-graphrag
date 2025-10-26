# 🚀 Youtu-GraphRAG 完整指南

<div align="center">
  <img src="assets/logo.png" alt="Logo" width="100">
  
  **从安装到使用的完整指南**
  
  [⬅️ 返回主页](README-CN.md) | [🌐 English Version](FULLGUIDE.md)
</div>

---

## 📋 目录
- <a href="#web-interface-quick-experience">💻 Web 界面快速体验</a>
- <a href="#command-line-usage">🛠️ 命令行使用</a>
- <a href="#advanced-configuration">⚙️ 高级配置</a>
- <a href="#troubleshooting">🔧 常见问题</a>

---

<a id="web-interface-quick-experience"></a>
## 💻 Web 界面快速体验

本方式依赖 Docker 环境，可以根据 [官方文档](https://docs.docker.com/get-started/) 进行安装。

```bash
# 1. 克隆 Youtu-GraphRAG 项目
git clone https://github.com/TencentCloudADP/youtu-graphrag

# 2. 根据 .env.example 创建 .env 文件
cd youtu-graphrag && cp .env.example .env
# 在 .env 中配置兼容 OpenAI API 格式的 LLM API
# LLM_MODEL=deepseek-chat
# LLM_BASE_URL=https://api.deepseek.com
# LLM_API_KEY=sk-xxxxxx

# 3. 使用 dockerfile 构建镜像
docker build -t youtu_graphrag:v1 .

# 4. 运行 Docker 容器
docker run -d -p 8000:8000 youtu_graphrag:v1

# 5. 访问 http://localhost:8000
curl -v http://localhost:8000
```

> **💡 提示：** 如果在构建大规模知识图谱时遇到 `Segmentation fault: 11` 错误，请参考下方的<a href="#troubleshooting">常见问题章节</a>。

### 3 分钟快速体验流程

#### 1️⃣ 立即尝试演示数据
- 进入 **查询面板** 标签页
- 选择 **demo** 数据集
- 输入演示查询：*"When was the person who Messi's goals in Copa del Rey compared to get signed by Barcelona?"*
- 查看详细的推理过程和知识图谱

#### 2️⃣ 上传您自己的文档
- 进入 **上传文档** 标签页
- 按照页面上的 JSON 格式示例
- 拖拽文件进行上传

#### 3️⃣ 构建知识图谱
- 进入 **知识树可视化** 标签页
- 选择数据集 → 点击 **构建图谱**
- 观察实时构建进度

#### 4️⃣ 查询
- 返回 **查询面板** 标签页
- 选择已构建的数据集
- 开始自然语言问答
- 检索结果可视化

---

<a id="command-line-usage"></a>
## 🛠️ 命令行使用

### 使用 Docker 准备环境
```bash
# 1. 克隆 Youtu-GraphRAG 项目
git clone https://github.com/TencentCloudADP/youtu-graphrag

# 2. 根据 .env.example 创建 .env 文件
cd youtu-graphrag && cp .env.example .env
# 在 .env 中配置兼容 OpenAI API 格式的 LLM API
# LLM_MODEL=deepseek-chat
# LLM_BASE_URL=https://api.deepseek.com
# LLM_API_KEY=sk-xxxxxx

# 3. 使用 dockerfile 构建镜像
docker build -t youtu_graphrag:v1 .

# 4. 运行 Docker 容器
docker run -d -p 8000:8000 youtu_graphrag:v1
```

### 使用 Conda 准备环境
```bash
# 1. 克隆 Youtu-GraphRAG 项目
git clone https://github.com/TencentCloudADP/youtu-graphrag

# 2. 根据 .env.example 创建 .env 文件
cd youtu-graphrag && cp .env.example .env
# 在 .env 中配置兼容 OpenAI API 格式的 LLM API
LLM_MODEL=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=sk-xxxxxx

# 3. 创建 conda 环境
conda create -n YouTuGraphRAG python=3.10
conda activate YouTuGraphRAG

# 4. 配置环境
# 您也可以使用 bash ./setup_env.sh 来完成相同的操作
chmod +x setup_env.sh
./setup_env.sh

# 5. 启动 Web 服务（用于 Web 界面）
chmod +x start.sh
./start.sh
```

### 基本使用
```bash
# 1. 使用默认配置运行
python main.py --datasets demo

# 2. 指定多个数据集
python main.py --datasets hotpot 2wiki musique

# 3. 使用自定义配置文件
python main.py --config my_config.yaml --datasets demo

# 4. 运行时参数覆盖
python main.py --override '{"retrieval": {"top_k_filter": 50}, "triggers": {"mode": "noagent"}}' --datasets demo
```

### 专门功能
```bash
# 1. 仅构建知识图谱
python main.py --override '{"triggers": {"constructor_trigger": true, "retrieve_trigger": false}}' --datasets demo

# 2. 仅执行检索（跳过构建）
python main.py --override '{"triggers": {"constructor_trigger": false, "retrieve_trigger": true}}' --datasets demo

# 3. 性能优化配置
python main.py --override '{"construction": {"max_workers": 64}, "embeddings": {"batch_size": 64}}' --datasets demo
```

---

<a id="advanced-configuration"></a>
## ⚙️ 高级配置

### 🔧 关键配置项

| 配置类别 | 关键参数 | 说明 |
|---------|---------|------|
| **🤖 模式** | `triggers.mode` | agent(智能)/noagent(基础) |
| **🏗️ 构建** | `construction.max_workers` | 图构建并发数 |
| **🔍 检索** | `retrieval.top_k_filter`, `recall_paths` | 检索参数 |
| **🧠 智能体 CoT** | `retrieval.agent.max_steps` | 迭代检索步数 |
| **🌳 社区检测** | `tree_comm.struct_weight` | 控制拓扑影响的权重 |
| **⚡ 性能** | `embeddings.batch_size` | 批处理大小 |

### 🎛️ 配置参数覆盖示例

<details>
<summary><strong>点击展开详细配置选项</strong></summary>

```bash
# 检索相关配置
python main.py --override '{
  "retrieval": {
    "top_k_filter": 30,
    "chunk_similarity_threshold": 0.7,
    "batch_size": 32
  }
}' --datasets demo

# 构建相关配置
python main.py --override '{
  "construction": {
    "max_workers": 32,
    "chunk_size": 512,
    "overlap_size": 50
  }
}' --datasets demo

# 嵌入相关配置
python main.py --override '{
  "embeddings": {
    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
    "batch_size": 16,
    "device": "cpu"
  }
}' --datasets demo

# LLM 相关配置
python main.py --override '{
  "llm": {
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 1500
  }
}' --datasets demo
```

</details>

### 📊 性能优化建议

**CPU 优化：**
```bash
# 适用于 CPU 环境
python main.py --override '{
  "construction": {"max_workers": 4},
  "embeddings": {"batch_size": 8, "device": "cpu"}
}' --datasets demo
```

**GPU 优化：**
```bash
# 适用于 GPU 环境
python main.py --override '{
  "construction": {"max_workers": 16},
  "embeddings": {"batch_size": 64, "device": "cuda"}
}' --datasets demo
```

**内存优化：**
```bash
# 适用于低内存环境
python kt_rag.py --override '{
  "construction": {"max_workers": 2},
  "embeddings": {"batch_size": 4},
  "retrieval": {"top_k_filter": 10}
}' --datasets demo
```

---

<a id="troubleshooting"></a>
## 🔧 常见问题

### ❌ FAISS 构建时出现段错误

**问题描述：**

当处理大规模数据集（例如 7000+ 节点）时，在构建 FAISS 索引阶段可能会出现段错误并导致进程崩溃。

**典型错误日志：**
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

**关键识别点：**
- 日志显示 `Building FAISS indices and embeddings...` 后立即崩溃
- 出现 `Segmentation fault: 11` 错误
- 通常发生在处理大量节点（数千个）时

**原因分析：**

这是由于 OpenMP 多线程与 FAISS 库冲突导致的内存访问错误。详细技术分析请参考：[相关技术博客](https://blog.gitcode.com/b2031d6f6292a3c43ce76451badb9766.html)

---

**解决方案：**

> ⚠️ **注意：** 只有在遇到上述 `Segmentation fault: 11` 错误时才需要设置此参数。正常情况下无需配置。

**方法 1：临时设置（快速测试）**
```bash
# 对于 Web 服务（使用 start.sh）
OMP_NUM_THREADS=1 ./start.sh

# 对于命令行使用
OMP_NUM_THREADS=1 python main.py --datasets your_dataset

# 或者先导出环境变量
export OMP_NUM_THREADS=1
./start.sh  # 或 python main.py --datasets your_dataset
```

**方法 2：永久设置（如果经常处理大数据集）**
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
echo 'export OMP_NUM_THREADS=1' >> ~/.bashrc  # 或 ~/.zshrc
source ~/.bashrc  # 或 source ~/.zshrc

# 之后直接使用即可
./start.sh
# 或
python main.py --datasets your_dataset
```

**方法 3：修改启动脚本（推荐用于 Web 服务）**

编辑 `start.sh` 文件，在第 27 行（`python backend.py`）前添加环境变量：

```bash
# 修改 start.sh 的第 22-28 行为：
echo "🚀 Starting backend server..."
echo "🛑 Press Ctrl+C to stop the server"
echo "=========================================="

# 修复大数据集 FAISS 段错误
export OMP_NUM_THREADS=1

python backend.py
```

保存后正常启动：
```bash
./start.sh
```

**验证修复：**

设置后重新构建知识图谱，应该能够正常完成 FAISS 索引构建而不会崩溃。

**相关 Issue：** [#123](https://github.com/TencentCloudADP/youtu-graphrag/issues/123)

---

## 🎯 快速使用选择

| 使用场景 | 推荐方法 | 特点 |
|---------|---------|------|
| 🌐 **交互式体验** | <a href="#web-interface-quick-experience">Web 界面</a> | 可视化操作，实时反馈 |
| 💻 **批量处理** | <a href="#command-line-usage">命令行</a> | 可编程脚本，高效处理 |
| 🔧 **自定义开发** | <a href="#advanced-configuration">高级配置</a> | 灵活配置，性能调优 |

---


<div>
  
  **🌟 诚挚欢迎 STAR/PR/ISSUE 🌟**
  
  [⬅️ 返回主页](README-CN.md) | [🌐 English Version](FULLGUIDE.md)
  
</div>


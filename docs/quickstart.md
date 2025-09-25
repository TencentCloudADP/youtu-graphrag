# Quickstart

We provide two approaches to run and experience the demo service. Considering the differences in the underlying environment, we recommend using **Docker** as the preferred deployment method.

### 💻 Start with Dockerfile

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

### 💻 Web UI Experience

This approach relies on Python 3.10 and the corresponding pip environment, you can install it according to the [official documentation](https://docs.python.org/3.10/using/index.html).

```bash
# 1. Clone Youtu-GraphRAG project
git clone https://github.com/TencentCloudADP/youtu-graphrag

# 2. Create .env according to .env.example
cd youtu-graphrag && cp .env.example .env
# Config your LLM api in .env as OpenAI API format
# LLM_MODEL=deepseek-chat
# LLM_BASE_URL=https://api.deepseek.com
# LLM_API_KEY=sk-xxxxxx

# 3. Setup environment
./setup_env.sh

# 4. Launch the web
./start.sh

# 5. Visit http://localhost:8000
curl -v http://localhost:8000
```

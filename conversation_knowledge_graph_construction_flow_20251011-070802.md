# 知识图谱构建流程完整对话

**日期**: 2025-10-11  
**主题**: Youtu-GraphRAG 知识图谱构建与检索流程详解

---

## 问题1: 当我使用web界面的 Data Upload，并且上传了数据，并点击了construct，此时知识图谱是如何构建的，帮我梳理之后的构建流程

### 回答

我来帮你梳理一下Web界面上传数据并点击construct后知识图谱的构建流程。

## 📊 知识图谱构建流程完整梳理

### 🎯 **流程概览**

```
用户操作 → 前端上传 → 后端处理 → 构建图谱 → 社区检测 → 返回结果
```

### 📝 **详细流程**

#### **阶段1: 前端数据上传** (`frontend/index.html`)

1. **用户操作**：
   - 用户在 "Data Upload" 标签页上传文件（支持 `.json`, `.txt` 等格式）
   - 点击 "Upload Files" 按钮

2. **上传请求**：
   ```javascript
   POST /api/upload
   - 文件通过 FormData 上传
   - 携带 client_id 用于 WebSocket 连接
   ```

3. **文件处理**：
   - 前端将文件保存到 `data/uploaded/{dataset_name}/` 目录
   - 解析文件内容为 `corpus.json` 格式
   - 状态显示为 "needs_construction"

---

#### **阶段2: 点击 Construct 按钮**

1. **前端发起构建请求**：
   ```javascript
   POST /api/construct-graph
   {
     "dataset_name": "xxx",
     "client_id": "web_client"
   }
   ```

2. **建立 WebSocket 连接**：
   ```javascript
   ws://localhost:8000/ws/web_client
   // 用于接收实时构建进度更新
   ```

---

#### **阶段3: 后端构建处理** (`backend.py`)

**3.1 清理缓存** (Progress: 2%-5%)
```python
await clear_cache_files(dataset_name)
```
- 删除 FAISS 索引缓存：`retriever/faiss_cache_new/{dataset_name}/`
- 删除旧的 chunks 文件：`output/chunks/{dataset_name}.txt`
- 删除旧的图谱文件：`output/graphs/{dataset_name}_new.json`

**3.2 初始化配置** (Progress: 5%-10%)
```python
config = get_config("config/base_config.yaml")
schema_path = "schemas/demo.json"
corpus_path = f"data/uploaded/{dataset_name}/corpus.json"
```

**3.3 创建 KTBuilder 实例** (Progress: 10%-20%)
```python
builder = constructor.KTBuilder(
    dataset_name,
    schema_path,
    mode=config.construction.mode,  # "agent" 或 "noagent"
    config=config
)
```

---

#### **阶段4: 知识图谱构建** (`models/constructor/kt_gen.py`)

**4.1 加载语料库** (Progress: 20%-30%)
```python
def build_knowledge_graph(self, corpus):
    with open(corpus, 'r') as f:
        documents = json.load(f)  # 加载所有文档
```

**4.2 并行处理文档** (Progress: 30%-85%)
```python
def process_all_documents(self, documents):
    max_workers = min(config.max_workers, cpu_count + 4)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 为每个文档提交处理任务
        futures = [executor.submit(self.process_document, doc) 
                  for doc in documents]
```

**4.2.1 单个文档处理** (`process_document`)

1. **文本分块**：
   ```python
   chunks, chunk2id = self.chunk_text(doc)
   # 生成唯一的 chunk_id (8位 nanoid)
   ```

2. **LLM 信息抽取** (根据模式选择不同处理方法)：

   **如果是 agent 模式**：
   ```python
   process_level1_level2_agent(chunk, id)
   ```
   - 调用 LLM API 进行实体、关系、属性抽取
   - **支持 Schema Evolution**（模式演化）
   - 提取内容包括：
     - `attributes`: 实体属性 `{"实体名": ["属性1", "属性2"]}`
     - `triples`: 三元组 `[主体, 关系, 客体]`
     - `entity_types`: 实体类型映射
     - `new_schema_types`: 新发现的 schema 类型（仅 agent 模式）

   **如果是 noagent 模式**：
   ```python
   process_level1_level2(chunk, id)
   ```
   - 仅进行标准抽取，不支持模式演化

3. **构建图结构**：
   ```python
   # Level 1: 属性节点
   attr_node_id = f"attr_{counter}"
   graph.add_node(attr_node_id, 
                  label="attribute",
                  properties={"name": attr, "chunk id": chunk_id},
                  level=1)
   
   # Level 2: 实体节点
   entity_node_id = f"entity_{counter}"
   graph.add_node(entity_node_id,
                  label="entity", 
                  properties={"name": entity, "schema_type": type},
                  level=2)
   
   # 添加边 (关系)
   graph.add_edge(subj_id, obj_id, relation=predicate)
   ```

**4.3 三元组去重** (Progress: 85%-90%)
```python
def triple_deduplicate(self):
    # 去除重复的三元组关系
    seen_triples = set()
    for u, v, data in graph.edges(data=True):
        if (u, v, relation) not in seen_triples:
            seen_triples.add((u, v, relation))
            new_graph.add_edge(u, v, **data)
```

**4.4 社区检测 (Level 4)** (Progress: 90%-95%)
```python
def process_level4(self):
    # 使用 FastTreeComm 算法进行社区检测
    _tree_comm = tree_comm.FastTreeComm(
        self.graph,
        embedding_model="all-MiniLM-L6-v2",
        struct_weight=0.3
    )
    
    # 检测实体节点的社区结构
    level2_nodes = [n for n in graph.nodes if level == 2]
    comm_to_nodes = _tree_comm.detect_communities(level2_nodes)
    
    # 创建超级节点 (Level 4 社区)
    _tree_comm.create_super_nodes_with_keywords(comm_to_nodes, level=4)
```

**社区检测原理**：
- 基于结构和语义相似度聚类实体
- 为每个社区生成关键词标签
- 构建层次化的知识图谱结构

**4.5 保存结果** (Progress: 95%-100%)

1. **保存 Chunks**：
   ```python
   # 保存到 output/chunks/{dataset_name}.txt
   f.write(f"id: {chunk_id}\tChunk: {chunk_text}\n")
   ```

2. **格式化输出**：
   ```python
   def format_output(self):
       output = []
       for u, v, data in graph.edges(data=True):
           relationship = {
               "start_node": {
                   "label": u_data["label"],
                   "properties": u_data["properties"]
               },
               "relation": data["relation"],
               "end_node": {
                   "label": v_data["label"],
                   "properties": v_data["properties"]
               }
           }
           output.append(relationship)
       return output
   ```

3. **保存图谱**：
   ```python
   # 保存到 output/graphs/{dataset_name}_new.json
   json.dump(output, f, ensure_ascii=False, indent=2)
   ```

---

#### **阶段5: 准备可视化数据**

```python
graph_vis_data = await prepare_graph_visualization(graph_path)
```

**转换为 ECharts 格式**：
```javascript
{
  "nodes": [
    {
      "id": "entity_1",
      "name": "实体名称",
      "category": "person",
      "symbolSize": 25
    }
  ],
  "links": [
    {
      "source": "entity_1",
      "target": "entity_2",
      "name": "关系名称"
    }
  ],
  "categories": [...]
}
```

---

#### **阶段6: 返回前端**

1. **更新数据集状态**：
   ```
   status: "needs_construction" → "ready"
   ```

2. **WebSocket 推送完成消息**：
   ```json
   {
     "type": "complete",
     "message": "图构建完成!"
   }
   ```

3. **前端显示**：
   - 数据集列表中状态变为 "ready"
   - 显示 "Reconstruct" 和 "Delete" 按钮
   - 可以在 Graph Visualization 中查看图谱
   - 可以在 Q&A Interface 中进行检索问答

---

### 🔑 **关键技术点**

1. **并发处理**：使用 ThreadPoolExecutor 最多32个线程并行处理文档
2. **LLM 抽取**：调用 LLM API 进行结构化信息抽取
3. **Schema Evolution** (Agent模式)：动态扩展 schema 类型
4. **图结构**：使用 NetworkX MultiDiGraph 构建多层图结构
   - Level 1: 属性节点
   - Level 2: 实体节点
   - Level 4: 社区节点
5. **社区检测**：FastTreeComm 算法基于结构+语义进行聚类
6. **实时进度**：通过 WebSocket 向前端推送构建进度

---

### 📁 **输出文件**

构建完成后会生成：
- `output/chunks/{dataset_name}.txt` - 文本块存储
- `output/graphs/{dataset_name}_new.json` - 知识图谱数据
- `retriever/faiss_cache_new/{dataset_name}/` - FAISS 索引缓存（检索时生成）

这就是完整的知识图谱构建流程！🎉

---

## 问题2: 3.3 创建 KTBuilder 实例 (Progress: 10%-20%) 这个默认是什么模式

### 回答

## 🎯 **默认模式是 `agent`**

根据配置文件 `config/base_config.yaml`：

```yaml
construction:
  mode: agent        # 👈 构建模式默认为 agent
  max_workers: 32
  chunk_size: 1000
  overlap: 200

triggers:
  constructor_trigger: true
  mode: agent        # 👈 全局模式也是 agent
  retrieve_trigger: true
```

在 `KTBuilder` 初始化时：

```python
def __init__(self, dataset_name, schema_path=None, mode=None, config=None):
    # ...
    self.mode = mode or config.construction.mode  # 如果没传 mode，使用配置文件的 agent
```

---

## 📊 **两种模式的区别**

### **🤖 Agent 模式** (默认)

**特点**：
- ✅ **支持 Schema Evolution（模式演化）**
- ✅ LLM 可以动态发现并添加新的实体类型、关系类型、属性类型
- ✅ 更灵活，适合开放域知识抽取
- ✅ 使用 `process_level1_level2_agent()` 方法

**LLM Prompt 包含**：
```
Schema Evolution: If you find new and important entity types, 
relation types, or attribute types that are valuable for knowledge 
extraction, include them in a "new_schema_types" field.
```

**返回格式**：
```json
{
  "attributes": {...},
  "triples": [...],
  "entity_types": {...},
  "new_schema_types": {      // 👈 新增字段
    "nodes": ["新实体类型"],
    "relations": ["新关系类型"],
    "attributes": ["新属性类型"]
  }
}
```

---

### **📝 NoAgent 模式**

**特点**：
- ❌ **不支持 Schema Evolution**
- ✅ 严格按照预定义 schema 抽取
- ✅ 更可控，适合封闭域知识抽取
- ✅ 使用 `process_level1_level2()` 方法

**返回格式**：
```json
{
  "attributes": {...},
  "triples": [...],
  "entity_types": {...}
  // 没有 new_schema_types 字段
}
```

---

## 🔧 **如何切换模式？**

### **方法1: 修改配置文件**
编辑 `config/base_config.yaml`：
```yaml
construction:
  mode: noagent  # 改为 noagent
```

### **方法2: 通过命令行参数**
```bash
python main.py --datasets demo --override '{"construction": {"mode": "noagent"}}'
```

### **方法3: 在代码中指定**
```python
builder = constructor.KTBuilder(
    dataset_name,
    schema_path,
    mode="noagent",  # 显式指定
    config=config
)
```

---

## 💡 **模式选择建议**

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| 通用文档处理 | **agent** | 可以自动发现新类型 |
| 特定领域（如学术论文） | **agent** | 领域术语可能不在预定义 schema 中 |
| 严格结构化数据 | **noagent** | 保持 schema 一致性 |
| 已有完整 schema | **noagent** | 不需要扩展 schema |

**默认使用 agent 模式是合理的**，因为它更灵活，适合处理各种类型的文档！🎯

---

## 问题3: 继续

### 回答

好的！让我继续深入讲解 **检索和问答流程**，这是构建知识图谱后的关键应用环节！

---

## 🔍 **知识图谱检索与问答流程**

### **场景：用户在 Q&A Interface 提问**

当用户在 Web 界面的 "Q&A Interface" 输入问题并点击提交后，系统会进行以下处理：

---

## 📋 **检索流程总览**

```
用户提问 → 问题分解 → 初始检索 → IRCoT迭代推理 → 答案生成 → 返回结果
```

---

## 🚀 **详细流程（Agent 模式）**

### **Step 1: 前端发起请求**

```javascript
POST /api/ask-question
{
  "question": "When was the person who Messi's goals compared to get signed by Barcelona?",
  "dataset_name": "demo",
  "client_id": "web_client"
}
```

---

### **Step 2: 初始化检索系统** (Progress: 10%)

```python
# backend.py - ask_question()
graphq = decomposer.GraphQ(dataset_name, config=config)

kt_retriever = retriever.KTRetriever(
    dataset_name,
    graph_path,
    recall_paths=config.retrieval.recall_paths,  # 默认 2
    schema_path=schema_path,
    top_k=config.retrieval.top_k_filter,  # 默认 20
    mode="agent",  # 强制 agent 模式
    config=config
)
```

---

### **Step 3: 构建 FAISS 索引** (Progress: 10%-40%)

```python
kt_retriever.build_indices()
```

**索引类型**：
1. **Node Index** - 实体节点索引
   - 对所有 Level 2 实体节点的名称进行嵌入
   - 使用 FAISS IndexFlatIP (内积相似度)

2. **Relation Index** - 关系索引
   - 对所有边的关系进行嵌入

3. **Chunk Index** - 文本块索引
   - 对原始文本块进行嵌入

4. **Community Index** - 社区索引
   - 对 Level 4 社区节点的关键词进行嵌入

**缓存机制**：
```python
# 索引缓存在 retriever/faiss_cache_new/{dataset_name}/
cache_files = [
    "node.index",
    "node_embeddings.npy",
    "node_map.json",
    "chunk_embedding_cache.pt",
    "comm.index",
    "comm_map.json"
]
```

---

### **Step 4: 问题分解** (Progress: 40%-50%)

```python
decomposition = graphq.decompose(question, schema_path)
```

**LLM Prompt** (简化版):
```
You are a question decomposition expert.
Given the question and ontology, decompose it into 2-3 sub-questions.

Ontology: {schema}
Question: {question}

Return JSON:
{
  "sub_questions": [
    {"sub-question": "Who did Messi compare to?"},
    {"sub-question": "When was that person signed by Barcelona?"}
  ],
  "involved_types": {
    "nodes": ["person", "organization"],
    "relations": ["comparable_to", "signed_by"],
    "attributes": ["name", "date"]
  }
}
```

**返回结果**：
```python
{
  "sub_questions": [
    {"sub-question": "Who did Messi's goals in Copa del Rey compare to?"},
    {"sub-question": "When was that person signed by Barcelona?"}
  ],
  "involved_types": {
    "nodes": ["person", "organization", "event"],
    "relations": ["comparable_to", "signed_by"],
    "attributes": ["date"]
  }
}
```

---

### **Step 5: 并行子问题检索** (Progress: 50%-65%)

```python
# 如果有多个子问题，使用并行处理
if len(sub_questions) > 1:
    aggregated_results, elapsed = kt_retriever.process_subquestions_parallel(
        sub_questions, 
        top_k=20,
        involved_types=involved_types
    )
```

**每个子问题的检索过程**：

#### **5.1 多路召回 (Multi-Path Recall)**

```python
def process_retrieval_results(self, query, top_k, involved_types):
    all_triples = set()
    all_chunk_ids = set()
    
    # Path 1: 节点召回 (Node Recall)
    node_results = self._recall_from_nodes(query, top_k)
    all_triples.update(node_results['triples'])
    
    # Path 2: 社区召回 (Community Recall)
    comm_results = self._recall_from_communities(query, top_k)
    all_triples.update(comm_results['triples'])
    
    # Path 3: Chunk 召回 (Chunk Recall) - 如果启用
    if config.retrieval.enable_high_recall:
        chunk_results = self._recall_from_chunks(query, top_k)
        all_chunk_ids.update(chunk_results['chunk_ids'])
    
    return {
        'triples': list(all_triples),
        'chunk_ids': list(all_chunk_ids),
        'chunk_contents': chunk_contents_dict
    }
```

**Path 1: 节点召回详解**

```python
def _recall_from_nodes(self, query, top_k):
    # 1. 查询嵌入
    query_embedding = self.embedding_model.encode(query)
    
    # 2. FAISS 相似度搜索
    distances, indices = self.node_index.search(
        query_embedding.reshape(1, -1), 
        k=top_k * 2  # 召回2倍候选
    )
    
    # 3. 获取匹配的节点
    matched_nodes = [self.node_id_map[idx] for idx in indices[0]]
    
    # 4. 提取相关三元组
    triples = []
    for node_id in matched_nodes:
        # 获取该节点的所有出边和入边
        for u, v, data in self.graph.edges(node_id, data=True):
            triple = f"({u_name}, {relation}, {v_name})"
            triples.append(triple)
    
    return {'triples': triples}
```

**Path 2: 社区召回详解**

```python
def _recall_from_communities(self, query, top_k):
    # 1. 在社区索引中搜索
    distances, indices = self.comm_index.search(
        query_embedding.reshape(1, -1), 
        k=min(5, num_communities)  # 召回最相关的5个社区
    )
    
    # 2. 获取社区内的所有实体
    community_nodes = []
    for comm_id in matched_communities:
        # 社区节点连接的所有实体
        members = self.graph.neighbors(comm_id)
        community_nodes.extend(members)
    
    # 3. 提取社区内的三元组
    triples = self._extract_triples_from_nodes(community_nodes)
    
    return {'triples': triples}
```

**检索结果示例**：
```python
{
  'triples': [
    "(Messi [schema_type: person], comparable_to, Cristiano Ronaldo [schema_type: person])",
    "(Cristiano Ronaldo [schema_type: person], signed_by, Barcelona [schema_type: organization])",
    "(Cristiano Ronaldo [schema_type: person], has_attribute, signed_date: 2003)",
  ],
  'chunk_ids': ['AbCd1234', 'EfGh5678'],
  'chunk_contents': {
    'AbCd1234': "Messi's goals in Copa del Rey are often compared to...",
    'EfGh5678': "Cristiano Ronaldo was signed by Barcelona in 2003..."
  }
}
```

---

### **Step 6: 聚合子问题结果**

```python
all_triples = set()
all_chunk_ids = set()

for sub_q_result in sub_question_results:
    all_triples.update(sub_q_result['triples'])
    all_chunk_ids.update(sub_q_result['chunk_ids'])

# 去重
dedup_triples = list(all_triples)  # 约50-100条
dedup_chunks = list(all_chunk_ids)  # 约10-20个
```

---

### **Step 7: 生成初始答案** (Progress: 65%)

```python
# 构建上下文
context = "=== Triples ===\n" + "\n".join(dedup_triples[:20])
context += "\n=== Chunks ===\n" + "\n".join(dedup_chunks[:10])

# 生成提示词
prompt = f"""
You are an expert knowledge assistant.
Question: {question}
Knowledge Context:
{context}

Answer (be specific and direct):
"""

# 调用 LLM
initial_answer = kt_retriever.generate_answer(prompt)
# 结果: "Cristiano Ronaldo was signed by Barcelona in 2003."
```

---

### **Step 8: IRCoT 迭代推理** (Progress: 65%-90%)

**IRCoT (Iterative Retrieval Chain-of-Thought)**：通过多轮迭代，逐步完善答案

```python
max_steps = 5  # 最多5轮迭代
current_query = question
thoughts = [initial_answer]  # 记录推理历史

for step in range(1, max_steps + 1):
    # 8.1 生成推理提示
    ircot_prompt = f"""
    You are using iterative retrieval with chain-of-thought reasoning.
    
    Current Question: {question}
    Current Query: {current_query}
    
    Available Knowledge:
    {context}
    
    Previous Thoughts: {' | '.join(thoughts)}
    
    Instructions:
    1. If you have enough info, write "So the answer is: <answer>"
    2. If you need more info, write "The new query is: <query>"
    
    Your reasoning:
    """
    
    # 8.2 LLM 推理
    reasoning = kt_retriever.generate_answer(ircot_prompt)
    thoughts.append(reasoning)
    
    # 8.3 判断是否需要继续检索
    if "So the answer is:" in reasoning:
        # 找到最终答案，退出循环
        final_answer = extract_answer(reasoning)
        break
    
    if "The new query is:" in reasoning:
        # 提取新查询
        new_query = extract_query(reasoning)
        current_query = new_query
        
        # 8.4 执行新一轮检索
        new_results = kt_retriever.process_retrieval_results(
            new_query, 
            top_k=20
        )
        
        # 8.5 合并新知识
        all_triples.update(new_results['triples'])
        all_chunk_ids.update(new_results['chunk_ids'])
        
        # 更新上下文
        context = rebuild_context(all_triples, all_chunk_ids)
    else:
        # 没有明确指令，使用初始答案
        break
```

**IRCoT 示例对话**：

```
Step 1:
Reasoning: "I found that Messi is compared to Cristiano Ronaldo, 
           but I need to verify when Ronaldo was signed by Barcelona.
           The new query is: When did Cristiano Ronaldo sign with Barcelona?"

Step 2: (检索新信息)
Retrieved: "(Cristiano Ronaldo, signed_by, Barcelona), (date: 2003-07-01)"

Step 3:
Reasoning: "Based on the retrieved information, Cristiano Ronaldo 
           was signed by Barcelona on July 1, 2003.
           So the answer is: 2003"
```

---

### **Step 9: 生成最终答案** (Progress: 90%-100%)

```python
# 使用所有收集的知识生成最终答案
final_context = "=== Final Triples ===\n" + "\n".join(all_triples)
final_context += "\n=== Final Chunks ===\n" + "\n".join(all_chunks)

final_prompt = kt_retriever.generate_prompt(question, final_context)
final_answer = kt_retriever.generate_answer(final_prompt)
```

---

### **Step 10: 准备可视化数据**

```python
visualization_data = {
    "subqueries": prepare_subquery_visualization(sub_questions),
    "knowledge_graph": prepare_retrieved_graph_visualization(triples),
    "reasoning_flow": prepare_reasoning_flow_visualization(reasoning_steps),
    "retrieval_details": {
        "total_triples": len(triples),
        "total_chunks": len(chunks),
        "sub_questions_count": len(sub_questions),
        "ircot_steps": len(thoughts)
    }
}
```

---

### **Step 11: 返回前端**

```python
return QuestionResponse(
    answer=final_answer,  # "2003"
    sub_questions=sub_questions,
    retrieved_triples=triples[:20],  # 前20条三元组
    retrieved_chunks=chunks[:10],  # 前10个文本块
    reasoning_steps=reasoning_steps,  # IRCoT推理步骤
    visualization_data=visualization_data
)
```

---

## 🎨 **前端展示**

### **1. 答案区域**
```
Answer: 2003
```

### **2. 检索统计**
```
📊 Retrieval Stats
- Sub-questions: 2
- Retrieved Triples: 47
- Relevant Chunks: 12
```

### **3. 问题分解**
```
📝 Question Decomposition

1️⃣ Who did Messi's goals in Copa del Rey compare to?
   Triples: 23 | Chunks: 6 | Time: 0.45s

2️⃣ When was that person signed by Barcelona?
   Triples: 24 | Chunks: 6 | Time: 0.38s
```

### **4. 子图可视化**
- 使用 ECharts 绘制检索到的三元组子图
- 节点：实体（带类型颜色编码）
- 边：关系（带标签）

---

## ⚡ **性能优化策略**

### **1. 并行处理**
```python
# 子问题并行检索
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(process_subquestion, sq) 
               for sq in sub_questions]
    results = [f.result() for f in futures]
```

### **2. 缓存机制**
- FAISS 索引缓存在磁盘
- Embedding 缓存避免重复计算
- LRU 缓存常见查询结果

### **3. 早停策略**
- IRCoT 在找到答案后立即停止
- 相似度低于阈值时不召回

### **4. Top-K 截断**
- 每路召回最多 Top-20
- 最终输出最多 20 条三元组、10 个 chunks

---

## 📊 **Agent vs NoAgent 模式对比**

| 特性 | Agent 模式 | NoAgent 模式 |
|------|-----------|-------------|
| 问题分解 | ✅ 支持 | ✅ 支持 |
| 并行子问题处理 | ✅ 支持 | ✅ 支持 |
| **IRCoT 迭代推理** | ✅ **启用** | ❌ **禁用** |
| 多轮检索 | ✅ 最多5轮 | ❌ 只有1轮 |
| 推理链 | ✅ 记录完整思考过程 | ❌ 直接生成答案 |
| 适用场景 | 复杂多跳推理 | 简单事实查询 |
| 平均耗时 | ~3-5秒 | ~1-2秒 |

---

## 🎯 **总结**

完整的检索流程：

```
问题输入
  ↓
问题分解 (2-3个子问题)
  ↓
并行检索 (多路召回: Node + Community + Chunk)
  ↓
初始答案生成
  ↓
IRCoT 迭代推理 (最多5轮)
  ├─ 判断是否足够
  ├─ 生成新查询
  ├─ 执行新检索
  └─ 更新知识库
  ↓
最终答案生成
  ↓
可视化呈现
```

这就是完整的知识图谱检索和问答流程！🚀

---

## 问题4: agent模式下，发现的新的实体和关系，后续有什么处理

### 回答

## 🔄 **Agent 模式下新 Schema 类型的完整处理流程**

---

## 📊 **流程概览**

```
LLM 发现新类型 → 去重检查 → 更新 Schema 文件 → 更新内存 Schema → 后续文档使用新 Schema
```

---

## 🚀 **详细处理步骤**

### **Step 1: LLM 发现新类型**

在处理每个文本块时，LLM 可能返回新的 schema 类型：

```python
# LLM 返回示例
{
  "attributes": {
    "Tesla Model 3": ["color: red", "price: $40,000"]
  },
  "triples": [
    ["Tesla Model 3", "manufactured_by", "Tesla Inc."],
    ["Tesla Model 3", "has_feature", "Autopilot"]
  ],
  "entity_types": {
    "Tesla Model 3": "vehicle",        # 🆕 新实体类型
    "Tesla Inc.": "organization",
    "Autopilot": "technology"          # 🆕 新实体类型
  },
  "new_schema_types": {                # 🌟 关键字段
    "nodes": ["vehicle", "technology"],
    "relations": ["manufactured_by", "has_feature"],
    "attributes": ["color", "price"]
  }
}
```

---

### **Step 2: 解析和验证**

```python
def process_level1_level2_agent(self, chunk: str, id: int):
    # 1. 调用 LLM
    llm_response = self.extract_with_llm(prompt)
    
    # 2. 解析响应
    parsed_response = self._validate_and_parse_llm_response(prompt, llm_response)
    if not parsed_response:
        return  # 解析失败，跳过
    
    # 3. 提取新类型
    new_schema_types = parsed_response.get("new_schema_types", {})
    
    # 4. 如果有新类型，更新 schema
    if new_schema_types:
        self._update_schema_with_new_types(new_schema_types)
```

---

### **Step 3: 去重检查和更新 Schema 文件**

```python
def _update_schema_with_new_types(self, new_schema_types: Dict[str, List[str]]):
    """更新 Schema 文件，只添加不存在的类型"""
    
    # 1. 确定 schema 文件路径
    schema_paths = {
        "hotpot": "schemas/hotpot.json",
        "2wiki": "schemas/2wiki.json",
        "musique": "schemas/musique.json",
        "demo": "schemas/demo.json",      # ⚠️ 注意：demo 不在映射中
        "graphrag-bench": "schemas/graphrag-bench.json"
    }
    
    schema_path = schema_paths.get(self.dataset_name)
    if not schema_path:
        return  # ⚠️ 如果数据集不在映射中，不更新
    
    # 2. 读取当前 schema
    with open(schema_path, 'r', encoding='utf-8') as f:
        current_schema = json.load(f)
    
    # 当前 demo.json 内容：
    # {
    #   "Nodes": ["person", "location", "organization", ...],
    #   "Relations": ["is_a", "part_of", ...],
    #   "Attributes": ["name", "date", ...]
    # }
    
    updated = False
    
    # 3. 添加新的节点类型（去重）
    if "nodes" in new_schema_types:
        for new_node in new_schema_types["nodes"]:  # ["vehicle", "technology"]
            if new_node not in current_schema.get("Nodes", []):
                current_schema.setdefault("Nodes", []).append(new_node)
                updated = True
                logger.info(f"✨ Added new node type: {new_node}")
    
    # 4. 添加新的关系类型（去重）
    if "relations" in new_schema_types:
        for new_relation in new_schema_types["relations"]:  # ["manufactured_by", "has_feature"]
            if new_relation not in current_schema.get("Relations", []):
                current_schema.setdefault("Relations", []).append(new_relation)
                updated = True
                logger.info(f"✨ Added new relation type: {new_relation}")
    
    # 5. 添加新的属性类型（去重）
    if "attributes" in new_schema_types:
        for new_attribute in new_schema_types["attributes"]:  # ["color", "price"]
            if new_attribute not in current_schema.get("Attributes", []):
                current_schema.setdefault("Attributes", []).append(new_attribute)
                updated = True
                logger.info(f"✨ Added new attribute type: {new_attribute}")
    
    # 6. 如果有更新，保存到文件
    if updated:
        with open(schema_path, 'w', encoding='utf-8') as f:
            json.dump(current_schema, f, ensure_ascii=False, indent=2)
        
        # 7. 更新内存中的 schema
        self.schema = current_schema
        
        logger.info(f"📝 Schema file updated: {schema_path}")
```

---

### **Step 4: 更新后的 Schema 示例**

**更新前** (`schemas/demo.json`):
```json
{
  "Nodes": [
    "person", "location", "organization", "event", "object"
  ],
  "Relations": [
    "is_a", "part_of", "located_in", "created_by"
  ],
  "Attributes": [
    "name", "date", "size"
  ]
}
```

**更新后**:
```json
{
  "Nodes": [
    "person", "location", "organization", "event", "object",
    "vehicle",      // 🆕 新增
    "technology"    // 🆕 新增
  ],
  "Relations": [
    "is_a", "part_of", "located_in", "created_by",
    "manufactured_by",  // 🆕 新增
    "has_feature"       // 🆕 新增
  ],
  "Attributes": [
    "name", "date", "size",
    "color",   // 🆕 新增
    "price"    // 🆕 新增
  ]
}
```

---

### **Step 5: 后续文档使用新 Schema**

更新后，新的 schema 会立即生效：

```python
# 下一个文本块处理时
prompt = self._get_construction_prompt(next_chunk)

# Prompt 中包含最新的 schema
"""
Guidelines:
1. Prioritize the following predefined schema for extraction:
   ```
   {
     "Nodes": ["person", "location", ..., "vehicle", "technology"],
     "Relations": ["is_a", ..., "manufactured_by", "has_feature"],
     "Attributes": ["name", "date", ..., "color", "price"]
   }
   ```
2. Flexibility: If the context doesn't fit, extract as needed
...
"""
```

**优点**：
- ✅ 后续文档抽取时，LLM 能识别 "vehicle"、"technology" 等新类型
- ✅ 减少重复发现相同类型
- ✅ Schema 逐步完善

---

## 🔍 **关键机制**

### **1. 线程安全**
```python
with self.lock:
    self._process_attributes_agent(extracted_attr, id, entity_types)
    self._process_triples_agent(extracted_triples, id, entity_types)
```
- 使用锁保护 schema 更新
- 避免多线程并发写入冲突

---

### **2. 去重机制**
```python
if new_node not in current_schema.get("Nodes", []):
    current_schema.setdefault("Nodes", []).append(new_node)
```
- 严格检查，只添加不存在的类型
- 避免 schema 污染

---

### **3. 内存同步**
```python
self.schema = current_schema  # 更新内存中的 schema
```
- 文件和内存保持一致
- 立即对后续处理生效

---

## ⚠️ **重要限制**

### **1. 数据集白名单限制**

```python
schema_paths = {
    "hotpot": "schemas/hotpot.json",
    "2wiki": "schemas/2wiki.json",
    "musique": "schemas/musique.json",
    "novel": "schemas/novels_chs.json",
    "graphrag-bench": "schemas/graphrag-bench.json"
    # ⚠️ 注意：demo 不在这里！
}

schema_path = schema_paths.get(self.dataset_name)
if not schema_path:
    return  # 默认数据集 demo 不会更新 schema
```

**结论**：
- ❌ **demo 数据集不会更新 schema 文件**
- ❌ 通过 Web 界面上传的数据集（默认使用 demo schema）也不会更新
- ✅ 只有白名单中的数据集才会更新

---

### **2. 如何为新数据集启用 Schema Evolution？**

**方法1: 修改代码添加映射**

```python
# 在 kt_gen.py 中修改
schema_paths = {
    "hotpot": "schemas/hotpot.json",
    # ... 其他数据集 ...
    "my_dataset": "schemas/my_dataset.json",  # 添加你的数据集
}
```

**方法2: 动态生成 schema 路径**

```python
def _update_schema_with_new_types(self, new_schema_types: Dict[str, List[str]]):
    # 改进版本：自动查找 schema 文件
    schema_path = f"schemas/{self.dataset_name}.json"
    
    if not os.path.exists(schema_path):
        # 如果 schema 不存在，使用 demo schema 作为模板
        schema_path = "schemas/demo.json"
    
    # 后续处理...
```

---

## 📈 **Schema Evolution 的效果**

### **构建初期**
```json
{
  "Nodes": ["person", "location", "organization"],
  "Relations": ["located_in", "works_at"],
  "Attributes": ["name", "date"]
}
```

### **处理 100 个文档后**
```json
{
  "Nodes": [
    "person", "location", "organization",
    "vehicle", "technology", "product", "service",  // 新增
    "software", "hardware", "company_division"      // 新增
  ],
  "Relations": [
    "located_in", "works_at",
    "manufactured_by", "founded_by", "acquired_by",  // 新增
    "competes_with", "partners_with"                 // 新增
  ],
  "Attributes": [
    "name", "date",
    "price", "color", "version", "release_date",     // 新增
    "market_cap", "employee_count"                   // 新增
  ]
}
```

---

## 🎯 **实际应用场景**

### **场景1: 处理科技新闻**

**文档1** (初始 schema):
```
Tesla announces new Model Y...
```
**发现**: `vehicle`, `electric_car` → 添加到 schema

**文档2** (使用更新后的 schema):
```
Apple launches iPhone 15...
```
**发现**: LLM 已知 `product` 类型，直接使用
**新发现**: `smartphone`, `mobile_device` → 继续添加

---

### **场景2: 处理学术论文**

**论文1**:
```
Neural networks for image classification...
```
**发现**: `algorithm`, `model`, `dataset` → 添加

**论文2**:
```
Transformer architecture improves NLP tasks...
```
**发现**: LLM 已知 `algorithm`, `model`
**新发现**: `architecture`, `benchmark` → 添加

---

## 💡 **最佳实践**

### **1. 设置严格的添加阈值**

LLM Prompt 中已包含：
```
Notably, the strict threshold of adding new schema 
considering both importance and similarity to the 
pattern in the existing schema is 0.9.
```

这确保只有**真正重要且不重复**的类型才会被添加。

---

### **2. 定期审查 Schema**

```python
# 查看 schema 演化历史
git log schemas/hotpot.json

# 手动清理不必要的类型
# 编辑 schemas/hotpot.json，删除冗余类型
```

---

### **3. 使用 Schema 版本控制**

```python
{
  "version": "1.2.3",
  "last_updated": "2024-01-15",
  "Nodes": [...],
  "Relations": [...],
  "Attributes": [...]
}
```

---

## 📊 **总结对比**

| 方面 | Agent 模式 | NoAgent 模式 |
|------|-----------|-------------|
| Schema 更新 | ✅ 动态更新文件 | ❌ 不更新 |
| 新类型处理 | ✅ 添加到 schema | ❌ 忽略或强制映射到现有类型 |
| 适应性 | ✅ 高（自动学习） | ❌ 低（固定 schema） |
| 可控性 | ⚠️ 中（需要阈值控制） | ✅ 高（完全可控） |
| Schema 一致性 | ⚠️ 可能演化得很大 | ✅ 始终一致 |
| 适用场景 | 开放域、探索性任务 | 封闭域、标准化任务 |

---

## 🔧 **实战建议**

1. **首次构建**: 使用 **agent 模式**，让系统学习领域 schema
2. **Schema 稳定后**: 切换到 **noagent 模式**，保持一致性
3. **定期审查**: 检查 schema 演化是否合理
4. **备份 schema**: 构建前备份原始 schema 文件

```bash
# 构建前备份
cp schemas/demo.json schemas/demo.json.backup

# 构建后对比
diff schemas/demo.json schemas/demo.json.backup
```

这就是 Agent 模式下新发现实体和关系的完整处理流程！🎉

---

## 总结

本次对话详细梳理了 Youtu-GraphRAG 系统的完整工作流程：

1. **知识图谱构建流程**：从 Web 界面上传数据、点击 construct 后的完整处理流程
2. **Agent vs NoAgent 模式**：两种模式的区别、特点和应用场景
3. **检索与问答流程**：问题分解、多路召回、IRCoT 迭代推理的详细实现
4. **Schema Evolution 机制**：Agent 模式下如何动态发现和更新 schema 类型

核心技术要点：
- 并发处理（ThreadPoolExecutor）
- LLM 驱动的信息抽取
- 多层图结构（Level 1-4）
- FastTreeComm 社区检测
- FAISS 向量索引
- IRCoT 迭代推理
- Schema 动态演化

希望这份对话记录能帮助你深入理解 Youtu-GraphRAG 的设计理念和实现细节！

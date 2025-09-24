#!/usr/bin/env python3
"""
Simple but Complete Youtu-GraphRAG Backend
Integrates real GraphRAG functionality with a simple interface
"""

import os
import sys
import json
import asyncio
import glob
import shutil
import re
from typing import List, Dict, Optional
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# FastAPI imports
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from utils.logger import logger, setup_logger
import os
from datetime import datetime

# 启用文件日志
os.makedirs("output/logs", exist_ok=True)
log_file_path = f"output/logs/youtu-graphrag-{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logger = setup_logger(log_file=log_file_path)
import ast

# Try to import GraphRAG components
try:
    from models.constructor import kt_gen as constructor
    from models.retriever import agentic_decomposer as decomposer, enhanced_kt_retriever as retriever
    from config import get_config, ConfigManager
    GRAPHRAG_AVAILABLE = True
    logger.info("✅ GraphRAG components loaded successfully")
except ImportError as e:
    GRAPHRAG_AVAILABLE = False
    logger.error(f"⚠️  GraphRAG components not available: {e}")

app = FastAPI(title="Youtu-GraphRAG Unified Interface", version="1.0.0")

# Mount static files (assets directory)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
# Mount frontend directory for frontend assets
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
active_connections: Dict[str, WebSocket] = {}
config = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)

manager = ConnectionManager()

# Request/Response models
class FileUploadResponse(BaseModel):
    success: bool
    message: str
    dataset_name: Optional[str] = None
    files_count: Optional[int] = None

class GraphConstructionRequest(BaseModel):
    dataset_name: str

class GraphConstructionResponse(BaseModel):
    success: bool
    message: str
    graph_data: Optional[Dict] = None

class QuestionRequest(BaseModel):
    question: str
    dataset_name: str

class QuestionResponse(BaseModel):
    answer: str
    sub_questions: List[Dict]
    retrieved_triples: List[str]
    retrieved_chunks: List[str]
    reasoning_steps: List[Dict]
    visualization_data: Dict

def ensure_demo_schema_exists() -> str:
    """Ensure default demo schema exists and return its path."""
    os.makedirs("schemas", exist_ok=True)
    schema_path = "schemas/demo.json"
    if not os.path.exists(schema_path):
        demo_schema = {
            "Nodes": [
                "person", "location", "organization", "event", "object",
                "concept", "time_period", "creative_work", "biological_entity", "natural_phenomenon"
            ],
            "Relations": [
                "is_a", "part_of", "located_in", "created_by", "used_by", "participates_in",
                "related_to", "belongs_to", "influences", "precedes", "arrives_in", "comparable_to"
            ],
            "Attributes": [
                "name", "date", "size", "type", "description", "status",
                "quantity", "value", "position", "duration", "time"
            ]
        }
        with open(schema_path, 'w') as f:
            json.dump(demo_schema, f, indent=2)
    return schema_path

def get_schema_path_for_dataset(dataset_name: str) -> str:
    """Return dataset-specific schema if present; otherwise fallback to demo schema."""
    if dataset_name and dataset_name != "demo":
        ds_schema = f"schemas/{dataset_name}.json"
        if os.path.exists(ds_schema):
            return ds_schema
    return ensure_demo_schema_exists()

async def send_progress_update(client_id: str, stage: str, progress: int, message: str):
    """Send progress update via WebSocket"""
    await manager.send_message({
        "type": "progress",
        "stage": stage,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }, client_id)

async def clear_cache_files(dataset_name: str):
    """Clear all cache files for a dataset before graph construction"""
    try:
        # Clear FAISS cache files
        faiss_cache_dir = f"retriever/faiss_cache_new/{dataset_name}"
        if os.path.exists(faiss_cache_dir):
            shutil.rmtree(faiss_cache_dir)
            logger.info(f"Cleared FAISS cache directory: {faiss_cache_dir}")

        # Clear output chunks
        chunk_file = f"output/chunks/{dataset_name}.txt"
        if os.path.exists(chunk_file):
            os.remove(chunk_file)
            logger.info(f"Cleared chunk file: {chunk_file}")

        # Clear output graphs
        graph_file = f"output/graphs/{dataset_name}_new.json"
        if os.path.exists(graph_file):
            os.remove(graph_file)
            logger.info(f"Cleared graph file: {graph_file}")

        # Clear any other cache files with dataset name pattern
        cache_patterns = [
            f"output/logs/{dataset_name}_*.log",
            f"output/chunks/{dataset_name}_*",
            f"output/graphs/{dataset_name}_*"
        ]

        for pattern in cache_patterns:
            for file_path in glob.glob(pattern):
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        logger.info(f"Cleared cache file: {file_path}")
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        logger.info(f"Cleared cache directory: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clear {file_path}: {e}")

        logger.info(f"Cache cleanup completed for dataset: {dataset_name}")

    except Exception as e:
        logger.error(f"Error clearing cache files for {dataset_name}: {e}")
        # Don't raise exception, just log the error

# Serve frontend HTML
@app.get("/")
async def read_root():
    frontend_path = "frontend/index.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Youtu-GraphRAG Unified Interface is running!", "status": "ok"}

@app.get("/api/status")
async def get_status():
    return {
        "message": "Youtu-GraphRAG Unified Interface is running!",
        "status": "ok",
        "graphrag_available": GRAPHRAG_AVAILABLE
    }

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)


# --- Step 2: Replaced the entire upload_files function with the security-hardened version ---
@app.post("/api/upload", response_model=FileUploadResponse)
async def upload_files(files: List[UploadFile] = File(...), client_id: str = "default"):
    """Upload files and prepare for graph construction"""

    # --- Security Enhancement Configuration ---
    ALLOWED_EXTENSIONS = {".txt", ".json", ".md"}
    MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB

    def secure_filename_custom(filename: str) -> str:
        """Manually implement a simplified secure_filename function that supports Chinese characters."""
        if not filename:
            return ""
        filename = os.path.basename(filename)  # Crucial: remove any directory info
        filename = filename.replace(" ", "_")
        # 保留中文字符、字母、数字、下划线、连字符和点号
        filename = re.sub(r"[^\w\u4e00-\u9fff.-]", "", filename)
        return filename

    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files were uploaded.")

        main_file = files[0]
        safe_main_filename = secure_filename_custom(main_file.filename)
        if not safe_main_filename:
            raise HTTPException(status_code=400, detail="Invalid main file name.")

        original_name = os.path.splitext(safe_main_filename)[0]
        
        # 改进的数据集名称生成逻辑
        # 1. 首先尝试保留字母数字字符
        dataset_name = "".join(c for c in original_name if c.isalnum() or c in ('-', '_')).rstrip()
        
        # 2. 如果结果为空或只包含特殊字符，尝试保留中文字符
        if not dataset_name or dataset_name in ['-', '_']:
            # 保留中文字符、字母、数字、连字符和下划线
            dataset_name = "".join(c for c in original_name if c.isalnum() or c in ('-', '_') or '\u4e00' <= c <= '\u9fff').rstrip()
        
        # 3. 如果仍然为空，使用时间戳生成默认名称
        if not dataset_name or dataset_name in ['-', '_']:
            dataset_name = f"dataset_{int(datetime.now().timestamp())}"

        base_name = dataset_name
        counter = 1
        while os.path.exists(f"data/uploaded/{dataset_name}"):
            dataset_name = f"{base_name}_{counter}"
            counter += 1
        upload_dir = f"data/uploaded/{dataset_name}"
        os.makedirs(upload_dir, exist_ok=True)

        await send_progress_update(client_id, "upload", 10, "Starting file upload...")

        corpus_data = []
        processed_files_count = 0
        for i, file in enumerate(files):

            # =================== New Security Check Block ===================
            #
            # Vulnerability Fix 1: Check file size to prevent DoS attacks
            if file.size > MAX_FILE_SIZE:
                logger.warning(f"Skipping file '{file.filename}': Exceeds max size of {MAX_FILE_SIZE / 1024 ** 2}MB.")
                continue

            # Vulnerability Fix 2: Sanitize filename to prevent Path Traversal
            safe_filename = secure_filename_custom(file.filename)
            
            # 如果处理后的文件名为空或只有扩展名，生成一个默认名称
            if not safe_filename or safe_filename.startswith('.'):
                _, original_ext = os.path.splitext(file.filename)
                safe_filename = f"file_{int(datetime.now().timestamp())}{original_ext}"
            
            # Vulnerability Fix 3: Check file extension to prevent malicious script uploads
            _, ext = os.path.splitext(safe_filename)
            
            if ext.lower() not in ALLOWED_EXTENSIONS:
                logger.warning(f"Skipping file '{safe_filename}': File extension '{ext}' is not allowed.")
                continue
            #
            # =================== End of Security Check Block ===================

            file_path = os.path.join(upload_dir, safe_filename)

            try:
                # Use chunked writing to prevent memory exhaustion
                with open(file_path, "wb") as buffer:
                    while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                        buffer.write(content)
            except Exception as e:
                logger.error(f"Failed to write file '{safe_filename}': {e}")
                continue

            # Process file content (using the sanitized filename)
            try:
                if safe_filename.lower().endswith(('.txt', '.md')):
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    corpus_data.append({"title": safe_filename, "text": content})

                elif safe_filename.lower().endswith('.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            corpus_data.extend(data)
                        else:
                            corpus_data.append(data)

                processed_files_count += 1

            except Exception as e:
                logger.error(f"Failed to process content of file '{safe_filename}': {e}")
                os.remove(file_path)  # Delete the uploaded file if content processing fails
                continue

            progress = 10 + (i + 1) * 80 // len(files)
            await send_progress_update(client_id, "upload", progress, f"Processed {safe_filename}")

        if processed_files_count > 0:
            corpus_path = f"{upload_dir}/corpus.json"
            with open(corpus_path, 'w', encoding='utf-8') as f:
                json.dump(corpus_data, f, ensure_ascii=False, indent=2)

        # This function was renamed in the new version, ensuring compatibility
        ensure_demo_schema_exists()

        await send_progress_update(client_id, "upload", 100, "Upload completed successfully!")

        return FileUploadResponse(
            success=True,
            message=f"Upload complete. Processed {processed_files_count} valid files.",
            dataset_name=dataset_name,
            files_count=processed_files_count
        )

    except Exception as e:
        await send_progress_update(client_id, "upload", 0, f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def create_dataset_config():
    """Create dataset configuration"""
    # Ensure default demo schema exists
    ensure_demo_schema_exists()

@app.post("/api/construct-graph", response_model=GraphConstructionResponse)
async def construct_graph(request: GraphConstructionRequest, client_id: str = "default"):
    """Construct knowledge graph from uploaded data"""
    try:
        if not GRAPHRAG_AVAILABLE:
            raise HTTPException(status_code=503, detail="GraphRAG components not available. Please install or configure them.")
        dataset_name = request.dataset_name

        await send_progress_update(client_id, "construction", 2, "清理旧缓存文件...")

        # Clear all cache files before construction
        await clear_cache_files(dataset_name)

        await send_progress_update(client_id, "construction", 5, "初始化图构建器...")

        # Get dataset paths
        corpus_path = f"data/uploaded/{dataset_name}/corpus.json"
        # Choose schema: dataset-specific or default demo
        schema_path = get_schema_path_for_dataset(dataset_name)

        if not os.path.exists(corpus_path):
            # Try demo dataset
            corpus_path = "data/demo/demo_corpus.json"

        if not os.path.exists(corpus_path):
            raise HTTPException(status_code=404, detail="Dataset not found")

        await send_progress_update(client_id, "construction", 10, "加载配置和语料库...")

        # Initialize config
        global config
        if config is None:
            config = get_config("config/base_config.yaml")

        # Initialize KTBuilder
        builder = constructor.KTBuilder(
            dataset_name,
            schema_path,
            mode=config.construction.mode,
            config=config
        )

        await send_progress_update(client_id, "construction", 20, "开始实体关系抽取...")

        # Build knowledge graph
        def build_graph_sync():
            return builder.build_knowledge_graph(corpus_path)

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()

        # Run graph construction without simulated progress updates
        knowledge_graph = await loop.run_in_executor(None, build_graph_sync)

        await send_progress_update(client_id, "construction", 95, "准备可视化数据...")
        # Load constructed graph for visualization
        graph_path = f"output/graphs/{dataset_name}_new.json"
        graph_vis_data = await prepare_graph_visualization(graph_path)

        await send_progress_update(client_id, "construction", 100, "图构建完成!")
        # Notify completion via WebSocket
        try:
            await manager.send_message({
                "type": "complete",
                "stage": "construction",
                "message": "图构建完成!",
                "timestamp": datetime.now().isoformat()
            }, client_id)
        except Exception as _e:
            logger.warning(f"Failed to send completion message: {_e}")

        return GraphConstructionResponse(
            success=True,
            message="Knowledge graph constructed successfully",
            graph_data=graph_vis_data
        )

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Graph construction failed for dataset '{dataset_name}': {str(e)}")
        logger.error(f"Full traceback:\n{error_details}")
        
        await send_progress_update(client_id, "construction", 0, f"构建失败: {str(e)}")
        try:
            await manager.send_message({
                "type": "error",
                "stage": "construction",
                "message": f"构建失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }, client_id)
        except Exception as _e:
            logger.warning(f"Failed to send error message: {_e}")
        raise HTTPException(status_code=500, detail=str(e))


async def prepare_graph_visualization(graph_path: str) -> Dict:
    """Prepare graph data for visualization"""
    try:
        if os.path.exists(graph_path):
            with open(graph_path, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)
        else:
            return {"nodes": [], "links": [], "categories": [], "stats": {}}

        # Handle different graph data formats
        if isinstance(graph_data, list):
            # GraphRAG format: list of relationships
            return convert_graphrag_format(graph_data)
        elif isinstance(graph_data, dict) and "nodes" in graph_data:
            # Standard format: {nodes: [], edges: []}
            return convert_standard_format(graph_data)
        else:
            return {"nodes": [], "links": [], "categories": [], "stats": {}}

    except Exception as e:
        logger.error(f"Error preparing visualization: {e}")
        return {"nodes": [], "links": [], "categories": [], "stats": {}}

def convert_graphrag_format(graph_data: List) -> Dict:
    """Convert GraphRAG relationship list to ECharts format"""
    nodes_dict = {}
    links = []

    # Extract nodes and relationships from the list
    for item in graph_data:
        if not isinstance(item, dict):
            continue

        start_node = item.get("start_node", {})
        end_node = item.get("end_node", {})
        relation = item.get("relation", "related_to")

        # Process start node
        start_id = ""
        end_id = ""
        if start_node:
            start_id = start_node.get("properties", {}).get("name", "")
            if start_id and start_id not in nodes_dict:
                nodes_dict[start_id] = {
                    "id": start_id,
                    "name": start_id[:30],
                    "category": start_node.get("properties", {}).get("schema_type", start_node.get("label", "entity")),
                    "symbolSize": 25,
                    "properties": start_node.get("properties", {})
                }

        # Process end node
        if end_node:
            end_id = end_node.get("properties", {}).get("name", "")
            if end_id and end_id not in nodes_dict:
                nodes_dict[end_id] = {
                    "id": end_id,
                    "name": end_id[:30],
                    "category": end_node.get("properties", {}).get("schema_type", end_node.get("label", "entity")),
                    "symbolSize": 25,
                    "properties": end_node.get("properties", {})
                }

        # Add relationship
        if start_id and end_id:
            links.append({
                "source": start_id,
                "target": end_id,
                "name": relation,
                "value": 1
            })

    # Create categories
    categories_set = set()
    for node in nodes_dict.values():
        categories_set.add(node["category"])

    categories = []
    for i, cat_name in enumerate(categories_set):
        categories.append({
            "name": cat_name,
            "itemStyle": {
                "color": f"hsl({i * 360 / len(categories_set)}, 70%, 60%)"
            }
        })

    nodes = list(nodes_dict.values())

    return {
        "nodes": nodes[:500],  # Limit for better visual effects​​
        "links": links[:1000],
        "categories": categories,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(links),
            "displayed_nodes": len(nodes[:500]),
            "displayed_edges": len(links[:1000])
        }
    }

def convert_standard_format(graph_data: Dict) -> Dict:
    """Convert standard {nodes: [], edges: []} format to ECharts format"""
    nodes = []
    links = []
    categories = []

    # Extract unique categories
    node_types = set()
    for node in graph_data.get("nodes", []):
        node_type = node.get("type", "entity")
        node_types.add(node_type)

    for i, node_type in enumerate(node_types):
        categories.append({
            "name": node_type,
            "itemStyle": {
                "color": f"hsl({i * 360 / len(node_types)}, 70%, 60%)"
            }
        })

    # Process nodes
    for node in graph_data.get("nodes", []):
        nodes.append({
            "id": node.get("id", ""),
            "name": node.get("name", node.get("id", ""))[:30],
            "category": node.get("type", "entity"),
            "value": len(node.get("attributes", [])),
            "symbolSize": min(max(len(node.get("attributes", [])) * 3 + 15, 15), 40),
            "attributes": node.get("attributes", [])
        })

    # Process edges
    for edge in graph_data.get("edges", []):
        links.append({
            "source": edge.get("source", ""),
            "target": edge.get("target", ""),
            "name": edge.get("relation", "related_to"),
            "value": edge.get("weight", 1)
        })

    return {
        "nodes": nodes[:500],  # Limit for performance
        "links": links[:1000],
        "categories": categories,
        "stats": {
            "total_nodes": len(graph_data.get("nodes", [])),
            "total_edges": len(graph_data.get("edges", [])),
            "displayed_nodes": len(nodes[:500]),
            "displayed_edges": len(links[:1000])
        }
    }

@app.post("/api/ask-question", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest, client_id: str = "default"):
    """Process question using agent mode (iterative retrieval + reasoning) and return answer."""
    try:
        if not GRAPHRAG_AVAILABLE:
            raise HTTPException(status_code=503, detail="GraphRAG components not available. Please install or configure them.")
        dataset_name = request.dataset_name
        question = request.question

        await send_progress_update(client_id, "retrieval", 10, "初始化检索系统 (agent 模式)...")

        graph_path = f"output/graphs/{dataset_name}_new.json"
        schema_path = get_schema_path_for_dataset(dataset_name)
        if not os.path.exists(graph_path):
            graph_path = "output/graphs/demo_new.json"
        if not os.path.exists(graph_path):
            raise HTTPException(status_code=404, detail="Graph not found. Please construct graph first.")

        # Config & components
        global config
        if config is None:
            config = get_config("config/base_config.yaml")

        graphq = decomposer.GraphQ(dataset_name, config=config)
        kt_retriever = retriever.KTRetriever(
            dataset_name,
            graph_path,
            recall_paths=config.retrieval.recall_paths,
            schema_path=schema_path,
            top_k=config.retrieval.top_k_filter,
            mode="agent",  # 强制 agent 模式
            config=config
        )

        await send_progress_update(client_id, "retrieval", 40, "构建索引...")
        kt_retriever.build_indices()

        # Helper functions (复用 main.py 逻辑的精简版)
        def _dedup(items):
            return list({x: None for x in items}.keys())
        def _merge_chunk_contents(ids, mapping):
            return [mapping.get(i, f"[Missing content for chunk {i}]") for i in ids]

        # Step 1: decomposition
        await send_progress_update(client_id, "retrieval", 50, "问题分解...")
        try:
            decomposition = graphq.decompose(question, schema_path)
            sub_questions = decomposition.get("sub_questions", [])
            involved_types = decomposition.get("involved_types", {})
        except Exception as e:
            logger.error(f"Decompose failed: {e}")
            sub_questions = [{"sub-question": question}]
            involved_types = {"nodes": [], "relations": [], "attributes": []}
            decomposition = {"sub_questions": sub_questions, "involved_types": involved_types}

        reasoning_steps = []
        all_triples = set()
        all_chunk_ids = set()
        all_chunk_contents: Dict[str, str] = {}

        # Step 2: initial retrieval for each sub-question
        await send_progress_update(client_id, "retrieval", 65, "初始检索...")
        import time as _time
        for idx, sq in enumerate(sub_questions):
            sq_text = sq.get("sub-question", question)
            start_t = _time.time()
            retrieval_results, elapsed = kt_retriever.process_retrieval_results(
                sq_text,
                top_k=config.retrieval.top_k_filter,
                involved_types=involved_types
            )
            triples = retrieval_results.get('triples', []) or []
            chunk_ids = retrieval_results.get('chunk_ids', []) or []
            chunk_contents = retrieval_results.get('chunk_contents', []) or []
            if isinstance(chunk_contents, dict):
                for cid, ctext in chunk_contents.items():
                    all_chunk_contents[cid] = ctext
            else:
                for i_c, cid in enumerate(chunk_ids):
                    if i_c < len(chunk_contents):
                        all_chunk_contents[cid] = chunk_contents[i_c]
            all_triples.update(triples)
            all_chunk_ids.update(chunk_ids)
            reasoning_steps.append({
                "type": "sub_question",
                "question": sq_text,
                "triples": triples[:10],
                "triples_count": len(triples),
                "chunks_count": len(chunk_ids),
                "processing_time": elapsed,
                "chunk_contents": list(all_chunk_contents.values())[:3]
            })

        # Step 3: IRCoT iterative refinement
        await send_progress_update(client_id, "retrieval", 75, "迭代推理...")
        max_steps = getattr(getattr(config.retrieval, 'agent', object()), 'max_steps', 3)
        current_query = question
        thoughts = []

        # Initial answer attempt
        initial_triples = _dedup(list(all_triples))
        initial_chunk_ids = list(set(all_chunk_ids))
        initial_chunk_contents = _merge_chunk_contents(initial_chunk_ids, all_chunk_contents)
        context_initial = "=== Triples ===\n" + "\n".join(initial_triples[:20]) + "\n=== Chunks ===\n" + "\n".join(initial_chunk_contents[:10])
        init_prompt = kt_retriever.generate_prompt(question, context_initial)
        try:
            initial_answer = kt_retriever.generate_answer(init_prompt)
        except Exception as e:
            initial_answer = f"Initial answer failed: {e}"
        thoughts.append(f"Initial: {initial_answer[:200]}")
        final_answer = initial_answer

        import re as _re
        for step in range(1, max_steps + 1):
            loop_triples = _dedup(list(all_triples))
            loop_chunk_ids = list(set(all_chunk_ids))
            loop_chunk_contents = _merge_chunk_contents(loop_chunk_ids, all_chunk_contents)
            
            # 调试日志：检查最终context生成
            logger.info(f"Step{step} - loop_chunk_ids数量: {len(loop_chunk_ids)}")
            logger.info(f"Step{step} - all_chunk_contents数量: {len(all_chunk_contents)}")
            logger.info(f"Step{step} - loop_chunk_contents数量: {len(loop_chunk_contents)}")
            if loop_chunk_contents:
                logger.info(f"Step{step} - 第一个chunk内容: {loop_chunk_contents[0][:100]}...")
            
            loop_ctx = "=== Triples ===\n" + "\n".join(loop_triples[:20]) + "\n=== Chunks ===\n" + "\n".join(loop_chunk_contents[:10])
            loop_prompt = f"""
You are an expert knowledge assistant using iterative retrieval with chain-of-thought reasoning.

CRITICAL: When analyzing building equipment information, understand that device names contain location information:
- "A栋3层空调箱" means an air conditioning unit located on the 3rd floor of Building A
- "A栋3层01号变风量末端" means a VAV terminal located on the 3rd floor of Building A  
- "A栋3层照明配电箱" means a lighting distribution box located on the 3rd floor of Building A
- Equipment names like "X栋Y层设备名" directly indicate the building (X栋) and floor (Y层/YF) location

CRITICAL RULE: If the question asks about equipment on a specific floor (like "A栋3F" or "A栋3层"), and you see equipment with matching names in the chunks, these ARE NOT examples - they are ACTUAL REAL EQUIPMENT located on that floor. You MUST list them as the answer.

For example, if you see "#### 设备: A栋3层空调箱 (A-AHU-03)" in the chunks, this is a REAL air conditioning unit on A栋3层, not an example.

Current Question: {question}
Current Iteration Query: {current_query}
Knowledge Context:\n{loop_ctx}
Previous Thoughts: {' | '.join(thoughts) if thoughts else 'None'}
Instructions:
1. If enough info answer with: So the answer is: <answer>
2. Else propose new query with: The new query is: <query>
Your reasoning:
"""
            try:
                reasoning = kt_retriever.generate_answer(loop_prompt)
            except Exception as e:
                reasoning = f"Reasoning error: {e}"
            thoughts.append(reasoning[:400])
            reasoning_steps.append({
                "type": "ircot_step",
                "question": current_query,
                "triples": loop_triples[:10],
                "triples_count": len(loop_triples),
                "chunks_count": len(loop_chunk_ids),
                "processing_time": 0,
                "chunk_contents": loop_chunk_contents[:3],
                "thought": reasoning[:300]
            })
            if "So the answer is:" in reasoning:
                m = _re.search(r"So the answer is:\s*(.*)", reasoning, flags=_re.IGNORECASE | _re.DOTALL)
                final_answer = m.group(1).strip() if m else reasoning
                break
            if "The new query is:" not in reasoning:
                final_answer = initial_answer or reasoning
                break
            new_query = reasoning.split("The new query is:", 1)[1].strip().splitlines()[0]
            if not new_query or new_query == current_query:
                final_answer = initial_answer or reasoning
                break
            current_query = new_query
            await send_progress_update(client_id, "retrieval", min(90, 75 + step * 5), f"迭代检索 Step {step}...")
            try:
                new_ret, _ = kt_retriever.process_retrieval_results(current_query, top_k=config.retrieval.top_k_filter)
                new_triples = new_ret.get('triples', []) or []
                new_chunk_ids = new_ret.get('chunk_ids', []) or []
                new_chunk_contents = new_ret.get('chunk_contents', []) or []
                
                # 调试日志：检查新检索结果
                logger.info(f"迭代检索Step{step} - 新增chunk数量: {len(new_chunk_ids)}")
                logger.info(f"迭代检索Step{step} - 当前all_chunk_contents数量: {len(all_chunk_contents)}")
                
                if isinstance(new_chunk_contents, dict):
                    for cid, ctext in new_chunk_contents.items():
                        all_chunk_contents[cid] = ctext
                        logger.info(f"迭代检索Step{step} - 添加chunk: {cid} - {ctext[:100]}...")
                else:
                    for i_c, cid in enumerate(new_chunk_ids):
                        if i_c < len(new_chunk_contents):
                            all_chunk_contents[cid] = new_chunk_contents[i_c]
                            logger.info(f"迭代检索Step{step} - 添加chunk: {cid} - {new_chunk_contents[i_c][:100]}...")
                
                all_triples.update(new_triples)
                all_chunk_ids.update(new_chunk_ids)
                logger.info(f"迭代检索Step{step}后 - 总chunk数量: {len(all_chunk_contents)}")
            except Exception as e:
                logger.error(f"Iterative retrieval failed: {e}")
                break

        # Final aggregation
        final_triples = _dedup(list(all_triples))[:20]
        final_chunk_ids = list(set(all_chunk_ids))
        final_chunk_contents = _merge_chunk_contents(final_chunk_ids, all_chunk_contents)[:10]

        await send_progress_update(client_id, "retrieval", 100, "答案生成完成!")

        visualization_data = {
            "subqueries": prepare_subquery_visualization(sub_questions, reasoning_steps),
            "knowledge_graph": prepare_retrieved_graph_visualization(final_triples),
            "reasoning_flow": prepare_reasoning_flow_visualization(reasoning_steps),
            "retrieval_details": {
                "total_triples": len(final_triples),
                "total_chunks": len(final_chunk_contents),
                "sub_questions_count": len(sub_questions),
                "triples_by_subquery": [s.get("triples_count", 0) for s in reasoning_steps if s.get("type") == "sub_question"]
            }
        }

        return QuestionResponse(
            answer=final_answer,
            sub_questions=sub_questions,
            retrieved_triples=final_triples,
            retrieved_chunks=final_chunk_contents,
            reasoning_steps=reasoning_steps,
            visualization_data=visualization_data
        )
    except Exception as e:
        await send_progress_update(client_id, "retrieval", 0, f"问答处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def prepare_subquery_visualization(sub_questions: List[Dict], reasoning_steps: List[Dict]) -> Dict:
    """Prepare subquery visualization"""
    nodes = [{"id": "original", "name": "原始问题", "category": "question", "symbolSize": 40}]
    links = []

    for i, sub_q in enumerate(sub_questions):
        sub_id = f"sub_{i}"
        nodes.append({
            "id": sub_id,
            "name": sub_q.get("sub-question", "")[:20] + "...",
            "category": "sub_question",
            "symbolSize": 30
        })
        links.append({"source": "original", "target": sub_id, "name": "分解为"})

    return {
        "nodes": nodes,
        "links": links,
        "categories": [
            {"name": "question", "itemStyle": {"color": "#ff6b6b"}},
            {"name": "sub_question", "itemStyle": {"color": "#4ecdc4"}}
        ]
    }

def prepare_retrieved_graph_visualization(triples: List[str]) -> Dict:
    """Prepare retrieved knowledge visualization"""
    nodes = []
    links = []
    node_set = set()

    for triple in triples[:10]:
        try:
            if triple.startswith('[') and triple.endswith(']'):
                try:
                    parts = ast.literal_eval(triple)
                except Exception:
                    continue
                if len(parts) == 3:
                    source, relation, target = parts

                    for entity in [source, target]:
                        if entity not in node_set:
                            node_set.add(entity)
                            nodes.append({
                                "id": str(entity),
                                "name": str(entity)[:20],
                                "category": "entity",
                                "symbolSize": 20
                            })

                    links.append({
                        "source": str(source),
                        "target": str(target),
                        "name": str(relation)
                    })
        except:
            continue

    return {
        "nodes": nodes,
        "links": links,
        "categories": [{"name": "entity", "itemStyle": {"color": "#95de64"}}]
    }

def prepare_reasoning_flow_visualization(reasoning_steps: List[Dict]) -> Dict:
    """Prepare reasoning flow visualization"""
    steps_data = []
    for i, step in enumerate(reasoning_steps):
        steps_data.append({
            "step": i + 1,
            "type": step.get("type", "unknown"),
            "question": step.get("question", "")[:50],
            "triples_count": step.get("triples_count", 0),
            "chunks_count": step.get("chunks_count", 0),
            "processing_time": step.get("processing_time", 0)
        })

    return {
        "steps": steps_data,
        "timeline": [step["processing_time"] for step in steps_data]
    }

@app.get("/api/datasets")
async def get_datasets():
    """Get list of available datasets"""
    datasets = []

    # Check uploaded datasets
    upload_dir = "data/uploaded"
    if os.path.exists(upload_dir):
        for item in os.listdir(upload_dir):
            item_path = os.path.join(upload_dir, item)
            if os.path.isdir(item_path):
                corpus_path = os.path.join(item_path, "corpus.json")
                if os.path.exists(corpus_path):
                    graph_path = f"output/graphs/{item}_new.json"
                    status = "ready" if os.path.exists(graph_path) else "needs_construction"
                    has_custom_schema = os.path.exists(f"schemas/{item}.json")
                    datasets.append({
                        "name": item,
                        "type": "uploaded",
                        "status": status,
                        "has_custom_schema": has_custom_schema
                    })

    # Add demo dataset
    demo_corpus = "data/demo/demo_corpus.json"
    if os.path.exists(demo_corpus):
        demo_graph = "output/graphs/demo_new.json"
        status = "ready" if os.path.exists(demo_graph) else "needs_construction"
        datasets.append({
            "name": "demo",
            "type": "demo",
            "status": status,
            "has_custom_schema": False
        })

    return {"datasets": datasets}

@app.post("/api/datasets/{dataset_name}/schema")
async def upload_schema(dataset_name: str, schema_file: UploadFile = File(...)):
    """Upload a custom schema JSON for a dataset."""
    try:
        if dataset_name == "demo":
            raise HTTPException(status_code=400, detail="Cannot upload schema for demo dataset")
        if not schema_file.filename.lower().endswith('.json'):
            raise HTTPException(status_code=400, detail="Schema file must be a .json file")

        content = await schema_file.read()
        try:
            data = json.loads(content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="Schema JSON must be an object")

        os.makedirs("schemas", exist_ok=True)
        save_path = f"schemas/{dataset_name}.json"
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return {"success": True, "message": "Schema uploaded successfully", "dataset_name": dataset_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload schema: {str(e)}")

@app.delete("/api/datasets/{dataset_name}")
async def delete_dataset(dataset_name: str):
    """Delete a dataset and all its associated files"""
    try:
        if dataset_name == "demo":
            raise HTTPException(status_code=400, detail="Cannot delete demo dataset")

        deleted_files = []

        # Delete dataset directory
        dataset_dir = f"data/uploaded/{dataset_name}"
        if os.path.exists(dataset_dir):
            import shutil
            shutil.rmtree(dataset_dir)
            deleted_files.append(dataset_dir)

        # Delete graph file
        graph_path = f"output/graphs/{dataset_name}_new.json"
        if os.path.exists(graph_path):
            os.remove(graph_path)
            deleted_files.append(graph_path)

        # Delete schema file (if dataset-specific)
        schema_path = f"schemas/{dataset_name}.json"
        if os.path.exists(schema_path):
            os.remove(schema_path)
            deleted_files.append(schema_path)

        # Delete cache files
        cache_dir = f"retriever/faiss_cache_new/{dataset_name}"
        if os.path.exists(cache_dir):
            import shutil
            shutil.rmtree(cache_dir)
            deleted_files.append(cache_dir)

        # Delete chunk files
        chunk_file = f"output/chunks/{dataset_name}.txt"
        if os.path.exists(chunk_file):
            os.remove(chunk_file)
            deleted_files.append(chunk_file)

        return {
            "success": True,
            "message": f"Dataset '{dataset_name}' deleted successfully",
            "deleted_files": deleted_files
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete dataset: {str(e)}")

@app.post("/api/datasets/{dataset_name}/reconstruct")
async def reconstruct_dataset(dataset_name: str, client_id: str = "default"):
    """Reconstruct graph for an existing dataset"""
    try:
        if not GRAPHRAG_AVAILABLE:
            raise HTTPException(status_code=503, detail="GraphRAG components not available. Please install or configure them.")
        # Check if dataset exists
        corpus_path = f"data/uploaded/{dataset_name}/corpus.json"
        if not os.path.exists(corpus_path):
            if dataset_name == "demo":
                corpus_path = "data/demo/demo_corpus.json"
            else:
                raise HTTPException(status_code=404, detail="Dataset not found")

        await send_progress_update(client_id, "reconstruction", 5, "开始重新构图...")

        # Delete existing graph file
        graph_path = f"output/graphs/{dataset_name}_new.json"
        if os.path.exists(graph_path):
            os.remove(graph_path)
            await send_progress_update(client_id, "reconstruction", 15, "已删除旧图谱文件...")

        # Delete existing cache files
        cache_dir = f"retriever/faiss_cache_new/{dataset_name}"
        if os.path.exists(cache_dir):
            import shutil
            shutil.rmtree(cache_dir)
            await send_progress_update(client_id, "reconstruction", 25, "已清理缓存文件...")

        await send_progress_update(client_id, "reconstruction", 35, "重新初始化图构建器...")

        # Initialize config
        global config
        if config is None:
            config = get_config("config/base_config.yaml")

        # Choose schema: dataset-specific or default demo
        schema_path = get_schema_path_for_dataset(dataset_name)

        # Initialize KTBuilder
        builder = constructor.KTBuilder(
            dataset_name,
            schema_path,
            mode=config.construction.mode,
            config=config
        )

        await send_progress_update(client_id, "reconstruction", 50, "开始重新构建图谱...")

        # Build knowledge graph
        def build_graph_sync():
            return builder.build_knowledge_graph(corpus_path)

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()

        # Run graph reconstruction without simulated progress updates
        knowledge_graph = await loop.run_in_executor(None, build_graph_sync)

        await send_progress_update(client_id, "reconstruction", 100, "图谱重构完成!")
        # Notify completion via WebSocket
        try:
            await manager.send_message({
                "type": "complete",
                "stage": "reconstruction",
                "message": "图谱重构完成!",
                "timestamp": datetime.now().isoformat()
            }, client_id)
        except Exception as _e:
            logger.warning(f"Failed to send completion message: {_e}")

        return {
            "success": True,
            "message": "Dataset reconstructed successfully",
            "dataset_name": dataset_name
        }

    except Exception as e:
        await send_progress_update(client_id, "reconstruction", 0, f"重构失败: {str(e)}")
        try:
            await manager.send_message({
                "type": "error",
                "stage": "reconstruction",
                "message": f"重构失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }, client_id)
        except Exception as _e:
            logger.warning(f"Failed to send error message: {_e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/graph/{dataset_name}")
async def get_graph_data(dataset_name: str):
    """Get graph visualization data"""
    graph_path = f"output/graphs/{dataset_name}_new.json"

    if not os.path.exists(graph_path):
        # Return demo data
        return {
            "nodes": [
                {"id": "node1", "name": "示例实体1", "category": "person", "value": 5, "symbolSize": 25},
                {"id": "node2", "name": "示例实体2", "category": "location", "value": 3, "symbolSize": 20},
            ],
            "links": [
                {"source": "node1", "target": "node2", "name": "位于", "value": 1}
            ],
            "categories": [
                {"name": "person", "itemStyle": {"color": "#ff6b6b"}},
                {"name": "location", "itemStyle": {"color": "#4ecdc4"}},
            ],
            "stats": {"total_nodes": 2, "total_edges": 1, "displayed_nodes": 2, "displayed_edges": 1}
        }

    return await prepare_graph_visualization(graph_path)

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    os.makedirs("data/uploaded", exist_ok=True)
    os.makedirs("output/graphs", exist_ok=True)
    os.makedirs("output/logs", exist_ok=True)
    os.makedirs("schemas", exist_ok=True)

    logger.info("🚀 Youtu-GraphRAG Unified Interface initialized")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8866)

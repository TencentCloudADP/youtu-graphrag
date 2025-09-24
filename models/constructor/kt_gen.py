import json
import re
import os
import threading
import time
from concurrent import futures
from typing import Any, Dict, List, Tuple

import nanoid
import networkx as nx
import tiktoken
import json_repair

from config import get_config
from utils import call_llm_api, graph_processor, tree_comm
from utils.logger import logger

class KTBuilder:
    def __init__(self, dataset_name, schema_path=None, mode=None, config=None):
        if config is None:
            config = get_config()
        
        self.config = config
        self.dataset_name = dataset_name
        self.schema = self.load_schema(schema_path or config.get_dataset_config(dataset_name).schema_path)
        self.graph = nx.MultiDiGraph()
        self.node_counter = 0
        self.datasets_no_chunk = config.construction.datasets_no_chunk
        self.token_len = 0
        self.lock = threading.Lock()
        self.llm_client = call_llm_api.LLMCompletionCall()
        self.all_chunks = {}
        self.doc_chunks_mapping = {}  # 新增：文档到切片的映射
        self.mode = mode or config.construction.mode

    def load_schema(self, schema_path) -> Dict[str, Any]:
        try:
            with open(schema_path) as f:
                schema = json.load(f)
                return schema
        except FileNotFoundError:
            return dict()


    def chunk_text(self, text, doc_index=None) -> Tuple[List[str], Dict[str, str]]:
        """将文档切分为多个块：
        1) 若在 datasets_no_chunk，则整文返回（兼容旧数据集）。
        2) 否则优先按 Markdown 标题分段（#### > ### > ##），
           再对过长段落按 chunk_size/overlap 做二次切分。
        3) 智能合并：如果切片过多，按相似度和长度智能合并到30个以内。
        """
        # 1) no_chunk 数据集：整文返回
        if self.dataset_name in self.datasets_no_chunk:
            base = f"{text.get('title', '')} {text.get('text', '')}".strip() if isinstance(text, dict) else str(text)
            chunks = [base]
        else:
            # 2) 标题优先切分
            full_text = f"{text.get('title', '')}\n\n{text.get('text', '')}" if isinstance(text, dict) else str(text)
            # 依据标题级别粗切
            def split_by_header(s: str, header: str) -> List[str]:
                pattern = re.compile(rf"^\s*{re.escape(header)}")
                parts: List[str] = []
                buf: List[str] = []
                for line in s.splitlines():
                    if pattern.match(line):
                        if buf:  # 如果buf不为空，先保存当前段落
                            parts.append("\n".join(buf).strip())
                        buf = [line]  # 开始新段落
                    else:
                        buf.append(line)
                if buf:
                    parts.append("\n".join(buf).strip())
                return [p for p in parts if p]

            level4 = split_by_header(full_text, "#### ")
            if level4 and len(level4) > 1:
                segments = level4
            else:
                level3 = split_by_header(full_text, "### ")
                if level3 and len(level3) > 1:
                    segments = level3
                else:
                    level2 = split_by_header(full_text, "## ")
                    segments = level2 if (level2 and len(level2) > 1) else [full_text]

            # 3) 长度二次切分
            max_len = getattr(self.config.construction, 'chunk_size', 400) or 400
            overlap = getattr(self.config.construction, 'overlap', 100) or 100
            def split_by_length(s: str, size: int, ov: int) -> List[str]:
                if len(s) <= size:
                    return [s]
                res: List[str] = []
                start = 0
                while start < len(s):
                    end = min(start + size, len(s))
                    res.append(s[start:end])
                    if end == len(s):
                        break
                    start = max(0, end - ov)
                return res

            chunks: List[str] = []
            for seg in segments:
                chunks.extend(split_by_length(seg, max_len, overlap))

        # 3) 智能合并：如果切片过多，按相似度和长度合并
        if len(chunks) > 30:
            original_count = len(chunks)
            chunks = self.smart_merge_chunks(chunks, target_count=25)
            logger.info(f"智能合并：从 {original_count} 个切片合并到 {len(chunks)} 个")

        # 4) 生成 chunk_id 映射并缓存
        chunk2id: Dict[str, str] = {}
        for chunk in chunks:
            try:
                chunk_id = nanoid.generate(size=8)
                chunk2id[chunk_id] = chunk
            except Exception as e:
                logger.warning(f"Failed to generate chunk id with nanoid: {type(e).__name__}: {e}")

        with self.lock:
            self.all_chunks.update(chunk2id)
            # 记录文档到切片的映射
            if doc_index is not None:
                self.doc_chunks_mapping[doc_index] = list(chunk2id.keys())

        return chunks, chunk2id

    def smart_merge_chunks(self, chunks: List[str], target_count: int = 25) -> List[str]:
        """智能合并切片，基于相似度和长度将切片数量减少到目标数量"""
        if len(chunks) <= target_count:
            return chunks
        
        import difflib
        from collections import defaultdict
        
        # 1) 按内容相似度分组（基于关键词）
        def extract_keywords(text: str) -> set:
            """提取文本关键词"""
            import re
            # 提取中文词汇、英文单词、数字编号
            words = re.findall(r'[\u4e00-\u9fff]+|[A-Za-z]+|[A-Z0-9-]+', text)
            return set(word.lower() for word in words if len(word) > 1)
        
        def similarity_score(text1: str, text2: str) -> float:
            """计算两个文本的相似度"""
            keywords1 = extract_keywords(text1)
            keywords2 = extract_keywords(text2)
            if not keywords1 and not keywords2:
                return 0.0
            if not keywords1 or not keywords2:
                return 0.0
            
            intersection = len(keywords1 & keywords2)
            union = len(keywords1 | keywords2)
            return intersection / union if union > 0 else 0.0
        
        # 2) 贪心合并算法
        merged_chunks = []
        remaining_chunks = chunks.copy()
        
        while remaining_chunks and len(merged_chunks) < target_count:
            # 选择第一个未处理的chunk作为种子
            seed_chunk = remaining_chunks.pop(0)
            current_group = [seed_chunk]
            
            # 查找与种子相似的chunks进行合并
            i = 0
            while i < len(remaining_chunks) and len(current_group) < 8:  # 每组最多8个chunk
                candidate = remaining_chunks[i]
                
                # 计算与种子的相似度
                similarity = similarity_score(seed_chunk, candidate)
                
                # 相似度阈值：设备类型相似 > 0.3，或长度都很短
                should_merge = (
                    similarity > 0.3 or  # 高相似度
                    (len(seed_chunk) < 200 and len(candidate) < 200 and similarity > 0.1)  # 短文本低阈值
                )
                
                if should_merge:
                    current_group.append(remaining_chunks.pop(i))
                else:
                    i += 1
            
            # 合并当前组的chunks
            if len(current_group) == 1:
                merged_chunks.append(current_group[0])
            else:
                # 智能合并：保留结构化信息
                merged_text = self._merge_similar_chunks(current_group)
                merged_chunks.append(merged_text)
        
        # 3) 如果还有剩余chunks，按长度合并
        if remaining_chunks:
            # 将剩余chunks按长度分组合并
            while remaining_chunks:
                group = []
                total_length = 0
                target_length = 1500  # 目标合并长度
                
                while remaining_chunks and total_length < target_length:
                    chunk = remaining_chunks.pop(0)
                    group.append(chunk)
                    total_length += len(chunk)
                
                if len(group) == 1:
                    merged_chunks.append(group[0])
                else:
                    merged_text = "\n\n".join(group)
                    merged_chunks.append(merged_text)
        
        logger.info(f"智能合并完成：{len(chunks)} → {len(merged_chunks)} 个切片")
        return merged_chunks
    
    def _merge_similar_chunks(self, chunks: List[str]) -> str:
        """合并相似的chunks，保持结构化格式"""
        if not chunks:
            return ""
        
        # 检查是否都是设备条目格式
        device_pattern = re.compile(r'#### 设备:.*?\((.*?)\)')
        all_devices = all(device_pattern.search(chunk) for chunk in chunks)
        
        if all_devices:
            # 设备类合并：保持标题结构
            merged_parts = []
            for chunk in chunks:
                # 移除重复的标题信息，保留核心内容
                lines = chunk.strip().split('\n')
                if len(lines) > 1:
                    merged_parts.append('\n'.join(lines))
                else:
                    merged_parts.append(chunk.strip())
            
            return '\n\n'.join(merged_parts)
        else:
            # 普通文本合并
            return '\n\n'.join(chunk.strip() for chunk in chunks)

    def _clean_text(self, text: str) -> str:
        if not text:
            return "[EMPTY_TEXT]"
        
        if self.dataset_name == "graphrag-bench":
            safe_chars = {
                *" .:,!?()-+=[]{}()\\/|_^~<>*&%$#@!;\"'`"
            }
            cleaned = "".join(
                char for char in text 
                if char.isalnum() or char.isspace() or char in safe_chars
            ).strip()
        else:
            safe_chars = {
                *" .:,!?()-+="  
            }
            cleaned = "".join(
                char for char in text 
                if char.isalnum() or char.isspace() or char in safe_chars
            ).strip()
        
        return cleaned if cleaned else "[EMPTY_AFTER_CLEANING]"
    
    def save_chunks_to_file(self):
        os.makedirs("output/chunks", exist_ok=True)
        chunk_file = f"output/chunks/{self.dataset_name}.txt"
        
        existing_data = {}
        if os.path.exists(chunk_file):
            try:
                with open(chunk_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and "\t" in line:
                            # Parse line format: "id: {id} \tChunk: {chunk text}"
                            parts = line.split("\t", 1)
                            if len(parts) == 2 and parts[0].startswith("id: ") and parts[1].startswith("Chunk: "):
                                chunk_id = parts[0][4:] 
                                chunk_text = parts[1][7:] 
                                existing_data[chunk_id] = chunk_text
            except Exception as e:
                logger.warning(f"Failed to parse existing chunks from {chunk_file}: {type(e).__name__}: {e}")
        
        all_data = {**existing_data, **self.all_chunks}
        
        with open(chunk_file, "w", encoding="utf-8") as f:
            for chunk_id, chunk_text in all_data.items():
                f.write(f"id: {chunk_id}\tChunk: {chunk_text}\n")
        
        logger.info(f"Chunk data saved to {chunk_file} ({len(all_data)} chunks)")
    
    def extract_with_llm(self, prompt: str):
        # 获取数据集特定的增强prompt
        enhanced_prompt = self._get_enhanced_prompt(prompt)
        response = self.llm_client.call_api(enhanced_prompt)
        return response
    
    def _get_enhanced_prompt(self, base_prompt: str) -> str:
        """根据数据集类型生成增强的prompt"""
        
        # 建筑资产专用的增强prompt
        if self.dataset_name == "building_assets":
            return f"""{base_prompt}

CRITICAL FORMAT REQUIREMENTS FOR BUILDING ASSETS:
- Return ONLY valid JSON format
- Must include exactly these fields: "attributes", "triples", "entity_types"
- Use ENGLISH relation names from the provided schema
- Use specific entity names (not generic types) as keys in attributes
- Do not include any explanations or markdown formatting
- Start directly with {{ and end with }}

RELATION MAPPING (Use English names):
- "属于" → "belongs_to_system"
- "位于/安装位置" → "located_in" 
- "生产/制造" → "manufactured_by"
- "型号" → "has_model"
- "安装在" → "installed_in"
- "服务" → "serves"
- "连接" → "connects_to"
- "控制" → "controls"
- "供应" → "supplies"
- "包含" → "contains"
- "部分" → "part_of"

CRITICAL: Extract hierarchical location relationships!
- If equipment is in "LOC-A-03-AHU", create: ["LOC-A-03-AHU", "part_of", "A栋三层"]
- If space has "floor: 3F", create: ["space_name", "located_in", "A栋三层"]  
- If equipment has location_id, create both: equipment→located_in→location AND location→part_of→floor
- Always extract floor-level relationships from location codes (LOC-A-03-* means A栋三层)

Building Assets Example:
{{
  "attributes": {{
    "A栋3层空调箱": ["asset_id: A-AHU-03", "model: KML-20", "install_date: 2022-05-01"],
    "LOC-A-03-AHU": ["location_id: LOC-A-03-AHU", "asset_type: 机房"],
    "A栋三层": ["floor: 3F", "building: A栋"]
  }},
  "triples": [
    ["A栋3层空调箱", "located_in", "LOC-A-03-AHU"],
    ["A栋3层空调箱", "belongs_to_system", "HVAC系统"],
    ["LOC-A-03-AHU", "part_of", "A栋三层"],
    ["A栋三层", "located_in", "A栋"],
    ["A栋三层", "located_in", "3F层"]
  ],
  "entity_types": {{
    "A栋3层空调箱": "asset",
    "LOC-A-03-AHU": "location",
    "A栋三层": "floor",
    "A栋": "building",
    "3F层": "floor",
    "HVAC系统": "system"
  }}
}}"""
        else:
            # 通用增强prompt
            return f"""{base_prompt}

CRITICAL FORMAT REQUIREMENTS:
- Return ONLY valid JSON format
- Must include exactly these fields: "attributes", "triples", "entity_types"  
- Do not include any explanations or markdown formatting
- Start directly with {{ and end with }}

Example format:
{{
  "attributes": {{
    "entity_name": ["attribute1", "attribute2"]
  }},
  "triples": [
    ["entity1", "relation", "entity2"]
  ],
  "entity_types": {{
    "entity_name": "entity_type"
  }}
}}""" 

    def token_cal(self, text: str):
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    
    def _get_construction_prompt(self, chunk: str) -> str:
        """Get the appropriate construction prompt based on dataset name and mode (agent/noagent)."""
        recommend_schema = json.dumps(self.schema, ensure_ascii=False)
        
        # Base prompt type mapping
        prompt_type_map = {
            "novel": "novel",
            "novel_eng": "novel_eng"
        }
        
        base_prompt_type = prompt_type_map.get(self.dataset_name, "general")
        
        # Add agent suffix if in agent mode
        if self.mode == "agent":
            prompt_type = f"{base_prompt_type}_agent"
        else:
            prompt_type = base_prompt_type
        
        return self.config.get_prompt_formatted("construction", prompt_type, schema=recommend_schema, chunk=chunk)
    
    def _get_relation_mapping(self) -> dict:
        """获取中英文关系词映射表"""
        return {
            # 中文到英文的关系映射
            "属于": "belongs_to_system",
            "位于": "located_in",
            "安装位置": "located_in",
            "安装在": "located_in",
            "生产": "manufactured_by",
            "制造": "manufactured_by",
            "生产公司": "manufactured_by",
            "制造商": "manufactured_by",
            "型号": "has_model",
            "模型": "has_model",
            "服务": "serves",
            "连接": "connects_to",
            "控制": "controls",
            "供应": "supplies",
            "包含": "contains",
            "部分": "part_of",
            "组成": "part_of",
        }
    
    def _normalize_relations(self, triples: list) -> list:
        """标准化关系词，将中文关系映射为英文schema关系"""
        if not triples:
            return triples
            
        relation_mapping = self._get_relation_mapping()
        normalized_triples = []
        
        for triple in triples:
            if len(triple) >= 3:
                subj, pred, obj = triple[0], triple[1], triple[2]
                # 映射中文关系词到英文
                normalized_pred = relation_mapping.get(pred, pred)
                normalized_triples.append([subj, normalized_pred, obj])
            else:
                normalized_triples.append(triple)
                
        return normalized_triples
    
    def _add_hierarchical_relations(self, parsed_result: dict) -> dict:
        """为建筑资产数据补充层级关系"""
        if not parsed_result or "triples" not in parsed_result:
            return parsed_result
            
        additional_triples = []
        existing_triples = set()
        
        # 记录现有三元组，避免重复
        for triple in parsed_result["triples"]:
            if len(triple) >= 3:
                existing_triples.add((triple[0], triple[1], triple[2]))
        
        # 从属性中推导层级关系
        attributes = parsed_result.get("attributes", {})
        for entity, attrs in attributes.items():
            if not attrs:
                continue
                
            floor_info = None
            building_info = None
            
            # 解析属性
            for attr in attrs:
                if isinstance(attr, str):
                    if attr.startswith("floor:"):
                        floor_info = attr.split(":", 1)[1].strip()
                    elif attr.startswith("building:"):
                        building_info = attr.split(":", 1)[1].strip()
            
            # 补充楼层关系
            if floor_info and building_info:
                floor_name = f"{building_info}{self._normalize_floor_name(floor_info)}"
                
                # entity → located_in → floor
                triple1 = (entity, "located_in", floor_name)
                if triple1 not in existing_triples:
                    additional_triples.append([triple1[0], triple1[1], triple1[2]])
                    existing_triples.add(triple1)
        
        # 从位置编码推导层级关系 (LOC-A-03-* → A栋三层)
        for triple in parsed_result["triples"]:
            if len(triple) >= 3 and triple[1] == "located_in":
                location = triple[2]
                if isinstance(location, str) and location.startswith("LOC-"):
                    floor_name = self._extract_floor_from_location(location)
                    if floor_name:
                        # location → part_of → floor
                        triple_new = (location, "part_of", floor_name)
                        if triple_new not in existing_triples:
                            additional_triples.append([triple_new[0], triple_new[1], triple_new[2]])
                            existing_triples.add(triple_new)
        
        # 添加新的三元组
        if additional_triples:
            parsed_result["triples"].extend(additional_triples)
            logger.info(f"Added {len(additional_triples)} hierarchical relations")
        
        return parsed_result
    
    def _normalize_floor_name(self, floor_info: str) -> str:
        """标准化楼层名称"""
        floor_info = floor_info.strip().upper()
        if floor_info in ["3F", "3层", "三层"]:
            return "三层"
        elif floor_info in ["2F", "2层", "二层"]:
            return "二层"
        elif floor_info in ["1F", "1层", "一层"]:
            return "一层"
        elif floor_info in ["B1", "B1层", "地下一层"]:
            return "地下一层"
        else:
            return floor_info.replace("F", "层")
    
    def _extract_floor_from_location(self, location: str) -> str:
        """从位置编码提取楼层信息"""
        # LOC-A-03-* → A栋三层
        import re
        match = re.match(r"LOC-([AB])-(\d+)-", location)
        if match:
            building = f"{match.group(1)}栋"
            floor_num = match.group(2)
            
            # 数字转中文
            floor_map = {"01": "一", "02": "二", "03": "三", "04": "四", "05": "五", 
                        "06": "六", "07": "七", "08": "八", "09": "九", "10": "十"}
            floor_chinese = floor_map.get(floor_num, floor_num)
            return f"{building}{floor_chinese}层"
        return None

    def _validate_and_parse_llm_response(self, prompt: str, llm_response: str) -> dict:
        """Validate and parse LLM response, returning None if invalid."""
        if llm_response is None:
            return None
            
        try:
            self.token_len += self.token_cal(prompt + llm_response)
            
            # 如果响应已经是字符串，尝试解析
            if isinstance(llm_response, str):
                parsed_result = json_repair.loads(llm_response)
            else:
                parsed_result = llm_response
            
            # 确保返回的是字典格式
            if isinstance(parsed_result, list):
                logger.warning(f"LLM returned a list instead of dict, trying to extract first dict element")
                # 如果是列表，尝试找到第一个字典元素
                for item in parsed_result:
                    if isinstance(item, dict):
                        return item
                logger.warning(f"No dict found in list: {parsed_result}")
                return None
            elif isinstance(parsed_result, str):
                logger.warning(f"LLM returned raw string, attempting to extract JSON: {parsed_result[:200]}...")
                # 尝试从字符串中提取JSON
                json_match = re.search(r'\{.*\}', parsed_result, re.DOTALL)
                if json_match:
                    try:
                        extracted_json = json_repair.loads(json_match.group())
                        if isinstance(extracted_json, dict):
                            return extracted_json
                    except Exception as e:
                        logger.warning(f"Failed to extract JSON from string: {e}")
                # 如果无法提取JSON，返回空结果让系统跳过
                return {"attributes": {}, "triples": [], "entity_types": {}}
            elif not isinstance(parsed_result, dict):
                logger.warning(f"LLM returned unexpected type: {type(parsed_result)}, value: {parsed_result}")
                return None
                
            # 标准化关系词
            if "triples" in parsed_result:
                parsed_result["triples"] = self._normalize_relations(parsed_result["triples"])
                
            # 补充层级关系
            if self.dataset_name == "building_assets":
                parsed_result = self._add_hierarchical_relations(parsed_result)
                
            return parsed_result
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}, response: {llm_response[:200] if llm_response else 'None'}...")
            # 返回空结果让系统继续处理其他切片
            return {"attributes": {}, "triples": [], "entity_types": {}}
    
    def _find_or_create_entity(self, entity_name: str, chunk_id: int, nodes_to_add: list, entity_type: str = None) -> str:
        """Find existing entity or create a new one, returning the entity node ID."""
        with self.lock:
            entity_node_id = next(
                (
                    n
                    for n, d in self.graph.nodes(data=True)
                    if d.get("label") == "entity" and d["properties"]["name"] == entity_name
                ),
                None,
            )
            
            if not entity_node_id:
                entity_node_id = f"entity_{self.node_counter}"
                properties = {"name": entity_name, "chunk id": chunk_id}
                if entity_type:
                    properties["schema_type"] = entity_type
                
                nodes_to_add.append((
                    entity_node_id,
                    {
                        "label": "entity", 
                        "properties": properties, 
                        "level": 2
                    }
                ))
                self.node_counter += 1
                
        return entity_node_id
    
    def _validate_triple_format(self, triple: list) -> tuple:
        """Validate and normalize triple format, returning (subject, predicate, object) or None."""
        try:
            if len(triple) > 3:
                triple = triple[:3]
            elif len(triple) < 3:
                return None
            
            return tuple(triple)
        except Exception as e:
            return None
    
    def _process_attributes(self, extracted_attr: dict, chunk_id: int, entity_types: dict = None) -> tuple[list, list]:
        """Process extracted attributes and return nodes and edges to add."""
        nodes_to_add = []
        edges_to_add = []
        
        if not extracted_attr:
            return nodes_to_add, edges_to_add
        
        for entity, attributes in extracted_attr.items():
            # 防止 attributes 为 None 的情况
            if attributes is None:
                logger.warning(f"Attributes for entity '{entity}' is None, skipping")
                continue
            
            # 确保 attributes 是可迭代的
            if not hasattr(attributes, '__iter__') or isinstance(attributes, str):
                logger.warning(f"Attributes for entity '{entity}' is not iterable: {type(attributes)}, converting to list")
                attributes = [str(attributes)]
                
            for attr in attributes:
                # Create attribute node
                attr_node_id = f"attr_{self.node_counter}"
                nodes_to_add.append((
                    attr_node_id,
                    {
                        "label": "attribute",
                        "properties": {"name": attr, "chunk id": chunk_id},
                        "level": 1,
                    }
                ))
                self.node_counter += 1

                entity_type = entity_types.get(entity) if entity_types else None
                entity_node_id = self._find_or_create_entity(entity, chunk_id, nodes_to_add, entity_type)
                edges_to_add.append((entity_node_id, attr_node_id, "has_attribute"))
        
        return nodes_to_add, edges_to_add
    
    def _process_triples(self, extracted_triples: list, chunk_id: int, entity_types: dict = None) -> tuple[list, list]:
        """Process extracted triples and return nodes and edges to add."""
        nodes_to_add = []
        edges_to_add = []
        
        if not extracted_triples:
            return nodes_to_add, edges_to_add
        
        for triple in extracted_triples:
            validated_triple = self._validate_triple_format(triple)
            if not validated_triple:
                continue
                
            subj, pred, obj = validated_triple
            
            subj_type = entity_types.get(subj) if entity_types else None
            obj_type = entity_types.get(obj) if entity_types else None
            
            subj_node_id = self._find_or_create_entity(subj, chunk_id, nodes_to_add, subj_type)
            obj_node_id = self._find_or_create_entity(obj, chunk_id, nodes_to_add, obj_type)
            
            edges_to_add.append((subj_node_id, obj_node_id, pred))
        
        return nodes_to_add, edges_to_add

    def process_level1_level2(self, chunk: str, id: int):
        """Process attributes (level 1) and triples (level 2) with optimized structure."""
        prompt = self._get_construction_prompt(chunk)
        llm_response = self.extract_with_llm(prompt)
        
        # Validate and parse response
        parsed_response = self._validate_and_parse_llm_response(prompt, llm_response)
        if not parsed_response:
            return
        
        extracted_attr = parsed_response.get("attributes", {})
        extracted_triples = parsed_response.get("triples", [])
        entity_types = parsed_response.get("entity_types", {})
        
        # Process attributes and triples
        attr_nodes, attr_edges = self._process_attributes(extracted_attr, id, entity_types)
        triple_nodes, triple_edges = self._process_triples(extracted_triples, id, entity_types)
        
        all_nodes = attr_nodes + triple_nodes
        all_edges = attr_edges + triple_edges
        
        with self.lock:
            for node_id, node_data in all_nodes:
                self.graph.add_node(node_id, **node_data)
            
            for u, v, relation in all_edges:
                self.graph.add_edge(u, v, relation=relation)

    def _find_or_create_entity_direct(self, entity_name: str, chunk_id: int, entity_type: str = None) -> str:
        """Find existing entity or create a new one directly in graph (for agent mode)."""
        entity_node_id = next(
            (
                n
                for n, d in self.graph.nodes(data=True)
                if d.get("label") == "entity" and d["properties"]["name"] == entity_name
            ),
            None,
        )
        
        if not entity_node_id:
            entity_node_id = f"entity_{self.node_counter}"
            properties = {"name": entity_name, "chunk id": chunk_id}
            if entity_type:
                properties["schema_type"] = entity_type
                
            self.graph.add_node(
                entity_node_id, 
                label="entity", 
                properties=properties, 
                level=2
            )
            self.node_counter += 1
            
        return entity_node_id
    
    def _process_attributes_agent(self, extracted_attr: dict, chunk_id: int, entity_types: dict = None):
        """Process extracted attributes in agent mode (direct graph operations)."""
        if not extracted_attr:
            return
            
        for entity, attributes in extracted_attr.items():
            # 防止 attributes 为 None 的情况
            if attributes is None:
                logger.warning(f"Attributes for entity '{entity}' is None, skipping")
                continue
            
            # 确保 attributes 是可迭代的
            if not hasattr(attributes, '__iter__') or isinstance(attributes, str):
                logger.warning(f"Attributes for entity '{entity}' is not iterable: {type(attributes)}, converting to list")
                attributes = [str(attributes)]
            for attr in attributes:
                # Create attribute node
                attr_node_id = f"attr_{self.node_counter}"
                self.graph.add_node(
                    attr_node_id,
                    label="attribute",
                    properties={
                        "name": attr,
                        "chunk id": chunk_id
                    },
                    level=1,
                )
                self.node_counter += 1

                entity_type = entity_types.get(entity) if entity_types else None
                entity_node_id = self._find_or_create_entity_direct(entity, chunk_id, entity_type)
                self.graph.add_edge(entity_node_id, attr_node_id, relation="has_attribute")
    
    def _process_triples_agent(self, extracted_triples: list, chunk_id: int, entity_types: dict = None):
        """Process extracted triples in agent mode (direct graph operations)."""
        if not extracted_triples:
            return
            
        for triple in extracted_triples:
            validated_triple = self._validate_triple_format(triple)
            if not validated_triple:
                continue
                
            subj, pred, obj = validated_triple
            
            subj_type = entity_types.get(subj) if entity_types else None
            obj_type = entity_types.get(obj) if entity_types else None
            
            # Find or create subject and object entities
            subj_node_id = self._find_or_create_entity_direct(subj, chunk_id, subj_type)
            obj_node_id = self._find_or_create_entity_direct(obj, chunk_id, obj_type)
            
            self.graph.add_edge(subj_node_id, obj_node_id, relation=pred)

    def process_level1_level2_agent(self, chunk: str, id: int):
        """Process attributes (level 1) and triples (level 2) with agent mechanism for schema evolution.
        
        This method enables dynamic schema evolution by allowing the LLM to suggest new entity types,
        relation types, and attribute types that can be added to the existing schema.
        """
        prompt = self._get_construction_prompt(chunk)
        llm_response = self.extract_with_llm(prompt)
        
        # Validate and parse response (reuse helper method)
        parsed_response = self._validate_and_parse_llm_response(prompt, llm_response)
        if not parsed_response:
            return

        # Handle schema evolution
        new_schema_types = parsed_response.get("new_schema_types", {})
        if new_schema_types:
            self._update_schema_with_new_types(new_schema_types)
        
        extracted_attr = parsed_response.get("attributes", {})
        extracted_triples = parsed_response.get("triples", [])
        entity_types = parsed_response.get("entity_types", {})
        
        with self.lock:
            self._process_attributes_agent(extracted_attr, id, entity_types)
            self._process_triples_agent(extracted_triples, id, entity_types)

    def _update_schema_with_new_types(self, new_schema_types: Dict[str, List[str]]):
        """Update the schema file with new types discovered by the agent.
        
        This method processes schema evolution suggestions from the LLM and updates
        the corresponding schema file with new node types, relations, and attributes.
        Only adds types that don't already exist in the current schema.
        
        Args:
            new_schema_types: Dictionary containing 'nodes', 'relations', and 'attributes' lists
        """
        try:
            schema_paths = {
                "hotpot": "schemas/hotpot.json",
                "2wiki": "schemas/2wiki.json", 
                "musique": "schemas/musique.json",
                "novel": "schemas/novels_chs.json",
                "graphrag-bench": "schemas/graphrag-bench.json"
            }
            
            schema_path = schema_paths.get(self.dataset_name)
            if not schema_path:
                return
                
            with open(schema_path, 'r', encoding='utf-8') as f:
                current_schema = json.load(f)
            
            updated = False
            
            if "nodes" in new_schema_types:
                for new_node in new_schema_types["nodes"]:
                    if new_node not in current_schema.get("Nodes", []):
                        current_schema.setdefault("Nodes", []).append(new_node)
                        updated = True
            
            if "relations" in new_schema_types:
                for new_relation in new_schema_types["relations"]:
                    if new_relation not in current_schema.get("Relations", []):
                        current_schema.setdefault("Relations", []).append(new_relation)
                        updated = True

            if "attributes" in new_schema_types:
                for new_attribute in new_schema_types["attributes"]:
                    if new_attribute not in current_schema.get("Attributes", []):
                        current_schema.setdefault("Attributes", []).append(new_attribute)
                        updated = True
            
            # Save updated schema back to file
            if updated:
                with open(schema_path, 'w', encoding='utf-8') as f:
                    json.dump(current_schema, f, ensure_ascii=False, indent=2)
                
                # Update the in-memory schema
                self.schema = current_schema
                
        except Exception as e:
            logger.error(f"Failed to update schema for dataset '{self.dataset_name}': {type(e).__name__}: {e}")

    def process_level4(self):
        """Process communities using Tree-Comm algorithm"""
        level2_nodes = [n for n, d in self.graph.nodes(data=True) if d['level'] == 2]
        start_comm = time.time()
        _tree_comm = tree_comm.FastTreeComm(
            self.graph, 
            embedding_model=self.config.tree_comm.embedding_model,
            struct_weight=self.config.tree_comm.struct_weight,
        )
        comm_to_nodes = _tree_comm.detect_communities(level2_nodes)

        # create super nodes (level 4 communities)
        _tree_comm.create_super_nodes_with_keywords(comm_to_nodes, level=4)
        # _tree_comm.add_keywords_to_level3(comm_to_nodes)
        # connect keywords to communities (optional)
        # self._connect_keywords_to_communities()
        end_comm = time.time()
        logger.info(f"Community Indexing Time: {end_comm - start_comm}s")
    
    def _connect_keywords_to_communities(self):
        """Connect relevant keywords to communities"""
        # comm_names = [self.graph.nodes[n]['properties']['name'] for n, d in self.graph.nodes(data=True) if d['level'] == 4]
        comm_nodes = [n for n, d in self.graph.nodes(data=True) if d['level'] == 4]
        kw_nodes = [n for n, d in self.graph.nodes(data=True) if d['label'] == 'keyword']
        with self.lock:
            for comm in comm_nodes:
                comm_name = self.graph.nodes[comm]['properties']['name'].lower()
                for kw in kw_nodes:
                    kw_name = self.graph.nodes[kw]['properties']['name'].lower()
                    if kw_name in comm_name or comm_name in kw_name:
                        self.graph.add_edge(kw, comm, relation="describes")

    def process_document(self, doc: Dict[str, Any], doc_index: int = None) -> List[Dict[str, Any]]:
        """Process a single document and return its results."""
        try:
            if not doc:
                raise ValueError("Document is empty or None")
            
            # 使用文档索引来找到对应的切片
            doc_chunks = []
            
            if doc_index is not None and doc_index in self.doc_chunks_mapping:
                # 通过文档索引获取切片ID列表
                chunk_ids = self.doc_chunks_mapping[doc_index]
                for chunk_id in chunk_ids:
                    if chunk_id in self.all_chunks:
                        chunk_content = self.all_chunks[chunk_id]
                        doc_chunks.append((chunk_content, chunk_id))
            else:
                # 兜底：使用原来的匹配逻辑（基于文档标题）
                doc_title = doc.get('title', '')
                for chunk_id, chunk_content in self.all_chunks.items():
                    if doc_title in chunk_content:
                        doc_chunks.append((chunk_content, chunk_id))
            
            if not doc_chunks:
                raise ValueError(f"No chunks found for document at index {doc_index}: {doc.get('title', 'Unknown')}")
            
            logger.info(f"Processing document {doc_index} with {len(doc_chunks)} chunks")
            
            for chunk_content, chunk_id in doc_chunks:
                # Route to appropriate processing method based on mode
                if self.mode == "agent":
                    # Agent mode: includes schema evolution capabilities
                    self.process_level1_level2_agent(chunk_content, chunk_id)
                else:
                    # NoAgent mode: standard processing without schema evolution
                    self.process_level1_level2(chunk_content, chunk_id)
                
        except Exception as e:
            error_msg = f"Error processing document {doc_index}: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    def process_all_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Process all documents with high concurrency and pass results to process_level4."""

        max_workers = min(self.config.construction.max_workers, (os.cpu_count() or 1) + 4)
        start_construct = time.time()
        total_docs = len(documents)
        
        logger.info(f"Starting processing {total_docs} documents with {max_workers} workers...")
        
        # Step 1: 先完成所有文档的切片，立即保存切片文件
        logger.info("🔪 Step 1: Chunking all documents...")
        total_chunks = 0
        for i, doc in enumerate(documents):
            try:
                chunks, chunk2id = self.chunk_text(doc, doc_index=i)
                total_chunks += len(chunks)
                logger.info(f"  Document {i+1}/{total_docs}: {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"  Failed to chunk document {i+1}: {e}")
        
        # 立即保存切片文件
        logger.info(f"💾 Saving {total_chunks} chunks to file...")
        self.save_chunks_to_file()
        logger.info("✅ Chunks saved! You can check intermediate results now.")
        self._chunks_saved = True
        
        # Step 2: 开始LLM处理
        logger.info("🧠 Step 2: Starting LLM processing for graph construction...")

        all_futures = []
        processed_count = 0
        failed_count = 0
        
        try:
            with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all documents for processing and store futures
                all_futures = [executor.submit(self.process_document, doc, doc_index=i) for i, doc in enumerate(documents)]

                for i, future in enumerate(futures.as_completed(all_futures, timeout=300)):  # 5分钟超时
                    try:
                        future.result(timeout=180)  # 单个文档3分钟超时
                        processed_count += 1
                        
                        # 更频繁的进度报告
                        if processed_count % 1 == 0 or processed_count == total_docs:
                            elapsed_time = time.time() - start_construct
                            avg_time_per_doc = elapsed_time / processed_count if processed_count > 0 else 0
                            remaining_docs = total_docs - processed_count
                            estimated_remaining_time = remaining_docs * avg_time_per_doc
                            
                            logger.info(f"Progress: {processed_count}/{total_docs} documents processed "
                                  f"({processed_count/total_docs*100:.1f}%) "
                                  f"[{failed_count} failed] "
                                  f"Avg: {avg_time_per_doc:.1f}s/doc "
                                  f"ETA: {estimated_remaining_time/60:.1f} minutes")
                        
                    except futures.TimeoutError:
                        logger.error(f"Document processing timed out after 3 minutes")
                        failed_count += 1
                        
                    except Exception as e:
                        failed_count += 1

        except Exception as e:
            return

        end_construct = time.time()
        logger.info(f"Construction Time: {end_construct - start_construct}s")
        logger.info(f"Successfully processed: {processed_count}/{total_docs} documents")
        logger.info(f"Failed: {failed_count} documents")
        
        logger.info(f"🚀🚀🚀🚀 {'Processing Level 3 and 4':^20} 🚀🚀🚀🚀")
        logger.info(f"{'➖' * 20}")
        self.triple_deduplicate()
        self.process_level4()

       

    def triple_deduplicate(self):
        """deduplicate triples in lv1 and lv2"""
        new_graph = nx.MultiDiGraph()

        for node, node_data in self.graph.nodes(data=True):
            new_graph.add_node(node, **node_data)

        seen_triples = set()
        for u, v, key, data in self.graph.edges(keys=True, data=True):
            relation = data.get('relation') 
            if (u, v, relation) not in seen_triples:
                seen_triples.add((u, v, relation))
                new_graph.add_edge(u, v, **data)
        self.graph = new_graph

    def format_output(self) -> List[Dict[str, Any]]:
        """convert graph to specified output format"""
        output = []

        for u, v, data in self.graph.edges(data=True):
            u_data = self.graph.nodes[u]
            v_data = self.graph.nodes[v]

            relationship = {
                "start_node": {
                    "label": u_data["label"],
                    "properties": u_data["properties"],
                },
                "relation": data["relation"],
                "end_node": {
                    "label": v_data["label"],
                    "properties": v_data["properties"],
                },
            }
            output.append(relationship)

        return output
    
    def save_graphml(self, output_path: str):
        graph_processor.save_graph(self.graph, output_path)
    
    def build_knowledge_graph(self, corpus):
        logger.info(f"========{'Start Building':^20}========")
        logger.info(f"{'➖' * 30}")
        
        with open(corpus, 'r', encoding='utf-8') as f:
            documents = json_repair.load(f)
        
        # 设置标志，在处理第一个文档后保存切片文件
        self._chunks_saved = False
        
        self.process_all_documents(documents)
        
        logger.info(f"All Process finished, token cost: {self.token_len}")
        
        # 确保切片文件已保存（兜底保护）
        if not self._chunks_saved:
            self.save_chunks_to_file()
        
        output = self.format_output()
        
        json_output_path = f"output/graphs/{self.dataset_name}_new.json"
        os.makedirs("output/graphs", exist_ok=True)
        with open(json_output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        logger.info(f"Graph saved to {json_output_path}")
        
        return output

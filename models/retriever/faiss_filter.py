import json
import os
import time
import hashlib
from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Set, Tuple

import faiss
import networkx as nx
import numpy as np
import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer

from utils.logger import logger

class DualFAISSRetriever:
    def __init__(self, dataset, graph: nx.MultiDiGraph, model_name: str = "all-MiniLM-L6-v2", cache_dir: str = "retriever/faiss_cache_new", device: str = None):
        """
        :param graph: nx graph
        :param model_name: embedding model
        :param cache_dir: cache directory for FAISS indices
        """
        self.graph = graph
        self.model = SentenceTransformer(model_name)
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.dataset = dataset
        # 使用 ASCII-safe 目录名避免 Windows + FAISS 处理中文路径失败
        safe_suffix = hashlib.md5(str(dataset).encode("utf-8")).hexdigest()[:8]
        self.dataset_cache_dir = os.path.join(self.cache_dir, safe_suffix)
        os.makedirs(self.dataset_cache_dir, exist_ok=True)
        
        self.triple_index = None
        self.comm_index = None
        
        if device is not None:
            if device == "cuda" and not torch.cuda.is_available():
                logger.warning("Warning: CUDA requested but not available in DualFAISSRetriever, falling back to CPU")
                self.device = torch.device("cpu")
            else:
                self.device = torch.device(device)
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        logger.info(f"DualFAISSRetriever using device: {self.device}")
        
        # Add attributes for storing embeddings and maps
        self.node_embeddings = None
        self.relation_embeddings = None
        self.node_id_to_embedding = {}
        self.relation_to_embedding = {}
        
        # Initialize map attributes to prevent AttributeError
        self.node_map = {}
        self.relation_map = {}
        self.triple_map = {}
        self.comm_map = {}
        
        # FAISS caching and optimization
        self.faiss_search_cache = {}  
        self.index_loaded = False     
        self.gpu_resources = None     
        
        self.node_embedding_cache = {}  # 缓存已编码的节点嵌入
        
        # Get model output dimension
        self.model_dim = self.model.get_sentence_embedding_dimension()
        self.dim_transform = None
        if self.model_dim != 384:  # If model output dimension is not 384
            self.dim_transform = torch.nn.Linear(self.model_dim, 384)
            if self.device.type == "cuda" and torch.cuda.is_available():
                self.dim_transform = self.dim_transform.to(self.device)
            else:
                self.dim_transform = self.dim_transform.to("cpu")

        self.name_to_id = {}
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            if 'properties' in node_data and isinstance(node_data['properties'], dict):
                name = node_data['properties'].get('name', '')
                if name:
                    # Convert list or other types to string
                    if isinstance(name, list):
                        name = ", ".join(str(item) for item in name)
                    elif not isinstance(name, str):
                        name = str(name)
                    self.name_to_id[name] = node_id
            else:
                name = node_data.get('name', '')
                if name:
                    # Convert list or other types to string
                    if isinstance(name, list):
                        name = ", ".join(str(item) for item in name)
                    elif not isinstance(name, str):
                        name = str(name)
                    self.name_to_id[name] = node_id
        
        
    def _preload_faiss_indices(self):
        if self.index_loaded:
            return
        
        # Initialize GPU resources if available
        if torch.cuda.is_available():
            try:
                self.gpu_resources = faiss.StandardGpuResources()
            except Exception as e:
                self.gpu_resources = None
        
        # Preload indices to GPU if possible
        if self.gpu_resources and self.node_index:
            try:
                self.node_index = faiss.index_cpu_to_gpu(self.gpu_resources, 0, self.node_index)
                logger.info("Node index moved to GPU")
            except Exception as e:
                logger.warning(f"Warning: Failed to move node index to GPU: {e}")
        
        if self.gpu_resources and self.relation_index:
            try:
                self.relation_index = faiss.index_cpu_to_gpu(self.gpu_resources, 0, self.relation_index)
                logger.info("Relation index moved to GPU")
            except Exception as e:
                logger.warning(f"Warning: Failed to move relation index to GPU: {e}")
        
        if self.gpu_resources and self.triple_index:
            try:
                self.triple_index = faiss.index_cpu_to_gpu(self.gpu_resources, 0, self.triple_index)
                logger.info("Triple index moved to GPU")
            except Exception as e:
                logger.warning(f"Warning: Failed to move triple index to GPU: {e}")
        
        if self.gpu_resources and self.comm_index:
            try:
                self.comm_index = faiss.index_cpu_to_gpu(self.gpu_resources, 0, self.comm_index)
                logger.info("Community index moved to GPU")
            except Exception as e:
                logger.warning(f"Warning: Failed to move community index to GPU: {e}")
        
        self.index_loaded = True
        logger.info("FAISS indices preloaded successfully")

    def _cached_faiss_search(self, index, query_embed, top_k: int, cache_key: str):
        if cache_key in self.faiss_search_cache:
            return self.faiss_search_cache[cache_key]
        

        query_embed_np = query_embed.cpu().detach().numpy().reshape(1, -1)
        D, I = index.search(query_embed_np, top_k)
        

        result = (D, I)
        self.faiss_search_cache[cache_key] = result

        if len(self.faiss_search_cache) > 1000:

            oldest_key = next(iter(self.faiss_search_cache))
            del self.faiss_search_cache[oldest_key]
        
        return result

    def dual_path_retrieval(self, query_emb: str, top_k: int = 10) -> Dict:
        """
        Complete dual-path retrieval process
        :return: {
            "triple_nodes": entities and their neighbors found through triples,
            "comm_nodes": nodes found through communities,
            "scores": node relevance scores,
            "scored_triples": scored triples from triple retrieval
        }
        """
        
        start_time = time.time()
        scored_triples = self.retrieve_via_triples(query_emb, top_k)
        
        triple_nodes = set()
        for h, r, t, score in scored_triples:
            triple_nodes.add(h)
            triple_nodes.add(t)
        
        # Filter out nodes that don't exist in the graph
        triple_nodes = [node for node in triple_nodes if node in self.graph.nodes]
                    
        end_time = time.time()
        logger.info(f"Time taken to get triple nodes: {end_time - start_time} seconds")
        
        start_time = time.time()
        comm_nodes = self.retrieve_via_communities(query_emb, top_k)
        # Filter out nodes that don't exist in the graph
        comm_nodes = [node for node in comm_nodes if node in self.graph.nodes]
                            
        end_time = time.time()

        merged_nodes = list(set(triple_nodes + comm_nodes))
        start_time = time.time()

        node_scores = self._calculate_node_scores_optimized(query_emb, merged_nodes)
        end_time = time.time()
        logger.info(f"Time taken to calculate node scores: {end_time - start_time} seconds")
        
        result = {
            "triple_nodes": triple_nodes,
            "comm_nodes": comm_nodes,
            "scores": node_scores,
            "scored_triples": scored_triples
        }
        
        return result

    def _collect_neighbor_triples(self, node: str) -> List[Tuple[str, str, str]]:
        """Collect all triples involving 3-hop neighbors of a given node."""
        if node not in self.node_id_to_embedding:
            return []
            
        neighbor_triples = []
        neighbors = self._get_3hop_neighbors(node)
        
        for neighbor in neighbors:
            # Get outgoing edges from neighbor
            for _, target, edge_data in self.graph.out_edges(neighbor, data=True):
                if 'relation' in edge_data and target in self.node_id_to_embedding:
                    neighbor_triples.append((neighbor, edge_data['relation'], target))
            
            # Get incoming edges to neighbor
            for source, _, edge_data in self.graph.in_edges(neighbor, data=True):
                if 'relation' in edge_data and source in self.node_id_to_embedding:
                    neighbor_triples.append((source, edge_data['relation'], neighbor))
                    
        return neighbor_triples
    
    def _process_triple_index(self, idx: int) -> List[Tuple[str, str, str]]:
        """Process a single triple index and return all related triples."""
        try:
            h, r, t = self.triple_map[str(idx)]
            triples = [(h, r, t)]  # Original triple
            
            # Add neighbor triples for both head and tail
            triples.extend(self._collect_neighbor_triples(h))
            triples.extend(self._collect_neighbor_triples(t))
            
            return triples
            
        except (KeyError, ValueError) as e:
            logger.error(f"Warning: Error processing triple index {idx}: {str(e)}")
            return []
    
    def _deduplicate_triples(self, triples: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
        """Remove duplicate triples while preserving order."""
        unique_triples = []
        seen = set()
        
        for triple in triples:
            if triple not in seen:
                unique_triples.append(triple)
                seen.add(triple)
                
        return unique_triples

    def retrieve_via_triples(self, query_embed, top_k: int = 5) -> List[Tuple[str, str, str, float]]:
        """
        Path 1: Retrieve triples and their 3-hop neighbors through triples.
        Returns scored triples that have relevance scores above threshold.
        """
        if not self.triple_index:
            raise ValueError("Please build triple index first!")
        
        # Ensure query_embed is on the correct device and apply transformations
        if isinstance(query_embed, torch.Tensor):
            query_embed = query_embed.to(self.device)
        else:
            query_embed = torch.FloatTensor(query_embed).to(self.device)
            
        query_embed = self.transform_vector(query_embed)
        
        # Create cache key and perform search
        cache_key = f"triple_search_{hash(query_embed.cpu().numpy().tobytes())}_{top_k}"
        D, I = self._cached_faiss_search(self.triple_index, query_embed, top_k, cache_key)
        
        # Collect all triples from matched indices using helper methods
        all_triples = []
        for idx in I[0]:
            all_triples.extend(self._process_triple_index(idx))
        
        # Remove duplicates
        unique_triples = self._deduplicate_triples(all_triples)
        
        logger.info(f"Calling _calculate_triple_relevance_scores with {len(unique_triples)} unique triples")
        scored_triples = self._calculate_triple_relevance_scores(query_embed, unique_triples, threshold=0.1, top_k=top_k)

        logger.info(f"_calculate_triple_relevance_scores returned {len(scored_triples)} scored triples")
        return scored_triples

    def retrieve_via_communities(self, query_embed, top_k: int = 3) -> List[str]:
        """
        Path 2: Retrieve nodes through communities.
        Returns only nodes that have a valid, cached embedding.
        """
        if not self.comm_index:
            raise ValueError("Please build community index first!")
        
        # Ensure query_embed is on the correct device before transformation
        if isinstance(query_embed, torch.Tensor):
            query_embed = query_embed.to(self.device)
        else:
            query_embed = torch.FloatTensor(query_embed).to(self.device)
            
        # Apply dimension transformation
        query_embed = self.transform_vector(query_embed)
        
        # Create cache key for this search
        cache_key = f"comm_search_{hash(query_embed.cpu().numpy().tobytes())}_{top_k}"
        
        # Use cached search if available
        D, I = self._cached_faiss_search(self.comm_index, query_embed, top_k, cache_key)

        nodes = []
        for idx in I[0]:
            if idx >= 0:  # Valid index
                try:
                    community = self.comm_map[str(idx)]
                    # Get all nodes in this community
                    community_nodes = self._get_community_nodes(community)
                    nodes.extend(community_nodes)
                except (KeyError, ValueError) as e:
                    logger.error(f"Warning: Error processing community index {idx}: {str(e)}")
                    continue
        
        # Remove duplicates while preserving order
        unique_nodes = []
        seen = set()
        for node in nodes:
            if node not in seen and node in self.node_id_to_embedding:
                unique_nodes.append(node)
                seen.add(node)
        
        return unique_nodes

    def _get_3hop_neighbors(self, center: str) -> Set[str]:
        """
        Optimized 3-hop neighbor search using BFS with caching
        """
        # Check if center node exists in both embedding map and graph
        if center not in self.node_id_to_embedding:
            logger.warning(f"Warning: Node {center} not found in embedding map")
            return set()
        
        if center not in self.graph.nodes:
            logger.warning(f"Warning: Node {center} not found in graph")
            return set()
        
        # Check cache first
        cache_key = f"3hop_{center}"
        if hasattr(self, '_3hop_cache') and cache_key in self._3hop_cache:
            return self._3hop_cache[cache_key]
        
        neighbors = {center}
        visited = {center}
        
        try:
            # Use BFS for more efficient traversal
            queue = [(center, 0)]  # (node, depth)
            
            while queue:
                current_node, depth = queue.pop(0)
                
                if depth >= 3:
                    continue
                
                # Check if current node exists in graph before getting neighbors
                if current_node not in self.graph.nodes:
                    logger.warning(f"Current node {current_node} not found in graph during BFS")
                    continue
                    
                for neighbor in self.graph.neighbors(current_node):
                    # Only include neighbors that exist in both graph and embedding map
                    if neighbor in self.node_id_to_embedding and neighbor not in visited:
                        visited.add(neighbor)
                        neighbors.add(neighbor)
                        if depth < 2:  # Only add to queue if we can go deeper
                            queue.append((neighbor, depth + 1))
                    elif neighbor not in self.node_id_to_embedding:
                        logger.warning(f"Warning: Neighbor {neighbor} of {current_node} not found in embedding map")
                            
        except Exception as e:
            logger.error(f"Error getting neighbors for node {center}: {str(e)}")
        
        # Cache the result
        if not hasattr(self, '_3hop_cache'):
            self._3hop_cache = {}
        self._3hop_cache[cache_key] = neighbors
        
        # Limit cache size
        if len(self._3hop_cache) > 10000:
            # Simple LRU: remove oldest entries
            oldest_keys = list(self._3hop_cache.keys())[:1000]
            for key in oldest_keys:
                del self._3hop_cache[key]
        
        return neighbors

    def _get_community_nodes(self, community: str) -> List[str]:
        """
        Get all nodes that belong to a community.
        Communities are nodes with label 'community' and have members property.
        """
        if community not in self.graph.nodes:
            return []
            
        # Check if it's a community node
        if self.graph.nodes[community].get('label') != 'community':
            return []
            
        # Get members from the community's properties
        if 'properties' in self.graph.nodes[community]:
            member_names = self.graph.nodes[community]['properties'].get('members', [])
            # Convert member names to node IDs
            member_ids = []
            for name in member_names:
                # Convert list or other types to string before checking
                if isinstance(name, list):
                    name = ", ".join(str(item) for item in name)
                elif not isinstance(name, str):
                    name = str(name)
                    
                if name in self.name_to_id:
                    member_ids.append(self.name_to_id[name])
                else:
                    logger.warning(f"Warning: Member name '{name}' not found in graph nodes")
            return member_ids
        return []

    def _calculate_node_scores(self, query_embed, nodes: List[str]) -> Dict[str, float]:
        scores = {}
        
        if not nodes:
            return scores
            
        query_embed = query_embed.cpu().detach().numpy()
        query_tensor = torch.FloatTensor(query_embed).to(self.device)
        query_tensor = self.transform_vector(query_tensor)
        
        nodes_with_embedding = []
        nodes_without_embedding = []
        nodes_to_encode = []
        
        for node in nodes:
            if 'embedding' in self.graph.nodes[node]:
                nodes_with_embedding.append(node)
            elif node in self.node_embedding_cache:
                scores[node] = F.cosine_similarity(query_tensor, self.node_embedding_cache[node], dim=0).item()
            else:
                nodes_without_embedding.append(node)
                nodes_to_encode.append(node)
        
        if nodes_with_embedding:
            embeddings = []
            for node in nodes_with_embedding:
                node_embed = torch.FloatTensor(self.graph.nodes[node]['embedding']).to(self.device)
                embeddings.append(node_embed)
            
            if embeddings:
                embeddings_tensor = torch.stack(embeddings)
                similarities = F.cosine_similarity(query_tensor.unsqueeze(0), embeddings_tensor, dim=1)
                
                for i, node in enumerate(nodes_with_embedding):
                    scores[node] = similarities[i].item()
        
        if nodes_to_encode:
            texts = []
            for node in nodes_to_encode:
                text = self._get_node_text(node)
                texts.append(text)
            
            if texts:
                node_embeddings = self.model.encode(texts, convert_to_tensor=True, device=self.device)
                
                if self.dim_transform is not None:
                    node_embeddings = self.dim_transform(node_embeddings)
                
                similarities = F.cosine_similarity(query_tensor.unsqueeze(0), node_embeddings, dim=1)
                
                for i, node in enumerate(nodes_to_encode):
                    scores[node] = similarities[i].item()
                    self.node_embedding_cache[node] = node_embeddings[i].detach()
        
        return scores

    def _calculate_node_scores_optimized(self, query_embed, nodes: List[str]) -> Dict[str, float]:

        if not nodes:
            return {}
        
        query_embed = query_embed.cpu().detach().numpy()
        query_tensor = torch.FloatTensor(query_embed).to(self.device)
        query_tensor = self.transform_vector(query_tensor)
        

        node_embeddings = []
        node_names = []
        
        for node in nodes:
            if 'embedding' in self.graph.nodes[node]:
                embed = torch.FloatTensor(self.graph.nodes[node]['embedding']).to(self.device)
                node_embeddings.append(embed)
                node_names.append(node)
            elif node in self.node_embedding_cache:
                node_embeddings.append(self.node_embedding_cache[node])
                node_names.append(node)
            else:
                continue
        
        scores = {}
        if node_embeddings:
            embeddings_tensor = torch.stack(node_embeddings)
            similarities = F.cosine_similarity(query_tensor.unsqueeze(0), embeddings_tensor, dim=1)
            
            for i, node in enumerate(node_names):
                scores[node] = similarities[i].item()
        
        nodes_to_encode = [node for node in nodes if node not in scores]
        if nodes_to_encode:
            texts = [self._get_node_text(node) for node in nodes_to_encode]
            if texts:
                try:
                    embeddings = self.model.encode(texts, convert_to_tensor=True, device=self.device)
                    
                    if self.dim_transform is not None:
                        embeddings = self.dim_transform(embeddings)
                    
                    similarities = F.cosine_similarity(query_tensor.unsqueeze(0), embeddings, dim=1)
                    
                    for i, node in enumerate(nodes_to_encode):
                        scores[node] = similarities[i].item()
                        self.node_embedding_cache[node] = embeddings[i].detach()
                        
                except Exception as e:
                    logger.warning(f"Error encoding nodes: {e}")
                    for node in nodes_to_encode:
                        if node not in scores:
                            scores[node] = 0.0
        
        return scores

    def clear_embedding_cache(self, max_cache_size: int = 10000):

        if len(self.node_embedding_cache) > max_cache_size:
            items_to_remove = len(self.node_embedding_cache) - max_cache_size
            oldest_keys = list(self.node_embedding_cache.keys())[:items_to_remove]
            for key in oldest_keys:
                del self.node_embedding_cache[key]

    def save_embedding_cache(self):
        """Save embedding cache to disk using numpy format to avoid pickle issues"""
        cache_path = f"{self.dataset_cache_dir}/node_embedding_cache.pt"
        try:
            if not self.node_embedding_cache:
                return False
                
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            
            # Convert tensors to numpy arrays for safe serialization
            numpy_cache = {}
            for node, embed in self.node_embedding_cache.items():
                if embed is not None:
                    try:
                        # Convert to numpy array for safer serialization
                        if hasattr(embed, 'detach'):
                            numpy_cache[node] = embed.detach().cpu().numpy()
                        elif isinstance(embed, np.ndarray):
                            numpy_cache[node] = embed
                        else:
                            numpy_cache[node] = np.array(embed)
                    except Exception as e:
                        continue
            
            if not numpy_cache:
                return False
            
            # Save using torch.save with tensor format for better compatibility
            try:
                tensor_cache = {}
                for node, embed_array in numpy_cache.items():
                    if isinstance(embed_array, np.ndarray):
                        tensor_cache[node] = torch.from_numpy(embed_array).float()
                    else:
                        tensor_cache[node] = embed_array
                
                torch.save(tensor_cache, cache_path)
            except Exception as torch_error:
                # Fallback to numpy format to avoid pickle tensor issues
                cache_path_npz = cache_path.replace('.pt', '.npz')
                np.savez_compressed(cache_path_npz, **numpy_cache)
                cache_path = cache_path_npz
            
            file_size = os.path.getsize(cache_path)
            logger.info(f"Saved embedding cache with {len(numpy_cache)} entries to {cache_path} (size: {file_size} bytes)")
            return True
                
        except Exception as e:
            return False

    def load_embedding_cache(self):
        """从磁盘加载嵌入缓存"""
        cache_path = f"{self.dataset_cache_dir}/node_embedding_cache.pt"
        if os.path.exists(cache_path):
            try:
                file_size = os.path.getsize(cache_path)
                if file_size < 1000:  
                    logger.warning(f"Warning: Cache file too small ({file_size} bytes), likely empty or corrupted")
                    return False
                
                # 兼容PyTorch 2.6+的weights_only参数
                try:
                    cpu_cache = torch.load(cache_path, map_location='cpu', weights_only=False)
                except TypeError:
                    cpu_cache = torch.load(cache_path, map_location='cpu')
                except Exception as e:
                    if "numpy.core.multiarray._reconstruct" in str(e):
                        try:
                            import importlib
                            torch_serialization = importlib.import_module('torch.serialization')
                            torch_serialization.add_safe_globals(["numpy.core.multiarray._reconstruct"])
                            cpu_cache = torch.load(cache_path, map_location='cpu')
                        except:
                            raise e
                    else:
                        raise e
                
                if not cpu_cache:
                    logger.warning("Warning: Loaded cache is empty")
                    return False
                

                self.node_embedding_cache.clear()
                
                for node, embed in cpu_cache.items():
                    if embed is not None:
                        try:
                            # 安全地移动到目标设备，兼容CPU环境
                            if isinstance(embed, np.ndarray):
                                embed_tensor = torch.from_numpy(embed).float()
                            else:
                                embed_tensor = embed.cpu() if hasattr(embed, 'cpu') else embed
                            
                            # 只在CUDA可用时移动到CUDA设备
                            if self.device.type == "cuda" and torch.cuda.is_available():
                                embed_tensor = embed_tensor.to(self.device)
                            else:
                                embed_tensor = embed_tensor.to("cpu")
                            
                            self.node_embedding_cache[node] = embed_tensor
                        except Exception as e:
                            logger.warning(f"Warning: Failed to load embedding for node {node}: {e}")
                            continue

                logger.info(f"Loaded embedding cache with {len(self.node_embedding_cache)} entries from {cache_path} (file size: {file_size} bytes)")
                return True
                
            except Exception as e:
                logger.error(f"Error loading embedding cache: {e}")
                try:
                    os.remove(cache_path)
                    logger.info(f"Removed corrupted cache file: {cache_path}")
                except Exception as e2:
                    logger.warning(f"Failed to remove corrupted cache file {cache_path}: {type(e2).__name__}: {e2}")
        else:
            logger.info(f"Cache file not found: {cache_path}")
        return False

    def _is_valid_node_text(self, text: str) -> bool:
        """Check if node text is valid for embedding computation."""
        return text and not text.startswith('[Error') and not text.startswith('[Unknown')
    
    def _prepare_batch_data(self, batch_nodes: list) -> tuple[list, list]:
        """Prepare batch texts and valid nodes from a batch of nodes."""
        batch_texts = []
        valid_nodes = []
        
        for node in batch_nodes:
            try:
                text = self._get_node_text(node)
                if self._is_valid_node_text(text):
                    batch_texts.append(text)
                    valid_nodes.append(node)
                else:
                    logger.warning(f"Warning: Invalid text for node {node}: {text}")
            except Exception as e:
                logger.error(f"Error getting text for node {node}: {e}")
                continue
                
        return batch_texts, valid_nodes
    
    def _compute_and_transform_embeddings(self, texts: list) -> torch.Tensor:
        """Compute embeddings and apply dimension transformation if needed."""
        embeddings = self.model.encode(texts, convert_to_tensor=True, device=self.device)
        
        if hasattr(self, 'dim_transform') and self.dim_transform is not None:
            embeddings = self.dim_transform(embeddings)
            
        return embeddings
    
    def _process_single_node_fallback(self, node: str) -> bool:
        """Process a single node as fallback when batch processing fails."""
        try:
            text = self._get_node_text(node)
            if not self._is_valid_node_text(text):
                return False
                
            embedding = self.model.encode([text], convert_to_tensor=True, device=self.device)[0]
            
            if hasattr(self, 'dim_transform') and self.dim_transform is not None:
                embedding = self.dim_transform(embedding.unsqueeze(0)).squeeze(0)
                
            self.node_embedding_cache[node] = embedding.detach()
            return True
            
        except Exception as e:
            logger.error(f"Error encoding individual node {node}: {e}")
            return False
    
    def _process_batch(self, batch_nodes: list, batch_num: int, total_batches: int) -> int:
        """Process a single batch of nodes and return the number of successfully processed nodes."""
        batch_texts, valid_nodes = self._prepare_batch_data(batch_nodes)
        
        if not batch_texts:
            logger.info(f"Warning: No valid texts in batch {batch_num}")
            return 0
        
        try:
            # Try batch processing first
            embeddings = self._compute_and_transform_embeddings(batch_texts)
            
            for j, node in enumerate(valid_nodes):
                self.node_embedding_cache[node] = embeddings[j].detach()
            
            logger.info(f"Encoded batch {batch_num}/{total_batches} ({len(valid_nodes)} nodes)")
            return len(valid_nodes)
            
        except Exception as e:
            logger.error(f"Error encoding batch {batch_num}: {e}")
            logger.info("Falling back to individual node processing...")
            
            # Fallback to individual processing
            success_count = 0
            for node in valid_nodes:
                if self._process_single_node_fallback(node):
                    success_count += 1
                    
            return success_count

    def _precompute_node_embeddings(self, batch_size: int = 100, force_recompute: bool = False):
        """Precompute embeddings for all graph nodes with optimized batch processing."""
        # Try to load from cache if not forcing recomputation
        if not force_recompute:
            logger.info("Attempting to load node embeddings from disk cache...")
            if self.load_embedding_cache():
                logger.info("Successfully loaded node embeddings from disk cache")
                return

        logger.info("Precomputing node embeddings...")
        self.node_embedding_cache.clear()
        
        # Prepare batch processing
        all_nodes = list(self.graph.nodes())
        total_nodes = len(all_nodes)
        total_batches = (total_nodes + batch_size - 1) // batch_size
        
        logger.info(f"Total nodes to process: {total_nodes}")
        logger.info(f"Processing in {total_batches} batches of size {batch_size}")
        
        # Process nodes in batches
        total_processed = 0
        for i in range(0, total_nodes, batch_size):
            batch_nodes = all_nodes[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            processed_count = self._process_batch(batch_nodes, batch_num, total_batches)
            total_processed += processed_count
        
        # Final summary and cache saving
        logger.info(f"Successfully precomputed embeddings for {len(self.node_embedding_cache)} nodes")
        logger.info(f"Processing success rate: {len(self.node_embedding_cache)}/{total_nodes} ({len(self.node_embedding_cache)/total_nodes*100:.1f}%)")
        
        if self.node_embedding_cache:
            self.save_embedding_cache()

    def build_indices(self):
        """Build FAISS Index only if they don't already exist and are consistent with current graph"""
        # Check if all indices and embedding files already exist
        node_path = f"{self.dataset_cache_dir}/node.index"
        relation_path = f"{self.dataset_cache_dir}/relation.index"
        triple_path = f"{self.dataset_cache_dir}/triple.index"
        comm_path = f"{self.dataset_cache_dir}/comm.index"
        node_embed_path = f"{self.dataset_cache_dir}/node_embeddings.pt"
        relation_embed_path = f"{self.dataset_cache_dir}/relation_embeddings.pt"
        node_map_path = f"{self.dataset_cache_dir}/node_map.json"
        dim_transform_path = f"{self.dataset_cache_dir}/dim_transform.pt"
        
        all_exist = (os.path.exists(node_path) and 
                    os.path.exists(relation_path) and 
                    os.path.exists(triple_path) and 
                    os.path.exists(comm_path) and
                    os.path.exists(node_embed_path) and
                    os.path.exists(relation_embed_path) and
                    os.path.exists(node_map_path))
        
        indices_consistent = False
        if all_exist:
            try:
                with open(node_map_path, 'r') as f:
                    cached_node_map = json.load(f)
                current_nodes = set(self.graph.nodes())
                cached_nodes = set(cached_node_map.values())
                
                # Check graph consistency
                graph_consistent = current_nodes == cached_nodes
                
                # Check model dimension consistency
                dim_consistent = True
                if os.path.exists(dim_transform_path):
                    try:
                        cached_dim_info = torch.load(dim_transform_path, map_location='cpu', weights_only=False)
                        cached_model_dim = cached_dim_info.get('model_dim')
                        if cached_model_dim != self.model_dim:
                            logger.info(f"Model dimension changed: cached {cached_model_dim}, current {self.model_dim}")
                            dim_consistent = False
                    except Exception as e:
                        logger.warning(f"Error checking dimension transform consistency: {e}")
                        dim_consistent = False
                
                if graph_consistent and dim_consistent:
                    indices_consistent = True
                    logger.info("Cached FAISS indices are consistent with current graph and model")
                else:
                    if not graph_consistent:
                        logger.info(f"Graph inconsistency detected: current nodes {len(current_nodes)}, cached nodes {len(cached_nodes)}")
                        logger.info(f"Missing in cache: {current_nodes - cached_nodes}")
                        logger.info(f"Extra in cache: {cached_nodes - current_nodes}")
                    if not dim_consistent:
                        logger.info("Model dimension inconsistency detected")
            except Exception as e:
                logger.error(f"Error checking index consistency: {e}")
        
        if all_exist and indices_consistent:
            logger.info("All FAISS indices and embeddings already exist, loading from cache...")
            if not hasattr(self, 'node_index') or self.node_index is None:
                self._load_indices()
            
            logger.info("Attempting to load node embedding cache from disk...")
            if not self.load_embedding_cache():
                logger.info("Disk cache not available, rebuilding node embedding cache...")
                self._precompute_node_embeddings(force_recompute=True)
            else:
                logger.info("Successfully loaded node embedding cache from disk")
        else:
            logger.info("Building FAISS indices and embeddings...")
            if all_exist and not indices_consistent:
                logger.info("Clearing inconsistent cache files...")
                for path in [node_path, relation_path, triple_path, comm_path, node_embed_path, relation_embed_path, node_map_path, dim_transform_path]:
                    if os.path.exists(path):
                        os.remove(path)
            
            self._build_node_index()
            self._build_relation_index()
            self._build_triple_index()
            self._build_community_index()
            self._save_dim_transform()
            logger.info("FAISS indices and embeddings built successfully!")
            self._populate_embedding_maps()
            try:
                if self.node_embeddings is not None and self.node_map:
                    self.node_embedding_cache = {}
                    for i_str, node_id in self.node_map.items():
                        try:
                            self.node_embedding_cache[node_id] = self.node_embeddings[int(i_str)].detach()
                        except Exception:
                            continue
                    self.save_embedding_cache()
            except Exception as e:
                logger.warning(f"Warning: Failed to seed node_embedding_cache from built embeddings: {e}")
        
        self._preload_faiss_indices()

    def _save_dim_transform(self):
        """Save dimension transform state to disk"""
        dim_transform_path = f"{self.dataset_cache_dir}/dim_transform.pt"
        try:
            save_data = {
                'model_dim': self.model_dim,
                'target_dim': 384,
                'has_transform': self.dim_transform is not None
            }
            
            if self.dim_transform is not None:
                save_data['state_dict'] = self.dim_transform.cpu().state_dict()
            
            torch.save(save_data, dim_transform_path)
            logger.info(f"Saved dimension transform to {dim_transform_path}")
        except Exception as e:
            logger.error(f"Error saving dimension transform: {e}")

    def _load_dim_transform(self):
        """Load dimension transform state from disk"""
        dim_transform_path = f"{self.dataset_cache_dir}/dim_transform.pt"
        if not os.path.exists(dim_transform_path):
            return False
            
        try:
            try:
                save_data = torch.load(dim_transform_path, map_location='cpu', weights_only=False)
            except TypeError:
                save_data = torch.load(dim_transform_path, map_location='cpu')
            
            cached_model_dim = save_data.get('model_dim')
            has_transform = save_data.get('has_transform', False)
            
            # Verify dimension consistency
            if cached_model_dim != self.model_dim:
                logger.warning(f"Model dimension mismatch: cached {cached_model_dim}, current {self.model_dim}")
                return False
            
            if has_transform and 'state_dict' in save_data:
                if self.dim_transform is None:
                    self.dim_transform = torch.nn.Linear(self.model_dim, 384)
                
                # Load the saved weights
                self.dim_transform.load_state_dict(save_data['state_dict'])
                
                if self.device.type == "cuda" and torch.cuda.is_available():
                    self.dim_transform = self.dim_transform.to(self.device)
                else:
                    self.dim_transform = self.dim_transform.to("cpu")
                    
                logger.info(f"Loaded dimension transform from {dim_transform_path}")
                return True
            elif not has_transform:
                if self.dim_transform is None:
                    logger.info("No dimension transform needed (cached and current both 384-dim)")
                    return True
                else:
                    logger.warning("Dimension transform state mismatch")
                    return False
                    
        except Exception as e:
            logger.error(f"Error loading dimension transform: {e}")
            return False
        
        return False

    def _build_node_index(self):
        """Build FAISS index for all nodes and cache embeddings"""
        nodes = list(self.graph.nodes())
        texts = [self._get_node_text(n) for n in nodes]
        embeddings = self.model.encode(texts, convert_to_tensor=True)
        
        # Store embeddings on CPU to save GPU memory
        self.node_embeddings = embeddings.cpu()
        # Save as .pt for consistency across the codebase
        torch.save(self.node_embeddings, f"{self.dataset_cache_dir}/node_embeddings.pt")
        
        # Build FAISS index
        embeddings_np = embeddings.cpu().numpy()
        dim = embeddings_np.shape[1]
        index = faiss.IndexFlatIP(dim)
        faiss.normalize_L2(embeddings_np)
        index.add(embeddings_np)
        
        faiss.write_index(index, f"{self.dataset_cache_dir}/node.index")
        self.node_map = {str(i): n for i, n in enumerate(nodes)}
        with open(f"{self.dataset_cache_dir}/node_map.json", 'w') as f:
            json.dump(self.node_map, f)
            
        self.node_index = index
        
    def _build_relation_index(self):
        """Build FAISS index for all relations and cache embeddings"""
        relations = sorted(list({
            data['relation'] for _, _, data in self.graph.edges(data=True) if 'relation' in data
        }))
                
        embeddings = self.model.encode(relations, convert_to_tensor=True)

        # Store embeddings on CPU
        self.relation_embeddings = embeddings.cpu()
        # Save as .pt for consistency across the codebase
        torch.save(self.relation_embeddings, f"{self.dataset_cache_dir}/relation_embeddings.pt")

        # Build FAISS index
        embeddings_np = embeddings.cpu().numpy()
        dim = embeddings_np.shape[1]
        index = faiss.IndexFlatIP(dim)
        faiss.normalize_L2(embeddings_np)
        index.add(embeddings_np)
        
        faiss.write_index(index, f"{self.dataset_cache_dir}/relation.index")
        self.relation_map = {str(i): r for i, r in enumerate(relations)}
        with open(f"{self.dataset_cache_dir}/relation_map.json", 'w') as f:
            json.dump(self.relation_map, f)
            
        self.relation_index = index

    def _build_triple_index(self):
        """Build FAISS Triple Index"""
        triples = []
        for u, v, data in self.graph.edges(data=True):
            if 'relation' in data:
                triples.append((u, data['relation'],v))
        
        texts = [f"{self._get_node_text(h)},{r},{self._get_node_text(t)}" for h, r, t in triples]
        embeddings = self.model.encode(texts)
        
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        
        faiss.write_index(index, f"{self.dataset_cache_dir}/triple.index")
        with open(f"{self.dataset_cache_dir}/triple_map.json", 'w') as f:
            json.dump({i: n for i, n in enumerate(triples)}, f)
        
        self.triple_index = index
        self.triple_map = {str(i): n for i, n in enumerate(triples)}

    def _build_community_index(self):
        """Build FAISS Community Index"""
        communities = {
            n for n, d in self.graph.nodes(data=True) 
            if d.get('label') == 'community'
        }
        
        texts = []
        valid_communities = []
        for comm in communities:
            # Get community text representation
            data = self.graph.nodes[comm]
            if 'properties' in data:
                name = data['properties'].get('name', '')
                description = data['properties'].get('description', '')
                if name or description:  # Only include if it has name or description
                    texts.append(f"{name},{description}".strip())
                    valid_communities.append(comm)
        
        if not valid_communities:
            return
            
        embeddings = self.model.encode(texts)
        
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        
        faiss.write_index(index, f"{self.dataset_cache_dir}/comm.index")
        with open(f"{self.dataset_cache_dir}/comm_map.json", 'w') as f:
            json.dump({i: n for i, n in enumerate(valid_communities)}, f)
        
        self.comm_index = index
        self.comm_map = {str(i): n for i, n in enumerate(valid_communities)}

    def _load_indices(self):
        logger.info("Starting _load_indices...")
        triple_path = f"{self.dataset_cache_dir}/triple.index"
        comm_path = f"{self.dataset_cache_dir}/comm.index"
        node_path = f"{self.dataset_cache_dir}/node.index"
        relation_path = f"{self.dataset_cache_dir}/relation.index"
        node_embed_path = f"{self.dataset_cache_dir}/node_embeddings.pt"
        relation_embed_path = f"{self.dataset_cache_dir}/relation_embeddings.pt"
        
        logger.debug(f"Checking cache files...")
        logger.debug(f"node_path exists: {os.path.exists(node_path)}")
        logger.debug(f"relation_path exists: {os.path.exists(relation_path)}")
        logger.debug(f"triple_path exists: {os.path.exists(triple_path)}")
        logger.debug(f"comm_path exists: {os.path.exists(comm_path)}")
        logger.debug(f"node_embed_path exists: {os.path.exists(node_embed_path)}")
        logger.debug(f"relation_embed_path exists: {os.path.exists(relation_embed_path)}")
        
        if os.path.exists(node_path):
            logger.debug("Loading node index...")
            self.node_index = faiss.read_index(node_path)
            with open(f"{self.dataset_cache_dir}/node_map.json", 'r') as f:
                self.node_map = json.load(f)
                
        if os.path.exists(relation_path):
            self.relation_index = faiss.read_index(relation_path)
            with open(f"{self.dataset_cache_dir}/relation_map.json", 'r') as f:
                self.relation_map = json.load(f)
        
        if os.path.exists(triple_path):
            self.triple_index = faiss.read_index(triple_path)
            with open(f"{self.dataset_cache_dir}/triple_map.json", 'r') as f:
                self.triple_map = json.load(f)
                
        if os.path.exists(comm_path):
            self.comm_index = faiss.read_index(comm_path)
            with open(f"{self.dataset_cache_dir}/comm_map.json", 'r') as f:
                self.comm_map = json.load(f)

        if os.path.exists(node_embed_path):
            try:
                # 兼容PyTorch 2.6+的weights_only参数
                try:
                    self.node_embeddings = torch.load(node_embed_path, weights_only=False)
                except TypeError:
                    self.node_embeddings = torch.load(node_embed_path)
            except Exception as e:
                logger.warning(f"Warning: Failed to load node embeddings: {e}")
                
        if os.path.exists(relation_embed_path):
            try:
                # 兼容PyTorch 2.6+的weights_only参数
                try:
                    self.relation_embeddings = torch.load(relation_embed_path, weights_only=False)
                except TypeError:
                    self.relation_embeddings = torch.load(relation_embed_path)
            except Exception as e:
                logger.warning(f"Warning: Failed to load relation embeddings: {e}")

        # Load dimension transform if available
        self._load_dim_transform()
        
        # Populate maps if all necessary data is loaded
        if self.node_map and self.node_embeddings is not None:
            self._populate_embedding_maps()
        else:
            logger.debug("Cannot populate embedding maps - missing node_map or node_embeddings")
            logger.debug(f"node_map exists: {self.node_map is not None}")
            logger.debug(f"node_embeddings exists: {self.node_embeddings is not None}")

    def _populate_embedding_maps(self):
        """Populate the node_id and relation to embedding maps."""
        if self.node_map and self.node_embeddings is not None:
            for i_str, node_id in self.node_map.items():
                self.node_id_to_embedding[node_id] = self.node_embeddings[int(i_str)]
        
        if self.relation_map and self.relation_embeddings is not None:
            for i_str, rel in self.relation_map.items():
                self.relation_to_embedding[rel] = self.relation_embeddings[int(i_str)]
        
        # Verify data consistency
        self._verify_data_consistency()

    def _verify_data_consistency(self):
        """Verify that graph nodes and embedding maps are consistent"""
        logger.debug("Verifying data consistency...")
        
        graph_nodes = set(self.graph.nodes())
        embedding_nodes = set(self.node_id_to_embedding.keys())
        
        missing_in_embeddings = graph_nodes - embedding_nodes
        extra_in_embeddings = embedding_nodes - graph_nodes
        
        if missing_in_embeddings:
            logger.warning(f"Warning: {len(missing_in_embeddings)} nodes in graph but not in embeddings: {list(missing_in_embeddings)[:5]}...")
        
        if extra_in_embeddings:
            logger.warning(f"Warning: {len(extra_in_embeddings)} nodes in embeddings but not in graph: {list(extra_in_embeddings)[:5]}...")
        
        if not missing_in_embeddings and not extra_in_embeddings:
            logger.info("✓ Data consistency verified: all graph nodes have embeddings")
        else:
            logger.info(f"✗ Data inconsistency detected: {len(missing_in_embeddings)} missing, {len(extra_in_embeddings)} extra")

    def _get_node_text(self, node: str) -> str:
        data = self.graph.nodes[node]
        if 'properties' in data and isinstance(data['properties'], dict):
            name = data['properties'].get('name') or 'none'
            description = data['properties'].get('description') or 'none'
            name = str(name).strip()
            description = str(description).strip()
        else:
            name = data.get('name') or 'none'
            description = data.get('description') or 'none'
            name = str(name).strip()
            description = str(description).strip()
        
        if isinstance(name, list):
            name = ", ".join(str(item) for item in name)
        elif not isinstance(name, str):
            name = str(name)
            
        if isinstance(description, list):
            description = ", ".join(str(item) for item in description)
        elif not isinstance(description, str):
            description = str(description)
        
        return f"{name},{description}".strip()

    def _subgraph_to_text(self, subgraph: nx.MultiDiGraph) -> str:
        """
        Convert subgraph to readable text format
        """
        text_parts = []
        
        # Add nodes information
        for node, data in subgraph.nodes(data=True):
            node_text = f"Node: {data.get('name', node)}\n"
            if 'description' in data:
                node_text += f"Description: {data['description']}\n"
            if 'properties' in data:
                node_text += f"Properties: {data['properties']}\n"
            text_parts.append(node_text)
        
        # Add edges information
        for u, v, data in subgraph.edges(data=True):
            edge_text = f"Relation: {data.get('relation', '')} between {subgraph.nodes[u].get('name', u)} and {subgraph.nodes[v].get('name', v)}\n"
            text_parts.append(edge_text)
            
        return "\n".join(text_parts)

    def _extract_node_info(self, node_data: dict) -> tuple[str, str]:
        """Extract and normalize name and description from node data."""
        def normalize_field(field) -> str:
            """Convert various field types to clean string."""
            if not field:
                return ''
            if isinstance(field, list):
                return ", ".join(str(item) for item in field)
            return str(field).strip()
        
        # Try properties first, then fallback to direct attributes
        if 'properties' in node_data and isinstance(node_data['properties'], dict):
            name = normalize_field(node_data['properties'].get('name'))
            description = normalize_field(node_data['properties'].get('description'))
        else:
            name = normalize_field(node_data.get('name'))
            description = normalize_field(node_data.get('description'))
        
        return name, description
    
    def _format_node_text(self, name: str, description: str) -> str:
        """Format node name and description into display text."""
        if not name:
            return ''
        return f"{name} - {description}" if description else name
    
    def _get_community_members(self, community_node: str) -> tuple[list[str], list[str]]:
        """Get entities and keywords that belong to a community."""
        entities, keywords = [], []
        
        for node_id, node_data in self.graph.nodes(data=True):
            if node_data.get('community_l4') == community_node:
                name, description = self._extract_node_info(node_data)
                if not name:
                    continue
                    
                formatted_text = self._format_node_text(name, description)
                node_type = node_data.get('level')
                
                if node_type == 2:  # Entity
                    entities.append(formatted_text)
                elif node_type == 1:  # Keyword
                    keywords.append(formatted_text)
        
        return entities, keywords
    
    def _format_community_content(self, base_text: str, entities: list[str], keywords: list[str]) -> str:
        """Format community with its member entities and keywords."""
        if not entities and not keywords:
            return base_text
            
        content_parts = [base_text, "\n  Contains:"]
        
        if entities:
            shown = entities[:3]
            entities_text = f"\n    Entities: {', '.join(shown)}"
            if len(entities) > 3:
                entities_text += f" and {len(entities) - 3} more"
            content_parts.append(entities_text)
            
        if keywords:
            shown = keywords[:3]
            keywords_text = f"\n    Keywords: {', '.join(shown)}"
            if len(keywords) > 3:
                keywords_text += f" and {len(keywords) - 3} more"
            content_parts.append(keywords_text)
            
        return "".join(content_parts)
    
    def _nodes_to_text(self, nodes: List[str]) -> str:
        """Convert a list of nodes to a readable text format with node information."""
        # Node type mapping for cleaner code
        NODE_TYPES = {1: 'keywords', 2: 'entities', 4: 'communities'}
        
        # Collect nodes by type
        collected = {node_type: [] for node_type in NODE_TYPES.values()}
        
        for node in nodes:
            if node not in self.graph.nodes:
                continue
                
            node_data = self.graph.nodes[node]
            node_type = node_data.get('level')
            name, description = self._extract_node_info(node_data)
            
            if not name:  # Skip nodes without meaningful names
                continue
                
            if node_type == 2:  # Entity
                formatted = self._format_node_text(name, description)
                collected['entities'].append(formatted)
                
            elif node_type == 1:  # Keyword
                formatted = self._format_node_text(name, description)
                collected['keywords'].append(formatted)
                
            elif node_type == 4:  # Community
                base_text = self._format_node_text(name, description)
                entities, keywords = self._get_community_members(node)
                community_text = self._format_community_content(base_text, entities, keywords)
                collected['communities'].append(community_text)
        
        # Build output sections
        text_parts = ["=== Retrieved Information ==="]
        
        section_configs = [
            ('entities', '=== Entity Information ==='),
            ('keywords', '=== Keyword Information ==='),
            ('communities', '=== Community Information ===')
        ]
        
        for section_key, section_header in section_configs:
            items = collected[section_key]
            if items:
                text_parts.extend([f"\n{section_header}"] + [f"• {item}" for item in items])
        
        # Return result or fallback message
        if len(text_parts) == 1:  # Only header present
            return "No relevant information found."
        
        return "\n".join(text_parts)

    def transform_vector(self, vector: torch.Tensor) -> torch.Tensor:
        """Transform vector dimensions if needed"""
        if self.dim_transform is not None:
            return self.dim_transform(vector)
        return vector

    def _calculate_triple_relevance_scores(self, query_embed: torch.Tensor, triples: List[Tuple[str, str, str]], threshold: float = 0.3, top_k: int = 10) -> List[Tuple[str, str, str, float]]:
        """
        Calculate relevance scores for triples and filter out low-relevance ones using FAISS.
        
        Args:
            query_embed: Query embedding tensor
            triples: List of (head, tail, relation) tuples
            threshold: Minimum relevance score threshold
            top_k: Maximum number of triples to return
            
        Returns:
            List of (head, relation, tail, score) tuples with scores above threshold, limited to top_k
        """
        
        scored_triples = []
        
        if not triples:
            logger.debug("No triples to process")
            return []
        
        # Transform query embedding for FAISS search
        query_embed = self.transform_vector(query_embed)
        query_embed_np = query_embed.cpu().detach().numpy().reshape(1, -1)
        
        # Normalize query embedding for FAISS search
        faiss.normalize_L2(query_embed_np)
        
        # Create a set of input triples for fast lookup
        input_triples_set = set(triples)
        logger.debug(f"Input triples set size: {len(input_triples_set)}")
        logger.debug(f"First few input triples: {list(input_triples_set)[:3]}")
        
        # Check if triple_index exists and is valid
        if not hasattr(self, 'triple_index') or self.triple_index is None:
            logger.debug("triple_index is None or doesn't exist")
            # Fallback: return all triples with default scores
            for h, r, t in triples:
                scored_triples.append((h, r, t, 0.5))  # Default score
            logger.debug(f"Using fallback method, returning {len(scored_triples)} triples")
            return scored_triples[:top_k]
        logger.debug(f"triple_index exists, size: {self.triple_index.ntotal}")
        # Use FAISS to search for similar triples in the index
        try:
            # Search for top similar triples in the index
            search_k = min(len(triples) * 2, 50)  # Search more than needed to get good matches
            logger.debug(f"Searching for {search_k} similar triples")
            D, I = self.triple_index.search(query_embed_np, search_k)
            # Process results from FAISS search
            for i, (distance, idx) in enumerate(zip(D[0], I[0])):
                if idx >= 0:  # Valid index
                    try:
                        # Get the triple from the index
                        indexed_triple = self.triple_map[str(idx)]
                        h, r, t = indexed_triple  # This is (head, tail, relation) format
                        # Check if this triple is in our input triples
                        if (h, r, t) in input_triples_set:
                            # Convert distance to similarity score (FAISS returns distances, we need similarities)
                            # For normalized vectors, similarity = 1 - distance^2 / 2
                            # similarity_score = 1.0 - (distance ** 2) / 2.0
                            # bug fixing since D already returns similarity in IndexFlatIP
                            similarity_score = distance
                            # Only keep triples above threshold
                            if similarity_score >= threshold:
                                scored_triples.append((h, r, t, similarity_score))  # Return as (head, tail, relation, score)
                            else:
                                logger.debug(f"Triple ({h}, {t}, {r}) below threshold {threshold}")
                                
                    except (KeyError, ValueError) as e:
                        logger.error(f"Warning: Error processing indexed triple {idx}: {str(e)}")
                        continue
        except Exception as e:
            for h, r, t in triples:
                scored_triples.append((h, r, t, 0.5))  # Default score
        
        logger.debug(f"Found {len(scored_triples)} triples above threshold")
        
        # Sort by score in descending order
        scored_triples.sort(key=lambda x: x[3], reverse=True)
        
        # Return only top_k triples
        result = scored_triples[:top_k]
        return result

    def __del__(self):
        try:
            if hasattr(self, 'node_embedding_cache') and self.node_embedding_cache:
                self.save_embedding_cache()
        except Exception as e:
            logger.warning(f"Error during __del__ saving embedding cache: {type(e).__name__}: {e}")


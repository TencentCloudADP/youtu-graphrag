"""
Configuration loader and manager for KT-RAG framework.
Handles loading, validation, and access to configuration parameters.
"""

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from utils.logger import logger


@dataclass
class DatasetConfig:
    """Dataset configuration for a specific dataset"""
    corpus_path: str
    qa_path: str
    schema_path: str
    graph_output: str

@dataclass
class TriggersConfig:
    """Execution triggers configuration"""
    constructor_trigger: bool = True
    retrieve_trigger: bool = True
    mode: str = "agent"  # "agent" or "noagent"

@dataclass
class ConstructionConfig:
    """Construction configuration"""
    mode: str = "agent"
    max_workers: int = 32
    datasets_no_chunk: list = None
    chunk_size: int = 1000
    overlap: int = 200
    
    def __post_init__(self):
        if self.datasets_no_chunk is None:
            self.datasets_no_chunk = ["hotpot", "2wiki", "musique", "graphrag-bench", "anony_chs", "anony_eng"]

@dataclass
class TreeCommConfig:
    """Tree-Comm algorithm configuration"""
    embedding_model: str = "all-MiniLM-L6-v2"
    struct_weight: float = 0.3
    enable_fast_mode: bool = True
    max_total_communities: int = 100

@dataclass
class FAISSConfig:
    """FAISS configuration"""
    search_k: int = 50
    max_workers: int = 4
    device: str = "cpu"

@dataclass
class AgentConfig:
    """Agent mode configuration"""
    max_steps: int = 5
    enable_ircot: bool = True
    enable_parallel_subquestions: bool = True

@dataclass
class RetrievalConfig:
    """Retrieval configuration"""
    top_k: int = 5
    recall_paths: int = 2
    top_k_filter: int = 20
    similarity_threshold: float = 0.3
    enable_query_enhancement: bool = True
    enable_reranking: bool = True
    enable_high_recall: bool = True
    enable_caching: bool = True
    cache_dir: str = "retriever/faiss_cache_new"
    faiss: FAISSConfig = None
    agent: AgentConfig = None
    
    def __post_init__(self):
        if self.faiss is None:
            self.faiss = FAISSConfig()
        if self.agent is None:
            self.agent = AgentConfig()

@dataclass
class EmbeddingsConfig:
    """Embeddings configuration"""
    model_name: str = "all-MiniLM-L6-v2"
    device: str = "cpu"
    batch_size: int = 32
    max_length: int = 512

@dataclass
class NLPConfig:
    """NLP configuration"""
    spacy_model: str = 'en_core_web_lg' 


@dataclass
class OutputConfig:
    """Output configuration"""
    base_dir: str = "output"
    graphs_dir: str = "output/graphs"
    chunks_dir: str = "output/chunks"
    logs_dir: str = "output/logs"
    save_intermediate_results: bool = True
    save_chunk_details: bool = True

@dataclass
class PerformanceConfig:
    """Performance configuration"""
    parallel_processing: bool = True
    max_workers: int = 32
    batch_size: int = 16
    memory_optimization: bool = True

@dataclass
class EvaluationConfig:
    """Evaluation configuration"""
    enable_evaluation: bool = True
    metrics: list = None
    save_detailed_results: bool = True
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = ["accuracy", "precision", "recall", "f1"]

class ConfigManager:
    """
    Main configuration manager for the KT-RAG framework.
    Handles loading, validation, and providing access to configuration settings.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file. If None, uses default.
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config_data: Dict[str, Any] = {}
        self.datasets: Dict[str, DatasetConfig] = {}
        self.triggers: Optional[TriggersConfig] = None
        self.construction: Optional[ConstructionConfig] = None
        self.tree_comm: Optional[TreeCommConfig] = None
        self.retrieval: Optional[RetrievalConfig] = None
        self.embeddings: Optional[EmbeddingsConfig] = None
        self.nlp: Optional[NLPConfig] = None
        self.prompts: Dict[str, Any] = {}
        self.output: Optional[OutputConfig] = None
        self.performance: Optional[PerformanceConfig] = None
        self.evaluation: Optional[EvaluationConfig] = None

        self.load_config()
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        current_dir = Path(__file__).parent
        return str(current_dir / "base_config.yaml")
    
    def load_config(self) -> None:
        """Load and parse the configuration file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f)
            
            self._parse_config()
            self._validate_config()
            
            logger.info(f"Configuration loaded successfully from {self.config_path}")
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading configuration: {e}")
    
    def _parse_config(self) -> None:
        """Parse the loaded configuration data into structured objects."""
        datasets_data = self.config_data.get("datasets", {})
        self.datasets = {
            name: DatasetConfig(**config) 
            for name, config in datasets_data.items()
        }
        
        triggers_data = self.config_data.get("triggers", {})
        self.triggers = TriggersConfig(**triggers_data)
        
        construction_data = self.config_data.get("construction", {})
        tree_comm_data = construction_data.pop("tree_comm", {})
        self.construction = ConstructionConfig(**construction_data)
        self.tree_comm = TreeCommConfig(**tree_comm_data)
        
        retrieval_data = self.config_data.get("retrieval", {})
        faiss_data = retrieval_data.pop("faiss", {})
        agent_data = retrieval_data.pop("agent", {})
        self.retrieval = RetrievalConfig(**retrieval_data)
        self.retrieval.faiss = FAISSConfig(**faiss_data)
        self.retrieval.agent = AgentConfig(**agent_data)
        
        embeddings_data = self.config_data.get("embeddings", {})
        self.embeddings = EmbeddingsConfig(**embeddings_data)
        
        nlp = self.config_data.get("nlp", {})
        self.nlp = NLPConfig(**nlp)
        
        self.prompts = self.config_data.get("prompts", {})
        
        output_data = self.config_data.get("output", {})
        self.output = OutputConfig(**output_data)
        
        performance_data = self.config_data.get("performance", {})
        self.performance = PerformanceConfig(**performance_data)
        
        evaluation_data = self.config_data.get("evaluation", {})
        self.evaluation = EvaluationConfig(**evaluation_data)
    
    def _validate_config(self) -> None:
        """Validate the loaded configuration."""
        for dataset_name, dataset_config in self.datasets.items():
            if not os.path.exists(dataset_config.corpus_path):
                logger.warning(f"Corpus path not found for {dataset_name}: {dataset_config.corpus_path}")
            if not os.path.exists(dataset_config.schema_path):
                logger.warning(f"Schema path not found for {dataset_name}: {dataset_config.schema_path}")
        
        valid_modes = ["agent", "noagent"]
        if self.triggers.mode not in valid_modes:
            raise ValueError(f"Invalid mode: {self.triggers.mode}. Must be one of {valid_modes}")
        
        if self.construction.mode not in ["agent", "basic"]:
            raise ValueError(f"Invalid construction mode: {self.construction.mode}")
        
        # Validate numerical parameters
        if self.retrieval.top_k <= 0:
            raise ValueError("top_k must be positive")
        
        if self.tree_comm.struct_weight < 0 or self.tree_comm.struct_weight > 1:
            raise ValueError("struct_weight must be between 0 and 1")
    
    def get_dataset_config(self, dataset_name: str) -> DatasetConfig:
        """Get configuration for a specific dataset."""
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset '{dataset_name}' not found in configuration")
        return self.datasets[dataset_name]
    
    def get_prompt(self, category: str, prompt_type: str) -> str:
        """Get a specific prompt template."""
        try:
            return self.prompts[category][prompt_type]
        except KeyError:
            raise ValueError(f"Prompt not found: {category}.{prompt_type}")
    
    def get_prompt_formatted(self, category: str, prompt_type: str, **kwargs) -> str:
        """Get a formatted prompt with variables substituted."""
        template = self.get_prompt(category, prompt_type)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing variable {e} for prompt {category}.{prompt_type}")
    
    def override_config(self, overrides: Dict[str, Any]) -> None:
        """Override configuration values at runtime."""
        def update_nested_dict(d: dict, overrides: dict) -> None:
            for key, value in overrides.items():
                if isinstance(value, dict) and key in d and isinstance(d[key], dict):
                    update_nested_dict(d[key], value)
                else:
                    d[key] = value
        
        update_nested_dict(self.config_data, overrides)
        self._parse_config()
        self._validate_config()
    
    def save_config(self, output_path: str) -> None:
        """Save current configuration to a file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config_data, f, default_flow_style=False, ensure_ascii=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            "api": asdict(self.api),
            "datasets": {name: asdict(config) for name, config in self.datasets.items()},
            "triggers": asdict(self.triggers),
            "construction": asdict(self.construction),
            "tree_comm": asdict(self.tree_comm),
            "retrieval": asdict(self.retrieval),
            "embeddings": asdict(self.embeddings),
            "prompts": self.prompts,
            "output": asdict(self.output),
            "performance": asdict(self.performance),
            "evaluation": asdict(self.evaluation),
        }
    
    def create_output_directories(self) -> None:
        """Create necessary output directories."""
        directories = [
            self.output.base_dir,
            self.output.graphs_dir,
            self.output.chunks_dir,
            self.output.logs_dir,
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

_config_instance: Optional[ConfigManager] = None

def get_config(config_path: Optional[str] = None) -> ConfigManager:
    """
    Get the global configuration instance.
    
    Args:
        config_path: Path to configuration file (only used on first call)
        
    Returns:
        ConfigManager instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ConfigManager(config_path)
    
    return _config_instance

def reload_config(config_path: Optional[str] = None) -> ConfigManager:
    """
    Reload the configuration.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        New ConfigManager instance
    """
    global _config_instance
    _config_instance = ConfigManager(config_path)
    return _config_instance

"""
Configuration module for KT-RAG framework.
Provides easy access to configuration management.
"""

from .config_loader import (
    ConfigManager,
    get_config,
    reload_config,
    get_spacy_model_for_dataset_config,
    DatasetConfig,
    TriggersConfig,
    ConstructionConfig,
    TreeCommConfig,
    RetrievalConfig,
    EmbeddingsConfig,
    OutputConfig,
    PerformanceConfig,
    EvaluationConfig,
    LanguageConfig,
)

__all__ = [
    "ConfigManager",
    "get_config",
    "reload_config",
    "get_spacy_model_for_dataset_config",
    "DatasetConfig",
    "TriggersConfig",
    "ConstructionConfig",
    "TreeCommConfig",
    "RetrievalConfig",
    "EmbeddingsConfig",
    "OutputConfig",
    "PerformanceConfig",
    "EvaluationConfig",
    "LanguageConfig",
]

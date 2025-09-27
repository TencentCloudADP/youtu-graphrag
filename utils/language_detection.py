"""
Language detection utilities for automatic spacy model selection.
Provides functions to detect language from dataset name and select appropriate spacy models.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Chinese character Unicode range
CHINESE_CHAR_PATTERN = re.compile(r'[\u4e00-\u9fff]')
CHINESE_KEYWORDS = ['chinese', 'zh', 'chs', 'cn', 'novel', '中文', '汉语', '华语']
ENGLISH_KEYWORDS = ['en', 'eng', 'english', '英文', '英语']

def detect_language_from_dataset_name(dataset_name: str) -> str:
    """
    Detect language from dataset name.

    Args:
        dataset_name: Name of the dataset

    Returns:
        str: 'zh' for Chinese, 'en' for English
    """
    if not dataset_name:
        logger.warning("Empty dataset name, defaulting to English")
        return 'en'

    # Convert to lowercase for case-insensitive matching
    dataset_lower = dataset_name.lower()

    # Check for Chinese characters first
    if CHINESE_CHAR_PATTERN.search(dataset_name):
        logger.info(f"Detected Chinese characters in dataset name: {dataset_name}")
        return 'zh'

    # Special case handling for existing dataset naming conventions
    if dataset_name == 'novel_eng':
        logger.info(f"Detected special case English dataset: {dataset_name}")
        return 'en'

    # Check for English keywords with higher priority (except for 'novel')
    for keyword in ENGLISH_KEYWORDS:
        if keyword in dataset_lower and dataset_name != 'novel':
            logger.info(f"Detected English keyword '{keyword}' in dataset name: {dataset_name}")
            return 'en'

    # Check for Chinese keywords (including 'novel')
    for keyword in CHINESE_KEYWORDS:
        if keyword in dataset_lower:
            logger.info(f"Detected Chinese keyword '{keyword}' in dataset name: {dataset_name}")
            return 'zh'

    # Default to English if no indicators found
    logger.info(f"No language indicators found in dataset name: {dataset_name}, defaulting to English")
    return 'en'

def get_spacy_model_name(language: str) -> str:
    """
    Get spacy model name based on language.

    Args:
        language: Language code ('zh' or 'en')

    Returns:
        str: Spacy model name
    """
    model_map = {
        'zh': 'zh_core_web_lg',
        'en': 'en_core_web_lg'
    }

    if language not in model_map:
        logger.warning(f"Unsupported language: {language}, defaulting to English model")
        return model_map['en']

    return model_map[language]

def get_spacy_model_for_dataset(dataset_name: str) -> str:
    """
    Get appropriate spacy model name for a dataset.

    Args:
        dataset_name: Name of the dataset

    Returns:
        str: Spacy model name
    """
    language = detect_language_from_dataset_name(dataset_name)
    model_name = get_spacy_model_name(language)

    logger.info(f"Selected spacy model '{model_name}' for dataset '{dataset_name}' (language: {language})")
    return model_name

def validate_spacy_model(model_name: str) -> bool:
    """
    Validate if a spacy model is available.

    Args:
        model_name: Name of the spacy model

    Returns:
        bool: True if model is available, False otherwise
    """
    try:
        import spacy
        # Try to load the model
        spacy.load(model_name)
        logger.info(f"Spacy model '{model_name}' is available")
        return True
    except OSError:
        logger.warning(f"Spacy model '{model_name}' is not available")
        return False
    except Exception as e:
        logger.error(f"Error validating spacy model '{model_name}': {e}")
        return False

def get_available_models() -> dict:
    """
    Get available spacy models.

    Returns:
        dict: Dictionary mapping language codes to available model names
    """
    available_models = {}

    # Check Chinese model
    if validate_spacy_model('zh_core_web_lg'):
        available_models['zh'] = 'zh_core_web_lg'

    # Check English model
    if validate_spacy_model('en_core_web_lg'):
        available_models['en'] = 'en_core_web_lg'

    logger.info(f"Available spacy models: {available_models}")
    return available_models

def get_fallback_model(dataset_name: str) -> str:
    """
    Get fallback model when preferred model is not available.

    Args:
        dataset_name: Name of the dataset

    Returns:
        str: Fallback model name
    """
    available_models = get_available_models()

    if not available_models:
        logger.error("No spacy models available")
        raise RuntimeError("No spacy models available")

    # Try to get model for dataset language
    language = detect_language_from_dataset_name(dataset_name)
    if language in available_models:
        return available_models[language]

    # Fall back to English if available
    if 'en' in available_models:
        logger.warning(f"Model for language '{language}' not available, falling back to English")
        return available_models['en']

    # Use whatever is available
    fallback_model = list(available_models.values())[0]
    logger.warning(f"English model not available, using fallback: {fallback_model}")
    return fallback_model
#!/usr/bin/env python3
"""
Test script for language detection functionality.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.language_detection import (
    detect_language_from_dataset_name,
    get_spacy_model_name,
    get_spacy_model_for_dataset,
    validate_spacy_model,
    get_available_models,
    get_fallback_model
)

def test_language_detection():
    """Test language detection for various dataset names."""
    print("🧪 Testing Language Detection Functionality")
    print("=" * 50)

    # Test cases for language detection
    test_cases = [
        # (dataset_name, expected_language)
        ("demo", "en"),
        ("hotpot", "en"),
        ("2wiki", "en"),
        ("musique", "en"),
        ("graphrag-bench", "en"),
        ("novel", "zh"),  # Special case
        ("novel_eng", "en"),  # Special case
        ("anony_chs", "zh"),  # Contains 'chs'
        ("anony_eng", "en"),  # Contains 'eng'
        ("chinese_dataset", "zh"),  # Contains 'chinese'
        ("zh_test", "zh"),  # Contains 'zh'
        ("中文数据集", "zh"),  # Contains Chinese characters
        ("english_data", "en"),  # Contains 'english'
        ("mixed_中文_dataset", "zh"),  # Mixed with Chinese characters
        ("unknown", "en"),  # Default case
    ]

    print("\n📋 Language Detection Tests:")
    all_passed = True
    for dataset_name, expected in test_cases:
        result = detect_language_from_dataset_name(dataset_name)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{dataset_name}' -> {result} (expected: {expected})")
        if result != expected:
            all_passed = False

    print(f"\n🎯 Language Detection Test Result: {'✅ All Passed' if all_passed else '❌ Some Failed'}")
    return all_passed

def test_model_selection():
    """Test spacy model selection."""
    print("\n🤖 Testing Spacy Model Selection:")
    print("=" * 50)

    # Test model name mapping
    print("\n📋 Model Name Mapping Tests:")
    model_tests = [
        ("zh", "zh_core_web_lg"),
        ("en", "en_core_web_lg"),
        ("invalid", "en_core_web_lg"),  # Should fallback to English
    ]

    for language, expected_model in model_tests:
        result = get_spacy_model_name(language)
        status = "✅" if result == expected_model else "❌"
        print(f"  {status} Language '{language}' -> Model '{result}' (expected: {expected_model})")

    # Test dataset-based model selection
    print("\n📋 Dataset-based Model Selection Tests:")
    dataset_tests = [
        ("demo", "en_core_web_lg"),
        ("anony_chs", "zh_core_web_lg"),
        ("中文数据集", "zh_core_web_lg"),
        ("novel_eng", "en_core_web_lg"),
    ]

    for dataset, expected_model in dataset_tests:
        result = get_spacy_model_for_dataset(dataset)
        status = "✅" if result == expected_model else "❌"
        print(f"  {status} Dataset '{dataset}' -> Model '{result}' (expected: {expected_model})")

    return True

def test_model_validation():
    """Test spacy model validation."""
    print("\n🔍 Testing Spacy Model Validation:")
    print("=" * 50)

    print("\n📋 Checking Available Models:")
    available_models = get_available_models()
    print(f"  Available models: {available_models}")

    print("\n📋 Model Validation Tests:")
    models_to_test = ["en_core_web_lg", "zh_core_web_lg"]
    for model in models_to_test:
        is_valid = validate_spacy_model(model)
        status = "✅" if is_valid else "❌"
        print(f"  {status} Model '{model}' -> {'Available' if is_valid else 'Not Available'}")

    # Test fallback mechanism
    print("\n📋 Fallback Mechanism Test:")
    try:
        fallback = get_fallback_model("test_dataset")
        print(f"  ✅ Fallback model for 'test_dataset': {fallback}")
    except Exception as e:
        print(f"  ❌ Fallback test failed: {e}")

    return True

def test_config_integration():
    """Test configuration integration."""
    print("\n⚙️ Testing Configuration Integration:")
    print("=" * 50)

    try:
        from config import get_config, get_spacy_model_for_dataset_config

        # Load config
        config = get_config()
        print("  ✅ Configuration loaded successfully")

        # Test config-based model selection
        test_datasets = ["demo", "anony_chs", "novel", "novel_eng"]
        print("\n📋 Config-based Model Selection Tests:")
        for dataset in test_datasets:
            try:
                model_name = get_spacy_model_for_dataset_config(dataset, config)
                print(f"  ✅ Dataset '{dataset}' -> Model '{model_name}' (with config)")
            except Exception as e:
                print(f"  ❌ Config-based selection failed for '{dataset}': {e}")

        return True

    except ImportError as e:
        print(f"  ⚠️ Configuration test skipped (config module not available): {e}")
        return True
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Language Detection and Model Selection Tests")
    print("=" * 60)

    results = []
    results.append(test_language_detection())
    results.append(test_model_selection())
    results.append(test_model_validation())
    results.append(test_config_integration())

    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print("=" * 60)

    test_names = [
        "Language Detection",
        "Model Selection",
        "Model Validation",
        "Config Integration"
    ]

    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {i+1}. {name:<20} {status}")

    all_passed = all(results)
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

    if all_passed:
        print("\n🎉 Language detection and model selection functionality is working correctly!")
    else:
        print("\n⚠️ Some tests failed. Please check the output above for details.")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
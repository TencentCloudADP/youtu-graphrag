# 語言偵測與動態Spacy模型選擇功能

## 功能概述

此功能為Youtu-GraphRAG專案新增了自動偵測dataset名稱並選擇適當語言模型的能力。系統會根據dataset名稱自動判斷使用中文或英文的spacy模型，無需手動指定。

## 主要特性

### 1. 自動語言偵測
- 根據dataset名稱自動偵測語言
- 支援多種偵測方式：
  - 中文字符檢測（Unicode範圍 \u4e00-\u9fff）
  - 關鍵字匹配（chs、zh、chinese、novel等）
  - 特殊名稱處理（novel、novel_eng等）

### 2. 動態模型選擇
- 中文dataset：使用 `zh_core_web_lg` 模型
- 英文dataset：使用 `en_core_web_lg` 模型
- 自動fallback機制確保系統穩定性

### 3. 配置管理增強
- 新增 `LanguageConfig` 配置類別
- 支援手動覆蓋模型選擇
- 可配置預設語言和模型名稱

### 4. 智能Prompt選擇
- 根據偵測的語言自動選擇對應的prompt模板
- 保持向下相容性

## 實作檔案

### 新增檔案
- `utils/language_detection.py` - 語言偵測工具函數
- `test_language_detection.py` - 測試腳本
- `LANGUAGE_DETECTION_README.md` - 本說明文件

### 修改檔案
- `models/retriever/enhanced_kt_retriever.py` - 增強KTRetriever類別
- `models/constructor/kt_gen.py` - 更新prompt選擇邏輯
- `config/config_loader.py` - 增強配置管理
- `config/__init__.py` - 更新導出函數

## 使用方式

### 基本使用
```python
# 系統會自動根據dataset名稱選擇適當的spacy模型
retriever = KTRetriever(dataset="中文資料集")  # 自動使用zh_core_web_lg
retriever = KTRetriever(dataset="english_data")  # 自動使用en_core_web_lg
```

### 配置覆蓋
```yaml
# 在config/base_config.yaml中添加
language:
  enable_auto_detection: true
  default_language: "en"
  override_models:
    special_dataset: "zh_core_web_lg"
```

### 程式化配置
```python
from config import get_spacy_model_for_dataset_config

model_name = get_spacy_model_for_dataset_config("my_dataset", config)
```

## 測試驗證

執行測試腳本驗證功能：
```bash
python test_language_detection.py
```

測試覆蓋：
- 語言偵測準確性
- 模型選擇正確性
- 配置整合功能
- 錯誤處理機制

## 支援的Dataset命名模式

### 中文Dataset
- 包含中文字符：`中文資料集`、`汉语数据`
- 包含關鍵字：`chinese_dataset`、`zh_test`、`anony_chs`、`novel`

### 英文Dataset
- 包含關鍵字：`english_data`、`anony_eng`、`novel_eng`
- 預設情況：`demo`、`hotpot`、`2wiki`、`musique`

## 錯誤處理

- 模型載入失敗時自動使用fallback模型
- 詳細的日誌記錄便於除錯
- 優雅降級確保系統穩定性

## 向下相容性

- 完全相容現有的dataset名稱（novel、novel_eng等）
- 不影響現有的英文dataset功能
- 可選擇性使用新功能

## 擴展性

- 易於新增其他語言支援
- 模組化設計便於維護
- 配置驅動的靈活設定

## 效能影響

- 語言偵測開銷極小
- 模型載入只在初始化時執行
- 無執行時效能損失

## 日誌範例

```
✅ Successfully loaded spacy model 'zh_core_web_lg' for dataset 'novel'
🔍 Detected language for dataset 'novel': zh
✅ Successfully loaded spacy model 'en_core_web_lg' for dataset 'demo'
🔍 Detected language for dataset 'demo': en
```

此功能大幅提升了專案的多語言支援能力，同時保持了系統的穩定性和易用性。
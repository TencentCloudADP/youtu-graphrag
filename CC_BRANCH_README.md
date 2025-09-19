# CC 分支說明文檔

## 概述

CC (Cross-Cultural) 分支是在 main 分支基礎上擴展的功能分支，主要增加了**自動語言檢測**和**智能化模型選擇**功能。該分支旨在提升 Youtu-GraphRAG 在多語言環境下的用戶體驗和系統智能化程度。

## 與 Main 分支的核心差異

### 1. 自動語言檢測系統

#### 新增檔案
- `utils/language_detection.py` - 核心語言檢測模組
- `test_language_detection.py` - 語言檢測測試套件
- `LANGUAGE_DETECTION_README.md` - 語言檢測功能詳細說明

#### 主要功能
- **智能語言識別**：根據數據集名稱自動檢測中文/英文
- **多種檢測策略**：
  - 中文字符模式匹配（Unicode 範圍 `\u4e00-\u9fff`）
  - 關鍵詞匹配（中文：`novel`, `zh`, `chs`, `cn`；英文：`en`, `eng`, `english`）
  - 特殊案例處理（如 `novel_eng` → 英文，`novel` → 中文）
- **後備機制**：默認選擇英文，確保系統穩定性

### 2. 動態 Spacy 模型選擇

#### 修改檔案
- `models/retriever/enhanced_kt_retriever.py`

#### 主要改進
- **自動模型載入**：根據檢測到的語言自動選擇對應的 spacy 模型
  - 中文：`zh_core_web_lg`
  - 英文：`en_core_web_lg`
- **錯誤處理機制**：
  - 模型不存在時自動嘗試後備模型
  - 詳細的日誌記錄和錯誤信息
  - 優雅的降級處理
- **配置覆蓋支持**：允許通過配置文件覆蓋特定數據集的模型選擇

### 3. 智能提示詞選擇

#### 修改檔案
- `models/constructor/kt_gen.py`

#### 主要改進
- **語言感知提示詞**：
  - 中文數據集：優先使用 `chinese` 或 `chinese_agent` 提示詞
  - 英文數據集：優先使用 `english` 或 `english_agent` 提示詞
- **後備邏輯**：當語言特定提示詞不存在時，回退到原有的映射邏輯
- **Agent 模式兼容**：完全保留並兼容 main 分支的 agent/noagent 模式架構

### 4. 配置系統擴展

#### 修改檔案
- `config/config_loader.py`
- `config/__init__.py`

#### 新增功能
- **LanguageConfig 類**：
  ```python
  @dataclass
  class LanguageConfig:
      enable_auto_detection: bool = True
      default_language: str = "en"
      override_models: Dict[str, str] = None
      chinese_model: str = "zh_core_web_lg"
      english_model: str = "en_core_web_lg"
  ```
- **配置函數**：
  - `get_spacy_model_for_dataset_config()` - 基於配置的智能模型選擇
- **配置驗證**：擴展了配置驗證邏輯以支持語言相關設置

### 5. 環境和依賴更新

#### 修改檔案
- `setup_env.sh` - 更新依賴安裝腳本
- `.gitignore` - 新增測試和緩存文件的忽略規則

## 使用示例

### 自動語言檢測
```python
from utils.language_detection import detect_language_from_dataset_name

# 自動檢測
print(detect_language_from_dataset_name("novel"))        # 輸出: zh
print(detect_language_from_dataset_name("novel_eng"))   # 輸出: en
print(detect_language_from_dataset_name("hotpot"))      # 輸出: en
```

### 配置覆蓋示例
```yaml
# config/base_config.yaml
language:
  enable_auto_detection: true
  default_language: "en"
  override_models:
    special_dataset: "zh_core_web_sm"  # 特定數據集使用指定模型
  chinese_model: "zh_core_web_lg"
  english_model: "en_core_web_lg"
```

## 更新 CC 分支的流程

### 當需要從 upstream/main 更新時

由於 CC 分支包含大量自定義功能，推薦使用以下策略保持與 main 分支同步：

#### 方法 1：Rebase 策略（推薦）
```bash
# 1. 切換到 CC 分支
git checkout CC

# 2. 獲取最新的 upstream 更新
git fetch upstream

# 3. 以 main 為基礎重新應用 CC 分支的更改
git rebase upstream/main

# 4. 如果有衝突，手動解決後繼續
#    - 衝突通常發生在配置文件和核心功能文件
#    - 優先保留 CC 分支的自動化功能
#    - 確保 main 分支的新功能被正確整合
git add .
git rebase --continue

# 5. 推送到您的 fork
git push origin CC --force-with-lease
```

#### 方法 2：Merge 策略（適合大量衝突）
```bash
# 1. 創建臨時分支跟踪 upstream/main
git checkout -b temp-main upstream/main

# 2. 將 CC 分支合併到臨時分支
git merge CC --no-edit

# 3. 解決衝突並測試
#    - 確保所有自動化功能正常工作
#    - 驗證 main 分支的新功能被保留

# 4. 將結果合併回 CC 分支
git checkout CC
git merge temp-main

# 5. 清理並推送
git branch -d temp-main
git push origin CC
```

### 衝突解決指南

#### 常見衝突類型

1. **配置系統衝突** (`config/config_loader.py`)
   - **解決策略**：保留 CC 分支的 `LanguageConfig` 和相關函數
   - **關鍵代碼**：確保 `get_spacy_model_for_dataset_config()` 函數被保留

2. **構造器衝突** (`models/constructor/kt_gen.py`)
   - **解決策略**：保留 `_get_construction_prompt()` 中的語言檢測邏輯
   - **關鍵代碼**：確保 `from utils.language_detection import detect_language_from_dataset_name` 被保留

3. **檢索器衝突** (`models/retriever/enhanced_kt_retriever.py`)
   - **解決策略**：保留自動 spacy 模型選擇的完整邏輯
   - **關鍵代碼**：保留包含 `get_spacy_model_for_dataset_config()` 的 try-catch 塊

#### 衝突解決步驟
1. 識別衝突標記 (`<<<<<<<`, `=======`, `>>>>>>>`)
2. 分析雙方的更改內容
3. **優先保留 CC 分支的自動化功能**
4. 整合 main 分支的新功能和修復
5. 測試確保功能完整性

### 驗證更新結果

更新完成後，運行以下測試確保功能正常：

```bash
# 測試語言檢測功能
python -c "
from utils.language_detection import detect_language_from_dataset_name
print('Language detection tests:')
print('novel:', detect_language_from_dataset_name('novel'))
print('novel_eng:', detect_language_from_dataset_name('novel_eng'))
print('hotpot:', detect_language_from_dataset_name('hotpot'))
"

# 運行完整測試套件
python test_language_detection.py

# 測試構建功能（如有測試數據）
python main.py --datasets demo --override '{"triggers": {"constructor_trigger": true}}'
```

## 最佳實踐

### 開發工作流
1. **日常開發**：在 CC 分支上進行開發
2. **同步更新**：定期從 upstream/main 更新（建議每週）
3. **測試驗證**：每次更新後運行完整測試
4. **文檔更新**：及時更新此文檔記錄重要變更

### 功能擴展
- 添加新語言支持時，擴展 `utils/language_detection.py`
- 修改提示詞模板時，確保中英文版本都存在
- 配置新數據集時，考慮語言檢測規則

### 性能優化
- 語言檢測結果可考慮緩存
- spacy 模型載入可考慮延遲加載
- 配置驗證可添加語言相關的檢查

## 故障排除

### 常見問題
1. **Spacy 模型載入失敗**
   - 確保已安裝對應的 spacy 模型
   - 檢查 `setup_env.sh` 是否正確執行
   - 查看日誌中的後備機制是否生效

2. **語言檢測錯誤**
   - 檢查數據集名稱是否符合預期格式
   - 驗證 `utils.language_detection` 中的關鍵詞列表
   - 考慮使用配置覆蓋功能

3. **提示詞模板缺失**
   - 確保配置文件中包含對應的提示詞定義
   - 檢查後備邏輯是否正確處理異常
   - 驗證 agent 模式下的提示詞命名規範

### 調試技巧
- 啟用詳細日誌：`logging.basicConfig(level=logging.INFO)`
- 使用測試腳本驗證功能：`python test_language_detection.py`
- 檢查配置文件：`python -c "from config import get_config; print(get_config().language)"`

## 總結

CC 分支通過引入自動語言檢測和智能化模型選擇，顯著提升了 Youtu-GraphRAG 的多語言支持能力。在與 main 分支保持同步時，重點是保留這些自動化功能，同時整合 main 分支的最新改進和修復。

通過遵循本文檔的更新流程和最佳實踐，可以確保 CC 分支始終處於最佳狀態，為用戶提供優質的多語言圖譜構建和檢索體驗。
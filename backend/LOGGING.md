# ログシステム / Logging System

## 概要 / Overview

このプロジェクトでは、Pythonの標準`logging`モジュールを使用した統一ロギングシステムを実装しています。
This project implements a unified logging system using Python's standard `logging` module.

## ログレベル / Log Levels

環境変数 `LOG_LEVEL` でログレベルを制御できます。
You can control the log level using the `LOG_LEVEL` environment variable.

### レベル一覧 / Available Levels

| レベル | 用途 | 表示内容 |
|--------|------|----------|
| `DEBUG` | 開発・デバッグ時 | すべてのログ（データ抽出の詳細、内部処理など） |
| `INFO` | 本番環境（デフォルト） | 重要な情報のみ（データ保存、エラー、ユーザー操作） |
| `WARNING` | 警告のみ | 警告とエラー |
| `ERROR` | エラーのみ | エラーのみ |

| Level | Purpose | Output |
|-------|---------|--------|
| `DEBUG` | Development/Debugging | All logs (extraction details, internal processing, etc.) |
| `INFO` | Production (Default) | Important information only (data saved, errors, user actions) |
| `WARNING` | Warnings only | Warnings and errors |
| `ERROR` | Errors only | Errors only |

### ログレベルの設定 / Setting Log Level

```bash
# 本番環境 - 重要な情報のみ表示 / Production - Show important info only
export LOG_LEVEL=INFO
python app.py

# 開発環境 - 詳細なデバッグ情報を表示 / Development - Show detailed debug info
export LOG_LEVEL=DEBUG
python app.py

# エラーのみ表示 / Show errors only
export LOG_LEVEL=ERROR
python app.py
```

## ログカテゴリー / Log Categories

各ログメッセージには12文字のカテゴリー名が付与されます。
Each log message is tagged with a 12-character category name.

### カテゴリー一覧 / Category List

| カテゴリー | 説明 | ログレベル | 表示例 |
|-----------|------|-----------|--------|
| `System` | システム起動・設定 | INFO | `[INFO ] [System      ] ✓ LM Studio is connected!` |
| `API` | APIエンドポイント処理 | INFO/DEBUG | `[DEBUG] [API         ] Calling get_response with 5 messages` |
| `Data` | データ保存・更新 | INFO | `[INFO ] [Data        ] Saved: 基本プロフィール > 名前 = 田中` |
| `Extraction` | データ抽出処理 | DEBUG | `[DEBUG] [Extraction  ] Found 3 data points` |
| `LMStudio` | LM Studio通信 | INFO/ERROR | `[ERROR] [LMStudio    ] LM Studio error: 500` |
| `Validation` | データ検証 | INFO/WARNING | `[INFO ] [Validation  ] Data rejected: [矛盾...]` |
| `Normalize` | キー正規化 | DEBUG | `[DEBUG] [Normalize   ] 基本プロフィール/職業: '仕事' → 職業` |
| `Undo` | Undo操作 | INFO | `[INFO ] [Undo        ] Successfully removed last turn` |
| `Correction` | 訂正・削除検出 | INFO/DEBUG | `[INFO ] [Correction  ] User requested deletion` |
| `Async` | 非同期処理 | INFO/DEBUG | `[INFO ] [Async       ] Data extraction completed` |
| `Debug` | その他デバッグ情報 | DEBUG | `[DEBUG] [Debug       ] Found user name in session data` |

| Category | Description | Log Level | Example |
|----------|-------------|-----------|---------|
| `System` | System startup and configuration | INFO | `[INFO ] [System      ] ✓ LM Studio is connected!` |
| `API` | API endpoint processing | INFO/DEBUG | `[DEBUG] [API         ] Calling get_response with 5 messages` |
| `Data` | Data save/update operations | INFO | `[INFO ] [Data        ] Saved: 基本プロフィール > 名前 = 田中` |
| `Extraction` | Data extraction processing | DEBUG | `[DEBUG] [Extraction  ] Found 3 data points` |
| `LMStudio` | LM Studio communication | INFO/ERROR | `[ERROR] [LMStudio    ] LM Studio error: 500` |
| `Validation` | Data validation | INFO/WARNING | `[INFO ] [Validation  ] Data rejected: [contradiction...]` |
| `Normalize` | Key normalization | DEBUG | `[DEBUG] [Normalize   ] 基本プロフィール/職業: '仕事' → 職業` |
| `Undo` | Undo operations | INFO | `[INFO ] [Undo        ] Successfully removed last turn` |
| `Correction` | Correction/deletion detection | INFO/DEBUG | `[INFO ] [Correction  ] User requested deletion` |
| `Async` | Asynchronous processing | INFO/DEBUG | `[INFO ] [Async       ] Data extraction completed` |
| `Debug` | Other debug information | DEBUG | `[DEBUG] [Debug       ] Found user name in session data` |

## ログフォーマット / Log Format

```
[時刻] [レベル] [カテゴリー] メッセージ
[Time] [Level] [Category  ] Message
```

### 例 / Examples

```
[15:30:45] [INFO ] [System      ] Interview System Backend Starting...
[15:30:46] [INFO ] [System      ] ✓ LM Studio is connected!
[15:30:47] [INFO ] [Data        ] Saved: 基本プロフィール > 名前 > 名前 = 田中太郎
[15:30:48] [DEBUG] [Extraction  ] Found 3 data points
[15:30:49] [DEBUG] [Extraction  ] After splitting: 5 data points
[15:30:50] [INFO ] [Async       ] Data extraction completed for session abc123
[15:30:51] [ERROR] [LMStudio    ] LM Studio error: 500
```

## 使用方法 / Usage

### コード内での使用 / Usage in Code

```python
from logger import get_logger

# ロガーを取得 / Get logger
log_data = get_logger('Data')
log_api = get_logger('API')

# ログ出力 / Output logs
log_data.info(f"Saved: {category} > {key} = {value}")
log_api.debug(f"Calling get_response with {len(messages)} messages")
log_api.error(f"LM Studio connection failed: {error}")
```

### ログレベルの動的変更 / Dynamic Log Level Change

```python
from logger import set_log_level

# 開発中にデバッグモードに切り替え / Switch to debug mode during development
set_log_level('DEBUG')

# 本番環境に戻す / Return to production mode
set_log_level('INFO')
```

## ログ出力の指針 / Logging Guidelines

### INFOレベル（本番環境で表示） / INFO Level (Shown in Production)

- ✅ **表示すべき** / **Should show:**
  - データの保存・更新
  - ユーザーの重要な操作（削除、訂正、Undo）
  - システムの起動・停止
  - エラーや警告
  - 非同期処理の完了

- ❌ **表示すべきでない** / **Should NOT show:**
  - 内部処理の詳細
  - データ抽出の中間状態
  - LLMへのプロンプト内容
  - 重複データのスキップ

### DEBUGレベル（開発環境でのみ表示） / DEBUG Level (Development Only)

- データ抽出の詳細な進行状況
- LLMとの通信内容
- 正規化・バリデーションの詳細
- 内部ロジックのフロー
- パフォーマンスデバッグ情報

## 旧ログシステムからの移行 / Migration from Old Logging System

### 変更点 / Changes

| 旧システム | 新システム |
|-----------|-----------|
| `print("[Data] ...")` | `log_data.info("...")` |
| `print("[DEBUG] ...")` | `log_xxx.debug("...")` |
| `print("[ERROR] ...")` | `log_xxx.error("...")` |
| `print("[WARNING] ...")` | `log_xxx.warning("...")` |

### 移行済みファイル / Migrated Files

- ✅ `backend/app.py` - 全てのログを移行済み
- ✅ `backend/interviewer.py` - 全てのログを移行済み
- ✅ `backend/profile_manager.py` - 全てのログを移行済み

## トラブルシューティング / Troubleshooting

### ログが表示されない / Logs Not Showing

```bash
# 環境変数を確認 / Check environment variable
echo $LOG_LEVEL

# DEBUGレベルに設定 / Set to DEBUG level
export LOG_LEVEL=DEBUG
python app.py
```

### ログが多すぎる / Too Many Logs

```bash
# INFOレベルに設定（デフォルト）/ Set to INFO level (default)
export LOG_LEVEL=INFO
python app.py
```

### エラーのみ表示したい / Show Only Errors

```bash
export LOG_LEVEL=ERROR
python app.py
```

## 技術仕様 / Technical Specifications

### ロガーモジュール / Logger Module

ファイル: `backend/logger.py`

- **フォーマッター**: カスタムColoredFormatter
- **出力先**: 標準出力（stdout）
- **カラー**: ANSIカラーコード対応
- **タイムスタンプ**: HH:MM:SS形式

### カラーコード / Color Codes

| レベル | カラー |
|--------|--------|
| DEBUG | シアン（Cyan） |
| INFO | 緑（Green） |
| WARNING | 黄（Yellow） |
| ERROR | 赤（Red） |
| CRITICAL | マゼンタ（Magenta） |

| Level | Color |
|-------|-------|
| DEBUG | Cyan |
| INFO | Green |
| WARNING | Yellow |
| ERROR | Red |
| CRITICAL | Magenta |

## 今後の拡張 / Future Enhancements

### ファイル出力 / File Output

将来的には、ログをファイルにも出力することを検討しています。
Future consideration: Output logs to files as well.

```python
# 将来の実装例 / Future implementation example
file_handler = logging.FileHandler('interview_system.log')
logger.addHandler(file_handler)
```

### ログローテーション / Log Rotation

大量のログを管理するために、ログローテーションを実装する予定です。
Plan to implement log rotation to manage large volumes of logs.

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'interview_system.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

## まとめ / Summary

- 🎯 **本番環境**: `LOG_LEVEL=INFO`（デフォルト）
- 🔍 **開発環境**: `LOG_LEVEL=DEBUG`
- 🎨 **カラー対応**: ターミナルで見やすい色分け
- 📝 **12文字カテゴリー**: 一目で分かるログ分類
- 🚀 **高速**: 標準loggingモジュール使用

---

**Production**: `LOG_LEVEL=INFO` (default)
**Development**: `LOG_LEVEL=DEBUG`
**Color-coded**: Easy to read in terminal
**12-char categories**: Clear log classification
**Fast**: Uses standard logging module

"""
統一ロギングシステム / Unified Logging System

環境変数 LOG_LEVEL で制御:
- INFO (デフォルト): 重要な情報のみ
- DEBUG: 詳細なデバッグ情報
- ERROR: エラーのみ
"""

import logging
import os
import sys
from datetime import datetime

# ログレベル設定（環境変数から取得、デフォルトはINFO）
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# カスタムフォーマッター
class ColoredFormatter(logging.Formatter):
    """ターミナルで色付きログを表示するフォーマッター"""

    # ANSIカラーコード
    COLORS = {
        'DEBUG': '\033[36m',    # シアン
        'INFO': '\033[32m',     # 緑
        'WARNING': '\033[33m',  # 黄
        'ERROR': '\033[31m',    # 赤
        'CRITICAL': '\033[35m', # マゼンタ
    }
    RESET = '\033[0m'

    def format(self, record):
        # ログレベルに応じた色を適用
        color = self.COLORS.get(record.levelname, self.RESET)

        # タイムスタンプ
        timestamp = datetime.now().strftime('%H:%M:%S')

        # カテゴリー（ロガー名から抽出）
        category = record.name.split('.')[-1] if '.' in record.name else record.name

        # フォーマット: [時刻] [レベル] [カテゴリー] メッセージ
        formatted = f"[{timestamp}] {color}[{record.levelname:5s}]{self.RESET} [{category:12s}] {record.getMessage()}"

        # 例外情報がある場合は追加
        if record.exc_info:
            formatted += '\n' + self.formatException(record.exc_info)

        return formatted


def setup_logger(name: str) -> logging.Logger:
    """
    統一されたロガーを作成

    Args:
        name: ロガー名（通常は __name__ を使用）

    Returns:
        設定済みのロガー
    """
    logger = logging.getLogger(name)

    # すでに設定済みの場合はスキップ
    if logger.handlers:
        return logger

    # ログレベル設定
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logger.setLevel(level)

    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())

    logger.addHandler(console_handler)

    # 親ロガーへの伝播を無効化（重複出力を防ぐ）
    logger.propagate = False

    return logger


# ログレベル簡易設定関数
def set_log_level(level: str):
    """
    ログレベルを動的に変更

    Args:
        level: ログレベル ('DEBUG', 'INFO', 'WARNING', 'ERROR')
    """
    global LOG_LEVEL
    LOG_LEVEL = level.upper()

    log_level = getattr(logging, LOG_LEVEL, logging.INFO)

    # すべての既存ロガーのレベルを更新
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        for handler in logger.handlers:
            handler.setLevel(log_level)


# カテゴリー別ロガーの事前定義（主要モジュール用）
def get_logger(category: str) -> logging.Logger:
    """
    カテゴリー別ロガーを取得

    主要カテゴリー:
    - System: システム起動・設定
    - API: APIエンドポイント
    - Data: データ保存・更新
    - Extraction: データ抽出処理
    - LMStudio: LM Studio通信
    - Session: セッション管理
    - Validation: データ検証
    - Normalization: キー正規化
    - Undo: Undo操作
    - Correction: 訂正・削除検出
    - Debug: その他デバッグ情報

    Args:
        category: カテゴリー名

    Returns:
        設定済みのロガー
    """
    return setup_logger(f'interview.{category}')


# 起動時にログレベルを表示
if __name__ != '__main__':
    startup_logger = get_logger('System')
    startup_logger.info(f"Logging initialized (level: {LOG_LEVEL})")

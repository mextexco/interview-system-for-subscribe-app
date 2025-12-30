"""
プロファイル管理: ユーザープロファイルとセッションデータの保存・読み込み
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from config import PROFILES_DIR, SESSIONS_DIR, CATEGORIES
from data_validator import DataValidator


class ProfileManager:
    """ユーザープロファイルとセッションを管理するクラス"""

    def __init__(self):
        # データディレクトリの作成
        os.makedirs(PROFILES_DIR, exist_ok=True)
        os.makedirs(SESSIONS_DIR, exist_ok=True)

    def create_user(self, name: str, gender: str, character: str) -> Dict:
        """新規ユーザープロファイルを作成"""
        user_id = str(uuid.uuid4())
        profile = {
            "user_id": user_id,
            "name": name,
            "gender": gender,
            "character": character,
            "created_at": datetime.now().isoformat(),
            "badges": [],
            "total_data_count": 0,
            "sessions": []
        }

        # プロファイル保存
        self._save_profile(user_id, profile)
        return profile

    def get_user(self, user_id: str) -> Optional[Dict]:
        """ユーザープロファイルを取得"""
        profile_path = os.path.join(PROFILES_DIR, f"{user_id}.json")
        if not os.path.exists(profile_path):
            return None

        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def update_user(self, user_id: str, updates: Dict) -> Dict:
        """ユーザープロファイルを更新"""
        profile = self.get_user(user_id)
        if not profile:
            raise ValueError(f"User {user_id} not found")

        profile.update(updates)
        profile["updated_at"] = datetime.now().isoformat()
        self._save_profile(user_id, profile)
        return profile

    def create_session(self, user_id: str) -> Dict:
        """新規セッションを作成"""
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "date": datetime.now().isoformat(),
            "conversation": [],
            "extracted_data": {cat: [] for cat in CATEGORIES.keys()},
            "events_triggered": [],
            "reactions": {
                "small": 0,
                "medium": 0,
                "large": 0
            }
        }

        # セッション保存
        self._save_session(session_id, session)

        # ユーザープロファイルにセッションIDを追加
        profile = self.get_user(user_id)
        if profile:
            profile["sessions"].append(session_id)
            self._save_profile(user_id, profile)

        return session

    def get_session(self, session_id: str) -> Optional[Dict]:
        """セッションを取得"""
        session_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if not os.path.exists(session_path):
            return None

        with open(session_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def update_session(self, session_id: str, updates: Dict) -> Dict:
        """セッションを更新"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.update(updates)
        session["updated_at"] = datetime.now().isoformat()
        self._save_session(session_id, session)
        return session

    def add_message(self, session_id: str, role: str, content: str,
                   expression: str = "normal") -> Dict:
        """会話メッセージを追加"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

        if role == "assistant":
            message["expression"] = expression

        session["conversation"].append(message)
        self._save_session(session_id, session)
        return session

    def add_extracted_data(self, session_id: str, category: str,
                          key: str, value: any) -> Dict:
        """
        抽出したプロファイリングデータを追加
        Add extracted profiling data with validation
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if category not in session["extracted_data"]:
            session["extracted_data"][category] = []

        # データバリデーションを実行 / Validate data
        validator = DataValidator()
        existing_data = session["extracted_data"][category]
        all_data = session["extracted_data"]  # カテゴリーをまたいだ矛盾検出用

        validation_result = validator.validate_data_point(
            category, key, value, existing_data, all_data
        )

        # 矛盾がある場合はスキップ / Skip if contradictions found
        if not validation_result["valid"]:
            contradictions = validation_result.get("contradictions", [])
            print(f"[Validation] Data rejected: {contradictions}")
            for contradiction in contradictions:
                print(f"  - {contradiction}")

            # 矛盾データは保存しない / Don't save contradictory data
            return session

        # 警告がある場合はログ出力 / Log warnings if any
        warnings = validation_result.get("warnings", [])
        if warnings:
            print(f"[Validation] Warnings for {category}/{key}:")
            for warning in warnings:
                print(f"  - {warning}")

        # 値を正規化 / Normalize value
        normalized_value = validator.normalize_value(category, key, value)

        # 正規化が行われたかチェック / Check if normalization occurred
        normalization_occurred = normalized_value != value
        if normalization_occurred:
            print(f"[Normalization] {category}/{key}: '{value}' → {normalized_value}")

        # 重複チェック / Check for duplicates
        # 同じカテゴリー・キー・値の組み合わせが既に存在する場合はスキップ
        for existing_item in existing_data:
            if existing_item.get("key") == key:
                existing_value = existing_item.get("value")

                # 値の比較（正規化された値同士で比較）
                if self._values_are_equal(normalized_value, existing_value):
                    print(f"[Duplicate] Skipping duplicate data: {category}/{key} = {value}")
                    return session

        # データエントリ作成 / Create data entry
        data_entry = {
            "key": key,
            "value": normalized_value,
            "timestamp": datetime.now().isoformat(),
            "data_version": "2.0"  # バージョン追跡
        }

        # 正規化が行われた場合は元の値も保存 / Save original value if normalized
        if normalization_occurred:
            data_entry["original_value"] = value

        # バリデーション情報を追加（オプション） / Add validation info (optional)
        if warnings:
            data_entry["validation_warnings"] = warnings

        session["extracted_data"][category].append(data_entry)
        self._save_session(session_id, session)

        return session

    def _values_are_equal(self, value1: any, value2: any) -> bool:
        """
        2つの値が等しいかチェック
        Check if two values are equal (handles both simple types and dict/list)
        """
        # 両方とも辞書型の場合
        if isinstance(value1, dict) and isinstance(value2, dict):
            # originalフィールドで比較（正規化された値の場合）
            v1_original = value1.get("original", value1)
            v2_original = value2.get("original", value2)
            return str(v1_original).strip().lower() == str(v2_original).strip().lower()

        # 文字列として比較（大文字小文字を無視、前後の空白を除去）
        return str(value1).strip().lower() == str(value2).strip().lower()

    def get_category_data_count(self, user_id: str) -> Dict[str, int]:
        """各カテゴリーのデータ数を取得"""
        profile = self.get_user(user_id)
        if not profile:
            return {}

        category_counts = {cat: 0 for cat in CATEGORIES.keys()}

        for session_id in profile["sessions"]:
            session = self.get_session(session_id)
            if session:
                for category, data_list in session["extracted_data"].items():
                    category_counts[category] += len(data_list)

        return category_counts

    def get_total_data_count(self, user_id: str) -> int:
        """総データ数を取得"""
        category_counts = self.get_category_data_count(user_id)
        return sum(category_counts.values())

    def get_empty_categories(self, user_id: str) -> List[str]:
        """データが空のカテゴリーを取得"""
        category_counts = self.get_category_data_count(user_id)
        return [cat for cat, count in category_counts.items() if count == 0]

    def add_badge(self, user_id: str, badge_name: str) -> Dict:
        """バッジを追加"""
        profile = self.get_user(user_id)
        if not profile:
            raise ValueError(f"User {user_id} not found")

        if badge_name not in profile["badges"]:
            profile["badges"].append(badge_name)
            self._save_profile(user_id, profile)

        return profile

    def _save_profile(self, user_id: str, profile: Dict):
        """プロファイルをファイルに保存"""
        profile_path = os.path.join(PROFILES_DIR, f"{user_id}.json")
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)

    def _save_session(self, session_id: str, session: Dict):
        """セッションをファイルに保存"""
        session_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(session, f, ensure_ascii=False, indent=2)

    def undo_last_turn(self, session_id: str) -> Dict:
        """最後のターン（ユーザーメッセージ + AIレスポンス）を取り消す"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        conversation = session.get("conversation", [])

        # 会話が2件未満の場合は取り消せない（初期メッセージのみ）
        if len(conversation) < 2:
            print("[Undo] Not enough messages to undo")
            return {"success": False, "message": "取り消せるメッセージがありません"}

        # 最後の2つのメッセージを確認（user → assistant のペア）
        removed_messages = []

        # 最後がassistantの場合
        if conversation[-1]["role"] == "assistant":
            removed_messages.append(conversation.pop())
            assistant_timestamp = removed_messages[0]["timestamp"]
        else:
            print("[Undo] Last message is not from assistant")
            return {"success": False, "message": "最後のメッセージがAIの応答ではありません"}

        # その前がuserの場合
        if conversation and conversation[-1]["role"] == "user":
            removed_messages.append(conversation.pop())
            user_timestamp = removed_messages[1]["timestamp"]
        else:
            # assistantメッセージを戻す
            conversation.append(removed_messages[0])
            print("[Undo] No user message before assistant message")
            return {"success": False, "message": "対応するユーザーメッセージが見つかりません"}

        print(f"[Undo] Removed messages: user at {user_timestamp}, assistant at {assistant_timestamp}")

        # そのターンで抽出されたデータを削除（timestampで判定）
        removed_data_count = 0
        for category in session["extracted_data"]:
            data_list = session["extracted_data"][category]
            # user_timestamp以降に抽出されたデータを削除
            original_count = len(data_list)
            session["extracted_data"][category] = [
                item for item in data_list
                if item.get("timestamp", "") < user_timestamp
            ]
            removed_count = original_count - len(session["extracted_data"][category])
            if removed_count > 0:
                print(f"[Undo] Removed {removed_count} data points from {category}")
                removed_data_count += removed_count

        # セッションを保存
        self._save_session(session_id, session)

        print(f"[Undo] Successfully removed last turn and {removed_data_count} data points")

        return {
            "success": True,
            "message": "最後のやりとりを取り消しました",
            "removed_data_count": removed_data_count,
            "session": session
        }

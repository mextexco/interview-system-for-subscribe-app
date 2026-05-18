"""
mem0を使ったユーザー記憶の管理
"""

import json
import os
from datetime import datetime
from mem0 import MemoryClient
from config import MEM0_API_KEY, DATA_DIR
from logger import get_logger

log_mem = get_logger('Memory')

CACHE_DIR = os.path.join(DATA_DIR, "mem0_cache")


class MemoryManager:
    """mem0クラウドAPIを使った記憶管理クラス"""

    def __init__(self):
        self.client = MemoryClient(api_key=MEM0_API_KEY)
        os.makedirs(CACHE_DIR, exist_ok=True)

    # ------------------------------------------------------------------ #
    # キャッシュ操作
    # ------------------------------------------------------------------ #

    def _cache_path(self, user_id: str) -> str:
        return os.path.join(CACHE_DIR, f"{user_id}.json")

    def read_cache(self, user_id: str) -> dict | None:
        """キャッシュファイルを読む。なければ None を返す"""
        path = self._cache_path(user_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_cache(self, user_id: str, memories: list[dict]) -> None:
        """記憶一覧をキャッシュファイルに書く"""
        data = {
            "user_id": user_id,
            "fetched_at": datetime.now().isoformat(),
            "memories": memories,
        }
        with open(self._cache_path(user_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log_mem.info(f"キャッシュ保存: {user_id} ({len(memories)}件)")

    # ------------------------------------------------------------------ #
    # mem0 API 操作
    # ------------------------------------------------------------------ #

    def get_memories(self, user_id: str) -> list[dict]:
        """mem0から全記憶を取得（API消費あり）"""
        try:
            result = self.client.get_all(filters={"user_id": user_id})
            return result.get("results", [])
        except Exception as e:
            log_mem.error(f"記憶取得エラー: {e}")
            return []

    def get_memories_cached(self, user_id: str) -> dict:
        """
        キャッシュがあればキャッシュから返す（API消費なし）。
        なければ None を返す（呼び出し元が判断）。
        戻り値: {"memories": [...], "fetched_at": "...", "from_cache": bool}
        """
        cached = self.read_cache(user_id)
        if cached:
            return {
                "memories": cached["memories"],
                "fetched_at": cached["fetched_at"],
                "from_cache": True,
            }
        return {"memories": [], "fetched_at": None, "from_cache": False}

    def refresh_memories(self, user_id: str) -> dict:
        """mem0から強制取得してキャッシュを更新する（API消費あり）"""
        memories = self.get_memories(user_id)
        self.write_cache(user_id, memories)
        return {
            "memories": memories,
            "fetched_at": datetime.now().isoformat(),
            "from_cache": False,
        }

    def search_memories(self, user_id: str, query: str, limit: int = 5) -> list[dict]:
        """クエリに関連する記憶を検索"""
        try:
            result = self.client.search(query, filters={"user_id": user_id}, limit=limit)
            return result.get("results", [])
        except Exception as e:
            log_mem.error(f"記憶検索エラー: {e}")
            return []

    def add_memories(self, user_id: str, data_items: list[dict]) -> list[dict]:
        """
        抽出データをmem0に保存し、キャッシュを更新する。
        data_items: [{"category": ..., "key": ..., "value": ..., ...}, ...]
        """
        if not data_items:
            return []

        lines = []
        for item in data_items:
            parts = [item.get("category", "")]
            if item.get("subcategory1"):
                parts.append(item["subcategory1"])
            if item.get("subcategory2"):
                parts.append(item["subcategory2"])
            key = item.get("key", "")
            value = item.get("value", "")
            lines.append(f"[{' > '.join(parts)}] {key}: {value}")

        text = "\n".join(lines)
        log_mem.info(f"mem0に送信するデータ ({user_id}):\n{text}")

        try:
            self.client.add(text, user_id=user_id)
        except Exception as e:
            log_mem.error(f"記憶保存エラー: {e}")
            return []

        # 保存後にキャッシュを更新
        result = self.refresh_memories(user_id)
        return result["memories"]

    def delete_memory(self, memory_id: str) -> bool:
        """指定した記憶を削除"""
        try:
            self.client.delete(memory_id)
            log_mem.info(f"記憶削除: {memory_id}")
            return True
        except Exception as e:
            log_mem.error(f"記憶削除エラー: {e}")
            return False

    def delete_all_memories(self, user_id: str) -> bool:
        """ユーザーの全記憶を削除しキャッシュも消す"""
        try:
            memories = self.get_memories(user_id)
            for mem in memories:
                self.client.delete(mem["id"])
            # キャッシュも削除
            path = self._cache_path(user_id)
            if os.path.exists(path):
                os.remove(path)
            log_mem.info(f"全記憶削除完了: {user_id} ({len(memories)}件)")
            return True
        except Exception as e:
            log_mem.error(f"全記憶削除エラー: {e}")
            return False

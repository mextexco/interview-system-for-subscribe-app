"""
mem0を使ったユーザー記憶の管理
"""

from mem0 import MemoryClient
from config import MEM0_API_KEY
from logger import get_logger

log_mem = get_logger('Memory')


class MemoryManager:
    """mem0クラウドAPIを使った記憶管理クラス"""

    def __init__(self):
        self.client = MemoryClient(api_key=MEM0_API_KEY)

    def find_user_by_name(self, name: str) -> dict | None:
        """名前でユーザーを検索。見つかればユーザー情報を返す"""
        try:
            users = self.client.users()
            for user in users.get("results", []):
                if user.get("name") == name:
                    return user
        except Exception as e:
            log_mem.error(f"ユーザー検索エラー: {e}")
        return None

    def get_memories(self, user_id: str) -> list[dict]:
        """ユーザーの全記憶を取得"""
        try:
            result = self.client.get_all(filters={"user_id": user_id})
            return result.get("results", [])
        except Exception as e:
            log_mem.error(f"記憶取得エラー: {e}")
            return []

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
        抽出データをmem0に保存する。
        data_items: [{"category": ..., "key": ..., "value": ..., "subcategory1": ..., "subcategory2": ...}, ...]
        保存後の記憶一覧を返す。
        """
        if not data_items:
            return []

        # 構造化データをテキストに変換してまとめて送信
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

        # 保存後の記憶を返す
        return self.get_memories(user_id)

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
        """ユーザーの全記憶を削除（ローカル削除と同期用）"""
        try:
            memories = self.get_memories(user_id)
            for mem in memories:
                self.client.delete(mem["id"])
            log_mem.info(f"全記憶削除完了: {user_id} ({len(memories)}件)")
            return True
        except Exception as e:
            log_mem.error(f"全記憶削除エラー: {e}")
            return False

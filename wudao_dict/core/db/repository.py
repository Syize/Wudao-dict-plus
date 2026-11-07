"""新旧本地词典文件的统一查询门面。"""

from os.path import exists
from typing import Literal

from ..config import CREDENCE_DB_FILE, LEGACY_DICT_DB_FILE, WUDAO_DICT_DB_FILE
from .adapter import details_to_legacy_json
from .history import QueryHistoryRepository
from .legacy import LegacyDictionaryRepository
from .wudao import WudaoDictionaryRepository


class LocalDictionaryRepository:
    """优先读取新词典，并在缺词时回退到旧版词典。"""

    def __init__(
        self,
        wudao_db_path: str | None = None,
        legacy_db_path: str | None = None,
        history_db_path: str | None = None,
    ):
        wudao_db_path = wudao_db_path or WUDAO_DICT_DB_FILE
        legacy_db_path = legacy_db_path or LEGACY_DICT_DB_FILE
        history_db_path = history_db_path or CREDENCE_DB_FILE

        self.wudao: WudaoDictionaryRepository | None = None
        self.legacy: LegacyDictionaryRepository | None = None
        self.history: QueryHistoryRepository | None = None

        if exists(wudao_db_path):
            self.wudao = WudaoDictionaryRepository(wudao_db_path)

        if exists(legacy_db_path):
            self.legacy = LegacyDictionaryRepository(legacy_db_path)
        elif self.wudao is None:
            # 没有新词典时维持旧版本的首次启动行为。
            self.legacy = LegacyDictionaryRepository()
        else:
            # 新库独立使用时，历史不能再写入词典内容文件。
            self.history = QueryHistoryRepository(history_db_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_db()

    def close_db(self):
        """关闭已打开的所有本地数据库。"""
        if self.wudao is not None:
            self.wudao.close_db()
        if self.legacy is not None:
            self.legacy.close_db()
        if self.history is not None:
            self.history.close_db()

    def query_word(self, table: Literal["en", "zh"], word: str) -> str:
        """优先查询新词典；缺失时按旧协议回退到 ``dict.db``。"""
        if self.wudao is not None:
            details = self.wudao.lookup(word, table)
            if details:
                return details_to_legacy_json(details, word, table)
        if self.legacy is not None:
            return self.legacy.query_word(table, word)
        return ""

    def insert_word(self, table: Literal["en", "zh"], word_info: str) -> bool:
        """暂按旧格式缓存在线结果，不将其混写进结构化词典。"""
        if self.legacy is not None:
            self.legacy.insert_word(table, word_info)
            return True
        return False

    def record_query(self, word: str):
        """记录成功查询。"""
        if self.history is not None:
            self.history.record_query(word)
        elif self.legacy is not None:
            self.legacy.record_query(word)

    def get_query_history(self, limit: int | None = None) -> list[tuple[str, int]]:
        """读取查询历史。"""
        if self.history is not None:
            return self.history.get_query_history(limit)
        if self.legacy is not None:
            return self.legacy.get_query_history(limit)
        return []


__all__ = ["LocalDictionaryRepository"]

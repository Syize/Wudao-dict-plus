"""不依附于词典内容文件的查询历史存储。"""

import sqlite3
from os import makedirs
from os.path import dirname
from time import time_ns


class QueryHistoryRepository:
    """管理 ``credence.db`` 中的用户查询历史。"""

    def __init__(self, db_path: str):
        parent = dirname(db_path)
        if parent:
            makedirs(parent, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS query_history (
                word TEXT PRIMARY KEY,
                query_count INTEGER NOT NULL DEFAULT 0,
                last_queried_at INTEGER NOT NULL
            )
            """
        )
        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_query_history_rank
            ON query_history (query_count DESC, last_queried_at DESC)
            """
        )
        self.db.commit()

    def close_db(self):
        """关闭历史数据库连接。"""
        self.db.close()

    def record_query(self, word: str):
        """记录一次成功查询。"""
        word = word.strip()
        if not word:
            return
        self.db.execute(
            """
            INSERT INTO query_history (word, query_count, last_queried_at)
            VALUES (?, 1, ?)
            ON CONFLICT(word) DO UPDATE SET
                query_count = query_count + 1,
                last_queried_at = excluded.last_queried_at
            """,
            (word, time_ns()),
        )
        self.db.commit()

    def get_query_history(self, limit: int | None = None) -> list[tuple[str, int]]:
        """获取按频次和最近查询时间排序的历史。"""
        command = """
            SELECT word, query_count
            FROM query_history
            ORDER BY query_count DESC, last_queried_at DESC, word ASC
        """
        values: tuple[int, ...] = ()
        if limit is not None:
            command += " LIMIT ?"
            values = (limit,)
        return self.db.execute(command, values).fetchall()


__all__ = ["QueryHistoryRepository"]

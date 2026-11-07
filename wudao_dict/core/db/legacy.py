"""旧版 ``dict.db`` 的兼容读取与写入实现。"""

import sqlite3
from json import dumps, loads
from os.path import exists
from time import time_ns
from typing import Literal

from rich import print

from ..config import LEGACY_DICT_DB_FILE, ensure_legacy_dict_db
from ..interface import ENWord, ZHWord


class LegacyDictionaryRepository:
    """保持旧 ``en``/``zh`` 表语义的词典仓库。"""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = LEGACY_DICT_DB_FILE
            ensure_legacy_dict_db()

        if not exists(db_path):
            print(f"[red]找不到词典数据库，请检查数据库文件是否存在：[red]{db_path}")
            raise FileNotFoundError(
                f"找不到词典数据库，请检查数据库文件是否存在：{db_path}"
            )

        self.db = sqlite3.connect(db_path)
        self.db_cur = self.db.cursor()
        self._ensure_history_schema()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_db()

    def close_db(self):
        """关闭 SQLite 连接。"""
        self.db.close()

    def _ensure_history_schema(self):
        self.db_cur.execute(
            """
            CREATE TABLE IF NOT EXISTS query_history (
                word TEXT PRIMARY KEY,
                query_count INTEGER NOT NULL DEFAULT 0,
                last_queried_at INTEGER NOT NULL
            )
            """
        )
        self.db_cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_query_history_rank
            ON query_history (query_count DESC, last_queried_at DESC)
            """
        )
        self.db.commit()

    def record_query(self, word: str):
        """记录一次成功查询，并保留输入词的大小写。"""
        history_word = word.strip()
        if not history_word:
            return

        self.db_cur.execute(
            """
            INSERT INTO query_history (word, query_count, last_queried_at)
            VALUES (?, 1, ?)
            ON CONFLICT(word) DO UPDATE SET
                query_count = query_count + 1,
                last_queried_at = excluded.last_queried_at
            """,
            (history_word, time_ns()),
        )
        self.db.commit()

    def get_query_history(self, limit: int | None = None) -> list[tuple[str, int]]:
        """获取按查询次数和最近查询时间排序的历史。"""
        command = """
            SELECT word, query_count
            FROM query_history
            ORDER BY query_count DESC, last_queried_at DESC, word ASC
        """
        values: tuple[int, ...] = ()
        if limit is not None:
            command += " LIMIT ?"
            values = (limit,)
        return self.db_cur.execute(command, values).fetchall()

    def query_word(self, table: Literal["en", "zh"], word: str) -> str:
        """按旧版 JSON 协议查询词语。"""
        if table == "en":
            return query_word_en(self.db_cur, word)
        if table == "zh":
            return query_word_zh(self.db_cur, word)
        raise ValueError(f"未知的语言类型：{table}")

    def insert_word(self, table: Literal["en", "zh"], word_info: str):
        """按旧版 JSON 协议写入在线查询结果。"""
        if table == "en":
            insert_word_en(self.db_cur, word_info)
        elif table == "zh":
            insert_word_zh(self.db_cur, word_info)
        else:
            raise ValueError(f"未知的语言类型：{table}")
        self.db.commit()


def query_word_en(db_cur: sqlite3.Cursor, word: str) -> str:
    """按旧版 ``ENWord`` 格式查询英文词条。"""
    row = db_cur.execute(
        """
        SELECT pronunciation, paraphrase, rank, pattern, sentence
        FROM en WHERE word=?
        """,
        (word,),
    ).fetchone()
    if not row:
        return ""

    result: ENWord = {
        "word": word,
        "pronunciation": loads(row[0]),
        "paraphrase": loads(row[1]),
        "rank": row[2],
        "pattern": row[3],
        "sentence": loads(row[4]),
    }
    return dumps(result)


def query_word_zh(db_cur: sqlite3.Cursor, word: str) -> str:
    """按旧版 ``ZHWord`` 格式查询中文词条。"""
    row = db_cur.execute(
        """
        SELECT pronunciation, paraphrase, desc, sentence
        FROM zh WHERE word=?
        """,
        (word,),
    ).fetchone()
    if not row:
        return ""

    result: ZHWord = {
        "word": word,
        "pronunciation": row[0],
        "paraphrase": {} if row[1] == "" else loads(row[1]),
        "desc": [] if row[2] == "" else loads(row[2]),
        "sentence": [] if row[3] == "" else loads(row[3]),
    }
    return dumps(result)


def insert_word_en(db_cur: sqlite3.Cursor, word_info: str):
    """插入或替换一个旧版英文词条。"""
    info: ENWord = loads(word_info)
    db_cur.execute(
        """
        INSERT OR REPLACE INTO en
        (word, pronunciation, paraphrase, rank, pattern, sentence)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            info["word"],
            dumps(info["pronunciation"], ensure_ascii=False),
            dumps(info["paraphrase"], ensure_ascii=False),
            info["rank"],
            info["pattern"],
            dumps(info["sentence"], ensure_ascii=False),
        ),
    )


def insert_word_zh(db_cur: sqlite3.Cursor, word_info: str):
    """插入或替换一个旧版中文词条。"""
    info: ZHWord = loads(word_info)
    db_cur.execute(
        """
        INSERT OR REPLACE INTO zh
        (word, pronunciation, paraphrase, desc, sentence)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            info["word"],
            info["pronunciation"],
            info["paraphrase"],
            info["desc"],
            info["sentence"],
        ),
    )


DictDBClient = LegacyDictionaryRepository


__all__ = [
    "DictDBClient",
    "LegacyDictionaryRepository",
    "insert_word_en",
    "insert_word_zh",
    "query_word_en",
    "query_word_zh",
]

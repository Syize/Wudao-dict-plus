"""
wudao_dict.dict.local
#####################

无道词典本地词典逻辑实现。

本地词典存储于一个sqlite3数据库中，支持查询和写入新的词语释义。

.. autosummary::
    :toctree: generated/
    
    DictDBClient
    query_word_en
    query_word_zh
    insert_word_en
    insert_word_zh
"""

# TODO:
#   1. 更新插入新词语的函数。
#   2. 对词典数据库检查哈希值防止数据库损坏。这个检查应当在试图使用词典数据库但发生错误后的下一次试图使用时检查。

import sqlite3
from json import dumps, loads
from os.path import exists
from typing import Literal, Optional

from rich import print

from ..core import DICT_DB_FILE, ENWord, ZHWord


class DictDBClient:
    """
    词典数据库查询和写入客户端。
    """
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = DICT_DB_FILE
            
        if not exists(db_path):
            print(f"[red]找不到词典数据库，请检查数据库文件是否存在：[red]{db_path}")
            raise FileNotFoundError(f"找不到词典数据库，请检查数据库文件是否存在：{db_path}")

        self.db = sqlite3.connect(db_path)
        self.db_cur = self.db.cursor()
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_db()
        
    def close_db(self):
        self.db.close()
        
    def query_word(self, table: Literal["en", "zh"], word: str) -> str:
        """查询词语的释义。

        :param table: 要查询的表名，目前仅支持``["en", "zh"]``。
        :type table: str
        :param word: 要查询的单词。
        :type word: str
        :return: 释义的JSON字符串。如果没有查询到对应的单词，则返回空字符串。
        :rtype: str
        """
        if table == "en":
            return query_word_en(self.db_cur, word)
        
        elif table == "zh":
            return query_word_zh(self.db_cur, word)
        
        else:
            print(f"[red]未知的语言类型[red]：{table}")
            raise ValueError(f"未知的语言类型：{table}")
        
    def insert_word(self, table: Literal["en", "zh"], word_info: str):
        """
        向词典数据库插入新的词语以更新数据库。

        :param table: 要查询的表名，目前仅支持``["en", "zh"]``。
        :type table: str
        :param word_info: 词语释义JSON字符串。
        :type word_info: str
        """
        if table == "en":
            insert_word_en(self.db_cur, word_info)
        
        elif table == "zh":
            insert_word_zh(self.db_cur, word_info)
        
        else:
            print(f"[red]未知的语言类型[red]：{table}")
            raise ValueError(f"未知的语言类型：{table}")
        
        self.db.commit()


def query_word_en(db_cur: sqlite3.Cursor, word: str) -> str:
    """
    查询英文单词/词组释义。

    :param db_cur: 数据库查询指针。
    :type db_cur: Cursor
    :param word: 查询的单词/词组。
    :type word: str
    :return: 释义的JSON字符串。
    :rtype: str
    """
    db_cmd = """
        SELECT pronunciation, paraphrase, rank, pattern, sentence
        FROM en WHERE word=?
    """
    row = db_cur.execute(db_cmd, (word, )).fetchone()
    
    if not row:
        return ""
    
    result: ENWord = {
        'word': word,
        'pronunciation': loads(row[0]),
        'paraphrase': loads(row[1]),
        'rank': row[2],
        'pattern': row[3],
        'sentence': loads(row[4])
    }
    
    return dumps(result)


def query_word_zh(db_cur: sqlite3.Cursor, word: str) -> str:
    """
    查询中文单词/词组释义。

    :param db_cur: 数据库查询指针。
    :type db_cur: Cursor
    :param word: 查询的单词/词组。
    :type word: str
    :return: 释义的JSON字符串。
    :rtype: str
    """
    db_cmd = """
        SELECT pronunciation, paraphrase, desc, sentence
        FROM zh WHERE word=?
    """
    row = db_cur.execute(db_cmd, (word, )).fetchone()
    
    if not row:
        return ""

    paraphrase = row[1]
    desc = row[2]
    sentence = row[3]

    paraphrase = {} if paraphrase == "" else loads(paraphrase)
    desc = [] if desc == "" else loads(desc)
    sentence = [] if sentence == "" else loads(sentence)
    
    result: ZHWord = {
        'word': word,
        'pronunciation': row[0],
        'paraphrase': paraphrase,
        'desc': desc,
        'sentence': sentence
    }
    
    return dumps(result)


def insert_word_en(db_cur: sqlite3.Cursor, word_info: str):
    """
    插入新的英文单词/词组释义。

    :param db_cur: 数据库查询指针。
    :type db_cur: Cursor
    :param word_info: 释义的JSON字符串。
    :type word_info: str
    """
    db_cmd = """
            INSERT OR REPLACE INTO en
            (word, pronunciation, paraphrase, rank, pattern, sentence)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            
    info_value: ENWord = loads(word_info)
    values = (
        info_value["word"], dumps(info_value["pronunciation"], ensure_ascii=False),
        dumps(info_value["paraphrase"], ensure_ascii=False), info_value["rank"], info_value["pattern"],
        dumps(info_value["sentence"], ensure_ascii=False)
    )
    
    db_cur.execute(db_cmd, values)


def insert_word_zh(db_cur: sqlite3.Cursor, word_info: str):
    """
    插入新的中文词语释义。

    :param db_cur: 数据库查询指针。
    :type db_cur: Cursor
    :param word_info: 释义的JSON字符串。
    :type word_info: str
    """
    db_cmd = """
            INSERT OR REPLACE INTO zh
            (word, pronunciation, paraphrase, desc, sentence)
            VALUES (?, ?, ?, ?, ?)
            """
    info_value: ZHWord = loads(word_info)
    values = (
        info_value["word"], info_value["pronunciation"],
        info_value["paraphrase"], info_value["desc"], info_value["sentence"]
    )
    
    db_cur.execute(db_cmd, values)


__all__ = ["DictDBClient", "query_word_en", "query_word_zh", "insert_word_en", "insert_word_zh"]

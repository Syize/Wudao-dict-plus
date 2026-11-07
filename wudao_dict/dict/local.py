"""旧版本地词典接口的兼容导出。

本地词典实现已迁至 :mod:`wudao_dict.core.db.legacy`。保留本模块可避免
现有调用方和旧版扩展的导入路径立即失效。
"""

from ..core.db.legacy import (
    DictDBClient,
    insert_word_en,
    insert_word_zh,
    query_word_en,
    query_word_zh,
)

__all__ = [
    "DictDBClient",
    "insert_word_en",
    "insert_word_zh",
    "query_word_en",
    "query_word_zh",
]

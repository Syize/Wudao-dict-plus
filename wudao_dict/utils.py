"""
wudao_dict.utils
################

在无道词典中使用的工具函数，例如日志设置、数据压缩等。

.. autosummary::
    :toctree: generated/
    
    set_log_level
    set_log_file
    compress
    decompress
"""

import logging
from os import environ, makedirs
from os.path import dirname, exists

import zstandard as zstd

COMPRESSOR = zstd.ZstdCompressor(level=10)
DECOMPRESSOR = zstd.ZstdDecompressor()

logger = logging.getLogger("wudao-dict")
if "WUDAO_DICT_DEBUG_MODE" in environ and environ["WUDAO_DICT_DEBUG_MODE"]:
    _log_mode = logging.DEBUG
else:
    _log_mode = logging.INFO
logger.setLevel(_log_mode)


def set_log_level(level: int):
    """
    设置无道词典的日志等级。

    :param level: 日志等级。
    :type level: int
    """
    global logger
    logger.setLevel(level)


def set_log_file(file_path: str):
    """
    设置无道词典的日志文存储路径。

    :param file_path: 日志文件存储路径。
    :type file_path: str
    """
    global logger

    dir_path = dirname(file_path)

    if not exists(dir_path):
        makedirs(dir_path)

    file_handler = logging.FileHandler(file_path)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s :: %(message)s", datefmt="%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def compress(data: bytes) -> bytes:
    """使用zstd算法压缩数据。

    :param data: 数据块。
    :type data: bytes
    :return: 压缩后的数据块。
    :rtype: bytes
    """
    return COMPRESSOR.compress(data)


def decompress(data: bytes) -> bytes:
    """使用zstd算法解压缩数据。

    :param data: 数据块。
    :type data: bytes
    :return: 解压后的数据块。
    :rtype: bytes
    """
    return DECOMPRESSOR.decompress(data)


def is_alphabet(uchar):
    if (u'\u0041' <= uchar <= u'\u005a') or (u'\u0061' <= uchar <= u'\u007a') or uchar == '\'':
        return True
    else:
        return False


__all__ = ["is_alphabet", "set_log_level", "set_log_file", "compress", "decompress"]

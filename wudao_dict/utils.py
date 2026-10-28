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
from logging.handlers import RotatingFileHandler
from os import environ, makedirs
from os.path import dirname, exists
from pathlib import Path
from time import time

import zstandard as zstd
from rich.logging import RichHandler

COMPRESSOR = zstd.ZstdCompressor(level=10)
DECOMPRESSOR = zstd.ZstdDecompressor()

# Set logger for server and client.
logger = logging.getLogger("wudao-dict")
logger_client = logging.getLogger("wudao-dict-client")

if environ.get("WUDAO_DICT_DEBUG_MODE"):
    _log_mode = logging.DEBUG
else:
    _log_mode = logging.INFO

logger.setLevel(_log_mode)
logger_client.setLevel(_log_mode)

formatter = logging.Formatter("%(name)s :: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
# use rich handler
handler = RichHandler()
handler.setFormatter(formatter)
logger_client.addHandler(handler)

if _log_mode == logging.DEBUG:
    logger_client.debug("Debug mode is on.")


def set_log_level(level: int):
    """
    设置无道词典的日志等级。

    :param level: 日志等级。
    :type level: int
    """
    logger.setLevel(level)


class SizeAndAgeRotatingFileHandler(RotatingFileHandler):
    """按大小轮转日志，并删除超过保留期的轮转文件。"""

    def __init__(self, filename: str, max_bytes: int, backup_count: int, max_age_days: int):
        self.max_age_seconds = max_age_days * 24 * 60 * 60
        self._next_cleanup_at = 0.0
        super().__init__(filename, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        self._cleanup_expired_backups()

    def emit(self, record):
        self._cleanup_expired_backups()
        super().emit(record)

    def _cleanup_expired_backups(self):
        """删除同一日志文件超过保留期的数字序号备份。"""
        now = time()
        # 每小时检查一次即可，避免每条日志都扫描目录。
        if now < self._next_cleanup_at:
            return

        self._next_cleanup_at = now + 60 * 60
        log_path = Path(self.baseFilename)
        expiry_time = now - self.max_age_seconds
        prefix = f"{log_path.name}."

        try:
            for backup_path in log_path.parent.glob(f"{log_path.name}.*"):
                suffix = backup_path.name[len(prefix):]
                if suffix.isdigit() and backup_path.is_file() and backup_path.stat().st_mtime < expiry_time:
                    backup_path.unlink()
        except OSError:
            # 日志清理失败不应影响词典服务的正常运行；下次写入时会重试。
            pass


def set_log_file(
    file_path: str,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
    max_age_days: int = 30,
):
    """
    设置无道词典的日志文存储路径。

    :param file_path: 日志文件存储路径。
    :type file_path: str
    :param max_bytes: 单个日志文件的最大字节数，达到该大小后会轮转。
    :type max_bytes: int
    :param backup_count: 最多保留的轮转备份数量。
    :type backup_count: int
    :param max_age_days: 轮转备份的最长保留天数。
    :type max_age_days: int
    """
    dir_path = dirname(file_path)

    if dir_path and not exists(dir_path):
        makedirs(dir_path)

    absolute_path = str(Path(file_path).resolve())
    if any(getattr(handler, "baseFilename", None) == absolute_path for handler in logger.handlers):
        return

    file_handler = SizeAndAgeRotatingFileHandler(file_path, max_bytes, backup_count, max_age_days)
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
    return ('\u0041' <= uchar <= '\u005a') or ('\u0061' <= uchar <= '\u007a') or uchar == '\''


__all__ = ["compress", "decompress", "is_alphabet", "set_log_file", "set_log_level"]

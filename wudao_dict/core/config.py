"""
wudao_dict.core.config
######################

这是无道词典的配置模块，根据操作系统的不同，无道词典将配置文件存储在相应的用户配置目录中。

.. py:data:: APP_NAME
    :type: str
    :value: "wudao-dict"
    
    无道词典的APP名称。

.. py:data:: CONFIG_DIR
    :type: str
    :value: 取决于运行的平台。
    
    无道词典的配置目录路径。
    无道词典使用`platformdirs <https://github.com/tox-dev/platformdirs>`_获取相应平台的配置目录。
    
.. py:data:: CONFIG_FILE
    :type: str
    :value: 取决于``CONFIG_DIR``的值。
    
    无道词典的配置文件路径。
    
.. py:data:: CONFIG_SOCKET_FILE
    :type: str
    :value: 取决于``CONFIG_DIR``的值。
    
    无道词典的socket文件路径。
    该文件为运行时文件，用于记录正在运行中的无道词典服务的端口。
    在服务退出后，该文件就会被删除。
    
.. py:data:: LOG_DIR
    :type: str
    :value: 取决于运行的平台。
    
    无道词典的日志存储路径。
    无道词典使用`platformdirs <https://github.com/tox-dev/platformdirs>`_获取相应平台的日志目录。
    
.. py:data:: LOG_FILE
    :type: str
    :value: 取决于``LOG_DIR``的值。
    
    无道词典的日志文件路径。

.. autosummary::
    :toctree: generated/
    
    load_config
    save_config
    read_socket
    create_socket
    delete_socket
"""

from json import dump, load
from os import makedirs, remove
from os.path import exists
from typing import Any

from platformdirs import user_config_dir, user_log_dir
from rich import print
from zstandard import ZstdDecompressor

from ..res import DICT_DB_ZST

APP_NAME = "wudao-dict"
CONFIG_DIR = user_config_dir(appname=APP_NAME)
CONFIG_FILE = f"{CONFIG_DIR}/config.json"
CONFIG_SOCKET_FILE = f"{CONFIG_DIR}/socket.json"
LOG_DIR = user_log_dir(appname=APP_NAME)
LOG_FILE = f"{LOG_DIR}/log.txt"
DICT_DB_FILE = f"{CONFIG_DIR}/dict.db"
CREDENCE_DB_FILE = f"{CONFIG_DIR}/credence.db"


def load_config() -> "dict[str, Any]":
    """
    读取无道词典的配置。

    :return: 无道词典的配置。
    :rtype: dict[str, Any]
    """
    global CONFIG_DIR, CONFIG_FILE
    
    default_config = {
            "short": False,      # 简明模式
            "online": False,
            "update_db": True
        }
    
    if not exists(CONFIG_DIR):
        makedirs(CONFIG_DIR)
        
    if exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = load(f)
            
        # 通过此种方式保证所有配置项都存在
        default_config.update(config)
        
    else:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            dump(default_config, f)
        
    return default_config


def save_config(configs: "dict[str, Any]"):
    """
    保存无道词典的配置。

    :param configs: 无道词典配置。
    :type configs: dict[str, Any]
    """
    global CONFIG_DIR, CONFIG_FILE
    
    if not exists(CONFIG_DIR):
        makedirs(CONFIG_DIR)
        
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        dump(configs, f)
        
        
def read_socket() -> int:
    """
    读取可能由正在运行的无道词典服务创建的socket文件，其中包含了服务的端口号。
    
    正常情况下，无道词典服务退出时会要求删除该文件。此时函数返回``-1``，表示新的无道词典服务可以启动。
    
    如果socket文件存在，则返回文件中记录的端口号。

    :return: 无道词典服务端口号。
    :rtype: int
    """
    global CONFIG_SOCKET_FILE
    
    if not exists(CONFIG_SOCKET_FILE):
        return -1
    
    with open(CONFIG_SOCKET_FILE, "r", encoding="utf-8") as f:
        socket_setting = load(f)
        
    if "port" not in socket_setting:
        remove(CONFIG_SOCKET_FILE)
        return -1
    
    else:
        return socket_setting["port"]
    
    
def create_socket(port: int):
    """
    创建socket文件，记录无道词典服务的端口号。

    :param port: 无道词典服务的端口号。
    :type port: int
    """
    global CONFIG_DIR, CONFIG_SOCKET_FILE
    
    if not exists(CONFIG_DIR):
        makedirs(CONFIG_DIR)
        
    with open(CONFIG_SOCKET_FILE, "w", encoding="utf-8") as f:
        dump({"port": port}, f)
        
        
def delete_socket():
    """
    删除socket文件。
    """
    global CONFIG_SOCKET_FILE
    
    if exists(CONFIG_SOCKET_FILE):
        remove(CONFIG_SOCKET_FILE)
        
        
def check_dict_db():
    """
    检测本地词典数据库是否存在。若不存在，则解压数据库文件到配置目录。
    """
    global DICT_DB_FILE, CONFIG_DIR
    
    if exists(DICT_DB_FILE):
        return
    
    if not exists(DICT_DB_ZST):
        print("[red]检测到无道词典不完整！请重新安装 wudao-dict！[red]")
        exit(1)
        
    print("[red]正在解压词典数据库。本操作理应只执行一次，请稍等...[red]")
    
    if not exists(CONFIG_DIR):
        makedirs(CONFIG_DIR)
        
    decompressor = ZstdDecompressor()
    
    with open(DICT_DB_ZST, "rb") as f:
        with open(DICT_DB_FILE, "wb") as f2:
            decompressor.copy_stream(f, f2)
            
            
check_dict_db()


__all__ = ["load_config", "save_config", "read_socket", "create_socket", "delete_socket",
           "CONFIG_DIR", "CONFIG_FILE", "CONFIG_SOCKET_FILE", "LOG_DIR", "LOG_FILE", "check_dict_db",
           "DICT_DB_FILE"]

"""
wudao_dict.core.server
######################

无道词典后台服务实现。

.. autosummary::
    :toctree: generated/
    
    start_wudao_server
    WudaoServer
"""

import logging
import os
import socket
import sys
from json import dumps, loads
from traceback import format_exception

from rich.logging import RichHandler

from .core import LOG_FILE, Message, QueryMessage, create_socket, delete_socket
from .dict import DictDBClient, search_youdao_en, search_youdao_zh
from .utils import is_alphabet, set_log_file


def _daemonize() -> bool:
    """
    创建后台进程。
    
    如果该函数返回``True``，则表明收到该返回值的进程是父进程。
    如果返回``False``，则表明进程是后台进程。

    :return: ``True`` 或 ``False``。
    :rtype: bool
    """
    if os.fork() > 0:
        return True
        
    os.setsid()     # 创建新会话
    
    if os.fork() > 0:
        sys.exit()  # 第一子进程退出，第二子进程成为孤儿进程

    sys.stdout.flush()
    sys.stderr.flush()
    with open("/dev/null", "r") as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open("/dev/null", "a+") as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())
        
    return False


def start_wudao_server(address="127.0.0.1"):
    """
    启动无道词典的后台服务。
    
    在无道词典服务退出以后，本函数会调用``exit``结束服务进程。
    
    :param address: 无道词典后台服务的监听地址。
    :type address: str
    """
    status = _daemonize()
    
    if status:
        return
    
    server = WudaoServer(address)

    try:
        server.run()

    except Exception as error:
        server.logger.error("无道词典服务出现错误：")
        for _line in format_exception(error):
            _line = _line.strip("\n")

            if "\n" in _line:
                for _subline in _line.split("\n"):
                    server.logger.error(_subline)

            else:
                server.logger.error(_line)
    
    exit(0)


class WudaoServer:
    """
    无道词典服务器类
    
    负责启动本地服务器进程，监听客户端查询请求，
    并从本地词典文件中检索单词信息。
    
    该服务器使用的端口由系统分配，并将其记录到socket文件中。
    """
    
    def __init__(self, address="127.0.0.1", is_foreground=False):
        self.local_dict = DictDBClient()
        self.logger = logging.getLogger("wudao-dict")
        set_log_file(LOG_FILE)
        
        if is_foreground:
            self.add_stdout_handler()
        
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((address, 0))
        _, port = self.server.getsockname()
        create_socket(port)
        self.logger.info(f"WudaoServer listening on: {address}:{port}")
        self.server.listen(5)
        
    def add_stdout_handler(self):
        formatter = logging.Formatter("%(name)s :: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        # use rich handler
        handler = RichHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
    def run(self):
        """
        启动服务器主循环
        
        持续监听客户端连接请求，接收查询单词，
        从本地词典中检索单词信息并返回给客户端。
        支持通过特定关键字关闭服务器。
        """
        with self.local_dict:
            while True:
                conn, addr = self.server.accept()
                data = conn.recv(1024)
                
                msg = data.decode('utf-8').strip()
                
                if msg:
                    msg_data: Message = loads(msg)
                    self.logger.info(f"Receive message: {msg_data}")
                    
                    if msg_data["cmd"] == "quit":
                        self.server.close()
                        delete_socket()
                        self.logger.info("WudaoServer exits.")
                        break

                    msg = self._generate_msg(msg_data)
                    
                else:
                    self.logger.warning(f"Receive empty message, please check your request: {msg}")

                conn.sendall(msg.encode('utf-8'))
                conn.close()
                
    def _query_online_api(self, api_name: str, word: str, lang_type: str, is_update_db: bool) -> str:
        """
        Query word from online API.

        :param api_name: API name.
        :type api_name: str
        :param word: Word.
        :type word: str
        :param lang_type: Word type.
        :type lang_type: str
        :param is_update_db: If update local DB.
        :type is_update_db: bool
        :return: Word information.
        :rtype: str
        """
        if api_name == "youdao":
            if lang_type == "zh":
                res = search_youdao_zh(word)
            else:
                res = search_youdao_en(word)
                
            if res:
                word_info = dumps(res)
                
                if is_update_db and lang_type == "en":
                    self.logger.info(f"Update DB: {res}")
                    self.local_dict.insert_word("en", word_info)
            
            else:
                word_info = ""
                    
        else:
            self.logger.error(f"Unknown online API: {api_name}")
            word_info = ""
            
        return word_info

    def _generate_msg(self, msg_data: QueryMessage) -> str:
        if "cmd" not in msg_data:
            self.logger.error("Wrong message")
            return ""

        elif msg_data["cmd"] == "query":
            if "word" not in msg_data:
                self.logger.error("Wrong message")
                return ""
            
            word = msg_data["word"]
            if not word:
                return ""
            
            is_online = msg_data["online"]
            is_update_db = msg_data["update_db"]
            
            lang_type = "en" if is_alphabet(word[0]) else "zh"
            
            if is_online:
                word_info = self._query_online_api("youdao", word, lang_type, is_update_db)
                        
            else:
                word_info = self.local_dict.query_word(lang_type, word)
                
                if not word_info:
                    word_info = self._query_online_api("youdao", word, lang_type, is_update_db)
            
            return word_info

        else:
            self.logger.error(f"Unknow command: {msg_data['cmd']}")
           
            return ""
        
    def __del__(self):
        self.local_dict.close_db()


__all__ = ["start_wudao_server", "WudaoServer"]

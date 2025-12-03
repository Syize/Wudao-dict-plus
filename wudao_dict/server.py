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
import socket
import sys
import os
from json import loads, dumps
from traceback import format_exception

from .core import create_socket, LOG_FILE, delete_socket, Message, QueryMessage
from .dict import DictDBClient, search_youdao_en
from .utils import set_log_file, is_alphabet


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
        server.logger.error(f"无道词典服务出现错误：")
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
    
    def __init__(self, address="127.0.0.1"):
        self.local_dict = DictDBClient()
        self.logger = logging.getLogger("wudao-dict")
        set_log_file(LOG_FILE)
        
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((address, 0))
        _, port = self.server.getsockname()
        create_socket(port)
        self.logger.info(f"WudaoServer listening on: {address}:{port}")
        self.server.listen(5)
        
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
                msg_data: Message = loads(msg)
                self.logger.info(f"Receive message: {msg_data}")
                
                if msg_data["cmd"] == "quit":
                    self.server.close()
                    delete_socket()
                    self.logger.info("WudaoServer exits.")
                    break
                
                msg = self._generate_msg(msg_data)
                
                conn.sendall(msg.encode('utf-8'))
                conn.close()

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
                
                if lang_type == "zh":
                    # online query for Chinese word hasn't been implemented yet.
                    word_info = self.local_dict.query_word(lang_type, word)
                
                else:
                    res = search_youdao_en(word)
                    
                    if res:
                        word_info = dumps(res)
                        if is_update_db:
                            self.local_dict.insert_word("en", word_info)
                    else:
                        word_info = ""
                        
            else:
                word_info = self.local_dict.query_word(lang_type, word)
                
                if not word_info and lang_type == "en":
                    res = search_youdao_en(word)
                    if res:
                        word_info = dumps(res)
                        if is_update_db:
                            self.local_dict.insert_word("en", word_info)
            
            return word_info

        else:
            self.logger.error(f"Unknow command: {msg_data['cmd']}")
           
            return ""


__all__ = ["start_wudao_server", "WudaoServer"]

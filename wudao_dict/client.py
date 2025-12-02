"""
wudao_dict.core.client
######################

无道词典的客户端实现。

.. autosummary::
    :toctree: generated/
    
    WudaoClient
"""

import socket
from json import dumps
from time import sleep
from typing import Optional

from rich import print

from .core import LOG_FILE, read_socket
from .server import start_wudao_server


def _start_wudao_server():
    start_wudao_server()
    print("[red]正在启动后台查询服务，请稍等...[red]")
    sleep(1)
    
    
def _check_server(client: socket.socket, address: str, port: int) -> bool:
    check_res = False
    
    for _ in range(5):
        try:
            client.connect((address, port))
            check_res = True
            break
        
        except ConnectionRefusedError:
            sleep(0.2)
            
    return check_res


class WudaoClient:
    """
    无道词典客户端。
    """
    def __init__(self, address="127.0.0.1", port: Optional[int] = None):
        
        if port is None:
            port = read_socket()
        
        if port < 0:
            _start_wudao_server()
            has_call_start = True
            port = read_socket()
            
        else:
            has_call_start = False
            
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # 检查后台服务。
        res = _check_server(self.client, address, port)
        fail_flag = False
        
        if not res and not has_call_start:
            # 如果连接失败且没有执行过启动函数，则尝试启动。
            _start_wudao_server()
            port = read_socket()
            
            if not _check_server(self.client, address, port):
                fail_flag = True
        
        elif not res:
            fail_flag = True
            
        if fail_flag:
            print("[red]后台查询服务启动失败![red]")
            print(f"[red]请试着检查日志文件[red]：{LOG_FILE}")
            exit(1)
                
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
        
    def close_server(self):
        """
        关闭无道词典服务进程。
        """
        msg = dumps({"cmd": "quit"})
        self.client.sendall(msg.encode('utf-8'))
    
    def get_word_info(self, word: str, online=True) -> str:
        """
        查询单词信息。
        
        :param word: 要查询的单词
        :type word: str
        :return: 服务器返回的单词信息
        :rtype: str
        """
        msg = dumps({"cmd": "query", "word": word, "online": online})
        self.client.sendall(msg.encode('utf-8'))
        
        server_context = b''
        while True:
            rec = self.client.recv(512)
            if not rec:
                break
            server_context += rec
        server_context = server_context.decode('utf-8')
        return server_context
            
            
__all__ = ["WudaoClient"]

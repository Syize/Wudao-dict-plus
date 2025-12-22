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

from .core import LOG_FILE, QueryMessage, QuitMessage, read_socket
from .server import start_wudao_server


def _start_wudao_server():
    start_wudao_server()
    print("[red]正在启动后台查询服务，请稍等...[red]")
    sleep(1)
    
    
def _check_server(address: str, port: int) -> Optional[socket.socket]:
    """
    Check if the server running and return connected socket.

    :param address: Server address.
    :type address: str
    :param port: Server port.
    :type port: int
    :return: Connected socket if server is running, else None.
    :rtype: Optional[socket.socket]
    """
    client = None
    
    for _ in range(5):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            client.connect((address, port))

        except (ConnectionRefusedError, OSError):
            client.close()
            client = None
            sleep(0.2)

    return client


class WudaoClient:
    """
    无道词典客户端。
    """
    def __init__(self, address="127.0.0.1", port: Optional[int] = None):
        self.address = address

        if port is None:
            self.port = read_socket()
        else:
            self.port = port

        self._server_checked = False
        self.client: Optional[socket.socket] = None

    def _check_server_internal(self, no_start=False) -> bool:
        """
        Check background server.

        :param no_start: If not to start server, defaults to False
        :type no_start: bool, optional
        :return: True if the server running, else False.
        :rtype: bool
        """
        if self._server_checked:
            return True

        if no_start:
            if self.port < 0:
                return False

            self.client = _check_server(self.address, self.port)
            return self.client is not None

        if self.port < 0:
            _start_wudao_server()
            has_call_start = True
            self.port = read_socket()

        else:
            has_call_start = False

        # 检查后台服务。
        self.client = _check_server(self.address, self.port)

        if self.client is None and not has_call_start:
            # 如果连接失败且没有执行过启动函数，则尝试启动。
            _start_wudao_server()
            self.port = read_socket()
            self.client = _check_server(self.address, self.port)

        if self.client is None:
            print("[red]后台查询服务启动失败![red]")
            print(f"[red]请试着检查日志文件[red]：{LOG_FILE}")
            exit(1)

        self._server_checked = True

        return True
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()

    def __del__(self):
        if self.client:
            self.client.close()

    def close_server(self):
        """
        关闭无道词典服务进程。
        """
        if self._check_server_internal(no_start=True):
            msg: QuitMessage = {"cmd": "quit"}
            # client should not be None
            self.client.sendall(dumps(msg).encode('utf-8'))     # type: ignore

    def get_word_info(self, word: str, online=True, update_db=True) -> str:
        """
        查询单词信息。

        :param word: 要查询的单词
        :type word: str
        :return: 服务器返回的单词信息
        :rtype: str
        """
        self._check_server_internal()
        
        msg: QueryMessage = {
            "cmd": "query",
            "word": word,
            "online": online,
            "update_db": update_db
        }
        self.client.sendall(dumps(msg).encode('utf-8'))     # type: ignore
        
        server_context = b''
        while True:
            rec = self.client.recv(512)     # type: ignore
            if not rec:
                break
            server_context += rec
        server_context = server_context.decode('utf-8')
        return server_context
            
            
__all__ = ["WudaoClient"]

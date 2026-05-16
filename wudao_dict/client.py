"""
wudao_dict.core.client
######################

无道词典的客户端实现。

.. autosummary::
    :toctree: generated/
    
    WudaoClient
"""

import logging
import os
import socket
import subprocess
import sys
from json import dumps, loads
from time import sleep
from typing import Optional

from rich import print

from .core import (
    LOG_FILE,
    PlaybackResponseMessage,
    PlayPronunciationMessage,
    QueryMessage,
    QuitMessage,
    read_socket,
)

LOGGER = logging.getLogger("wudao-dict-client")


def _get_server_python_executable() -> str:
    if os.name != "nt":
        return sys.executable

    executable_dir = os.path.dirname(sys.executable)
    executable_name = os.path.basename(sys.executable)

    if executable_name.lower() == "python.exe":
        pythonw = os.path.join(executable_dir, "pythonw.exe")

        if os.path.exists(pythonw):
            return pythonw

    return sys.executable


def _start_wudao_server():
    popen_kwargs = {
        "args": [_get_server_python_executable(), "-m", "wudao_dict.cli", "--serve"],
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True
    }

    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        popen_kwargs["startupinfo"] = startupinfo
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        LOGGER.debug("Start background service on Windows.")
    else:
        popen_kwargs["start_new_session"] = True
        LOGGER.debug("Start background service on Linux/MacOS.")

    subprocess.Popen(**popen_kwargs)    # type: ignore
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
    
    for i in range(5):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            client.connect((address, port))
            break

        except (ConnectionRefusedError, OSError):
            LOGGER.debug(f"Failed to connect to server {i} times.")
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

        if self.port > 0:
            LOGGER.debug(f"Server listened at :{self.port}.")

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

            client = _check_server(self.address, self.port)
            if client:
                client.close()
                return True
            return False

        if self.port < 0:
            _start_wudao_server()
            has_call_start = True
            self.port = read_socket()

        else:
            has_call_start = False

        # 检查后台服务。
        client = _check_server(self.address, self.port)

        if client is None and not has_call_start:
            # 如果连接失败且没有执行过启动函数，则尝试启动。
            _start_wudao_server()
            self.port = read_socket()
            client = _check_server(self.address, self.port)

        if client is None:
            print("[red]后台查询服务启动失败![red]")
            print(f"[red]请试着检查日志文件[red]：{LOG_FILE}")
            exit(1)

        client.close()

        self._server_checked = True

        return True
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _ = (exc_type, exc_val, exc_tb)

    def __del__(self):
        return

    def _create_request_client(self) -> socket.socket:
        self._check_server_internal()
        client = _check_server(self.address, self.port)
        if client is None:
            print("[red]无法连接后端查询服务![red]")
            print(f"[red]请试着检查日志文件[red]：{LOG_FILE}")
            exit(1)
        return client

    def close_server(self):
        """
        关闭无道词典服务进程。
        """
        if self._check_server_internal(no_start=True):
            msg: QuitMessage = {"cmd": "quit"}
            client = self._create_request_client()
            client.sendall(dumps(msg).encode('utf-8'))
            client.close()

    def get_word_info(self, word: str, online=True, update_db=True) -> str:
        """
        查询单词信息。

        :param word: 要查询的单词
        :type word: str
        :return: 服务器返回的单词信息
        :rtype: str
        """
        msg: QueryMessage = {
            "cmd": "query",
            "word": word,
            "online": online,
            "update_db": update_db
        }
        client = self._create_request_client()
        client.sendall(dumps(msg).encode('utf-8'))

        server_context = b''
        while True:
            rec = client.recv(512)
            if not rec:
                break
            server_context += rec
        client.close()
        server_context = server_context.decode('utf-8')
        return server_context

    def play_pronunciation(self, word: str):
        msg: PlayPronunciationMessage = {
            "cmd": "play_pronunciation",
            "word": word
        }
        client = self._create_request_client()
        client.sendall(dumps(msg).encode('utf-8'))

        server_context = b''
        while True:
            rec = client.recv(512)
            if not rec:
                break
            server_context += rec
        client.close()

        if not server_context:
            response: PlaybackResponseMessage = {
                "cmd": "playback_response",
                "status": "play_failed",
                "backend": "",
                "message": "Empty response from server."
            }

        else:
            response = loads(server_context.decode('utf-8'))

        self._handle_playback_response(response)

    def _handle_playback_response(self, response: PlaybackResponseMessage):
        if response["status"] == "ok":
            return

        status = response["status"]
        print("[red]播放发音失败。[red]")

        if status == "afplay_not_found":
            print("[red]未找到 `afplay`。请检查 macOS 的音频环境。[red]")
            return

        if status == "linux_backend_not_found":
            print("[red]未找到可用的 Linux 音频后端。请安装 `mpv`、`ffplay` 或 `paplay` 之一。[red]")
            return

        if status == "vlc_not_installed":
            print("[red]Windows 平台需要额外安装 `python-vlc` 和 VLC。[red]")
            # print("[red]可以先安装 VLC，再运行 `pip install \"wudao-dict-plus[windows-audio]\"`。[red]")
            return

        if status == "vlc_path_invalid":
            print("[red]当前 VLC 路径配置无效。请检查 `vlc_path`，必要时也配置 `vlc_lib_path`。[red]")
            return

        if status in {"backend_not_found", "backend_broken"}:
            print(f"[red]当前音频后端不可用：{response['backend'] or 'unknown'}。[red]")
            if response["message"]:
                print(f"[red]{response['message']}[red]")
            return

        if response["message"]:
            print(f"[red]{response['message']}[red]")
        else:
            print(f"[red]请试着检查日志文件[red]：{LOG_FILE}")
            
            
__all__ = ["WudaoClient"]

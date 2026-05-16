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
from json import dumps, loads
from traceback import format_exception
from typing import Literal

from rich.logging import RichHandler

from .audio import ensure_pronunciation_file, play_audio
from .core import (
    LOG_FILE,
    Message,
    PlaybackResponseMessage,
    PlayPronunciationMessage,
    QueryMessage,
    create_socket,
    delete_socket,
    load_config,
)
from .dict import DictDBClient, search_youdao_en, search_youdao_zh
from .utils import is_alphabet, set_log_file


def start_wudao_server(address="127.0.0.1"):
    """
    在当前进程中启动无道词典服务。
    
    :param address: 无道词典后台服务的监听地址。
    :type address: str
    """
    server = WudaoServer(address)

    try:
        server.run()

    except BaseException as error:
        server.logger.error("无道词典服务出现错误：")
        for _line in format_exception(error, value=None, tb=None):  # type: ignore
            _line = _line.strip("\n")

            if "\n" in _line:
                for _subline in _line.split("\n"):
                    server.logger.error(_subline)

            else:
                server.logger.error(_line)


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
                response = ""
                
                if msg:
                    msg_data: Message = loads(msg)
                    self.logger.info(f"Receive message: {msg_data}")
                    
                    if msg_data["cmd"] == "quit":
                        self.server.close()
                        delete_socket()
                        self.logger.info("WudaoServer exits.")
                        break

                    elif msg_data["cmd"] == "query":
                        response = self._generate_msg(msg_data)

                    elif msg_data["cmd"] == "play_pronunciation":
                        response = self._handle_play_pronunciation(msg_data)
                    
                else:
                    self.logger.warning(f"Receive empty message, please check your request: {msg}")

                if response:
                    conn.sendall(response.encode('utf-8'))
                
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

    def _query_local_with_online_fallback(self, word: str, lang_type: Literal["en", "zh"], is_update_db: bool) -> str:
        """
        Query local DB first, then fallback to online API when local result is missing.

        :param word: Word.
        :type word: str
        :param lang_type: Word type.
        :type lang_type: str
        :param is_update_db: If update local DB.
        :type is_update_db: bool
        :return: Word information.
        :rtype: str
        """
        word_info = self.local_dict.query_word(lang_type, word)

        if not word_info:
            word_info = self._query_online_api("youdao", word, lang_type, is_update_db)

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

                if not word_info:
                    self.logger.info(f"Online query failed, fallback to local DB: {word}")
                    word_info = self.local_dict.query_word(lang_type, word)

            else:
                word_info = self._query_local_with_online_fallback(word, lang_type, is_update_db)

            self._prefetch_pronunciation_audio(word, lang_type, word_info)
            
            return word_info

        else:
            self.logger.error(f"Unknow command: {msg_data['cmd']}")
           
            return ""

    def _prefetch_pronunciation_audio(self, word: str, lang_type: Literal["en", "zh"], word_info: str):
        if lang_type != "en" or not word_info:
            return

        conf = load_config()
        if not conf["pronounce"] or not conf["audio_cache_enabled"]:
            return

        try:
            ensure_pronunciation_file(word, conf["pronounce_accent"])
        except Exception as error:
            self.logger.warning(f"Failed to cache pronunciation audio for '{word}': {error}")

    def _handle_play_pronunciation(self, msg_data: PlayPronunciationMessage) -> str:
        conf = load_config()
        
        response: PlaybackResponseMessage = {
            "cmd": "playback_response",
            "status": "ok",
            "backend": conf["audio_player_backend"],
            "message": ""
        }

        word = msg_data["word"].strip()
        if not word:
            response["status"] = "play_failed"
            response["message"] = "Word cannot be empty."
            return dumps(response)

        if not conf["pronounce"]:
            response["status"] = "play_failed"
            response["message"] = "Pronunciation feature is disabled."
            return dumps(response)

        if not conf["audio_cache_enabled"]:
            response["status"] = "play_failed"
            response["message"] = "Audio cache is disabled."
            return dumps(response)

        try:
            audio_file = ensure_pronunciation_file(word, conf["pronounce_accent"])
            playback_result = play_audio(audio_file)
            self.logger.info(f"Pronunciation trigger accepted: {audio_file}")
            response.update(playback_result)
        except Exception as error:
            response["status"] = "play_failed"
            response["message"] = str(error)

        return dumps(response)
        
    def __del__(self):
        self.local_dict.close_db()


__all__ = ["start_wudao_server", "WudaoServer"]

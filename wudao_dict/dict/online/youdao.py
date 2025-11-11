import logging

import httpx
from bs4 import BeautifulSoup

from wudao_dict.core import OnlineDictError, ENWord, ZHWord
from .utils import HEADERS


logger = logging.getLogger("wudao-dict")


def _get_res_from_api(word: str) -> str:
    """

    :param word: Word.
    :type word: str
    :return: Response text.
    :rtype: str
    """
    url = f"https://dict.youdao.com/result?word={word}&lang=en"
    response = httpx.get(url, headers=HEADERS)

    if response.status_code != 200:
        logger.warning("Failed to get response from Youdao API.")
        logger.warning(f"Response from Youdao API: status_code={response.status_code}, text={response.text}")
        raise OnlineDictError

    return response.text


def _parse_response(res: str) -> str:
    """

    :param res: Response text.
    :type res: str
    :return: JSON string.
    :rtype: str
    """
    html = BeautifulSoup(res, "lxml")
    pronounce_div = html.find("div", attrs={"class": "phone_con"})

    # 1. pronunciation
    pronounce = {
        "usa": "",
        "uk": "",
        "other": ""
    }

    if not None:
        _res_list = pronounce_div.find_all("div", attrs={"class": "per-phone"})

        for _res in _res_list:
            _text = _res.text

            if "英" in _text:
                _pronounce = _res.find("span", attrs={"class": "phonetic"}).text.strip("/ ")
                pronounce["uk"] = f"[{_pronounce}]"

            elif "美" in _text:
                _pronounce = _res.find("span", attrs={"class": "phonetic"}).text.strip("/ ")
                pronounce["usa"] = f"[{_pronounce}]"

            else:
                _pronounce = _res.find("span", attrs={"class": "phonetic"}).text.strip("/ ")
                pronounce["other"] = f"[{_pronounce}]"


def query_word_from_youdao(word: str) -> str:
    """
    从有道词典查询词语释义。

    :param word: 要查询的词语。
    :type word: str
    :return: 词语释义的JSON字符串。
    :rtype: str
    """
    pass

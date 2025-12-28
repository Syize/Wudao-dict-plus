import re
from typing import Dict, List, Literal, Optional, Tuple

from bs4 import BeautifulSoup
from bs4.element import Tag
from requests import get
from requests.exceptions import ReadTimeout, Timeout

from wudao_dict.core import (CollinsSentenceUnit, ENPronounce, ENSentence,
                             ENWord, SentenceUnit, ZHDesc, ZHWord)

HEADERS = {
        'Accept': 'text/html, application/xhtml+xml, application/xml;q=0.9, image/webp, */*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'zh-CN, zh;q=0.8',
        'Upgrade-Insecure-Requests': '1',
        'Host': 'dict.youdao.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) \
                       Chrome/48.0.2564.116 Safari/537.36'
    }


def _get_pron_en(html: BeautifulSoup) -> ENPronounce:
    """
    Get pronunciation.

    :param html: HTML.
    :type html: BeautifulSoup
    :return: Pronunciation.
    :rtype: ENPronounce
    """
    prons = html.find_all("span", class_="pronounce")
    en_pron: ENPronounce = {
        "usa": "",
        "uk": "",
        "other": ""
    }
    
    for _pron in prons:
        if "英" in _pron.text:
            _pron_text = _pron.find("span", class_="phonetic")
            _pron_text = _pron_text.text if _pron_text else ""
            en_pron["uk"] = _pron_text
            
        elif "美" in _pron.text:
            _pron_text = _pron.find("span", class_="phonetic")
            _pron_text = _pron_text.text if _pron_text else ""
            en_pron["usa"] = _pron_text
            
        else:
            _pron_text = _pron.find("span", class_="phonetic")
            _pron_text = _pron_text.text if _pron_text else ""
            en_pron["other"] = _pron_text
    
    return en_pron


def _get_pron_zh(html: BeautifulSoup) -> str:
    """
    Get prounuciation.

    :param html: HTML.
    :type html: BeautifulSoup
    :return: Pronunciation.
    :rtype: str
    """
    pron = html.find("span", class_="phonetic")
    pron_text = pron.text if pron else ""
    
    return pron_text


def _get_paraphrase(trans_div: Tag, word_type: Literal["en", "zh"]) -> Dict[str, List[str]]:
    """
    Get word paraphrase.
    
    By analysing the web page, we can get paraphrases of both English and Chinese word
    with the same function.

    :param trans_div: Tag.
    :type trans_div: Tag
    :return: Paraphrase.
    :rtype: Dict[str, List[str]]
    """
    tag_name = "li" if word_type == "en" else "p"
    
    para_list = trans_div.find_all(tag_name)
    paraphrase: Dict[str, List[str]] = {}
    
    for _para in para_list:
        text = str(_para.text).strip() if _para.text else ""
        # print("========")
        # print(text)
        para_type = re.match(r"[a-zA-Z]+\.\s", text)
        # print(para_type)
        
        if para_type:
            _para_type = para_type.group().strip()
            _para_content = text.replace(_para_type, "").strip()
            
        else:
            _para_type = "other"
            _para_content = text.strip()
            
        if _para_type in paraphrase:
            
            if word_type == "en":
                paraphrase[_para_type].append(_para_content)
                
            else:
                # zh word has multiple paraphrase
                _para_list = _para_content.split(";")
                _para_list = [x.strip() for x in _para_list]
                paraphrase[_para_type] += _para_list
            
        else:
            
            if word_type == "en":
                paraphrase[_para_type] = [_para_content]
                
            else:
                # zh word has multiple paraphrase
                _para_list = _para_content.split(";")
                _para_list = [x.strip() for x in _para_list]
                paraphrase[_para_type] = _para_list
            
    return paraphrase


def _get_pattern(p_tag: Tag) -> str:
    """
    Get word pattern.

    :param p_tag: Tag.
    :type p_tag: Tag
    :return: Word pattern.
    :rtype: str
    """
    text = str(p_tag.text) if p_tag.text else ""
    
    if not text:
        return ""
    
    text = text.strip("[]")
    pattern_list = re.findall(r"[a-zA-Z\s]+", text)
    pattern_list = [x.strip() for x in pattern_list]
    return f"( {', '.join(x for x in pattern_list if x)} )"


def _get_paraphrase_pattern(html: BeautifulSoup) -> Tuple[Dict[str, List[str]], str]:
    """
    Get word paraphrase and pattern.

    :param html: HTML.
    :type html: BeautifulSoup
    :return: (Paraphrases, Pattern).
    :rtype: Tuple[Dict[str, List[str]], str]
    """
    trans_div = html.find("div", class_="trans-container")
    if trans_div is None:
        paraphrase: Dict[str, List[str]] = {}
        pattern = ""
        
    else:
        paraphrase = _get_paraphrase(trans_div, word_type="en")
        pattern_p = trans_div.find("p", class_="additional")
        
        if pattern_p:
            pattern = _get_pattern(pattern_p)
            
        else:
            pattern = ""
            
    return paraphrase, pattern


def _get_zh_description(html: BeautifulSoup) -> List[ZHDesc]:
    """
    Get description of Chinese word.

    :param html: HTML.
    :type html: BeautifulSoup
    :return: Description list.
    :rtype: List[ZHDesc]
    """
    # To be done.
    # Tring to parse the HTML is too diffcult,
    # because it's hard to distinguish the part of phrse and paraphrase.
    _ = html
    return []


def _get_collins_sentence(sentence_div: Tag) -> ENSentence:
    """
    Get Collins sentence.

    :param sentence_div: Sentence tag.
    :type sentence_div: Tag.
    :return: Word sentence.
    :rtype: ENSentence
    """
    sentence_list = sentence_div.find_all("li")
    en_sentence: ENSentence = {
        "is_collins": True,
        "sentences": []
    }
    
    for _sentence_li in sentence_list:
        _collins_sentence_unit: CollinsSentenceUnit = {
            "mean": "",
            "category": "",
            "sentences": []
        }
        
        trans_div = _sentence_li.find("div", class_="collinsMajorTrans")
        if not trans_div:
            continue
        
        if re.search(r"\s+→\s*see\s+", trans_div.text):
            continue
        
        p_tag = trans_div.find("p")
        if not p_tag:
            continue
        
        span = p_tag.find("span", class_="additional")
        if not span:
            _category = ""
        else:
            _category = str(span.text)
            
        _mean = str(p_tag.text).replace(_category, "").strip()
        _mean = re.sub(r"\s+", " ", _mean)
        
        _collins_sentence_unit["category"] = _category
        _collins_sentence_unit["mean"] = _mean
        
        examples = _sentence_li.find_all("div", class_="exampleLists")
        
        for _example in examples:
            # should have two
            p_list = _example.find_all("p")
            
            if len(p_list) == 1:
                en = str(p_list[0].text)
                zh = ""
                
            elif len(p_list) >= 2:
                en = str(p_list[0].text)
                zh = str(p_list[1].text)
                
            else:
                continue
            
            _collins_sentence_unit["sentences"].append({
                "en": en,
                "zh": zh
            })
            
        en_sentence["sentences"].append(_collins_sentence_unit)
        
    return en_sentence


def _get_sentence_zh(sentence_div: Tag) -> List[SentenceUnit]:
    """
    Get sentences of Chinese word.

    :param sentence_div: Div.
    :type sentence_div: Tag
    :return: Sentence list.
    :rtype: List[SentenceUnit]
    """
    sentence_list = sentence_div.find_all("li")
    zh_sentence: List[SentenceUnit] = []
    
    for _sentence_li in sentence_list:
        # should have at least two p tags
        _p_list = _sentence_li.find_all("p")
        
        if len(_p_list) == 1:
            zh = str(_p_list[0].text)
            en = ""
            
        elif len(_p_list) >= 2:
            zh = str(_p_list[0].text)
            en = str(_p_list[1].text)
            
        else:
            continue
        
        zh_sentence.append({
            "en": en,
            "zh": zh
        })
        
    return zh_sentence


def _query_api(word: str) -> Optional[str]:
    """
    Query results from youdao web api.

    :param word: English or Chinese word.
    :type word: str
    :return: HTML string.
    :rtype: Optional[str]
    """
    url = f"http://dict.youdao.com/w/{word}"
    
    try:
        res = get(url, headers=HEADERS, timeout=(2, 2))
    
    except (Timeout, ReadTimeout):
        res = None
        
    if not res:
        return None
    
    if res.status_code != 200:
        return None
    
    html_text = res.text
    
    return html_text


def search_youdao_en(word: str) -> Optional[ENWord]:
    """
    Search English word from youdao dict.

    :param word: English word or paraphrase.
    :type word: str
    :return: Word information.
    :rtype: ENWord
    """
    html_text = _query_api(word)
    
    if not html_text:
        return None
    
    html = BeautifulSoup(html_text, "lxml")
    
    # check if we have result
    span = html.find("span", class_="keyword")
    
    if not span:
        return None
    
    pronounce = _get_pron_en(html)
    paraphrase, pattern = _get_paraphrase_pattern(html)
    
    rank_span = html.find("span", class_="via rank")
    if rank_span:
        rank = str(rank_span.text).strip() if rank_span.text else ""
    
    else:
        rank = ""
    
    sentence_div = html.find("div", class_="collinsToggle trans-container")
    if sentence_div:
        sentences = _get_collins_sentence(sentence_div)
    else:
        sentences: ENSentence = {
            "is_collins": True,
            "sentences": []
        }
        
    return {
        "word": word,
        "pronunciation": pronounce,
        "paraphrase": paraphrase,
        "pattern": pattern,
        "rank": rank,
        "sentence": sentences
    }
    
    
def search_youdao_zh(word: str) -> Optional[ZHWord]:
    """
    Search Chinese word from youdao dict.

    :param word: Chinese word or paraphrase.
    :type word: str
    :return: Word information.
    :rtype: ZHWord
    """
    html_text = _query_api(word)
    
    if not html_text:
        return None
    
    html = BeautifulSoup(html_text, "lxml")
    
    # check if we have result
    span = html.find("span", class_="keyword")
    
    if not span:
        return None
    
    pronoun = _get_pron_zh(html)
    
    trans_div = html.find("div", class_="trans-container")
    if trans_div:
        paraphrase = _get_paraphrase(trans_div, "zh")
    else:
        paraphrase = {}
    
    description = _get_zh_description(html)

    sentence_div = html.find("div", id="bilingual")
    if sentence_div:
        sentense = _get_sentence_zh(sentence_div)
    else:
        sentense = []
        
    return {
        "word": word,
        "pronunciation": pronoun,
        "paraphrase": paraphrase,
        "desc": description,
        "sentence": sentense
    }
    
    
__all__ = ["search_youdao_en", "search_youdao_zh"]

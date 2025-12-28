from typing import Literal, TypedDict, Union


class ENPronounce(TypedDict):
    usa: str
    uk: str
    other: str


class SentenceUnit(TypedDict):
    en: str
    zh: str


class CollinsSentenceUnit(TypedDict):
    mean: str
    category: str
    sentences: "list[SentenceUnit]"


class ENSentence(TypedDict):
    is_collins: bool
    sentences: list


class ENWord(TypedDict):
    word: str
    pronunciation: ENPronounce
    paraphrase: "dict[str, list[str]]"
    rank: str
    pattern: str
    sentence: ENSentence


class ZHDesc(TypedDict):
    desc: str
    desc_sentences: "list[SentenceUnit]"


class ZHWord(TypedDict):
    word: str
    pronunciation: str
    paraphrase: "dict[str, list[str]]"
    desc: "list[ZHDesc]"
    sentence: "list[SentenceUnit]"
    
    
class QuitMessage(TypedDict):
    cmd: Literal["quit"]
    

class QueryMessage(TypedDict):
    cmd: Literal["query"]
    word: str
    online: bool
    update_db: bool
    
    
Message = Union[QuitMessage, QueryMessage]


__all__ = ["ENPronounce", "SentenceUnit", "CollinsSentenceUnit", "ENSentence", "ENWord", "ZHWord",
           "Message", "QuitMessage", "QueryMessage", "ZHDesc"]

from typing import TypedDict, Literal


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
    sentences: list[SentenceUnit]


class ENSentence(TypedDict):
    is_collins: bool
    sentences: list


class ENWord(TypedDict):
    word: str
    pronunciation: ENPronounce
    paraphrase: dict[str, list[str]]
    rank: str
    pattern: str
    sentence: ENSentence


class ZHWord(TypedDict):
    word: str
    pronunciation: str
    paraphrase: list[str]
    desc: list[list]
    sentence: list[list]


__all__ = ["ENPronounce", "SentenceUnit", "CollinsSentenceUnit", "ENSentence", "ENWord", "ZHWord"]

from typing import Literal, TypedDict

PronounceAccent = Literal["uk", "usa"]
AudioPlayerBackend = Literal["", "afplay", "mpv", "ffplay", "paplay", "vlc"]
PronunciationPlayStatus = Literal[
    "ok",
    "backend_not_found",
    "backend_broken",
    "afplay_not_found",
    "linux_backend_not_found",
    "vlc_not_installed",
    "vlc_path_invalid",
    "play_failed",
]


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
    sentences: list[CollinsSentenceUnit] | list[SentenceUnit]


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


class PlayPronunciationMessage(TypedDict):
    cmd: Literal["play_pronunciation"]
    word: str


class PlaybackResponseMessage(TypedDict):
    cmd: Literal["playback_response"]
    status: PronunciationPlayStatus
    backend: AudioPlayerBackend
    message: str


Message = QuitMessage | QueryMessage | PlayPronunciationMessage


__all__ = [
    "AudioPlayerBackend",
    "CollinsSentenceUnit",
    "ENPronounce",
    "ENSentence",
    "ENWord",
    "Message",
    "PlayPronunciationMessage",
    "PlaybackResponseMessage",
    "PronounceAccent",
    "PronunciationPlayStatus",
    "QueryMessage",
    "QuitMessage",
    "SentenceUnit",
    "ZHDesc",
    "ZHWord",
]

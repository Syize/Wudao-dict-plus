"""将结构化词典结果降级为现有 CLI 的 JSON 协议。"""

from collections import defaultdict
from json import dumps
from typing import Literal

from ..interface import ENPronounce, ENWord, SentenceUnit, ZHDesc, ZHWord
from .schema import DictionaryEntryDetail, Example, Sense


def details_to_legacy_json(
    details: list[DictionaryEntryDetail],
    word: str,
    language: Literal["en", "zh"],
) -> str:
    """将一个或多个新词库同键词条压缩为当前 CLI 可消费的 JSON。"""
    if not details:
        return ""
    if language == "en":
        return dumps(_details_to_en_word(details, word), ensure_ascii=False)
    return dumps(_details_to_zh_word(details, word), ensure_ascii=False)


def _details_to_en_word(details: list[DictionaryEntryDetail], word: str) -> ENWord:
    pronunciation: ENPronounce = {"uk": "", "usa": "", "other": ""}
    paraphrase: dict[str, list[str]] = defaultdict(list)
    sentences: list[SentenceUnit] = []

    for detail in details:
        for item in detail.pronunciations:
            if not pronunciation[item.accent.value]:
                pronunciation[item.accent.value] = item.value
        for sense in detail.senses:
            category = sense.part_of_speech or "释义"
            meaning = sense.translation or sense.definition
            if meaning:
                paraphrase[category].append(_with_sense_label(sense, meaning))
        sentences.extend(_examples_to_en_sentences(detail.examples))

    metadata = details[0].entry.metadata
    result: ENWord = {
        "word": word,
        "pronunciation": pronunciation,
        "paraphrase": dict(paraphrase),
        "rank": str(metadata.get("rank", "")),
        "pattern": str(metadata.get("pattern", "")),
        "sentence": {"is_collins": False, "sentences": sentences},
    }
    return result


def _details_to_zh_word(details: list[DictionaryEntryDetail], word: str) -> ZHWord:
    paraphrase: dict[str, list[str]] = defaultdict(list)
    desc: list[ZHDesc] = []
    pronunciation = ""

    for detail in details:
        if not pronunciation and detail.pronunciations:
            pronunciation = detail.pronunciations[0].value
        examples_by_sense = _examples_by_sense(detail.examples)
        for sense in detail.senses:
            category = sense.part_of_speech or "释义"
            if sense.translation:
                paraphrase[category].append(_with_sense_label(sense, sense.translation))
            if sense.definition:
                desc.append(
                    {
                        "desc": _with_sense_label(sense, sense.definition),
                        "desc_sentences": examples_by_sense.get(sense.id, []),
                    }
                )

    result: ZHWord = {
        "word": word,
        "pronunciation": pronunciation,
        "paraphrase": dict(paraphrase),
        "desc": desc,
        "sentence": [],
    }
    return result


def _with_sense_label(sense: Sense, text: str) -> str:
    if sense.sense_label:
        return f"{sense.sense_label}. {text}"
    return text


def _examples_to_en_sentences(examples: list[Example]) -> list[SentenceUnit]:
    return [{"en": item.source_text, "zh": item.target_text} for item in examples]


def _examples_by_sense(
    examples: list[Example],
) -> dict[int | None, list[SentenceUnit]]:
    result: dict[int | None, list[SentenceUnit]] = defaultdict(list)
    for item in examples:
        result[item.sense_id].append({"en": item.source_text, "zh": item.target_text})
    return result


__all__ = ["details_to_legacy_json"]

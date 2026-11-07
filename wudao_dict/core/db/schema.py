"""结构化词典数据库的领域数据模型。

本模块只定义词库导入、查询和渲染层之间使用的稳定数据接口，不包含
SQLite 连接、SQL 语句或 JSON 序列化逻辑。具体持久化实现应位于独立的
repository 模块中。
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EntryType(StrEnum):
    """词条在词典中的类型。"""

    HEADWORD = "headword"
    PHRASE = "phrase"
    REDIRECT = "redirect"


class EntryKeyType(StrEnum):
    """检索键与词条的关系。"""

    HEADWORD = "headword"
    ALIAS = "alias"
    VARIANT = "variant"
    REDIRECT = "redirect"


class PronunciationAccent(StrEnum):
    """发音所属的口音或区域。"""

    UK = "uk"
    USA = "usa"
    OTHER = "other"


class RelationType(StrEnum):
    """词条之间的关系类型。"""

    PHRASE_OF = "phrase_of"
    REDIRECT_TO = "redirect_to"
    SEE_ALSO = "see_also"
    VARIANT_OF = "variant_of"


@dataclass(slots=True)
class SchemaMeta:
    """``schema_meta`` 表的一项元数据。"""

    key: str
    value: str


@dataclass(slots=True)
class DictionarySource:
    """一份已导入词库的来源与可追溯信息。"""

    name: str
    source_language: str
    target_language: str
    imported_at: str
    id: int | None = None
    version: str = ""
    license_note: str = ""
    source_sha256: str = ""
    parser_name: str = ""
    parser_version: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DictionaryEntry:
    """``entries`` 表中的一个实际词典条目。"""

    source_id: int | None
    display_headword: str
    canonical_headword: str
    id: int | None = None
    homograph_label: str = ""
    entry_type: EntryType = EntryType.HEADWORD
    raw_format: str = ""
    raw_content: str = ""
    content_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EntryKey:
    """用于精确或规范化检索的词条键。"""

    entry_id: int | None
    lookup_key: str
    normalized_key: str
    id: int | None = None
    key_type: EntryKeyType = EntryKeyType.HEADWORD
    sort_order: int = 0


@dataclass(slots=True)
class Pronunciation:
    """一个词条的一项发音标注。"""

    entry_id: int | None
    value: str
    id: int | None = None
    accent: PronunciationAccent = PronunciationAccent.OTHER
    notation: str = "ipa"
    sort_order: int = 0


@dataclass(slots=True)
class Sense:
    """词条中的一个义项，可通过 ``parent_sense_id`` 表示层级。"""

    entry_id: int | None
    sort_order: int
    id: int | None = None
    parent_sense_id: int | None = None
    sense_label: str = ""
    part_of_speech: str = ""
    grammar_note: str = ""
    definition: str = ""
    translation: str = ""
    usage_labels: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    note: str = ""


@dataclass(slots=True)
class Example:
    """附属于一个义项的双语例句。"""

    sense_id: int | None
    source_text: str
    id: int | None = None
    target_text: str = ""
    sort_order: int = 0


@dataclass(slots=True)
class EntryRelation:
    """两个词典条目之间的结构化关系。"""

    from_entry_id: int | None
    to_entry_id: int | None
    relation_type: RelationType
    id: int | None = None
    label: str = ""
    sort_order: int = 0


@dataclass(slots=True)
class DictionaryEntryDetail:
    """查询与渲染所需的一个完整词条聚合。"""

    entry: DictionaryEntry
    source: DictionarySource | None = None
    keys: list[EntryKey] = field(default_factory=list)
    pronunciations: list[Pronunciation] = field(default_factory=list)
    senses: list[Sense] = field(default_factory=list)
    examples: list[Example] = field(default_factory=list)
    relations: list[EntryRelation] = field(default_factory=list)


__all__ = [
    "DictionaryEntry",
    "DictionaryEntryDetail",
    "DictionarySource",
    "EntryKey",
    "EntryKeyType",
    "EntryRelation",
    "EntryType",
    "Example",
    "Pronunciation",
    "PronunciationAccent",
    "RelationType",
    "SchemaMeta",
    "Sense",
]

"""结构化词典数据库的数据接口。"""

from .legacy import LegacyDictionaryRepository
from .repository import LocalDictionaryRepository
from .schema import (
    DictionaryEntry,
    DictionaryEntryDetail,
    DictionarySource,
    EntryKey,
    EntryKeyType,
    EntryRelation,
    EntryType,
    Example,
    Pronunciation,
    PronunciationAccent,
    RelationType,
    SchemaMeta,
    Sense,
)
from .wudao import WudaoDictionaryRepository, normalize_lookup_key

__all__ = [
    "DictionaryEntry",
    "DictionaryEntryDetail",
    "DictionarySource",
    "EntryKey",
    "EntryKeyType",
    "EntryRelation",
    "EntryType",
    "Example",
    "LegacyDictionaryRepository",
    "LocalDictionaryRepository",
    "Pronunciation",
    "PronunciationAccent",
    "RelationType",
    "SchemaMeta",
    "Sense",
    "WudaoDictionaryRepository",
    "normalize_lookup_key",
]

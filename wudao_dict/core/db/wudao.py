"""新结构化 ``wudao_dict.db`` 的 SQLite 仓库。"""

import sqlite3
from json import dumps, loads
from os import makedirs
from os.path import dirname, exists

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
    Sense,
)

SCHEMA_VERSION = "2"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dictionary_sources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '',
    source_language TEXT NOT NULL,
    target_language TEXT NOT NULL,
    license_note TEXT NOT NULL DEFAULT '',
    source_sha256 TEXT NOT NULL DEFAULT '',
    parser_name TEXT NOT NULL DEFAULT '',
    parser_version TEXT NOT NULL DEFAULT '',
    imported_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES dictionary_sources(id),
    display_headword TEXT NOT NULL,
    canonical_headword TEXT NOT NULL,
    homograph_label TEXT NOT NULL DEFAULT '',
    entry_type TEXT NOT NULL DEFAULT 'headword',
    raw_format TEXT NOT NULL DEFAULT '',
    raw_content TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS entry_keys (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    lookup_key TEXT NOT NULL,
    normalized_key TEXT NOT NULL,
    key_type TEXT NOT NULL DEFAULT 'headword',
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pronunciations (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    accent TEXT NOT NULL DEFAULT 'other',
    notation TEXT NOT NULL DEFAULT 'ipa',
    value TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS senses (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    parent_sense_id INTEGER REFERENCES senses(id) ON DELETE CASCADE,
    sense_label TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL,
    part_of_speech TEXT NOT NULL DEFAULT '',
    grammar_note TEXT NOT NULL DEFAULT '',
    definition TEXT NOT NULL DEFAULT '',
    translation TEXT NOT NULL DEFAULT '',
    usage_labels TEXT NOT NULL DEFAULT '[]',
    domains TEXT NOT NULL DEFAULT '[]',
    note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS examples (
    id INTEGER PRIMARY KEY,
    sense_id INTEGER NOT NULL REFERENCES senses(id) ON DELETE CASCADE,
    source_text TEXT NOT NULL,
    target_text TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS entry_relations (
    id INTEGER PRIMARY KEY,
    from_entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    to_entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_entry_keys_normalized
ON entry_keys (normalized_key);
CREATE INDEX IF NOT EXISTS idx_entries_source
ON entries (source_id);
CREATE INDEX IF NOT EXISTS idx_senses_entry
ON senses (entry_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_examples_sense
ON examples (sense_id, sort_order);
"""


def normalize_lookup_key(value: str) -> str:
    """生成大小写及连续空格不敏感的精确检索键。"""
    return " ".join(value.strip().casefold().split())


class WudaoDictionaryRepository:
    """管理独立 ``wudao_dict.db`` 文件的结构化词典内容。"""

    def __init__(self, db_path: str, *, create: bool = False):
        if not exists(db_path) and not create:
            raise FileNotFoundError(f"找不到新词典数据库：{db_path}")
        if create:
            parent = dirname(db_path)
            if parent:
                makedirs(parent, exist_ok=True)

        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        if create:
            has_tables = self.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1"
            ).fetchone()
            if has_tables and not self.is_wudao_database(self.db):
                self.db.close()
                raise ValueError(f"拒绝在非 wudao_dict 数据库中创建词库表：{db_path}")
            self._initialize_schema()
        elif not self.is_wudao_database(self.db):
            self.db.close()
            raise ValueError(f"不是兼容的 wudao_dict 数据库：{db_path}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_db()

    def close_db(self):
        """关闭数据库连接。"""
        self.db.close()

    @staticmethod
    def is_wudao_database(db: sqlite3.Connection) -> bool:
        """检查连接是否指向已初始化的新词典数据库。"""
        row = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_meta'"
        ).fetchone()
        if row is None:
            return False
        row = db.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        ).fetchone()
        return row is not None and row[0] == SCHEMA_VERSION

    def _initialize_schema(self):
        self.db.executescript(_SCHEMA_SQL)
        self.db.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('schema_version', ?)",
            (SCHEMA_VERSION,),
        )
        self.db.commit()

    def insert_source(self, source: DictionarySource) -> DictionarySource:
        """写入一个词典来源，并回填其数据库 ID。"""
        cursor = self.db.execute(
            """
            INSERT INTO dictionary_sources (
                name, version, source_language, target_language, license_note,
                source_sha256, parser_name, parser_version, imported_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source.name,
                source.version,
                source.source_language,
                source.target_language,
                source.license_note,
                source.source_sha256,
                source.parser_name,
                source.parser_version,
                source.imported_at,
                dumps(source.metadata, ensure_ascii=False),
            ),
        )
        source.id = _require_lastrowid(cursor)
        self.db.commit()
        return source

    def insert_entry_detail(
        self, detail: DictionaryEntryDetail
    ) -> DictionaryEntryDetail:
        """写入一个已关联来源的完整词条，并回填新生成的 ID。"""
        entry = detail.entry
        if entry.source_id is None:
            raise ValueError("写入词条前必须设置 source_id")

        with self.db:
            cursor = self.db.execute(
                """
                INSERT INTO entries (
                    source_id, display_headword, canonical_headword, homograph_label,
                    entry_type, raw_format, raw_content, content_hash, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.source_id,
                    entry.display_headword,
                    entry.canonical_headword,
                    entry.homograph_label,
                    entry.entry_type.value,
                    entry.raw_format,
                    entry.raw_content,
                    entry.content_hash,
                    dumps(entry.metadata, ensure_ascii=False),
                ),
            )
            entry.id = _require_lastrowid(cursor)

            for key in detail.keys:
                key.entry_id = entry.id
                key.id = _require_lastrowid(
                    self.db.execute(
                        """
                    INSERT INTO entry_keys (entry_id, lookup_key, normalized_key, key_type, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            key.entry_id,
                            key.lookup_key,
                            key.normalized_key,
                            key.key_type.value,
                            key.sort_order,
                        ),
                    )
                )

            for pronunciation in detail.pronunciations:
                pronunciation.entry_id = entry.id
                pronunciation.id = _require_lastrowid(
                    self.db.execute(
                        """
                    INSERT INTO pronunciations (entry_id, accent, notation, value, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            pronunciation.entry_id,
                            pronunciation.accent.value,
                            pronunciation.notation,
                            pronunciation.value,
                            pronunciation.sort_order,
                        ),
                    )
                )

            old_to_new_sense_ids: dict[int, int] = {}
            for sense in detail.senses:
                old_id = sense.id
                sense.entry_id = entry.id
                parent_id = sense.parent_sense_id
                if parent_id is not None:
                    parent_id = old_to_new_sense_ids.get(parent_id, parent_id)
                sense.id = _require_lastrowid(
                    self.db.execute(
                        """
                    INSERT INTO senses (
                        entry_id, parent_sense_id, sense_label, sort_order, part_of_speech,
                        grammar_note, definition, translation, usage_labels, domains, note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            sense.entry_id,
                            parent_id,
                            sense.sense_label,
                            sense.sort_order,
                            sense.part_of_speech,
                            sense.grammar_note,
                            sense.definition,
                            sense.translation,
                            dumps(sense.usage_labels, ensure_ascii=False),
                            dumps(sense.domains, ensure_ascii=False),
                            sense.note,
                        ),
                    )
                )
                if old_id is not None:
                    old_to_new_sense_ids[old_id] = sense.id

            for example in detail.examples:
                if example.sense_id is not None:
                    example.sense_id = old_to_new_sense_ids.get(
                        example.sense_id, example.sense_id
                    )
                if example.sense_id is None:
                    raise ValueError("写入例句前必须设置 sense_id")
                example.id = _require_lastrowid(
                    self.db.execute(
                        """
                    INSERT INTO examples (sense_id, source_text, target_text, sort_order)
                    VALUES (?, ?, ?, ?)
                    """,
                        (
                            example.sense_id,
                            example.source_text,
                            example.target_text,
                            example.sort_order,
                        ),
                    )
                )

        return detail

    def lookup(self, word: str, source_language: str) -> list[DictionaryEntryDetail]:
        """按规范化词头查询指定源语言的一个或多个实际词条。"""
        normalized_key = normalize_lookup_key(word)
        rows = self.db.execute(
            """
            SELECT DISTINCT e.*, s.id AS source_id, s.name AS source_name,
                   s.version AS source_version, s.source_language,
                   s.target_language, s.license_note, s.source_sha256,
                   s.parser_name, s.parser_version, s.imported_at,
                   s.metadata_json AS source_metadata_json
            FROM entry_keys AS k
            JOIN entries AS e ON e.id = k.entry_id
            JOIN dictionary_sources AS s ON s.id = e.source_id
            WHERE k.normalized_key = ? AND s.source_language = ?
            ORDER BY e.display_headword, e.id
            """,
            (normalized_key, source_language),
        ).fetchall()
        return [self._load_entry_detail(row) for row in rows]

    def _load_entry_detail(self, row: sqlite3.Row) -> DictionaryEntryDetail:
        entry_id = row["id"]
        source = DictionarySource(
            id=row["source_id"],
            name=row["source_name"],
            version=row["source_version"],
            source_language=row["source_language"],
            target_language=row["target_language"],
            license_note=row["license_note"],
            source_sha256=row["source_sha256"],
            parser_name=row["parser_name"],
            parser_version=row["parser_version"],
            imported_at=row["imported_at"],
            metadata=_load_dict(row["source_metadata_json"]),
        )
        entry = DictionaryEntry(
            id=entry_id,
            source_id=row["source_id"],
            display_headword=row["display_headword"],
            canonical_headword=row["canonical_headword"],
            homograph_label=row["homograph_label"],
            entry_type=EntryType(row["entry_type"]),
            raw_format=row["raw_format"],
            raw_content=row["raw_content"],
            content_hash=row["content_hash"],
            metadata=_load_dict(row["metadata_json"]),
        )
        keys = [
            EntryKey(
                id=item["id"],
                entry_id=entry_id,
                lookup_key=item["lookup_key"],
                normalized_key=item["normalized_key"],
                key_type=EntryKeyType(item["key_type"]),
                sort_order=item["sort_order"],
            )
            for item in self.db.execute(
                "SELECT * FROM entry_keys WHERE entry_id=? ORDER BY sort_order, id",
                (entry_id,),
            )
        ]
        pronunciations = [
            Pronunciation(
                id=item["id"],
                entry_id=entry_id,
                accent=PronunciationAccent(item["accent"]),
                notation=item["notation"],
                value=item["value"],
                sort_order=item["sort_order"],
            )
            for item in self.db.execute(
                "SELECT * FROM pronunciations WHERE entry_id=? ORDER BY sort_order, id",
                (entry_id,),
            )
        ]
        senses = [
            Sense(
                id=item["id"],
                entry_id=entry_id,
                parent_sense_id=item["parent_sense_id"],
                sense_label=item["sense_label"],
                sort_order=item["sort_order"],
                part_of_speech=item["part_of_speech"],
                grammar_note=item["grammar_note"],
                definition=item["definition"],
                translation=item["translation"],
                usage_labels=_load_list(item["usage_labels"]),
                domains=_load_list(item["domains"]),
                note=item["note"],
            )
            for item in self.db.execute(
                "SELECT * FROM senses WHERE entry_id=? ORDER BY sort_order, id",
                (entry_id,),
            )
        ]
        examples = [
            Example(
                id=item["id"],
                sense_id=item["sense_id"],
                source_text=item["source_text"],
                target_text=item["target_text"],
                sort_order=item["sort_order"],
            )
            for item in self.db.execute(
                "SELECT x.* FROM examples AS x JOIN senses AS se ON se.id=x.sense_id WHERE se.entry_id=? ORDER BY x.sort_order, x.id",
                (entry_id,),
            )
        ]
        relations = [
            EntryRelation(
                id=item["id"],
                from_entry_id=item["from_entry_id"],
                to_entry_id=item["to_entry_id"],
                relation_type=RelationType(item["relation_type"]),
                label=item["label"],
                sort_order=item["sort_order"],
            )
            for item in self.db.execute(
                "SELECT * FROM entry_relations WHERE from_entry_id=? ORDER BY sort_order, id",
                (entry_id,),
            )
        ]
        return DictionaryEntryDetail(
            entry, source, keys, pronunciations, senses, examples, relations
        )


def _load_dict(value: str) -> dict:
    parsed = loads(value)
    return parsed if isinstance(parsed, dict) else {}


def _load_list(value: str) -> list[str]:
    parsed = loads(value)
    return parsed if isinstance(parsed, list) else []


def _require_lastrowid(cursor: sqlite3.Cursor) -> int:
    """返回成功 INSERT 的行 ID，拒绝向后传播不完整对象。"""
    row_id = cursor.lastrowid
    if row_id is None:
        raise RuntimeError("词典数据库 INSERT 未返回 row ID")
    return row_id


__all__ = ["SCHEMA_VERSION", "WudaoDictionaryRepository", "normalize_lookup_key"]

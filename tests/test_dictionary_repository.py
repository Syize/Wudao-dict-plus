import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from wudao_dict.core.db import (
    DictionaryEntry,
    DictionaryEntryDetail,
    DictionarySource,
    EntryKey,
    Pronunciation,
    PronunciationAccent,
    Sense,
    WudaoDictionaryRepository,
    normalize_lookup_key,
)
from wudao_dict.core.db.repository import LocalDictionaryRepository


class DictionaryRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.wudao_path = self.root / "wudao_dict.db"
        self.legacy_path = self.root / "dict.db"
        self.history_path = self.root / "credence.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_wudao_entry(self):
        with WudaoDictionaryRepository(str(self.wudao_path), create=True) as db:
            source = db.insert_source(
                DictionarySource(
                    name="test source",
                    source_language="en",
                    target_language="zh",
                    imported_at="2026-11-07T00:00:00+00:00",
                )
            )
            detail = DictionaryEntryDetail(
                entry=DictionaryEntry(source.id, "ability", "ability"),
                keys=[EntryKey(None, "ability", normalize_lookup_key("ability"))],
                pronunciations=[
                    Pronunciation(
                        None,
                        "/əˈbɪləti/",
                        accent=PronunciationAccent.UK,
                    )
                ],
                senses=[
                    Sense(
                        None,
                        0,
                        sense_label="1",
                        part_of_speech="n.",
                        definition="capacity",
                        translation="能力",
                    )
                ],
            )
            db.insert_entry_detail(detail)

    def _create_legacy_entry(self):
        db = sqlite3.connect(self.legacy_path)
        db.execute(
            """
            CREATE TABLE en (
                word TEXT PRIMARY KEY,
                pronunciation TEXT,
                paraphrase TEXT,
                rank TEXT,
                pattern TEXT,
                sentence TEXT
            )
            """
        )
        db.execute(
            "INSERT INTO en VALUES (?, ?, ?, ?, ?, ?)",
            (
                "legacy",
                '{"usa":"","uk":"","other":""}',
                '{"n.":["旧释义"]}',
                "",
                "",
                '{"is_collins":false,"sentences":[]}',
            ),
        )
        db.commit()
        db.close()

    def test_new_dictionary_is_queried_before_legacy_fallback(self):
        self._create_wudao_entry()
        self._create_legacy_entry()

        with LocalDictionaryRepository(
            str(self.wudao_path), str(self.legacy_path), str(self.history_path)
        ) as db:
            new_result = json.loads(db.query_word("en", "ABILITY"))
            legacy_result = json.loads(db.query_word("en", "legacy"))

        self.assertEqual(new_result["paraphrase"], {"n.": ["1. 能力"]})
        self.assertEqual(legacy_result["paraphrase"], {"n.": ["旧释义"]})

    def test_new_database_is_not_created_over_an_existing_legacy_database(self):
        self._create_legacy_entry()

        with self.assertRaises(ValueError):
            WudaoDictionaryRepository(str(self.legacy_path), create=True)

    def test_new_database_uses_separate_history_when_legacy_is_absent(self):
        self._create_wudao_entry()

        with LocalDictionaryRepository(
            str(self.wudao_path), str(self.legacy_path), str(self.history_path)
        ) as db:
            self.assertTrue(db.query_word("en", "ability"))
            db.record_query("ability")
            self.assertEqual(db.get_query_history(), [("ability", 1)])

        self.assertTrue(self.history_path.exists())


if __name__ == "__main__":
    unittest.main()

import logging
import sqlite3
import tempfile
import unittest
from pathlib import Path

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from wudao_dict.cli import WudaoCLI
from wudao_dict.core import QueryMessage
from wudao_dict.dict.local import DictDBClient
from wudao_dict.server import WudaoServer


class QueryHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "dict.db"
        sqlite3.connect(self.db_path).close()
        self.db = DictDBClient(str(self.db_path))

    def tearDown(self):
        self.db.close_db()
        self.temp_dir.cleanup()

    def test_record_query_increments_without_changing_case(self):
        self.db.record_query(" apple ")
        self.db.record_query("apple")
        self.db.record_query("Apple")

        self.assertEqual(
            self.db.get_query_history(), [("apple", 2), ("Apple", 1)]
        )

    def test_history_limit_returns_most_queried_words(self):
        self.db.record_query("first")
        self.db.record_query("second")
        self.db.record_query("second")
        self.db.record_query("third")
        self.db.record_query("third")
        self.db.record_query("third")

        self.assertEqual(
            self.db.get_query_history(limit=2), [("third", 3), ("second", 2)]
        )

    def test_successful_server_query_is_recorded(self):
        server = object.__new__(WudaoServer)
        server.local_dict = self.db
        server.logger = logging.getLogger("test-query-history")
        server._query_local_with_online_fallback = lambda *_args: '{"word": "apple"}'
        server._prefetch_pronunciation_audio = lambda *_args: None
        msg: QueryMessage = {
            "cmd": "query",
            "word": "apple",
            "online": False,
            "update_db": False,
        }

        self.assertEqual(server._generate_msg(msg), '{"word": "apple"}')
        self.assertEqual(self.db.get_query_history(), [("apple", 1)])

    def test_failed_server_query_is_not_recorded(self):
        server = object.__new__(WudaoServer)
        server.local_dict = self.db
        server.logger = logging.getLogger("test-query-history")
        server._query_local_with_online_fallback = lambda *_args: ""
        server._prefetch_pronunciation_audio = lambda *_args: None
        msg: QueryMessage = {
            "cmd": "query",
            "word": "missing",
            "online": False,
            "update_db": False,
        }

        self.assertEqual(server._generate_msg(msg), "")
        self.assertEqual(self.db.get_query_history(), [])

    def test_server_history_response_is_sorted_json(self):
        self.db.record_query("apple")
        self.db.record_query("apple")
        self.db.record_query("banana")
        server = object.__new__(WudaoServer)
        server.local_dict = self.db
        server.logger = logging.getLogger("test-query-history")

        self.assertEqual(
            server._get_query_history({"cmd": "query_history", "limit": 1}),
            '[{"word": "apple", "query_count": 2}]',
        )

    def test_interaction_completer_includes_commands_and_history(self):
        cli = object.__new__(WudaoCLI)
        cli._history_completions = ["apple", "new york"]
        completer = cli._create_interaction_completer()

        command_completions = [
            item.text
            for item in completer.get_completions(
                Document(":h"), CompleteEvent()
            )
        ]
        history_completions = [
            item.text
            for item in completer.get_completions(
                Document("new y"), CompleteEvent()
            )
        ]

        self.assertEqual(command_completions, [":help", ":history"])
        self.assertEqual(history_completions, ["new york"])


if __name__ == "__main__":
    unittest.main()

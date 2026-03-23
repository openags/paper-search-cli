import os
import tempfile
import unittest
from unittest.mock import patch

from paper_search import config


class TestConfigEnv(unittest.TestCase):
    def test_new_prefix_has_priority(self):
        with patch.dict(
            os.environ,
            {
                "PAPER_SEARCH_ENV_FILE": "/tmp/missing.env",
                "PAPER_SEARCH_CORE_API_KEY": "new-prefix",
                "PAPER_SEARCH_MCP_CORE_API_KEY": "legacy-prefix",
                "CORE_API_KEY": "bare-value",
            },
            clear=True,
        ):
            self.assertEqual(config.get_env("CORE_API_KEY", ""), "new-prefix")

    def test_legacy_mcp_prefix_still_works(self):
        with patch.dict(
            os.environ,
            {
                "PAPER_SEARCH_ENV_FILE": "/tmp/missing.env",
                "PAPER_SEARCH_MCP_CORE_API_KEY": "legacy-prefix",
                "CORE_API_KEY": "bare-value",
            },
            clear=True,
        ):
            self.assertEqual(config.get_env("CORE_API_KEY", ""), "legacy-prefix")

    def test_bare_env_fallback_still_works(self):
        with patch.dict(
            os.environ,
            {
                "PAPER_SEARCH_ENV_FILE": "/tmp/missing.env",
                "CORE_API_KEY": "bare-value",
            },
            clear=True,
        ):
            self.assertEqual(config.get_env("CORE_API_KEY", ""), "bare-value")

    def test_empty_prefixed_value_blocks_fallback(self):
        with patch.dict(
            os.environ,
            {
                "PAPER_SEARCH_ENV_FILE": "/tmp/missing.env",
                "PAPER_SEARCH_CORE_API_KEY": "",
                "CORE_API_KEY": "bare-value",
            },
            clear=True,
        ):
            self.assertEqual(config.get_env("CORE_API_KEY", "default"), "")

    def test_loads_from_custom_env_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=True) as tmp:
            tmp.write("PAPER_SEARCH_UNPAYWALL_EMAIL=test@example.com\n")
            tmp.flush()

            with patch.dict(
                os.environ,
                {"PAPER_SEARCH_ENV_FILE": tmp.name},
                clear=True,
            ):
                config.load_env_file(force=True)
                self.assertEqual(config.get_env("UNPAYWALL_EMAIL", ""), "test@example.com")


if __name__ == "__main__":
    unittest.main()

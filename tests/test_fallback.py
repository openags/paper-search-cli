import os
import unittest
from unittest.mock import patch, MagicMock

from paper_search import engine


class TestDownloadWithFallback(unittest.TestCase):
    def test_repository_fallback_before_scihub(self):
        with patch.object(engine, "download", return_value="primary failed"), \
             patch.object(engine, "_try_repository_fallback", return_value=("/tmp/repo.pdf", "")), \
             patch("paper_search.engine.SciHubFetcher") as mock_scihub:
            mock_scihub.return_value.download_pdf.side_effect = AssertionError("Sci-Hub should not be called")
            result = engine.download_with_fallback(
                source="arxiv",
                paper_id="1234.5678",
                doi="10.1000/test",
                title="test",
                use_scihub=True,
            )
            self.assertEqual(result, "/tmp/repo.pdf")

    def test_no_scihub_returns_error(self):
        with patch.object(engine, "download", return_value="primary failed"), \
             patch.object(engine, "_try_repository_fallback", return_value=(None, "repo failed")), \
             patch("paper_search.engine.UnpaywallResolver") as mock_unpaywall:
            mock_unpaywall.return_value.resolve_best_pdf_url.return_value = None
            result = engine.download_with_fallback(
                source="arxiv",
                paper_id="1234.5678",
                doi="10.1000/test",
                title="test",
                use_scihub=False,
            )
            self.assertIn("OA fallback chain", result)


if __name__ == "__main__":
    unittest.main()

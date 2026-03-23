import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from paper_search.academic_platforms.unpaywall import UnpaywallSearcher, UnpaywallResolver
from paper_search.paper import Paper


class TestUnpaywallSearchSource(unittest.TestCase):
    def setUp(self):
        self.resolver = UnpaywallResolver()
        self.searcher = UnpaywallSearcher(resolver=self.resolver)

    def test_search_empty_without_access(self):
        with patch.object(self.resolver, "has_api_access", return_value=False):
            result = self.searcher.search("10.1000/test")
        self.assertEqual(result, [])

    def test_search_empty_without_doi(self):
        with patch.object(self.resolver, "has_api_access", return_value=True):
            result = self.searcher.search("machine learning")
        self.assertEqual(result, [])

    def test_search_returns_one_record(self):
        paper = Paper(
            paper_id="unpaywall:10.1000/test",
            title="Unpaywall Record",
            authors=["Alice Example"],
            abstract="",
            doi="10.1000/test",
            published_date=datetime(2023, 1, 1),
            pdf_url="https://example.org/paper.pdf",
            url="https://doi.org/10.1000/test",
            source="unpaywall",
        )

        with patch.object(self.resolver, "has_api_access", return_value=True), \
             patch.object(self.resolver, "get_paper_by_doi", return_value=paper):
            result = self.searcher.search("doi:10.1000/test")

        self.assertEqual(len(result), 1)
        paper_dict = result[0].to_dict()
        self.assertEqual(paper_dict["source"], "unpaywall")
        self.assertEqual(paper_dict["doi"], "10.1000/test")


if __name__ == "__main__":
    unittest.main()

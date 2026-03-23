# tests/test_engine.py
import unittest
import os
from paper_search import engine


class TestPaperSearchEngine(unittest.TestCase):
    def test_all_sources_include_platforms(self):
        sources = engine.list_sources()
        for expected in ["arxiv", "dblp", "openaire", "citeseerx", "doaj",
                         "base", "zenodo", "hal", "ssrn", "unpaywall"]:
            self.assertIn(expected, sources)

    def test_parse_sources(self):
        parsed = engine._parse_sources("dblp,doaj,base,zenodo,hal,ssrn,unpaywall,invalid")
        self.assertEqual(parsed, ["dblp", "doaj", "base", "zenodo", "hal", "ssrn", "unpaywall"])

    def test_search_arxiv(self):
        """Test search with arxiv source returns results."""
        result = engine.search("machine learning", sources="arxiv", max_results=3)
        self.assertIsInstance(result, dict)
        self.assertIn("papers", result)
        papers = result["papers"]
        self.assertIsInstance(papers, list)
        if papers:
            self.assertIn("title", papers[0])
            self.assertIn("paper_id", papers[0])

    def test_download_arxiv(self):
        """Test downloading an arXiv paper."""
        save_path = "./downloads"
        os.makedirs(save_path, exist_ok=True)
        result = engine.search("machine learning", sources="arxiv", max_results=1)
        papers = result.get("papers", [])
        if papers:
            paper_id = papers[0]["paper_id"]
            dl_result = engine.download(paper_id, "arxiv", save_path)
            self.assertIsInstance(dl_result, str)


if __name__ == "__main__":
    unittest.main()

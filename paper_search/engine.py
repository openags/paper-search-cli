"""Core search engine - synchronous API for CLI and programmatic use."""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import httpx

from .config import get_env
from .paper import Paper
from .utils import extract_doi

from .academic_platforms.arxiv import ArxivSearcher
from .academic_platforms.pubmed import PubMedSearcher
from .academic_platforms.biorxiv import BioRxivSearcher
from .academic_platforms.medrxiv import MedRxivSearcher
from .academic_platforms.google_scholar import GoogleScholarSearcher
from .academic_platforms.iacr import IACRSearcher
from .academic_platforms.semantic import SemanticSearcher
from .academic_platforms.crossref import CrossRefSearcher
from .academic_platforms.openalex import OpenAlexSearcher
from .academic_platforms.pmc import PMCSearcher
from .academic_platforms.core import CORESearcher
from .academic_platforms.europepmc import EuropePMCSearcher
from .academic_platforms.sci_hub import SciHubFetcher
from .academic_platforms.dblp import DBLPSearcher
from .academic_platforms.openaire import OpenAiresearcher
from .academic_platforms.citeseerx import CiteSeerXSearcher
from .academic_platforms.doaj import DOAJSearcher
from .academic_platforms.base_search import BASESearcher
from .academic_platforms.unpaywall import UnpaywallResolver, UnpaywallSearcher
from .academic_platforms.zenodo import ZenodoSearcher
from .academic_platforms.hal import HALSearcher
from .academic_platforms.ssrn import SSRNSearcher

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Searcher registry
# ---------------------------------------------------------------------------

_SEARCHERS: Dict[str, Any] = {}


def _init_searchers() -> Dict[str, Any]:
    if _SEARCHERS:
        return _SEARCHERS

    _SEARCHERS.update({
        "arxiv": ArxivSearcher(),
        "pubmed": PubMedSearcher(),
        "biorxiv": BioRxivSearcher(),
        "medrxiv": MedRxivSearcher(),
        "google_scholar": GoogleScholarSearcher(),
        "iacr": IACRSearcher(),
        "semantic": SemanticSearcher(),
        "crossref": CrossRefSearcher(),
        "openalex": OpenAlexSearcher(),
        "pmc": PMCSearcher(),
        "core": CORESearcher(),
        "europepmc": EuropePMCSearcher(),
        "dblp": DBLPSearcher(),
        "openaire": OpenAiresearcher(),
        "citeseerx": CiteSeerXSearcher(),
        "doaj": DOAJSearcher(),
        "base": BASESearcher(),
        "unpaywall": UnpaywallSearcher(resolver=UnpaywallResolver()),
        "zenodo": ZenodoSearcher(),
        "hal": HALSearcher(),
        "ssrn": SSRNSearcher(),
    })

    # Optional paid sources
    if get_env("IEEE_API_KEY", ""):
        from .academic_platforms.ieee import IEEESearcher
        _SEARCHERS["ieee"] = IEEESearcher()

    if get_env("ACM_API_KEY", ""):
        from .academic_platforms.acm import ACMSearcher
        _SEARCHERS["acm"] = ACMSearcher()

    return _SEARCHERS


def get_searcher(source: str):
    searchers = _init_searchers()
    return searchers.get(source)


def list_sources() -> List[str]:
    return list(_init_searchers().keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_sources(sources: str) -> List[str]:
    all_sources = list_sources()
    if not sources or sources.strip().lower() == "all":
        return all_sources
    normalized = [s.strip().lower() for s in sources.split(",") if s.strip()]
    return [s for s in normalized if s in all_sources]


def _paper_unique_key(paper: Dict[str, Any]) -> str:
    doi = (paper.get("doi") or "").strip().lower()
    if doi:
        return f"doi:{doi}"
    title = (paper.get("title") or "").strip().lower()
    authors = (paper.get("authors") or "").strip().lower()
    if title:
        return f"title:{title}|authors:{authors}"
    paper_id = (paper.get("paper_id") or "").strip().lower()
    return f"id:{paper_id}"


def _dedupe_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen: set = set()
    for paper in papers:
        key = _paper_unique_key(paper)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(paper)
    return deduped


def _safe_filename(filename_hint: str, default: str = "paper") -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", filename_hint).strip("._")
    if not safe:
        return default
    return safe[:120]


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def search(
    query: str,
    sources: str = "all",
    max_results: int = 5,
    year: Optional[str] = None,
) -> Dict[str, Any]:
    """Search papers across multiple sources concurrently.

    Returns dict with keys: query, sources_used, source_results, errors, papers, total.
    """
    selected = _parse_sources(sources)
    if not selected:
        return {
            "query": query, "sources_used": [], "source_results": {},
            "errors": {"sources": "No valid sources selected."}, "papers": [], "total": 0,
        }

    searchers = _init_searchers()
    merged: List[Dict[str, Any]] = []
    source_results: Dict[str, int] = {}
    errors: Dict[str, str] = {}

    def _do_search(source_name: str):
        searcher = searchers[source_name]
        kwargs: dict = {"max_results": max_results}
        if year and source_name == "semantic":
            kwargs["year"] = year
        papers = searcher.search(query, **kwargs)
        return source_name, [p.to_dict() for p in papers]

    with ThreadPoolExecutor(max_workers=min(len(selected), 8)) as pool:
        futures = {pool.submit(_do_search, s): s for s in selected}
        for future in as_completed(futures):
            source_name = futures[future]
            try:
                name, papers = future.result()
                source_results[name] = len(papers)
                for p in papers:
                    if not p.get("source"):
                        p["source"] = name
                    merged.append(p)
            except Exception as exc:
                errors[source_name] = str(exc)
                source_results[source_name] = 0

    deduped = _dedupe_papers(merged)
    return {
        "query": query,
        "sources_used": selected,
        "source_results": source_results,
        "errors": errors,
        "papers": deduped,
        "total": len(deduped),
        "raw_total": len(merged),
    }


def download(paper_id: str, source: str, save_path: str = "./downloads") -> str:
    """Download a paper PDF from a specific source.

    Returns: path to saved PDF or error message.
    """
    searcher = get_searcher(source)
    if not searcher:
        return f"Unknown source: {source}"
    try:
        result = searcher.download_pdf(paper_id, save_path)
        return result if result else f"Download returned empty result for {source}/{paper_id}"
    except NotImplementedError as exc:
        return str(exc)
    except Exception as exc:
        return f"Download failed for {source}/{paper_id}: {exc}"


def read(paper_id: str, source: str, save_path: str = "./downloads") -> str:
    """Read (download + extract text from) a paper.

    Returns: extracted text or error message.
    """
    searcher = get_searcher(source)
    if not searcher:
        return f"Unknown source: {source}"
    try:
        result = searcher.read_paper(paper_id, save_path)
        return result if result else f"Read returned empty result for {source}/{paper_id}"
    except NotImplementedError as exc:
        return str(exc)
    except Exception as exc:
        return f"Read failed for {source}/{paper_id}: {exc}"


def _download_from_url(pdf_url: str, save_path: str, filename_hint: str = "paper") -> Optional[str]:
    if not pdf_url:
        return None
    os.makedirs(save_path, exist_ok=True)
    output_name = f"{_safe_filename(filename_hint)}.pdf"
    output_path = os.path.join(save_path, output_name)
    try:
        with httpx.Client(follow_redirects=True, timeout=30) as client:
            response = client.get(pdf_url)
        if response.status_code >= 400 or not response.content:
            return None
        content_type = (response.headers.get("content-type") or "").lower()
        is_pdf = "pdf" in content_type or response.content.startswith(b"%PDF") or pdf_url.lower().endswith(".pdf")
        if not is_pdf:
            return None
        with open(output_path, "wb") as f:
            f.write(response.content)
        return output_path
    except Exception as exc:
        logger.warning("Direct URL download failed for %s: %s", pdf_url, exc)
        return None


def _try_repository_fallback(doi: str, title: str, save_path: str) -> tuple:
    searchers = _init_searchers()
    repository_order = ["openaire", "core", "europepmc", "pmc"]
    query_candidates = [q for q in [(doi or "").strip(), (title or "").strip()] if q]
    if not query_candidates:
        return None, "no DOI/title provided for repository fallback"

    errors: List[str] = []
    for repo_name in repository_order:
        searcher = searchers.get(repo_name)
        if not searcher:
            continue
        for query in query_candidates:
            try:
                papers = searcher.search(query, max_results=3)
            except Exception as exc:
                errors.append(f"{repo_name}:{exc}")
                continue
            for paper in papers:
                pdf_url = (getattr(paper, "pdf_url", "") or "").strip()
                if not pdf_url:
                    continue
                pid = (getattr(paper, "paper_id", "") or query).strip()
                downloaded = _download_from_url(pdf_url, save_path, f"{repo_name}_{pid}")
                if downloaded:
                    return downloaded, ""
    return None, "; ".join(errors)


def download_with_fallback(
    source: str,
    paper_id: str,
    doi: str = "",
    title: str = "",
    save_path: str = "./downloads",
    use_scihub: bool = True,
    scihub_base_url: str = "https://sci-hub.se",
) -> str:
    """Try source-native download, then OA repositories, Unpaywall, then optional Sci-Hub.

    Returns: path to saved PDF or error message.
    """
    attempt_errors: List[str] = []

    # 1. Primary download
    primary_result = download(paper_id, source, save_path)
    if os.path.exists(primary_result):
        return primary_result
    attempt_errors.append(f"primary: {primary_result}")

    # 2. Repository fallback
    repo_result, repo_error = _try_repository_fallback(doi, title, save_path)
    if repo_result:
        return repo_result
    if repo_error:
        attempt_errors.append(f"repositories: {repo_error}")

    # 3. Unpaywall
    normalized_doi = (doi or "").strip()
    if normalized_doi:
        resolver = UnpaywallResolver()
        unpaywall_url = resolver.resolve_best_pdf_url(normalized_doi)
        if unpaywall_url:
            unpaywall_result = _download_from_url(unpaywall_url, save_path, f"unpaywall_{normalized_doi}")
            if unpaywall_result:
                return unpaywall_result
            attempt_errors.append("unpaywall: resolved OA URL but download failed")
        else:
            attempt_errors.append("unpaywall: no OA URL found")
    else:
        attempt_errors.append("unpaywall: DOI not provided")

    # 4. Sci-Hub fallback
    if not use_scihub:
        return "Download failed after OA fallback chain. Details: " + " | ".join(attempt_errors)

    fallback_id = normalized_doi or (title or "").strip() or paper_id
    fetcher = SciHubFetcher(base_url=scihub_base_url, output_dir=save_path)
    result = fetcher.download_pdf(fallback_id)
    if result:
        return result

    return "Download failed after all fallback attempts. Details: " + " | ".join(attempt_errors)

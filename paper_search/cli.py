"""paper-search: CLI tool for searching and downloading academic papers."""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from typing import Any, Dict, List

from . import engine


def _json_dump(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _truncate(text: str, length: int = 80) -> str:
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    return text[:length] + "..." if len(text) > length else text


def _format_paper_table(papers: List[Dict[str, Any]]) -> str:
    if not papers:
        return "No papers found."

    lines = []
    for i, p in enumerate(papers, 1):
        title = _truncate(p.get("title", ""), 100)
        authors = _truncate(p.get("authors", ""), 60)
        source = p.get("source", "")
        doi = p.get("doi", "")
        pid = p.get("paper_id", "")
        url = p.get("url", "")
        year = (p.get("published_date") or "")[:10]

        lines.append(f"[{i}] {title}")
        if authors:
            lines.append(f"    Authors: {authors}")
        info_parts = []
        if source:
            info_parts.append(f"Source: {source}")
        if year:
            info_parts.append(f"Date: {year}")
        if doi:
            info_parts.append(f"DOI: {doi}")
        elif pid:
            info_parts.append(f"ID: {pid}")
        if info_parts:
            lines.append(f"    {' | '.join(info_parts)}")
        if url:
            lines.append(f"    URL: {url}")
        lines.append("")

    return "\n".join(lines)


def cmd_search(args: argparse.Namespace) -> int:
    result = engine.search(
        query=args.query,
        sources=args.sources,
        max_results=args.max_results,
        year=args.year,
    )

    if args.json:
        print(_json_dump(result))
    else:
        errors = result.get("errors", {})
        if errors:
            for src, err in errors.items():
                print(f"[WARN] {src}: {err}", file=sys.stderr)

        stats = result.get("source_results", {})
        if stats:
            active = [f"{k}({v})" for k, v in stats.items() if v > 0]
            if active:
                print(f"Sources: {', '.join(active)}", file=sys.stderr)

        print(f"Found {result['total']} papers (before dedup: {result.get('raw_total', result['total'])})\n",
              file=sys.stderr)
        print(_format_paper_table(result["papers"]))

    return 0


def cmd_download(args: argparse.Namespace) -> int:
    result = engine.download(
        paper_id=args.paper_id,
        source=args.source,
        save_path=args.output_dir,
    )
    if args.json:
        print(_json_dump({"result": result}))
    else:
        print(result)
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    result = engine.read(
        paper_id=args.paper_id,
        source=args.source,
        save_path=args.output_dir,
    )
    if args.json:
        print(_json_dump({"text": result}))
    else:
        print(result)
    return 0


def cmd_download_fallback(args: argparse.Namespace) -> int:
    result = engine.download_with_fallback(
        source=args.source,
        paper_id=args.paper_id,
        doi=args.doi or "",
        title=args.title or "",
        save_path=args.output_dir,
        use_scihub=not args.no_scihub,
    )
    if args.json:
        print(_json_dump({"result": result}))
    else:
        print(result)
    return 0


def cmd_sources(args: argparse.Namespace) -> int:
    sources = engine.list_sources()
    if args.json:
        print(_json_dump({"sources": sources}))
    else:
        print("Available sources:")
        for s in sources:
            print(f"  - {s}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paper-search",
        description="Search and download academic papers from 20+ sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              paper-search search "transformer architecture"
              paper-search search "quantum computing" --sources arxiv,semantic --max-results 5
              paper-search download 2106.12345 --source arxiv
              paper-search read 2106.12345 --source arxiv
              paper-search download-fallback 2106.12345 --source arxiv --doi 10.48550/arXiv.2106.12345
              paper-search sources
        """),
    )
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="Search papers across academic sources")
    p_search.add_argument("query", help="Search query string")
    p_search.add_argument("-s", "--sources", default="all",
                          help="Comma-separated source names or 'all' (default: all)")
    p_search.add_argument("-n", "--max-results", type=int, default=5,
                          help="Max results per source (default: 5)")
    p_search.add_argument("-y", "--year", default=None,
                          help="Year filter for Semantic Scholar (e.g. '2020', '2018-2022')")
    p_search.add_argument("--json", action="store_true", help="Output as JSON")
    p_search.set_defaults(func=cmd_search)

    # download
    p_dl = sub.add_parser("download", help="Download a paper PDF from a specific source")
    p_dl.add_argument("paper_id", help="Paper identifier (e.g. arXiv ID, DOI)")
    p_dl.add_argument("--source", required=True, help="Source name (e.g. arxiv, semantic)")
    p_dl.add_argument("-o", "--output-dir", default="./downloads", help="Output directory (default: ./downloads)")
    p_dl.add_argument("--json", action="store_true", help="Output as JSON")
    p_dl.set_defaults(func=cmd_download)

    # read
    p_read = sub.add_parser("read", help="Download and extract text from a paper")
    p_read.add_argument("paper_id", help="Paper identifier")
    p_read.add_argument("--source", required=True, help="Source name")
    p_read.add_argument("-o", "--output-dir", default="./downloads", help="Output directory (default: ./downloads)")
    p_read.add_argument("--json", action="store_true", help="Output as JSON")
    p_read.set_defaults(func=cmd_read)

    # download-fallback
    p_fb = sub.add_parser("download-fallback",
                          help="Download with multi-stage fallback (source -> OA repos -> Unpaywall -> Sci-Hub)")
    p_fb.add_argument("paper_id", help="Paper identifier")
    p_fb.add_argument("--source", required=True, help="Primary source name")
    p_fb.add_argument("--doi", default="", help="DOI for fallback resolution")
    p_fb.add_argument("--title", default="", help="Paper title for fallback search")
    p_fb.add_argument("-o", "--output-dir", default="./downloads", help="Output directory (default: ./downloads)")
    p_fb.add_argument("--no-scihub", action="store_true", help="Disable Sci-Hub fallback")
    p_fb.add_argument("--json", action="store_true", help="Output as JSON")
    p_fb.set_defaults(func=cmd_download_fallback)

    # sources
    p_src = sub.add_parser("sources", help="List available academic sources")
    p_src.add_argument("--json", action="store_true", help="Output as JSON")
    p_src.set_defaults(func=cmd_sources)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

# paper-search-cli

A CLI tool for searching and downloading academic papers from 20+ sources. Also works as a **Claude Code Skill** for AI-assisted research.

## Features

- **20+ academic sources**: arXiv, PubMed, Semantic Scholar, CrossRef, OpenAlex, CORE, bioRxiv, medRxiv, and more
- **Concurrent search**: searches multiple sources in parallel with automatic deduplication
- **Smart download**: multi-stage fallback chain (source -> OA repositories -> Unpaywall -> Sci-Hub)
- **PDF text extraction**: download and extract text from papers in one step
- **JSON output**: machine-readable output for scripting and AI integration
- **Claude Code Skill**: use as a slash command in Claude Code

## Installation

### pip

```bash
pip install paper-search-cli
```

### uv

```bash
uv tool install paper-search-cli
```

### From source

```bash
git clone https://github.com/openags/paper-search-cli.git
cd paper-search-cli
uv sync
```

### Docker

```bash
docker build -t paper-search .
docker run paper-search search "transformer architecture"
```

## Usage

### Search papers

```bash
# Search all sources
paper-search search "transformer architecture"

# Search specific sources
paper-search search "quantum computing" --sources arxiv,semantic --max-results 5

# Filter by year (Semantic Scholar)
paper-search search "large language models" --sources semantic --year 2023-2024

# JSON output (for scripting / AI tools)
paper-search search "CRISPR" --json
```

### Download a paper

```bash
paper-search download 2106.12345 --source arxiv
paper-search download 2106.12345 --source arxiv --output-dir ./papers
```

### Download with fallback chain

```bash
paper-search download-fallback 2106.12345 --source arxiv \
  --doi 10.48550/arXiv.2106.12345 --title "Paper Title"
```

### Read (download + extract text)

```bash
paper-search read 2106.12345 --source arxiv
```

### List available sources

```bash
paper-search sources
```

## Claude Code Skill

This tool can be used as a [Claude Code Skill](https://docs.anthropic.com/en/docs/claude-code/skills) for AI-assisted academic research.

### Setup

Copy the skill file to your project:

```bash
mkdir -p .claude/commands
cp claude-skill/paper-search.md .claude/commands/paper-search.md
```

Or for global access (all projects):

```bash
mkdir -p ~/.claude/commands
cp claude-skill/paper-search.md ~/.claude/commands/paper-search.md
```

Then in Claude Code, use:

```
/paper-search transformer architecture in NLP
```

## Available Sources

| Source | Search | Download | Read | Notes |
|--------|--------|----------|------|-------|
| arXiv | yes | yes | yes | Open API, reliable |
| PubMed | yes | no | no | Metadata only |
| bioRxiv | yes | yes | yes | Category-based search |
| medRxiv | yes | yes | yes | Category-based search |
| Google Scholar | limited | no | no | Bot-detection active |
| IACR | yes | yes | yes | Cryptography focus |
| Semantic Scholar | yes | OA | OA | Year filter support |
| CrossRef | yes | no | no | DOI metadata |
| OpenAlex | yes | no | no | Broad metadata |
| PMC | yes | OA | OA | Open access only |
| CORE | yes | yes | yes | API key recommended |
| Europe PMC | yes | OA | OA | Open access only |
| dblp | yes | no | no | CS bibliography |
| OpenAIRE | yes | no | no | EU research |
| CiteSeerX | limited | yes | limited | Intermittent |
| DOAJ | yes | limited | limited | Open access journals |
| BASE | limited | yes | yes | OAI-PMH based |
| Zenodo | yes | yes | yes | Record-dependent |
| HAL | yes | yes | yes | French archives |
| SSRN | limited | limited | limited | Metadata only |
| Unpaywall | DOI | no | no | DOI lookup only |
| Sci-Hub | limited | yes | no | Optional fallback |
| IEEE | key | key | key | Requires API key |
| ACM | key | key | key | Requires API key |

## Environment Variables

All environment variables are optional. Set them in a `.env` file or export them.

| Variable | Purpose |
|----------|---------|
| `PAPER_SEARCH_UNPAYWALL_EMAIL` | Required for Unpaywall DOI resolution |
| `PAPER_SEARCH_CORE_API_KEY` | Better rate limits for CORE |
| `PAPER_SEARCH_SEMANTIC_SCHOLAR_API_KEY` | Better rate limits for Semantic Scholar |
| `PAPER_SEARCH_ZENODO_ACCESS_TOKEN` | Access embargoed Zenodo records |
| `PAPER_SEARCH_DOAJ_API_KEY` | Higher rate limits for DOAJ |
| `PAPER_SEARCH_GOOGLE_SCHOLAR_PROXY_URL` | Proxy for Google Scholar |
| `PAPER_SEARCH_IEEE_API_KEY` | Enable IEEE Xplore |
| `PAPER_SEARCH_ACM_API_KEY` | Enable ACM Digital Library |

Legacy `PAPER_SEARCH_MCP_*` prefix is also supported for backward compatibility.

## License

MIT

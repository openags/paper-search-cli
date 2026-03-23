FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY paper_search/ paper_search/

RUN pip install --no-cache-dir build \
    && python -m build --wheel \
    && pip install --no-cache-dir dist/*.whl

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/paper-search /usr/local/bin/paper-search

ENV PAPER_SEARCH_UNPAYWALL_EMAIL=""
ENV PAPER_SEARCH_CORE_API_KEY=""
ENV PAPER_SEARCH_SEMANTIC_SCHOLAR_API_KEY=""
ENV PAPER_SEARCH_ZENODO_ACCESS_TOKEN=""
ENV PAPER_SEARCH_DOAJ_API_KEY=""
ENV PAPER_SEARCH_GOOGLE_SCHOLAR_PROXY_URL=""
ENV PAPER_SEARCH_IEEE_API_KEY=""
ENV PAPER_SEARCH_ACM_API_KEY=""

ENTRYPOINT ["paper-search"]

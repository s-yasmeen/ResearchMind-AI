from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .models import Source, StudyRecord

JsonGetter = Callable[[str, dict[str, str], dict[str, str]], dict[str, Any]]
TextGetter = Callable[[str, dict[str, str], dict[str, str]], str]


@dataclass(frozen=True)
class SearchAudit:
    provider: str
    query: str
    requested_at: str
    result_count: int
    parameters: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class SearchResult:
    records: tuple[StudyRecord, ...]
    audit: SearchAudit


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_get(url: str, params: dict[str, str], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _text_get(url: str, params: dict[str, str], headers: dict[str, str]) -> str:
    request = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    value = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", value)
    return value or None


def _title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _plain_text(value: str | None) -> str:
    if not value:
        return ""
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return " ".join(without_tags.split())


def record_key(record: StudyRecord) -> str:
    identifier = record.source.identifier or ""
    doi = normalize_doi(identifier)
    if doi and doi.startswith("10."):
        return f"doi:{doi}"
    if identifier.startswith("arXiv:"):
        return re.sub(r"v\d+$", "", identifier.lower())
    return f"title:{_title_key(record.source.title)}:{record.source.year or 'unknown'}"


def deduplicate(records: list[StudyRecord]) -> list[StudyRecord]:
    unique: dict[str, StudyRecord] = {}
    for record in records:
        key = record_key(record)
        current = unique.get(key)
        if current is None or len(record.abstract) > len(current.abstract):
            unique[key] = record
    return list(unique.values())


def parse_crossref(payload: dict[str, Any], retrieved_at: str | None = None) -> list[StudyRecord]:
    items = payload.get("message", {}).get("items", [])
    records: list[StudyRecord] = []
    timestamp = retrieved_at or _utc_now()
    for item in items:
        titles = item.get("title") or []
        title = " ".join(titles[0].split()) if titles else ""
        doi = normalize_doi(item.get("DOI"))
        if not title or not doi:
            continue
        authors = tuple(
            " ".join(part for part in (author.get("given", ""), author.get("family", "")) if part).strip()
            for author in item.get("author", [])
        )
        authors = tuple(author for author in authors if author)
        date_parts = (item.get("published-print") or item.get("published-online") or item.get("issued") or {}).get("date-parts", [[]])
        year = date_parts[0][0] if date_parts and date_parts[0] else None
        containers = item.get("container-title") or []
        records.append(StudyRecord(
            source=Source(
                title=title,
                url=item.get("URL") or f"https://doi.org/{doi}",
                authors=authors,
                year=year,
                identifier=doi,
                venue=containers[0] if containers else None,
                publication_type=item.get("type"),
                retrieved_from="Crossref",
                retrieved_at=timestamp,
            ),
            abstract=_plain_text(item.get("abstract")),
            study_type=item.get("type") or "unspecified",
            peer_reviewed=None,
        ))
    return records


_ATOM = {"atom": "http://www.w3.org/2005/Atom"}


def parse_arxiv(xml_text: str, retrieved_at: str | None = None) -> list[StudyRecord]:
    root = ET.fromstring(xml_text)
    timestamp = retrieved_at or _utc_now()
    records: list[StudyRecord] = []
    for entry in root.findall("atom:entry", _ATOM):
        title = " ".join((entry.findtext("atom:title", default="", namespaces=_ATOM)).split())
        abstract = " ".join((entry.findtext("atom:summary", default="", namespaces=_ATOM)).split())
        url = entry.findtext("atom:id", default="", namespaces=_ATOM)
        identifier = url.rstrip("/").split("/")[-1]
        published = entry.findtext("atom:published", default="", namespaces=_ATOM)
        year = int(published[:4]) if published[:4].isdigit() else None
        authors = tuple(
            " ".join((author.findtext("atom:name", default="", namespaces=_ATOM)).split())
            for author in entry.findall("atom:author", _ATOM)
        )
        if title and identifier:
            records.append(StudyRecord(
                source=Source(
                    title=title,
                    url=url,
                    authors=tuple(a for a in authors if a),
                    year=year,
                    identifier=f"arXiv:{identifier}",
                    venue="arXiv",
                    publication_type="preprint",
                    retrieved_from="arXiv",
                    retrieved_at=timestamp,
                ),
                abstract=abstract,
                study_type="preprint",
                peer_reviewed=False,
            ))
    return records


class CrossrefClient:
    endpoint = "https://api.crossref.org/works"

    def __init__(self, contact_email: str | None = None, getter: JsonGetter = _json_get):
        self.contact_email = contact_email
        self.getter = getter
        self._cache: dict[tuple[str, int], SearchResult] = {}

    def search(self, query: str, max_results: int = 20) -> SearchResult:
        if not 1 <= max_results <= 100:
            raise ValueError("max_results must be between 1 and 100.")
        query = query.strip()
        if not query:
            raise ValueError("query cannot be empty.")
        cache_key = (query, max_results)
        if cache_key in self._cache:
            return self._cache[cache_key]
        params = {"query.bibliographic": query, "rows": str(max_results), "select": "DOI,title,author,published-print,published-online,issued,container-title,type,URL,abstract"}
        if self.contact_email:
            params["mailto"] = self.contact_email
        payload = self.getter(self.endpoint, params, {"User-Agent": "ResearchMind-AI/0.3"})
        records = tuple(parse_crossref(payload))
        result = SearchResult(records, SearchAudit("Crossref", query, _utc_now(), len(records), tuple(sorted(params.items()))))
        self._cache[cache_key] = result
        return result


class ArxivClient:
    endpoint = "https://export.arxiv.org/api/query"

    def __init__(self, getter: TextGetter = _text_get, minimum_interval: float = 3.0):
        self.getter = getter
        self.minimum_interval = max(3.0, minimum_interval)
        self._last_request = 0.0
        self._cache: dict[tuple[str, int], SearchResult] = {}

    def search(self, query: str, max_results: int = 20) -> SearchResult:
        if not 1 <= max_results <= 100:
            raise ValueError("max_results must be between 1 and 100.")
        query = query.strip()
        if not query:
            raise ValueError("query cannot be empty.")
        cache_key = (query, max_results)
        if cache_key in self._cache:
            return self._cache[cache_key]
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.minimum_interval:
            time.sleep(self.minimum_interval - elapsed)
        params = {"search_query": f'all:"{query}"', "start": "0", "max_results": str(max_results), "sortBy": "relevance", "sortOrder": "descending"}
        xml_text = self.getter(self.endpoint, params, {"User-Agent": "ResearchMind-AI/0.3"})
        self._last_request = time.monotonic()
        records = tuple(parse_arxiv(xml_text))
        result = SearchResult(records, SearchAudit("arXiv", query, _utc_now(), len(records), tuple(sorted(params.items()))))
        self._cache[cache_key] = result
        return result


def search_all(query: str, clients: list[Any], max_results_per_source: int = 20) -> tuple[list[StudyRecord], list[SearchAudit]]:
    records: list[StudyRecord] = []
    audits: list[SearchAudit] = []
    for client in clients:
        result = client.search(query, max_results=max_results_per_source)
        records.extend(result.records)
        audits.append(result.audit)
    return deduplicate(records), audits

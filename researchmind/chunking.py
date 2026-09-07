from __future__ import annotations

import hashlib
import re

from .models import DocumentPage, EvidenceChunk

_HEADING = re.compile(
    r"^(?:\d+(?:\.\d+)*\s+)?(abstract|introduction|background|related work|literature review|"
    r"methodology|methods?|experimental setup|results?|discussion|limitations?|"
    r"threats to validity|conclusion|references)\s*$",
    re.IGNORECASE,
)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text) if part.strip()]


def chunk_pages(
    pages: list[DocumentPage],
    source_identifier: str,
    target_words: int = 220,
    overlap_sentences: int = 2,
) -> list[EvidenceChunk]:
    if target_words < 50:
        raise ValueError("target_words must be at least 50.")
    chunks: list[EvidenceChunk] = []
    seen: set[tuple[int, int, str | None, str]] = set()
    section: str | None = None
    buffer: list[tuple[str, int]] = []
    new_since_flush = False

    def flush() -> None:
        nonlocal buffer, new_since_flush
        if not buffer or not new_since_flush:
            return
        text = " ".join(sentence for sentence, _ in buffer).strip()
        if text:
            page_start = min(page for _, page in buffer)
            page_end = max(page for _, page in buffer)
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            duplicate_key = (page_start, page_end, section, content_hash)
            if duplicate_key in seen:
                buffer = buffer[-overlap_sentences:] if overlap_sentences else []
                new_since_flush = False
                return
            seen.add(duplicate_key)
            chunks.append(EvidenceChunk(
                chunk_id=f"{source_identifier}:{page_start}-{page_end}:{content_hash[:12]}",
                document_id=pages[0].document_id,
                source_identifier=source_identifier,
                page_start=page_start,
                page_end=page_end,
                section=section,
                text=text,
                content_hash=content_hash,
            ))
        buffer = buffer[-overlap_sentences:] if overlap_sentences else []
        new_since_flush = False

    for page in pages:
        for paragraph in re.split(r"\n\s*\n|\n(?=[A-Z][A-Z\s]{3,}$)", page.text):
            candidate = paragraph.strip()
            heading_match = _HEADING.match(candidate)
            if heading_match:
                flush()
                buffer = []
                section = heading_match.group(1).title()
                continue
            for sentence in _sentences(candidate):
                buffer.append((sentence, page.page_number))
                new_since_flush = True
                if sum(len(item.split()) for item, _ in buffer) >= target_words:
                    flush()
    flush()
    return chunks

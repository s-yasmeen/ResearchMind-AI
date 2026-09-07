from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import DocumentPage


class DocumentError(RuntimeError):
    pass


@dataclass(frozen=True)
class ValidatedPDF:
    path: Path
    sha256: str
    size_bytes: int


class PageExtractor(Protocol):
    def __call__(self, path: Path) -> tuple[bool, list[str]]: ...


def validate_pdf(path: Path, max_size_mb: int = 50) -> ValidatedPDF:
    path = Path(path)
    if not path.is_file():
        raise DocumentError("PDF file does not exist.")
    size = path.stat().st_size
    if size == 0:
        raise DocumentError("PDF file is empty.")
    if size > max_size_mb * 1024 * 1024:
        raise DocumentError(f"PDF exceeds the {max_size_mb} MB limit.")
    with path.open("rb") as stream:
        header = stream.read(5)
        digest = hashlib.sha256(header)
        while block := stream.read(1024 * 1024):
            digest.update(block)
    if header != b"%PDF-":
        raise DocumentError("File content is not a PDF.")
    return ValidatedPDF(path=path, sha256=digest.hexdigest(), size_bytes=size)


def _pypdf_extract(path: Path) -> tuple[bool, list[str]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentError("pypdf is required for PDF extraction.") from exc
    try:
        reader = PdfReader(str(path), strict=False)
        if reader.is_encrypted:
            return True, []
        return False, [(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:
        raise DocumentError(f"PDF could not be parsed: {type(exc).__name__}") from exc


def extract_pages(
    validated: ValidatedPDF,
    source_identifier: str,
    extractor: PageExtractor = _pypdf_extract,
) -> list[DocumentPage]:
    encrypted, texts = extractor(validated.path)
    if encrypted:
        raise DocumentError("Encrypted PDFs require the user to provide an accessible copy.")
    if not texts:
        raise DocumentError("PDF contains no extractable pages.")
    pages: list[DocumentPage] = []
    for number, raw_text in enumerate(texts, start=1):
        text = "\n".join(line.rstrip() for line in raw_text.splitlines()).strip()
        warning = None if text else "No text extracted; OCR or manual review may be required."
        pages.append(DocumentPage(
            document_id=validated.sha256,
            page_number=number,
            text=text,
            extraction_warning=warning,
        ))
    return pages

from pathlib import Path

import pytest

from researchmind.chunking import chunk_pages
from researchmind.documents import DocumentError, extract_pages, validate_pdf


def test_pdf_magic_and_hash_validation(tmp_path: Path):
    path = tmp_path / "paper.pdf"
    path.write_bytes(b"%PDF-1.7\nminimal fixture")
    result = validate_pdf(path)
    assert result.size_bytes == path.stat().st_size
    assert len(result.sha256) == 64


def test_non_pdf_is_rejected(tmp_path: Path):
    path = tmp_path / "fake.pdf"
    path.write_text("not a pdf", encoding="utf-8")
    with pytest.raises(DocumentError):
        validate_pdf(path)


def test_page_extraction_preserves_page_number_and_flags_ocr(tmp_path: Path):
    path = tmp_path / "paper.pdf"
    path.write_bytes(b"%PDF-1.7\nfixture")
    validated = validate_pdf(path)
    pages = extract_pages(validated, "doi:1", extractor=lambda _: (False, ["Abstract\nEvidence.", ""]))
    assert pages[0].page_number == 1
    assert pages[0].text == "Abstract\nEvidence."
    assert pages[1].page_number == 2
    assert "OCR" in pages[1].extraction_warning


def test_encrypted_pdf_is_rejected(tmp_path: Path):
    path = tmp_path / "paper.pdf"
    path.write_bytes(b"%PDF-1.7\nfixture")
    with pytest.raises(DocumentError, match="Encrypted"):
        extract_pages(validate_pdf(path), "doi:1", extractor=lambda _: (True, []))


def test_chunking_preserves_pages_sections_and_stable_hash(tmp_path: Path):
    path = tmp_path / "paper.pdf"
    path.write_bytes(b"%PDF-1.7\nfixture")
    validated = validate_pdf(path)
    text = "Abstract\n\n" + "Evidence supports the method. " * 30
    pages = extract_pages(validated, "doi:1", extractor=lambda _: (False, [text, "Results\n\nThe experiment improves utility. " * 20]))
    chunks = chunk_pages(pages, "doi:1", target_words=50, overlap_sentences=1)
    assert chunks
    assert chunks[0].source_identifier == "doi:1"
    assert chunks[0].page_start == 1
    assert chunks[0].section == "Abstract"
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)

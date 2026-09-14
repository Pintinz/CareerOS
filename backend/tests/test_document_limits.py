"""Phase 11 §98: CV parsing is bounded by content, not just by upload size."""

import io
import zipfile

import pytest
from fastapi import HTTPException
from pypdf import PdfWriter

from app.services.document_extraction import MAX_EXTRACTED_CHARS, MAX_PDF_PAGES, extract_text


def test_pdf_with_too_many_pages_is_rejected_before_text_extraction() -> None:
    writer = PdfWriter()
    for _ in range(MAX_PDF_PAGES + 1):
        writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)

    with pytest.raises(HTTPException) as exc_info:
        extract_text(filename="cv.pdf", content=buffer.getvalue(), content_type="application/pdf")
    assert exc_info.value.status_code == 422
    assert str(MAX_PDF_PAGES + 1) in exc_info.value.detail


def test_docx_decompression_bomb_is_rejected_without_being_parsed() -> None:
    # ~31MB of zeros compresses to a few kilobytes — well under the 5MB upload cap.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"\0" * (31 * 1024 * 1024))
    assert len(buffer.getvalue()) < 5 * 1024 * 1024

    with pytest.raises(HTTPException) as exc_info:
        extract_text(filename="cv.docx", content=buffer.getvalue(), content_type=None)
    assert exc_info.value.status_code == 422
    assert "unexpectedly large" in exc_info.value.detail


def test_non_zip_docx_is_rejected_cleanly() -> None:
    with pytest.raises(HTTPException) as exc_info:
        extract_text(filename="cv.docx", content=b"not a zip file", content_type=None)
    assert exc_info.value.status_code == 422


def test_extracted_text_beyond_the_limit_is_rejected() -> None:
    with pytest.raises(HTTPException) as exc_info:
        extract_text(filename="cv.txt", content=b"a" * (MAX_EXTRACTED_CHARS + 1), content_type="text/plain")
    assert exc_info.value.status_code == 422


def test_normal_text_cv_still_extracts() -> None:
    text = extract_text(filename="cv.txt", content=b"Process Technician with PLC experience", content_type="text/plain")
    assert "PLC" in text

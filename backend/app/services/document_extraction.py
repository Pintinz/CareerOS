"""Plain-text extraction from uploaded CV files. No AI/LLM involved — pypdf/python-docx do
structural parsing only (spec Rule 8: never claim AI where there is none)."""

import io

import docx
from fastapi import HTTPException, status
from pypdf import PdfReader

SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "text/plain",
}


def extract_text(*, filename: str | None, content: bytes, content_type: str | None) -> str:
    ext = (filename or "").lower().rsplit(".", 1)[-1] if filename and "." in filename else ""

    if content_type == "application/pdf" or ext == "pdf":
        return _extract_pdf_text(content)
    if (
        content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or ext == "docx"
    ):
        return _extract_docx_text(content)
    if content_type == "text/plain" or ext == "txt":
        return content.decode("utf-8", errors="ignore")

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Unsupported CV format. Upload a PDF, DOCX, or plain-text file.",
    )


def _extract_pdf_text(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # pypdf raises various exception types for malformed PDFs
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Could not read this PDF file."
        ) from exc

    text = "\n".join(pages).strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No extractable text found in this PDF (it may be a scanned image without OCR).",
        )
    return text


def _extract_docx_text(content: bytes) -> str:
    try:
        document = docx.Document(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Could not read this DOCX file."
        ) from exc

    paragraphs = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraphs.append(cell.text)

    text = "\n".join(p for p in paragraphs if p.strip())
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No extractable text found in this DOCX file."
        )
    return text

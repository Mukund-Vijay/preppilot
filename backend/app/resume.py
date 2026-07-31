"""Extract plain text from an uploaded resume file (PDF, DOCX, or TXT)."""
from __future__ import annotations

import io


def extract_text(filename: str, data: bytes) -> str:
    """Return the plain text of a resume file, chosen by extension."""
    name = (filename or "").lower()

    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()

    if name.endswith(".docx"):
        import docx
        doc = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs).strip()

    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore").strip()

    raise ValueError("Unsupported file type — please upload a PDF, DOCX, or TXT file.")

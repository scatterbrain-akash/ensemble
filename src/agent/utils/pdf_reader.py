from __future__ import annotations

from pathlib import Path


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract plain text from a non-scanned (text-layer) PDF.

    Uses pypdf to read each page and join the text. Strips blank lines.
    Raises ValueError if the file produces no extractable text (scanned/image PDF).
    """
    try:
        import pypdf
    except ImportError as exc:
        raise ImportError(
            "pypdf is required for PDF support. Install it with: pip install 'pypdf>=4.0.0,<5.0.0'"
        ) from exc

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    reader = pypdf.PdfReader(str(pdf_path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append(text)

    full_text = "\n\n".join(pages).strip()
    if not full_text:
        raise ValueError(
            f"No extractable text found in {pdf_path.name}. "
            "Only text-layer PDFs are supported (not scanned/image PDFs)."
        )
    return full_text

from __future__ import annotations

import io
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.agent.config import Settings
from src.agent.core.orchestrator import Orchestrator
from src.agent.utils.pdf_reader import extract_text_from_pdf

app = FastAPI(
    title="Claims Denial Appeal Intelligence",
    description="Upload a denial letter or EOB (text or PDF) and receive an evidence-grounded appeal package.",
    version="1.0.0",
)

# Shared orchestrator — created once at startup.
_orchestrator: Orchestrator | None = None


@app.on_event("startup")
def _startup() -> None:
    global _orchestrator
    settings = Settings(env="personal")
    _orchestrator = Orchestrator(settings=settings)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> HTMLResponse:
    from pathlib import Path
    html = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(
    file: Annotated[UploadFile | None, File(description="PDF denial letter / EOB")] = None,
    text: Annotated[str | None, Form(description="Plain-text denial letter")] = None,
) -> JSONResponse:
    """Accept either a PDF upload or raw text and run the full agent pipeline."""
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not ready.")

    if file is not None and file.filename:
        raw_bytes = await file.read()
        if file.filename.lower().endswith(".pdf"):
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
                pages = [p.extract_text() or "" for p in reader.pages]
                input_text = "\n\n".join(p.strip() for p in pages if p.strip())
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {exc}")
        else:
            try:
                input_text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="File could not be decoded as UTF-8 text.")
    elif text and text.strip():
        input_text = text.strip()
    else:
        raise HTTPException(status_code=400, detail="Provide either a file upload or a text field.")

    try:
        state = _orchestrator.run(input_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return JSONResponse(content=state.model_dump())

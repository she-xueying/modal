"""File service: docx upload, text extraction, and in-place editing.

Uses python-docx to read and modify .docx files while preserving formatting.
Modified files are saved as NEW files (the original is never touched).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import File

UPLOAD_DIR = settings.data_dir / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class FileError(Exception):
    """Raised when a file operation fails."""


def _new_id() -> str:
    return uuid.uuid4().hex


# --------------------------------------------------------------------------- #
#  File records (DB)
# --------------------------------------------------------------------------- #

def create_file_record(
    db: Session,
    *,
    filename: str,
    path: str,
    role: str,
    original_id: str | None = None,
) -> File:
    rec = File(id=_new_id(), filename=filename, path=path, role=role, original_id=original_id)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def get_file_record(db: Session, file_id: str) -> File | None:
    return db.get(File, file_id)


# --------------------------------------------------------------------------- #
#  Upload
# --------------------------------------------------------------------------- #

def save_docx_upload(content: bytes, filename: str) -> dict:
    """Save an uploaded docx; returns {filename, path, role}."""
    if not filename.lower().endswith(".docx"):
        raise FileError("仅支持 .docx 文件")
    safe_name = Path(filename).name  # strip any directory components
    fid = _new_id()
    path = UPLOAD_DIR / f"{fid}.docx"
    path.write_bytes(content)
    return {"filename": safe_name, "path": str(path), "role": "upload"}


# --------------------------------------------------------------------------- #
#  Extraction
# --------------------------------------------------------------------------- #

def extract_docx_paragraphs(path: str) -> list[str]:
    """Extract paragraph texts from a docx (non-empty)."""
    from docx import Document
    doc = Document(path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def paragraph_indexed_text(path: str, max_paras: int = 200, max_chars: int = 12000) -> str:
    """Build a numbered paragraph listing for the LLM context."""
    paras = extract_docx_paragraphs(path)
    lines: list[str] = []
    total = 0
    for i, t in enumerate(paras):
        if i >= max_paras:
            lines.append("……（段落较多，已截断）")
            break
        lines.append(f"[{i}] {t}")
        total += len(t)
        if total > max_chars:
            lines.append("……（文档较长，已截断）")
            break
    return "\n".join(lines) if lines else "（文档为空）"


# --------------------------------------------------------------------------- #
#  Editing (creates a NEW modified file)
# --------------------------------------------------------------------------- #

def apply_docx_edit(src_path: str, paragraph_index: int, new_text: str, filename: str) -> dict:
    """Replace one paragraph's text in a copy of the docx.

    Returns a new file record payload {filename, path, role}.
    """
    from docx import Document

    if paragraph_index < 0:
        raise FileError("段落索引无效")
    doc = Document(src_path)
    paras = doc.paragraphs
    if paragraph_index >= len(paras):
        raise FileError(f"段落索引超出范围（共 {len(paras)} 段，索引从 0 开始）")

    target = paras[paragraph_index]
    if target.runs:
        # Keep the first run's formatting; apply new text to it and clear the rest
        target.runs[0].text = new_text
        for r in target.runs[1:]:
            r.text = ""
    else:
        target.add_run(new_text)

    fid = _new_id()
    path = UPLOAD_DIR / f"{fid}.docx"
    doc.save(str(path))

    stem = Path(filename).stem or "document"
    ext = Path(filename).suffix or ".docx"
    new_name = f"{stem}_modified{ext}"
    return {"filename": new_name, "path": str(path), "role": "generated"}
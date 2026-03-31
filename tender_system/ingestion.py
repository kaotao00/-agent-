from __future__ import annotations

import csv
import importlib
import re
from io import StringIO
from pathlib import Path
from uuid import uuid4

from tender_system.schemas import KnowledgeDocumentModel


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md"}


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_text(text: str, chunk_size: int = 700, overlap: int = 120) -> list[str]:
    cleaned = normalize_text(text)
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    segments = re.split(r"(?<=[。！？；\n])", cleaned)
    chunks: list[str] = []
    current = ""

    for segment in segments:
        if not segment:
            continue
        if len(current) + len(segment) <= chunk_size:
            current += segment
            continue
        if current:
            chunks.append(current.strip())
        carry = current[-overlap:] if current else ""
        current = (carry + segment).strip()
        if len(current) > chunk_size:
            while len(current) > chunk_size:
                chunks.append(current[:chunk_size].strip())
                current = current[max(0, chunk_size - overlap):].strip()

    if current:
        chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk]


def extract_pdf_text(file_path: Path) -> str:
    try:
        pypdf = importlib.import_module("pypdf")
    except Exception as exc:
        raise RuntimeError("导入 PDF 需要安装 pypdf。") from exc

    reader = pypdf.PdfReader(str(file_path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def extract_docx_text(file_path: Path) -> str:
    try:
        docx = importlib.import_module("docx")
    except Exception as exc:
        raise RuntimeError("导入 Word 需要安装 python-docx。") from exc

    document = docx.Document(str(file_path))
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    tables = []
    for table in document.tables:
        for row in table.rows:
            values = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if values:
                tables.append(" | ".join(values))
    return "\n".join(paragraphs + tables)


def extract_xlsx_text(file_path: Path) -> str:
    try:
        openpyxl = importlib.import_module("openpyxl")
    except Exception as exc:
        raise RuntimeError("导入 Excel 需要安装 openpyxl。") from exc

    workbook = openpyxl.load_workbook(str(file_path), data_only=True)
    lines: list[str] = []
    for sheet in workbook.worksheets:
        lines.append(f"工作表: {sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            values = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
            if values:
                lines.append(" | ".join(values))
    return "\n".join(lines)


def extract_csv_text(file_path: Path) -> str:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    rows = csv.reader(StringIO(text))
    return "\n".join(" | ".join(cell.strip() for cell in row if cell.strip()) for row in rows if row)


def extract_plain_text(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore")


def extract_document_text(file_path: Path) -> tuple[str, str]:
    extension = file_path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise RuntimeError(f"暂不支持的文件类型: {extension}")
    if extension == ".pdf":
        return extract_pdf_text(file_path), "pdf"
    if extension == ".docx":
        return extract_docx_text(file_path), "word"
    if extension == ".xlsx":
        return extract_xlsx_text(file_path), "excel"
    if extension == ".csv":
        return extract_csv_text(file_path), "csv"
    return extract_plain_text(file_path), "text"


def build_documents_from_file(
    *,
    file_path: Path,
    category: str,
    region: str,
    project_type: str,
    tags: list[str] | None = None,
) -> tuple[list[KnowledgeDocumentModel], str]:
    title = file_path.stem
    raw_text, source_type = extract_document_text(file_path)
    chunks = split_text(raw_text)
    base_tags = tags or [source_type, category]
    documents: list[KnowledgeDocumentModel] = []
    for index, chunk in enumerate(chunks, start=1):
        documents.append(
            KnowledgeDocumentModel(
                doc_id=f"doc-{uuid4().hex[:12]}-{index}",
                title=f"{title}-片段-{index}",
                category=category,
                tags=base_tags,
                region=region,
                project_type=project_type,
                content=chunk,
            )
        )
    return documents, source_type

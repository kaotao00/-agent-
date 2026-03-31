from __future__ import annotations

import json
from pathlib import Path

from tender_system.schemas import KnowledgeDocumentModel


def load_documents(data_path: Path) -> list[KnowledgeDocumentModel]:
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    return [KnowledgeDocumentModel(**item) for item in raw.get("documents", [])]


def save_documents(data_path: Path, documents: list[KnowledgeDocumentModel]) -> None:
    payload = {"documents": [document.model_dump() for document in documents]}
    data_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_documents(data_path: Path, new_documents: list[KnowledgeDocumentModel]) -> int:
    documents = load_documents(data_path)
    documents.extend(new_documents)
    save_documents(data_path, documents)
    return len(new_documents)

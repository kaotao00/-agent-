from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class BillOfQuantityItem(BaseModel):
    item_code: str
    item_name: str
    quantity: float
    unit: str


class TenderRequirements(BaseModel):
    duration_days: int
    quality_target: str
    safety_target: str
    required_qualification: str
    bid_sections: list[str] = Field(default_factory=lambda: ["technical", "budget", "business", "compliance"])


class TenderRequest(BaseModel):
    project_name: str
    project_type: str
    region: str
    tender_requirements: TenderRequirements
    bill_of_quantities: list[BillOfQuantityItem]


class KnowledgeDocumentModel(BaseModel):
    doc_id: str
    title: str
    category: str
    tags: list[str]
    region: str
    project_type: str
    content: str


class RetrievalHit(BaseModel):
    title: str
    category: str
    score: float
    excerpt: str


class SearchResponse(BaseModel):
    query: str
    backend: str
    hits: list[RetrievalHit]


class IngestionResponse(BaseModel):
    imported_count: int
    titles: list[str]
    retrieval_backend: str
    source_type: str


class TenderSectionResult(BaseModel):
    name: str
    content: dict[str, Any]


class TenderGenerationResult(BaseModel):
    project_name: str
    execution_plan: dict[str, Any]
    sections: dict[str, dict[str, Any]]
    shared_memory: dict[str, Any]
    agent_logs: list[str]
    retrieval_backend: str


class ApiStatusResponse(BaseModel):
    status: Literal["ok"]
    retrieval_backend: str

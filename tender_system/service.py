from __future__ import annotations

from pathlib import Path

from tender_system.data_store import append_documents
from tender_system.ingestion import build_documents_from_file
from tender_system.config import Settings, load_settings
from tender_system.llm import build_section_writer
from tender_system.orchestrator import TenderOrchestrator
from tender_system.retrieval import LocalHybridRetriever, build_retriever
from tender_system.schemas import IngestionResponse, SearchResponse, TenderGenerationResult, TenderRequest


def build_demo_request_payload() -> dict:
    return {
        "project_name": "华东智造产业园一期总承包项目",
        "project_type": "industrial",
        "region": "江苏",
        "tender_requirements": {
            "duration_days": 180,
            "quality_target": "符合国家验收规范，一次性验收合格，争创省优",
            "safety_target": "零重大安全事故",
            "required_qualification": "建筑工程施工总承包一级",
            "bid_sections": ["technical", "budget", "business", "compliance"],
        },
        "bill_of_quantities": [
            {"item_code": "A101", "item_name": "土方开挖", "quantity": 3200, "unit": "m3"},
            {"item_code": "B205", "item_name": "钢筋工程", "quantity": 580, "unit": "t"},
            {"item_code": "C310", "item_name": "混凝土浇筑", "quantity": 4600, "unit": "m3"},
            {"item_code": "D410", "item_name": "脚手架搭设", "quantity": 12000, "unit": "m2"},
        ],
    }


class TenderGenerationService:
    def __init__(self, data_path: Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings(data_path.parent if data_path else None)
        if data_path is not None:
            self.settings.data_path = data_path
        self.retriever = build_retriever(self.settings)
        self.writer = build_section_writer(self.settings)
        self.orchestrator = TenderOrchestrator(self.retriever, self.writer)

    def refresh_retriever(self) -> None:
        self.retriever.refresh()
        self.orchestrator = TenderOrchestrator(self.retriever, self.writer)

    def generate_tender(self, request: TenderRequest) -> TenderGenerationResult:
        return self.orchestrator.run(request)

    def search_knowledge(self, query: str, category: str | None = None) -> SearchResponse:
        hits = self.retriever.search(query, top_k=5, filters={"category": category} if category else None)
        return SearchResponse(query=query, backend=self.retriever.backend_name, hits=hits)

    def import_document(
        self,
        *,
        file_path: Path,
        category: str,
        region: str,
        project_type: str,
        tags: list[str] | None = None,
    ) -> IngestionResponse:
        documents, source_type = build_documents_from_file(
            file_path=file_path,
            category=category,
            region=region,
            project_type=project_type,
            tags=tags,
        )
        imported_count = append_documents(self.settings.data_path, documents)
        self.refresh_retriever()
        return IngestionResponse(
            imported_count=imported_count,
            titles=[document.title for document in documents],
            retrieval_backend=self.retriever.backend_name,
            source_type=source_type,
        )


def build_local_only_service(base_dir: Path | None = None) -> TenderGenerationService:
    settings = load_settings(base_dir)
    settings.use_langchain = False
    settings.use_milvus = False
    service = TenderGenerationService(settings=settings)
    service.retriever = LocalHybridRetriever(settings.data_path)
    service.writer = build_section_writer(settings)
    service.orchestrator = TenderOrchestrator(service.retriever, service.writer)
    return service

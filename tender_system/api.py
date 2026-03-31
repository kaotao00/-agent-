from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tender_system.config import load_settings
from tender_system.schemas import ApiStatusResponse, IngestionResponse, SearchResponse, TenderGenerationResult, TenderRequest
from tender_system.service import TenderGenerationService, build_demo_request_payload


def create_app(base_dir: Path | None = None) -> FastAPI:
    settings = load_settings(base_dir)
    service = TenderGenerationService(settings=settings)

    app = FastAPI(title="Intelligent Tender Studio", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings.static_dir and settings.static_dir.exists():
        app.mount("/assets", StaticFiles(directory=settings.static_dir), name="assets")

    @app.get("/api/health", response_model=ApiStatusResponse)
    def health() -> ApiStatusResponse:
        return ApiStatusResponse(status="ok", retrieval_backend=service.retriever.backend_name)

    @app.get("/api/demo-request")
    def demo_request() -> dict:
        return build_demo_request_payload()

    @app.get("/api/search", response_model=SearchResponse)
    def search(query: str = Query(...), category: str | None = Query(default=None)) -> SearchResponse:
        return service.search_knowledge(query, category)

    @app.post("/api/generate", response_model=TenderGenerationResult)
    def generate(request: TenderRequest) -> TenderGenerationResult:
        return service.generate_tender(request)

    @app.post("/api/ingest-document", response_model=IngestionResponse)
    def ingest_document(
        file: UploadFile = File(...),
        category: str = Form(...),
        region: str = Form(...),
        project_type: str = Form(...),
        tags: str = Form(default="pdf"),
    ) -> IngestionResponse:
        upload_dir = settings.base_dir / "uploads"
        upload_dir.mkdir(exist_ok=True)
        filename: str = file.filename or "uploaded.pdf"
        target_path = upload_dir / filename
        with target_path.open("wb") as target:
            shutil.copyfileobj(file.file, target)
        tag_list = [item.strip() for item in tags.split(",") if item.strip()]
        response = service.import_document(
            file_path=target_path,
            category=category,
            region=region,
            project_type=project_type,
            tags=tag_list,
        )
        return response

    @app.post("/api/ingest-pdf", response_model=IngestionResponse)
    def ingest_pdf(
        file: UploadFile = File(...),
        category: str = Form(...),
        region: str = Form(...),
        project_type: str = Form(...),
        tags: str = Form(default="pdf"),
    ) -> IngestionResponse:
        return ingest_document(file=file, category=category, region=region, project_type=project_type, tags=tags)

    @app.get("/")
    def index() -> FileResponse:
        static_dir: Path = settings.static_dir if settings.static_dir is not None else settings.base_dir / "frontend"
        return FileResponse(static_dir / "index.html")

    return app

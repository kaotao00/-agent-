from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    base_dir: Path
    data_path: Path
    use_langchain: bool = False
    use_milvus: bool = False
    use_qwen: bool = False
    milvus_uri: str = "http://localhost:19530"
    qwen_api_key: str | None = None
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"
    static_dir: Path | None = None


def load_settings(base_dir: Path | None = None) -> Settings:
    resolved_base_dir = (base_dir or Path(__file__).resolve().parents[1]).resolve()
    return Settings(
        base_dir=resolved_base_dir,
        data_path=resolved_base_dir / "data" / "enterprise_docs.json",
        use_langchain=os.getenv("TENDER_USE_LANGCHAIN", "0") == "1",
        use_milvus=os.getenv("TENDER_USE_MILVUS", "0") == "1",
        use_qwen=os.getenv("TENDER_USE_QWEN", "0") == "1",
        milvus_uri=os.getenv("TENDER_MILVUS_URI", "http://localhost:19530"),
        qwen_api_key=os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY"),
        qwen_base_url=os.getenv("TENDER_QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        qwen_model=os.getenv("TENDER_QWEN_MODEL", "qwen-plus"),
        static_dir=resolved_base_dir / "frontend",
    )

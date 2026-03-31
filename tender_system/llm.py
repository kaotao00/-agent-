from __future__ import annotations

import importlib
import json
from abc import ABC, abstractmethod
from typing import Any

from tender_system.config import Settings


class SectionWriter(ABC):
    backend_name = "template"

    @abstractmethod
    def enabled(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        raise NotImplementedError


class NoopSectionWriter(SectionWriter):
    backend_name = "template"

    def enabled(self) -> bool:
        return False

    def generate_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        return None


class QwenSectionWriter(SectionWriter):
    backend_name = "qwen"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Any | None = None
        if not settings.qwen_api_key:
            return
        try:
            openai_module = importlib.import_module("openai")
        except Exception:
            return
        self._client = openai_module.OpenAI(api_key=settings.qwen_api_key, base_url=settings.qwen_base_url)

    def enabled(self) -> bool:
        return self._client is not None and self.settings.use_qwen

    def generate_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        if not self.enabled():
            return None
        client = self._client
        if client is None:
            return None
        try:
            response = client.chat.completions.create(
                model=self.settings.qwen_model,
                temperature=0.3,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content
        except Exception:
            return None
        if not content:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None


def build_section_writer(settings: Settings) -> SectionWriter:
    writer = QwenSectionWriter(settings)
    if writer.enabled():
        return writer
    return NoopSectionWriter()

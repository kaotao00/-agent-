from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from pathlib import Path

from tender_system.config import Settings
from tender_system.data_store import load_documents
from tender_system.schemas import KnowledgeDocumentModel, RetrievalHit


TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9_]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def char_ngrams(text: str, n: int = 3) -> set[str]:
    compact = re.sub(r"\s+", "", text.lower())
    if len(compact) <= n:
        return {compact} if compact else set()
    return {compact[index:index + n] for index in range(len(compact) - n + 1)}


class Retriever(ABC):
    backend_name = "base"

    @abstractmethod
    def search(self, query: str, top_k: int = 3, filters: dict | None = None) -> list[RetrievalHit]:
        raise NotImplementedError

    def refresh(self) -> None:
        return None


class LocalHybridRetriever(Retriever):
    backend_name = "本地混合检索"

    def __init__(self, data_path: Path) -> None:
        self.data_path = data_path
        self._rebuild()

    def _rebuild(self) -> None:
        self.documents = load_documents(self.data_path)
        self.doc_texts = {doc.doc_id: self._join_doc(doc) for doc in self.documents}
        self.doc_term_freq = {doc.doc_id: Counter(tokenize(self.doc_texts[doc.doc_id])) for doc in self.documents}
        self.doc_norm = {
            doc.doc_id: math.sqrt(sum(count * count for count in term_freq.values())) or 1.0
            for doc, term_freq in ((document, self.doc_term_freq[document.doc_id]) for document in self.documents)
        }
        self.doc_ngrams = {doc.doc_id: char_ngrams(self.doc_texts[doc.doc_id]) for doc in self.documents}

    def refresh(self) -> None:
        self._rebuild()

    @staticmethod
    def _join_doc(doc: KnowledgeDocumentModel) -> str:
        return " ".join([doc.title, doc.category, doc.region, doc.project_type, " ".join(doc.tags), doc.content])

    @staticmethod
    def _passes_filters(doc: KnowledgeDocumentModel, filters: dict) -> bool:
        if filters.get("region") and doc.region not in (filters["region"], "通用"):
            return False
        if filters.get("project_type") and doc.project_type not in (filters["project_type"], "general"):
            return False
        if filters.get("category") and doc.category != filters["category"]:
            return False
        return True

    def search(self, query: str, top_k: int = 3, filters: dict | None = None) -> list[RetrievalHit]:
        filters = filters or {}
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        query_tf = Counter(query_tokens)
        query_norm = math.sqrt(sum(count * count for count in query_tf.values())) or 1.0
        query_ngrams = char_ngrams(query)
        hits: list[tuple[KnowledgeDocumentModel, float, float, float, float]] = []

        for doc in self.documents:
            if not self._passes_filters(doc, filters):
                continue

            term_freq = self.doc_term_freq[doc.doc_id]
            lexical_score = sum(query_tf[token] * term_freq.get(token, 0) for token in query_tf) / (query_norm * self.doc_norm[doc.doc_id])
            overlap_score = 0.08 * len(set(query_tokens) & set(term_freq.keys()))
            doc_ngrams = self.doc_ngrams[doc.doc_id]
            vector_score = len(query_ngrams & doc_ngrams) / max(len(query_ngrams | doc_ngrams), 1)
            rerank_score = 0.15 if query.lower() in self.doc_texts[doc.doc_id].lower() else 0.0

            if filters.get("tags"):
                overlap_tags = len(set(filters["tags"]) & set(doc.tags))
                rerank_score += 0.05 * overlap_tags

            final_score = lexical_score * 0.55 + vector_score * 0.3 + overlap_score + rerank_score
            if final_score > 0:
                hits.append((doc, final_score, lexical_score, vector_score, rerank_score))

        hits.sort(key=lambda item: (item[1], item[2], item[3], item[4]), reverse=True)
        return [
            RetrievalHit(
                title=doc.title,
                category=doc.category,
                score=round(score, 4),
                excerpt=doc.content[:160],
            )
            for doc, score, _, _, _ in hits[:top_k]
        ]


class LangChainMilvusRetriever(Retriever):
    backend_name = "LangChain+Milvus"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        try:
            vectorstores_module = __import__("langchain_community.vectorstores", fromlist=["Milvus"])
            huggingface_module = __import__("langchain_huggingface", fromlist=["HuggingFaceEmbeddings"])
        except Exception as exc:
            raise RuntimeError("Optional LangChain/Milvus dependencies are not installed.") from exc

        self._embeddings = huggingface_module.HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self._milvus_cls = vectorstores_module.Milvus
        self._build_store()

    def _build_store(self) -> None:
        self.documents = load_documents(self.settings.data_path)
        texts = [LocalHybridRetriever._join_doc(doc) for doc in self.documents]
        metadatas = [doc.model_dump() for doc in self.documents]
        self.store = self._milvus_cls.from_texts(
            texts=texts,
            embedding=self._embeddings,
            metadatas=metadatas,
            connection_args={"uri": self.settings.milvus_uri},
            collection_name="tender_demo_docs",
            drop_old=True,
        )

    def refresh(self) -> None:
        self._build_store()

    def search(self, query: str, top_k: int = 3, filters: dict | None = None) -> list[RetrievalHit]:
        docs = self.store.similarity_search_with_score(query, k=max(top_k * 2, 6))
        filters = filters or {}
        hits: list[RetrievalHit] = []
        for document, score in docs:
            metadata = document.metadata
            candidate = KnowledgeDocumentModel(**metadata)
            if not LocalHybridRetriever._passes_filters(candidate, filters):
                continue
            hits.append(
                RetrievalHit(
                    title=metadata.get("title", "未知文档"),
                    category=metadata.get("category", "unknown"),
                    score=round(float(score), 4),
                    excerpt=metadata.get("content", "")[:160],
                )
            )
        return hits[:top_k]


def build_retriever(settings: Settings) -> Retriever:
    if settings.use_langchain and settings.use_milvus:
        try:
            return LangChainMilvusRetriever(settings)
        except Exception:
            return LocalHybridRetriever(settings.data_path)
    return LocalHybridRetriever(settings.data_path)

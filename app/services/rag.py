from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.core.config import get_settings
from app.core.rbac import allowed_roles_for_department


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    department: str
    source: str
    text: str
    chunk_index: int
    allowed_roles: str


@dataclass(frozen=True)
class SearchResult:
    chunk: DocumentChunk
    score: float


class RAGConfigurationError(RuntimeError):
    pass


def _read_file(path: Path) -> str:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        return "\n".join(
            "; ".join(f"{key}: {value}" for key, value in row.items()) for row in rows
        )
    return path.read_text(encoding="utf-8", errors="ignore")


def _split_text(text: str, max_chars: int = 1400, overlap: int = 180) -> list[str]:
    clean_text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not clean_text:
        return []

    pieces = re.split(r"\n(?=##?\s)|\n---+\n", clean_text)
    chunks: list[str] = []
    current = ""

    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if len(piece) > max_chars:
            step = max_chars - overlap
            for start in range(0, len(piece), step):
                chunks.append(piece[start : start + max_chars].strip())
            continue
        if len(current) + len(piece) + 2 <= max_chars:
            current = f"{current}\n\n{piece}".strip()
        else:
            if current:
                chunks.append(current)
            current = piece

    if current:
        chunks.append(current)
    return chunks


def _department_from_path(path: Path) -> str:
    return path.parent.name.lower()


def _chunk_id(path: Path, department: str, chunk_index: int, text: str) -> str:
    digest = hashlib.sha1(f"{path.as_posix()}:{chunk_index}:{text}".encode("utf-8")).hexdigest()
    return f"{department}-{path.stem}-{chunk_index}-{digest[:12]}"


def load_source_chunks() -> list[DocumentChunk]:
    data_dir = get_settings().data_dir
    chunks: list[DocumentChunk] = []

    for path in sorted(data_dir.glob("*/*")):
        if path.suffix.lower() not in {".md", ".txt", ".csv"}:
            continue
        department = _department_from_path(path)
        allowed_roles = ",".join(allowed_roles_for_department(department))
        for index, chunk_text in enumerate(_split_text(_read_file(path)), start=1):
            chunks.append(
                DocumentChunk(
                    id=_chunk_id(path, department, index, chunk_text),
                    department=department,
                    source=path.name,
                    text=chunk_text,
                    chunk_index=index,
                    allowed_roles=allowed_roles,
                )
            )
    return chunks


def _get_embeddings() -> HuggingFaceEndpointEmbeddings:
    settings = get_settings()
    if not settings.huggingfacehub_api_token:
        raise RAGConfigurationError(
            "HUGGINGFACEHUB_API_TOKEN is missing. Add it to your .env before indexing or chatting."
        )
    return HuggingFaceEndpointEmbeddings(
        model=settings.hf_embedding_model,
        task="feature-extraction",
        huggingfacehub_api_token=settings.huggingfacehub_api_token,
    )


def _get_vector_store() -> Chroma:
    settings = get_settings()
    settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=_get_embeddings(),
        persist_directory=str(settings.vector_store_dir),
    )


def _chunk_to_document(chunk: DocumentChunk) -> Document:
    return Document(
        page_content=chunk.text,
        metadata={
            "chunk_id": chunk.id,
            "department": chunk.department,
            "source": chunk.source,
            "chunk_index": chunk.chunk_index,
            "allowed_roles": chunk.allowed_roles,
        },
    )


def rebuild_vector_store() -> dict[str, int | str]:
    settings = get_settings()
    settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
    embeddings = _get_embeddings()
    old_store = Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=embeddings,
        persist_directory=str(settings.vector_store_dir),
    )
    try:
        old_store.delete_collection()
    except Exception:
        pass

    chunks = load_source_chunks()
    documents = [_chunk_to_document(chunk) for chunk in chunks]
    ids = [chunk.id for chunk in chunks]
    Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        ids=ids,
        collection_name=settings.chroma_collection,
        persist_directory=str(settings.vector_store_dir),
    )

    return {
        "status": "indexed",
        "chunks_indexed": len(chunks),
        "collection": settings.chroma_collection,
        "vector_store": str(settings.vector_store_dir),
    }


def ensure_vector_store() -> int:
    count = _get_vector_store()._collection.count()
    if count == 0:
        return int(rebuild_vector_store()["chunks_indexed"])
    return count


def _metadata_to_chunk(document: Document) -> DocumentChunk:
    metadata = document.metadata
    return DocumentChunk(
        id=str(metadata.get("chunk_id", "")),
        department=str(metadata.get("department", "")),
        source=str(metadata.get("source", "")),
        text=document.page_content,
        chunk_index=int(metadata.get("chunk_index", 0)),
        allowed_roles=str(metadata.get("allowed_roles", "")),
    )


def _where_for_departments(allowed_departments: set[str] | None) -> dict | None:
    if not allowed_departments:
        return None
    departments = sorted(department.lower() for department in allowed_departments)
    if len(departments) == 1:
        return {"department": departments[0]}
    return {"department": {"$in": departments}}


def search_documents(
    query: str,
    allowed_departments: set[str] | None = None,
    top_k: int | None = None,
) -> list[SearchResult]:
    settings = get_settings()
    top_k = top_k or settings.top_k
    ensure_vector_store()
    vector_store = _get_vector_store()
    docs_with_scores = vector_store.similarity_search_with_relevance_scores(
        query=query,
        k=max(top_k, 1),
        filter=_where_for_departments(allowed_departments),
    )

    results: list[SearchResult] = []
    for document, score in docs_with_scores:
        results.append(SearchResult(chunk=_metadata_to_chunk(document), score=float(score)))
    return results


def make_snippet(text: str, max_chars: int = 320) -> str:
    snippet = text.strip().replace("\n", " ")
    snippet = re.sub(r"\s+", " ", snippet).strip()
    if len(snippet) <= max_chars:
        return snippet
    return snippet[: max_chars - 3].rstrip() + "..."


def _context_for_prompt(results: list[SearchResult]) -> str:
    blocks = []
    for index, result in enumerate(results, start=1):
        blocks.append(
            "\n".join(
                [
                    f"[{index}] Source: {result.chunk.source}",
                    f"Department: {result.chunk.department}",
                    f"Relevance: {result.score:.3f}",
                    "Content:",
                    result.chunk.text,
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


def _messages_for_prompt(query: str, results: list[SearchResult]) -> list[SystemMessage | HumanMessage]:
    context = _context_for_prompt(results)
    system_prompt = (
        "You are an internal company assistant using retrieval-augmented generation. "
        "Answer only from the provided context. If the context is insufficient, say so. "
        "Never infer or reveal restricted information. Cite source file names in square brackets."
    )
    user_prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer with concise, useful bullets."
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]


def _generate_with_groq(query: str, results: list[SearchResult]) -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RAGConfigurationError(
            "GROQ_API_KEY is missing. Add it to your .env before using LLM answers."
        )
    llm = ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0.2,
    )
    response = llm.invoke(_messages_for_prompt(query, results))
    return str(response.content).strip()


def generate_answer(query: str, results: list[SearchResult]) -> str:
    if not results:
        return (
            "I could not find enough accessible information to answer that question. "
            "Try asking about data available to your role, or contact an administrator if you need broader access."
        )
    return _generate_with_groq(query, results)


def rag_status() -> dict[str, int | str]:
    settings = get_settings()
    try:
        count = _get_vector_store()._collection.count()
    except Exception:
        count = 0
    return {
        "chunks_indexed": count,
        "collection": settings.chroma_collection,
        "vector_store": str(settings.vector_store_dir),
        "embedding_provider": "huggingface-endpoint",
        "embedding_model": settings.hf_embedding_model,
        "generation_provider": "groq",
        "generation_model": settings.groq_model,
        "allowed_role_boundary": "metadata filter before retrieval",
    }

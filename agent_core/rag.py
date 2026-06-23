"""rag.py — SOP retrieval (HW3 patterns).

ChromaDB over the synthetic `data_spec/QC-SOP.md`. Each SOP clause is one chunk;
given a query (the breached parameters, or a free question) we retrieve the
governing clause(s) so the agent can cite them as `[N]`.

Embeddings come from the configured model (`settings.embed_model`, default
`bge-m3`) via Ollama — model name in config, so CPU dev can swap to a lighter
model (e.g. `nomic-embed-text`) with zero code change. The embedder is injectable
so retrieval logic is unit-tested without a running Ollama.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .config import settings

# QC-SOP.md is committed source (not on D:\) — resolve relative to the repo root.
SOP_PATH = Path(__file__).resolve().parents[1] / "data_spec" / "QC-SOP.md"
COLLECTION = "qc_sop"

Embedder = Callable[[list[str]], list[list[float]]]


@dataclass
class SopClause:
    cite_id: int       # the [N] shown to the user (1-based, by rank)
    source: str        # e.g. "QC-SOP.md#3.2"
    text: str


def _chunks(sop_path: Path) -> list[tuple[str, str]]:
    """Split QC-SOP.md into (source, text) clause chunks. Deterministic order."""
    text = Path(sop_path).read_text(encoding="utf-8")
    out: list[tuple[str, str]] = []
    section = "0"
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block or block.startswith(">") or block.startswith("# "):
            continue  # blank, doc-note blockquote, or the title
        sec = re.match(r"##\s*(\d+)\.", block)
        if sec:
            section = sec.group(1)
            parts = block.split("\n", 1)
            if len(parts) == 1 or not parts[1].strip():
                continue  # heading-only block
            block = parts[1].strip()
        clause = re.match(r"\*\*(\d+\.\d+)", block)
        source = f"QC-SOP.md#{clause.group(1)}" if clause else f"QC-SOP.md#{section}"
        out.append((source, block))
    return out


def _embed_ollama(texts: list[str]) -> list[list[float]]:
    """Default embedder: settings.embed_model served by local Ollama."""
    import ollama

    client = ollama.Client(host=settings.ollama_host)
    return [client.embeddings(model=settings.embed_model, prompt=t)["embedding"] for t in texts]


def _client(persist_dir):
    import chromadb

    persist_dir = settings.vectorstore_dir if persist_dir is None else persist_dir
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir))


def build_index(sop_path=None, persist_dir=None, embedder: Embedder | None = None) -> int:
    """(Re)build the SOP index. Returns the number of indexed clauses."""
    sop_path = SOP_PATH if sop_path is None else sop_path
    embedder = _embed_ollama if embedder is None else embedder

    chunks = _chunks(sop_path)
    sources = [s for s, _ in chunks]
    docs = [d for _, d in chunks]
    embeddings = embedder(docs)

    client = _client(persist_dir)
    try:
        client.delete_collection(COLLECTION)  # clean rebuild, no stale chunks
    except Exception:
        pass
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    col.add(
        ids=[f"c{i}" for i in range(len(docs))],
        embeddings=embeddings,
        documents=docs,
        metadatas=[{"source": s} for s in sources],
    )
    return len(docs)


def retrieve(query: str, k: int = 4, persist_dir=None, embedder: Embedder | None = None) -> list[SopClause]:
    """Top-k SOP clauses for the query, cited [1..k] by rank."""
    embedder = _embed_ollama if embedder is None else embedder
    col = _client(persist_dir).get_collection(COLLECTION)
    res = col.query(query_embeddings=embedder([query]), n_results=k)
    docs, metas = res["documents"][0], res["metadatas"][0]
    return [SopClause(cite_id=i + 1, source=m["source"], text=d)
            for i, (d, m) in enumerate(zip(docs, metas))]

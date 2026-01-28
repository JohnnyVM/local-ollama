#!/usr/bin/env python3
"""
Local KB MCP Server (stdio) backed by LlamaIndex + FAISS + FastEmbed.

Features:
- Plain text ingest
- HTML ingest (Playwright output) with section + heading-path extraction
- Local FAISS persistence
- Deterministic chunking
- URL + section-aware citations

Tools exposed:
- kb_add_text(source_id, text, extra_metadata?)
- kb_add_html(url, html, page_title?, extra_metadata?)
- kb_search(query, top_k)
- kb_quote(node_id)
"""

from __future__ import annotations

import argparse
import hashlib
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.settings import Settings
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore


# -----------------------------
# Utilities
# -----------------------------

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _stable_id(*parts: str) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# -----------------------------
# HTML → sections → chunks
# -----------------------------

def html_to_sections(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.select("script, style, noscript, svg"):
        tag.decompose()

    root = soup.select_one("main") or soup.select_one("article") or soup.body or soup

    heading_stack: List[tuple[int, str]] = []
    sections: List[Dict[str, Any]] = []
    current_lines: List[str] = []
    current_path: List[str] = []

    def flush():
        nonlocal current_lines
        text = _clean_text("\n".join(current_lines))
        if text:
            sections.append({"heading_path": list(current_path), "text": text})
        current_lines = []

    for el in root.select("h1,h2,h3,h4,h5,h6,p,li,pre,code,table"):
        name = el.name.lower()

        if name.startswith("h"):
            flush()
            level = int(name[1])
            title = _clean_text(el.get_text(" ", strip=True))
            if not title:
                continue
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            current_path = [t for _, t in heading_stack]
            continue

        if name == "li":
            txt = _clean_text(el.get_text(" ", strip=True))
            if txt:
                current_lines.append(f"- {txt}")
        elif name in ("pre", "code"):
            txt = el.get_text("\n", strip=True)
            if txt:
                current_lines.append(f"```text\n{txt}\n```")
        elif name == "table":
            txt = _clean_text(el.get_text(" ", strip=True))
            if txt:
                current_lines.append(f"[table] {txt}")
        else:
            txt = _clean_text(el.get_text(" ", strip=True))
            if txt:
                current_lines.append(txt)

    flush()

    if not sections:
        text = _clean_text(root.get_text("\n", strip=True))
        if text:
            sections = [{"heading_path": [], "text": text}]

    return sections


def split_text(text: str, max_chars: int = 2000, overlap: int = 200) -> List[str]:
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


# -----------------------------
# Index handling
# -----------------------------

def build_or_load_index(persist_dir: Path, embed_model: str) -> VectorStoreIndex:
    persist_dir.mkdir(parents=True, exist_ok=True)
    Settings.embed_model = FastEmbedEmbedding(model_name=embed_model)

    faiss_path = persist_dir / "faiss.index"

    if faiss_path.exists():
        faiss_index = faiss.read_index(str(faiss_path))
        vector_store = FaissVectorStore(faiss_index=faiss_index)
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store,
            persist_dir=str(persist_dir),
        )
        return VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
        )

    embed_dim = getattr(Settings.embed_model, "embed_dim", 384)
    faiss_index = faiss.IndexFlatIP(int(embed_dim))
    vector_store = FaissVectorStore(faiss_index=faiss_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents([], storage_context=storage_context)

    faiss.write_index(faiss_index, str(faiss_path))
    index.storage_context.persist(persist_dir=str(persist_dir))
    return index


def persist(index: VectorStoreIndex, persist_dir: Path) -> None:
    index.storage_context.persist(persist_dir=str(persist_dir))
    faiss_path = persist_dir / "faiss.index"
    vector_store = index.storage_context.vector_store
    faiss_index = getattr(vector_store, "faiss_index", None)
    if faiss_index is not None:
        faiss.write_index(faiss_index, str(faiss_path))


# -----------------------------
# MCP server
# -----------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="./kb_data")
    parser.add_argument("--embed-model", default="BAAI/bge-small-en-v1.5")
    args = parser.parse_args()

    persist_dir = Path(args.data_dir).resolve()
    index = build_or_load_index(persist_dir, args.embed_model)

    mcp = FastMCP("local-kb")

    @mcp.tool()
    def kb_add_text(source_id: str, text: str, extra_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        meta = {"source_id": source_id, "added_at": _now_iso()}
        if extra_metadata:
            meta.update(extra_metadata)
        index.insert(Document(text=text, metadata=meta))
        persist(index, persist_dir)
        return {"ok": True, "source_id": source_id}

    @mcp.tool()
    def kb_add_html(
        url: str,
        html: str,
        page_title: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sections = html_to_sections(html)
        inserted = 0
        for sec in sections:
            path = sec.get("heading_path", [])
            for i, chunk in enumerate(split_text(sec["text"])):
                meta = {
                    "url": url,
                    "source_id": url,
                    "page_title": page_title or "",
                    "heading_path": path,
                    "heading": path[-1] if path else "",
                    "section_id": _stable_id(url, " / ".join(path), str(i)),
                    "chunk_index": i,
                    "added_at": _now_iso(),
                }
                if extra_metadata:
                    meta.update(extra_metadata)
                index.insert(Document(text=chunk, metadata=meta))
                inserted += 1
        persist(index, persist_dir)
        return {"ok": True, "url": url, "chunks": inserted}

    @mcp.tool()
    def kb_search(query: str, top_k: int = 5) -> Dict[str, Any]:
        retriever = index.as_retriever(similarity_top_k=max(1, min(top_k, 20)))
        nodes = retriever.retrieve(query)
        return {
            "ok": True,
            "results": [
                {
                    "node_id": n.node.node_id,
                    "score": float(getattr(n, "score", 0.0) or 0.0),
                    "text": n.node.get_content()[:1500],
                    "metadata": dict(n.node.metadata or {}),
                }
                for n in nodes
            ],
        }

    @mcp.tool()
    def kb_quote(node_id: str) -> Dict[str, Any]:
        try:
            node = index.storage_context.docstore.get_node(node_id)
            return {
                "ok": True,
                "text": node.get_content()[:4000],
                "metadata": dict(node.metadata or {}),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()


"""
MustanAgent v3.3 PRO - RAG Buffer
TF-IDF tabanlı basit retrieval.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("mustan_agent.memory.rag_buffer")


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|[çğıöşüÇĞİÖŞÜ]+|\d+", text)
    return [t for t in tokens if len(t) > 2]


class RAGBuffer:
    def __init__(self, memory_dir: str = "Aimemory", chunk_size: int = 600, chunk_overlap: int = 80):
        self.memory_dir = Path(memory_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunks: List[Dict] = []
        self.idf: Dict[str, float] = {}
        self._indexed = False

    def _chunk_text(self, text: str, source: str) -> List[Dict]:
        words = text.split()
        chunks = []
        i, idx = 0, 0
        while i < len(words):
            piece = " ".join(words[i : i + self.chunk_size])
            if piece.strip():
                chunks.append({
                    "id": f"{source}::{idx}",
                    "source": source,
                    "text": piece,
                    "tf": Counter(_tokenize(piece)),
                })
                idx += 1
            i += self.chunk_size - self.chunk_overlap
        return chunks

    def index(self, force: bool = False) -> int:
        if self._indexed and not force:
            return len(self.chunks)
        self.chunks = []
        if not self.memory_dir.exists():
            self._indexed = True
            return 0
        files = []
        for pat in ("*.md", "*.json", "*.txt"):
            files.extend(self.memory_dir.rglob(pat))
        skip = {"stats.json", "plan_raw_debug.txt"}
        for fpath in files:
            if fpath.name in skip or fpath.stat().st_size > 2_000_000:
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
                rel = str(fpath.relative_to(self.memory_dir))
                self.chunks.extend(self._chunk_text(text, rel))
            except Exception as e:
                logger.debug("RAG index atlandı %s: %s", fpath, e)
        df: Dict[str, int] = defaultdict(int)
        for ch in self.chunks:
            for term in ch["tf"]:
                df[term] += 1
        n = max(len(self.chunks), 1)
        self.idf = {t: math.log(n / (1 + df[t])) + 1.0 for t in df}
        self._indexed = True
        logger.info("RAG indeksi hazır: %d chunk", len(self.chunks))
        return len(self.chunks)

    def _score(self, query_tf: Counter, chunk_tf: Counter) -> float:
        score = 0.0
        for term, qtf in query_tf.items():
            if term in chunk_tf:
                score += (chunk_tf[term] * self.idf.get(term, 1.0)) * qtf
        return score

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, str, float]]:
        if not self._indexed:
            self.index()
        if not self.chunks:
            return []
        qtf = Counter(_tokenize(query))
        if not qtf:
            return []
        scored = []
        for ch in self.chunks:
            s = self._score(qtf, ch["tf"])
            if s > 0:
                scored.append((ch["source"], ch["text"], s))
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:top_k]

    def get_context(self, query: str, top_k: int = 4, max_chars: int = 4000) -> str:
        hits = self.search(query, top_k=top_k)
        if not hits:
            return ""
        parts = ["### RAG ile getirilen ilgili bellek parçaları\n"]
        total = 0
        for source, text, score in hits:
            snippet = text.strip()
            if total + len(snippet) > max_chars:
                break
            parts.append(f"**Kaynak:** `{source}` (skor: {score:.2f})\n{snippet}\n")
            total += len(snippet)
        return "\n".join(parts)


_default_rag: Optional[RAGBuffer] = None


def get_rag_buffer(memory_dir: str = "Aimemory") -> RAGBuffer:
    global _default_rag
    if _default_rag is None or str(_default_rag.memory_dir) != memory_dir:
        _default_rag = RAGBuffer(memory_dir=memory_dir)
        _default_rag.index()
    return _default_rag



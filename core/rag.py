"""轻量 RAG：按段落加载 Markdown，关键词重叠打分（无向量模型依赖）。"""

from __future__ import annotations

import re
from pathlib import Path

_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"

_chunks: list[dict[str, str]] = []


def _tokenize(text: str) -> set[str]:
    text = text.lower()
    # 英文词 + 连续中文片段（2 字及以上）
    parts = re.findall(r"[a-z]{2,}|[\u4e00-\u9fff]{2,}", text)
    return set(parts)


def load_knowledge() -> None:
    global _chunks
    _chunks = []
    if not _KNOWLEDGE_DIR.exists():
        return
    for path in sorted(_KNOWLEDGE_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        title = path.stem
        paras = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
        for i, body in enumerate(paras):
            _chunks.append(
                {
                    "id": f"{path.name}#{i}",
                    "title": title,
                    "source": str(path.name),
                    "body": body,
                }
            )


def retrieve(query: str, top_k: int = 4) -> list[dict[str, str]]:
    if not _chunks:
        load_knowledge()
    if not query.strip():
        return []

    q_tokens = _tokenize(query)
    if not q_tokens:
        q_tokens = {query.strip()}

    scored: list[tuple[int, dict[str, str]]] = []
    for ch in _chunks:
        t_tokens = _tokenize(ch["body"] + " " + ch["title"])
        score = len(q_tokens & t_tokens)
        if score == 0:
            # 子串兜底：整句包含
            if any(tok in ch["body"] for tok in q_tokens if len(tok) >= 2):
                score = 1
        if score > 0:
            scored.append((score, ch))

    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:top_k]]


def knowledge_chunk_count() -> int:
    load_knowledge()
    return len(_chunks)


def format_hits(hits: list[dict[str, str]]) -> str:
    if not hits:
        return "（知识库未检索到直接相关条目，将仅基于通用安全约束回答。）"
    parts = []
    for h in hits:
        parts.append(f"【{h['source']}】{h['body']}")
    return "\n\n".join(parts)

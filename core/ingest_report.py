"""体检报告解析：PDF/TXT 抽取文本 + 正则抓取常见检验项。"""

from __future__ import annotations

import io
import re
from typing import Any

from pypdf import PdfReader

from core.rules import LAB_REF, flag_labs

# 别名 -> 标准 code
ALIASES: list[tuple[str, str]] = [
    (r"丙氨酸氨基转移酶|谷丙转氨酶|\bALT\b", "ALT"),
    (r"天门冬氨酸氨基转移酶|谷草转氨酶|\bAST\b", "AST"),
    (r"总胆红素|\bTBIL\b", "TBIL"),
    (r"肌酐|\bCREA\b|\bCr\b", "CREA"),
    (r"空腹血糖|血糖|\bGLU\b|\bFPG\b", "GLU"),
    (r"总胆固醇|\bTC\b", "TC"),
    (r"甘油三酯|\bTG\b", "TG"),
    (r"高密度脂蛋白|\bHDL\b", "HDL"),
    (r"低密度脂蛋白|\bLDL\b", "LDL"),
]


def _read_pdf_bytes(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    texts: list[str] = []
    for page in reader.pages:
        t = page.extract_text() or ""
        texts.append(t)
    return "\n".join(texts)


def extract_text(data: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return _read_pdf_bytes(data)
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace")
    # 图片等：提示转 PDF/TXT
    return ""


def parse_labs_from_text(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for pattern, code in ALIASES:
        # 名称后若干字符内的第一个数字
        rx = re.compile(
            rf"(?:{pattern})[^\d\n]{{0,24}}?(\d+\.?\d*)",
            re.IGNORECASE | re.UNICODE,
        )
        for m in rx.finditer(text):
            val = float(m.group(1))
            unit = LAB_REF.get(code, (None, None, ""))[2]
            items.append({"code": code, "value": val, "unit": unit})
            break
    # 去重：保留首次
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for it in items:
        if it["code"] in seen:
            continue
        seen.add(it["code"])
        uniq.append(it)
    return uniq


def analyze_upload(data: bytes, filename: str) -> dict[str, Any]:
    text = extract_text(data, filename)
    if not text.strip():
        return {
            "ok": False,
            "error": "无法从该文件提取文本。请上传 PDF/TXT，或将检查报告另存为文本演示文件。",
            "raw_preview": "",
            "items": [],
            "flags": [],
        }
    items = parse_labs_from_text(text)
    flags = [f.__dict__ for f in flag_labs(items)]
    return {
        "ok": True,
        "error": None,
        "raw_preview": text[:1200],
        "items": items,
        "flags": flags,
    }

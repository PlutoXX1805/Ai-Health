"""大模型调用：优先 DeepSeek API；其次 Ollama；最后模板回复。密钥仅允许来自环境变量 / .env，禁止写入代码库。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

SYSTEM_PROMPT = """你是「嗨 Hai」健康科普助手，面向大众做生活方式与就医引导类说明。
硬性约束：
1. 不进行疾病诊断，不开具体药方；必要时强烈建议用户咨询正规医疗机构。
2. 若提供了「知识库摘录」，请优先依据摘录表述，并可用自己的话归纳；勿编造引用。
3. 回答简洁、分点列出；语气友好专业。
4. 结尾不要重复免责声明全文（界面会单独展示）。"""


def deepseek_configured() -> bool:
    return bool(DEEPSEEK_API_KEY)


def _ollama_available(base: str = DEFAULT_OLLAMA_URL, timeout: float = 2.0) -> bool:
    try:
        r = requests.get(f"{base.rstrip('/')}/api/tags", timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return False


def _call_deepseek(messages: list[dict[str, str]]) -> tuple[str | None, str | None]:
    """成功返回 (content, None)，失败返回 (None, error_message)。"""
    if not DEEPSEEK_API_KEY:
        return None, "未配置 DEEPSEEK_API_KEY"
    url = f"{DEEPSEEK_API_BASE}/v1/chat/completions"
    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": messages,
                "temperature": 0.6,
            },
            timeout=120,
        )
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        text = (msg.get("content") or "").strip()
        if not text:
            return None, "空响应"
        return text, None
    except requests.RequestException as e:
        return None, str(e)


def _call_ollama(
    messages: list[dict[str, str]],
    model: str,
) -> tuple[str | None, str | None]:
    base = DEFAULT_OLLAMA_URL.rstrip("/")
    try:
        resp = requests.post(
            f"{base}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        text = (data.get("message") or {}).get("content") or ""
        text = text.strip()
        return (text, None) if text else (None, "空响应")
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        return None, str(e)


def chat(
    user_text: str,
    *,
    context: str | None = None,
    history: list[dict[str, str]] | None = None,
    model: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    返回 (回复文本, 元信息)。
    meta: provider deepseek | ollama | mock, model, error
    """
    ollama_model = model or DEFAULT_OLLAMA_MODEL
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        messages.append(
            {
                "role": "system",
                "content": "以下为检索到的知识库摘录（可能为空）：\n" + context,
            }
        )
    if history:
        for h in history[-10:]:
            role = h.get("role", "user")
            if role not in ("user", "assistant"):
                continue
            messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": user_text})

    if deepseek_configured():
        text, err = _call_deepseek(messages)
        if text:
            return text, {
                "provider": "deepseek",
                "model": DEEPSEEK_MODEL,
                "error": None,
                "used_ollama": False,
                "used_deepseek": True,
            }
        # DeepSeek 失败则尝试 Ollama，再退回 mock
        if _ollama_available():
            ot, oe = _call_ollama(messages, ollama_model)
            if ot:
                return ot, {
                    "provider": "ollama",
                    "model": ollama_model,
                    "error": None,
                    "used_ollama": True,
                    "used_deepseek": False,
                }
        return _mock_reply(user_text, context, err or "DeepSeek 调用失败")

    base = DEFAULT_OLLAMA_URL.rstrip("/")
    if _ollama_available(base):
        text, err = _call_ollama(messages, ollama_model)
        if text:
            return text, {
                "provider": "ollama",
                "model": ollama_model,
                "error": None,
                "used_ollama": True,
                "used_deepseek": False,
            }
        return _mock_reply(user_text, context, err)

    return _mock_reply(user_text, context, None)


def _mock_reply(user_text: str, context: str | None, err: str | None) -> tuple[str, dict[str, Any]]:
    hint = ""
    if err:
        hint = f"（大模型不可用：{err}，以下为离线模板回复。）\n\n"
    elif not deepseek_configured() and not _ollama_available():
        hint = (
            "（未配置 DEEPSEEK_API_KEY 且未检测到 Ollama，当前为离线模板回复。"
            "可在项目根目录创建 .env 并设置 DEEPSEEK_API_KEY。）\n\n"
        )

    kb = (context or "").strip()
    lines = [
        hint + "根据你的描述，我建议你：",
        "1. 记录症状出现时间、诱因与伴随表现，便于就诊时说明。",
    ]
    if kb and "未检索" not in kb:
        lines.append("2. 结合知识库摘录，核对是否涵盖你的问题；若有矛盾以医疗机构意见为准。")
        n = 3
    else:
        n = 2
    lines.append(f"{n}. 若出现胸痛、呼吸困难、意识障碍或剧烈腹痛等，请立即拨打当地急救电话或前往急诊。")
    lines.append(f"{n + 1}. 日常保持规律作息与适度运动；具体诊疗方案需由执业医师面诊后确定。")
    meta = {
        "provider": "mock",
        "model": None,
        "error": err,
        "used_ollama": False,
        "used_deepseek": False,
    }
    return "\n".join(lines), meta


def polish_plan(plan_markdown: str) -> tuple[str, dict[str, Any]]:
    """将结构化计划交给 LLM 润色；失败则原文返回。"""
    prompt = (
        "请将下列「一日健康计划要点」改写为更易读的中文段落，保留数字与比例，不添加新的医疗承诺：\n\n"
        + plan_markdown
    )
    text, meta = chat(prompt, context=None, history=None)
    if meta.get("provider") in ("deepseek", "ollama"):
        return text, meta
    return plan_markdown, meta

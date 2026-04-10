"""大模型调用：DeepSeek API（OpenAI 兼容）；密钥来自环境变量 / .env，勿写入代码库。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

SYSTEM_PROMPT = """你是「嗨 Hai」健康科普助手，面向大众做生活方式与就医引导类说明。
硬性约束：
1. 不进行疾病诊断，不开具体药方；必要时强烈建议用户咨询正规医疗机构。
2. 若提供了「知识库摘录」，请优先依据摘录表述，并可用自己的话归纳；勿编造引用。
3. 回答简洁、分点列出；语气友好专业。
4. 结尾不要重复免责声明全文（界面会单独展示）。"""

PLAN_GENERATOR_SYSTEM = """你是「嗨 Hai」明日生活规划助手。你的任务是：仅根据用户提供的【个人档案】【昨日回顾】与【公式参考 JSON】，生成针对「明天」一整天的整合建议。

输出要求（Markdown）：
- 必须使用二级标题组织，且至少包含：「明日饮食建议」「营养素与热量参考」「有氧与力量训练」「步数与日常活动」「作息与疗养提醒（非医疗）」。
- 饮食：给出明日三餐原则、推荐食物类别与示例搭配；结合用户忌口与饮食偏好（来自档案），不要建议其明确忌口的食物。
- 营养素：引用 JSON 中的估算数字作为参考区间，并强调个体差异与需营养师/医生个体化评估。
- 运动：区分有氧与力量/无氧；结合用户运动偏好与昨日完成情况，安排明日可执行强度与时长（科普级，非运动处方）。
- 步数：结合昨日步数与整体活动水平，给出明日步数与碎片化活动建议。
- 疗养：结合病史做生活习惯与复诊提醒，禁止诊断、禁止推荐具体药物或剂量。

语气：专业、克制、友好。不写完整免责声明段落（界面会单独展示）。"""


def deepseek_configured() -> bool:
    return bool(DEEPSEEK_API_KEY)


def _call_deepseek(messages: list[dict[str, str]]) -> tuple[str | None, str | None]:
    if not DEEPSEEK_API_KEY:
        return None, "服务暂不可用"
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


def chat(
    user_text: str,
    *,
    context: str | None = None,
    history: list[dict[str, str]] | None = None,
    model: str | None = None,
) -> tuple[str, dict[str, Any]]:
    del model  # 固定使用 DEEPSEEK_MODEL
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
            return text, _meta_ok("deepseek", DEEPSEEK_MODEL)
        return _mock_reply(user_text, context, err or "服务暂不可用")

    return _mock_reply(user_text, context, None)


def _mock_reply(user_text: str, context: str | None, err: str | None) -> tuple[str, dict[str, Any]]:
    hint = ""
    if err:
        hint = "（当前为离线说明模式。）\n\n"
    elif not deepseek_configured():
        hint = "（当前为离线说明模式。）\n\n"

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
        "used_deepseek": False,
    }
    return "\n".join(lines), meta


def _meta_ok(provider: str, model: str | None) -> dict[str, Any]:
    return {
        "provider": provider,
        "model": model,
        "error": None,
        "used_deepseek": provider == "deepseek",
    }


def generate_tomorrow_plan(
    *,
    profile_markdown: str,
    yesterday_markdown: str,
    reference: dict[str, Any],
    rag_context: str | None = None,
) -> tuple[str, dict[str, Any]]:
    chunks = [
        "请直接输出明日规划（Markdown）。",
        "",
        "### 公式参考（仅供对齐数量级）",
        "```json\n" + json.dumps(reference, ensure_ascii=False, indent=2) + "\n```",
        "",
        "### 个人档案",
        profile_markdown.strip() or "（未填写）",
        "",
        "### 昨日回顾（用于推导明日安排）",
        yesterday_markdown.strip() or "（未填写）",
    ]
    if rag_context and rag_context.strip():
        chunks.extend(["", "### 知识库摘录", rag_context.strip()])
    user_msg = "\n".join(chunks)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": PLAN_GENERATOR_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    if deepseek_configured():
        text, err = _call_deepseek(messages)
        if text:
            return text, _meta_ok("deepseek", DEEPSEEK_MODEL)
        return _fallback_plan(reference, err or "服务暂不可用")

    return _fallback_plan(reference, None)


def _fallback_plan(reference: dict[str, Any], err: str | None) -> tuple[str, dict[str, Any]]:
    hint = "> 当前为离线说明模式，展示公式估算摘要。\n\n" if err or not deepseek_configured() else ""

    body = [
        "## 营养素与热量参考（公式估算）",
        f"- 建议明日可参考总能量约 **{reference.get('suggested_intake_kcal_next_day_estimate', '—')} kcal**（个体差异常大）。",
        f"- 三大营养素可参考：{reference.get('macro_grams_suggestion_estimate', {})}。",
        "",
        "## 明日饮食与运动",
        "- 联网智能分析恢复后，可生成个性化三餐与有氧/力量安排。",
        "",
        "## 作息与疗养提醒（非医疗）",
        "- 慢性问题或不适请及时就诊。",
    ]
    meta: dict[str, Any] = {
        "provider": "mock",
        "model": None,
        "error": err,
        "used_deepseek": False,
    }
    return hint + "\n".join(body), meta

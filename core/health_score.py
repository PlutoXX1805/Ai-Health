"""综合健康评分引擎：基于 BMI、体征趋势、运动量、饮食质量与档案完整度计算 0-100 健康指数。"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

HAI_GREEN = "#1b6b4a"
HAI_MUTED = "#5c6f66"
PLOTLY_FONT = (
    "Microsoft YaHei,SimHei,PingFang SC,Hiragino Sans GB,Noto Sans SC,"
    "Arial Unicode MS,Segoe UI,sans-serif"
)


def bmi(weight_kg: float, height_cm: float) -> float:
    if height_cm <= 0 or weight_kg <= 0:
        return 0.0
    return round(weight_kg / ((height_cm / 100.0) ** 2), 1)


def bmi_category(val: float) -> str:
    if val <= 0:
        return "未知"
    if val < 18.5:
        return "偏瘦"
    if val < 24.0:
        return "正常"
    if val < 28.0:
        return "超重"
    return "肥胖"


def bmi_score(val: float) -> float:
    if val <= 0:
        return 50.0
    if 18.5 <= val < 24.0:
        return 95.0
    if 24.0 <= val < 28.0:
        return 70.0
    if val >= 28.0:
        return 50.0
    return 65.0


def profile_completeness(prof: dict[str, Any] | None) -> tuple[float, list[str]]:
    """返回 (0-100 完整度, 缺失项列表)。"""
    if not prof:
        return 0.0, ["全部基础信息"]
    fields = {
        "height_cm": "身高",
        "weight_kg": "体重",
        "age": "年龄",
        "sex": "性别",
        "diet_preferences": "饮食偏好",
        "exercise_preferences": "运动偏好",
        "medical_history": "病史记录",
    }
    missing = []
    filled = 0
    for key, label in fields.items():
        val = prof.get(key)
        if val is not None and str(val).strip():
            filled += 1
        else:
            missing.append(label)
    pct = round(100.0 * filled / len(fields), 0)
    return pct, missing


def exercise_score(latest_daily: dict[str, Any] | None) -> float:
    if not latest_daily:
        return 40.0
    steps = int(latest_daily.get("steps") or 0)
    score = 30.0
    score += min(30.0, steps / 400.0)
    a = latest_daily.get("aerobic_duration", "")
    if "60 分钟" in a:
        score += 20
    elif "30–60" in a or "30-60" in a:
        score += 14
    elif "15–30" in a:
        score += 9
    elif "15 分钟" in a and "几乎" not in a:
        score += 5
    s = latest_daily.get("strength_duration", "")
    if "45 分钟" in s:
        score += 12
    elif "20–45" in s or "20-45" in s:
        score += 8
    elif "20 分钟" in s and "未做" not in s:
        score += 5
    sleep = latest_daily.get("sleep_h", "")
    if "7–8" in sleep or "7-8" in sleep:
        score += 8
    elif "8 小时以上" in sleep:
        score += 6
    elif "6–7" in sleep or "6-7" in sleep:
        score += 4
    return max(20.0, min(98.0, score))


def diet_score(latest_daily: dict[str, Any] | None) -> float:
    if not latest_daily:
        return 50.0
    score = 60.0
    eo = latest_daily.get("eating_out", "")
    if "多数外食" in eo:
        score -= 15
    elif "约一半外食" in eo:
        score -= 8
    elif "几乎在家" in eo:
        score += 10
    meals = latest_daily.get("meals_yesterday", "")
    if "3 顿" in meals:
        score += 10
    elif "2 顿" in meals:
        score += 5
    elif "1 顿" in meals:
        score -= 10
    sleep = latest_daily.get("sleep_h", "")
    if "不足 5" in sleep:
        score -= 8
    return max(20.0, min(98.0, score))


def compute_health_index(
    *,
    prof: dict[str, Any] | None,
    latest_daily: dict[str, Any] | None,
    has_lab: bool,
    critical_alert: bool,
) -> tuple[float, dict[str, float]]:
    """
    综合健康指数 (0-100)。
    返回 (总分, 各维度分数字典)。
    """
    w_kg = float(prof.get("weight_kg") or 0) if prof else 0.0
    h_cm = float(prof.get("height_cm") or 0) if prof else 0.0
    bmi_val = bmi(w_kg, h_cm)

    completeness, _ = profile_completeness(prof)
    bmi_s = bmi_score(bmi_val)
    exercise_s = exercise_score(latest_daily)
    diet_s = diet_score(latest_daily)
    lab_s = 75.0 if has_lab else 50.0

    if critical_alert:
        exercise_s = max(20.0, exercise_s - 20)
        lab_s = max(30.0, lab_s - 15)

    weights = {
        "BMI 体型": (bmi_s, 0.20),
        "运动活力": (exercise_s, 0.25),
        "饮食均衡": (diet_s, 0.20),
        "体检关注": (lab_s, 0.15),
        "档案完整": (completeness, 0.20),
    }
    total = sum(s * w for s, w in weights.values())
    dims = {k: s for k, (s, _) in weights.items()}
    return round(max(20.0, min(98.0, total)), 1), dims


def fig_health_gauge(score: float) -> go.Figure:
    if score >= 80:
        bar_color = "#2d8f63"
    elif score >= 60:
        bar_color = "#c9a227"
    else:
        bar_color = "#c0392b"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number=dict(
                font=dict(size=42, family=PLOTLY_FONT, color=HAI_GREEN),
                suffix=" 分",
            ),
            gauge=dict(
                axis=dict(
                    range=[0, 100],
                    tickwidth=1,
                    tickcolor="#ddd",
                    tickfont=dict(size=10, family=PLOTLY_FONT),
                ),
                bar=dict(color=bar_color, thickness=0.75),
                bgcolor="rgba(0,0,0,0.03)",
                borderwidth=0,
                steps=[
                    dict(range=[0, 40], color="rgba(192,57,43,0.08)"),
                    dict(range=[40, 70], color="rgba(201,162,39,0.08)"),
                    dict(range=[70, 100], color="rgba(45,143,99,0.08)"),
                ],
                threshold=dict(
                    line=dict(color=HAI_GREEN, width=3),
                    thickness=0.8,
                    value=score,
                ),
            ),
            title=dict(
                text="综合健康指数",
                font=dict(size=15, color=HAI_MUTED, family=PLOTLY_FONT),
            ),
        )
    )
    fig.update_layout(
        height=220,
        margin=dict(t=48, b=16, l=32, r=32),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=PLOTLY_FONT),
    )
    return fig


def fig_dimension_bars(dims: dict[str, float]) -> go.Figure:
    names = list(dims.keys())
    values = list(dims.values())
    colors = []
    for v in values:
        if v >= 75:
            colors.append("#2d8f63")
        elif v >= 55:
            colors.append("#c9a227")
        else:
            colors.append("#c0392b")

    fig = go.Figure(
        go.Bar(
            y=names,
            x=values,
            orientation="h",
            marker_color=colors,
            text=[f"{v:.0f}" for v in values],
            textposition="outside",
            textfont=dict(size=12, family=PLOTLY_FONT),
        )
    )
    fig.update_layout(
        title=dict(
            text="各维度评分明细",
            font=dict(size=14, color=HAI_MUTED, family=PLOTLY_FONT),
        ),
        xaxis=dict(
            range=[0, 105],
            showgrid=True,
            gridcolor="rgba(0,0,0,0.05)",
            tickfont=dict(family=PLOTLY_FONT),
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=12, family=PLOTLY_FONT),
        ),
        height=220,
        margin=dict(t=48, b=16, l=110, r=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=PLOTLY_FONT, color=HAI_MUTED),
        bargap=0.35,
    )
    return fig

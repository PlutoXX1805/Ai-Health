"""总览页可视化：与档案、体检、体征序列及「昨日回顾」持久化记录联动。"""

from __future__ import annotations

import sqlite3
from typing import Any

import pandas as pd
import plotly.graph_objects as go

HAI_GREEN = "#1b6b4a"
HAI_MUTED = "#5c6f66"

# Windows 下图表内中文易乱码：优先系统中文字体，再回退网页字体
PLOTLY_FONT = (
    "Microsoft YaHei,SimHei,PingFang SC,Hiragino Sans GB,Noto Sans SC,"
    "Arial Unicode MS,Segoe UI,sans-serif"
)


def _latest_lab_flags(conn) -> list[dict[str, Any]]:
    from core import db

    reps = db.list_lab_reports(conn, limit=1)
    if not reps:
        return []
    return list(reps[0].get("structured", {}).get("flags") or [])


def _clean_log(log: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in log.items() if not str(k).startswith("_")}


def nutrition_radar_scores(
    conn,
    *,
    weight_kg: float | None,
    height_cm: float | None,
    latest_daily: dict[str, Any] | None = None,
    diet_hint: str = "",
) -> tuple[list[str], list[float]]:
    """五维营养评分：体检指标 + BMI + 档案饮食倾向 + 最近一次昨日回顾。"""
    flags = _latest_lab_flags(conn)
    codes_hi = {f.get("code") for f in flags if f.get("status") == "偏高"}
    codes_lo = {f.get("code") for f in flags if f.get("status") == "偏低"}

    scores = {
        "蛋白质与肌肉代谢": 78.0,
        "碳水与能量平衡": 76.0,
        "脂肪与血脂管理": 74.0,
        "糖代谢关注": 80.0,
        "肝脏代谢负担": 82.0,
    }

    if "ALT" in codes_hi or "AST" in codes_hi:
        scores["肝脏代谢负担"] -= 18
        scores["蛋白质与肌肉代谢"] -= 8
    if "GLU" in codes_hi:
        scores["糖代谢关注"] -= 22
        scores["碳水与能量平衡"] -= 10
    if "TC" in codes_hi or "TG" in codes_hi or "LDL" in codes_hi:
        scores["脂肪与血脂管理"] -= 20
    if "HDL" in codes_lo:
        scores["脂肪与血脂管理"] -= 8

    if weight_kg and height_cm:
        bmi = weight_kg / ((height_cm / 100.0) ** 2)
        if bmi >= 28:
            scores["碳水与能量平衡"] -= 10
            scores["脂肪与血脂管理"] -= 6
        elif bmi < 18.5:
            scores["蛋白质与肌肉代谢"] -= 8

    dh = diet_hint or ""
    if any(x in dh for x in ("少油", "低脂", "清淡")):
        scores["脂肪与血脂管理"] += 5
    if any(x in dh for x in ("控糖", "少糖", "糖尿病")):
        scores["糖代谢关注"] += 4
        scores["碳水与能量平衡"] += 3
    if "蛋白" in dh or "增肌" in dh:
        scores["蛋白质与肌肉代谢"] += 4

    if latest_daily:
        d = _clean_log(latest_daily)
        eo = d.get("eating_out", "")
        if "多数外食" in eo:
            scores["碳水与能量平衡"] -= 10
            scores["脂肪与血脂管理"] -= 8
            scores["肝脏代谢负担"] -= 5
        elif "约一半外食" in eo:
            scores["碳水与能量平衡"] -= 5
            scores["脂肪与血脂管理"] -= 4
        elif "三分之一" in eo:
            scores["脂肪与血脂管理"] -= 2

        meals = d.get("meals_yesterday", "")
        if "1 顿" in meals or "更少" in meals:
            scores["蛋白质与肌肉代谢"] -= 8
            scores["碳水与能量平衡"] -= 5
        elif "4 顿" in meals:
            scores["糖代谢关注"] -= 4

        sleep = d.get("sleep_h", "")
        if "不足 5" in sleep:
            scores["糖代谢关注"] -= 6
            scores["肝脏代谢负担"] -= 4

        diet_txt = (d.get("diet_yesterday") or "") + (d.get("symptoms") or "")
        if any(x in diet_txt for x in ("酒", "啤", "白", "醉")):
            scores["肝脏代谢负担"] -= 10
            scores["碳水与能量平衡"] -= 4

        bg = d.get("blood_glucose_mmol")
        try:
            if bg is not None and float(bg) >= 7.8:
                scores["糖代谢关注"] -= 8
                scores["碳水与能量平衡"] -= 4
        except (TypeError, ValueError):
            pass

    for k in scores:
        scores[k] = max(35.0, min(98.0, scores[k]))

    categories = list(scores.keys())
    values = [scores[k] for k in categories]
    return categories, values


def _daily_exercise_score(log: dict[str, Any]) -> float:
    d = _clean_log(log)
    steps = int(d.get("steps") or 0)
    occ = d.get("occ", "")
    a = d.get("aerobic_duration", "")
    s = d.get("strength_duration", "")
    sed = d.get("sedentary", "")
    score = 22.0 + min(30.0, steps / 900.0)
    if "60 分钟" in a or a.endswith("以上") and "60" in a:
        score += 20
    elif "30–60" in a or "30-60" in a:
        score += 14
    elif "15–30" in a:
        score += 9
    elif "15 分钟" in a and "几乎" not in a:
        score += 5
    if "45 分钟" in s and "未做" not in s:
        score += 14
    elif "20–45" in s or "20-45" in s:
        score += 10
    elif "20 分钟" in s and "未做" not in s:
        score += 6
    if "体力工作" in occ:
        score += 8
    elif "站立" in occ or "走动较多" in occ:
        score += 5
    elif "间断走动" in occ:
        score += 3
    if "4 小时" in sed:
        score -= 8
    elif "2–4" in sed or "2-4" in sed:
        score -= 4
    return max(18.0, min(98.0, score))


def _vitals_segment_scores(df: pd.DataFrame, n_segments: int) -> tuple[list[str], list[float]]:
    d = df.copy()
    if "ts" in d.columns:
        d = d.sort_values("ts").reset_index(drop=True)
    n = len(d)
    if n == 0 or "heart_rate" not in d.columns:
        return [], []
    step = max(1, n // n_segments)
    parts: list[float] = []
    labels: list[str] = []
    for i in range(n_segments):
        start = i * step
        end = (i + 1) * step if i < n_segments - 1 else n
        sl = d.iloc[start:end]
        if sl.empty:
            continue
        parts.append(float(sl["heart_rate"].mean()))
        labels.append(f"体征·段{i + 1}")
    if not parts:
        return [], []
    mn, mx = min(parts), max(parts)
    if mx - mn < 1e-6:
        norm = [48.0 + 5 * (i % 3) for i in range(len(parts))]
    else:
        norm = [25.0 + 65.0 * (p - mn) / (mx - mn) for p in parts]
    return labels, norm


def exercise_intensity_series(
    df: pd.DataFrame | None,
    daily_logs_old_first: list[dict[str, Any]],
) -> tuple[list[str], list[float], str]:
    """
    最多 7 根柱：优先使用已保存的「昨日回顾」记录（按时间从左到右），不足部分用心率序列切段补齐。
    """
    target = 7
    logs = [x for x in daily_logs_old_first if x][-target:]
    scores = [_daily_exercise_score(lg) for lg in logs]
    labels = []
    for lg in logs:
        lbl = lg.get("_date_label") or "记录"
        labels.append(lbl if lbl else "记录")

    need = target - len(scores)
    subtitle = "结合已保存的昨日回顾与体征心率估算"
    if need > 0 and df is not None and not df.empty and "heart_rate" in df.columns:
        vlab, vser = _vitals_segment_scores(df, need)
        labels = vlab + labels
        scores = vser + scores
        subtitle = "左侧为体征时段，右侧为已保存的昨日回顾推导的负荷指数"
    elif need > 0 and scores:
        pad = scores[0] * 0.92
        for i in range(need):
            labels.insert(0, f"待补记录·{need - i}")
            scores.insert(0, max(20.0, min(95.0, pad)))
    elif need > 0:
        days = ["一", "二", "三", "四", "五", "六", "日"]
        labels = [f"示例·{d}" for d in days]
        scores = [42.0, 55.0, 38.0, 62.0, 48.0, 70.0, 45.0]
        subtitle = "尚无保存记录，以下为演示数据；请在「明日规划」同步昨日回顾"

    if len(scores) > target:
        scores = scores[-target:]
        labels = labels[-target:]
    return labels, scores, subtitle


def fig_nutrition_radar(categories: list[str], values: list[float]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            fillcolor="rgba(27, 107, 74, 0.25)",
            line=dict(color=HAI_GREEN, width=2),
            name="综合评估",
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=11, family=PLOTLY_FONT),
            ),
            angularaxis=dict(tickfont=dict(size=11, family=PLOTLY_FONT)),
        ),
        showlegend=False,
        margin=dict(t=48, b=48, l=56, r=56),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=PLOTLY_FONT, color=HAI_MUTED),
        title=dict(
            text="饮食营养维度（档案 + 体检 + 最近昨日回顾）",
            font=dict(size=16, color=HAI_GREEN, family=PLOTLY_FONT),
        ),
        hoverlabel=dict(font=dict(family=PLOTLY_FONT, size=12)),
    )
    return fig


def fig_exercise_bars(labels: list[str], values: list[float], subtitle: str) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=HAI_GREEN,
            marker_line_width=0,
            text=[f"{v:.0f}" for v in values],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=dict(
            text=f"运动负荷指数 · {subtitle}",
            font=dict(size=15, color=HAI_GREEN, family=PLOTLY_FONT),
        ),
        yaxis=dict(
            title=dict(text="相对强度", font=dict(family=PLOTLY_FONT, size=13)),
            range=[0, 105],
            gridcolor="rgba(0,0,0,0.06)",
            tickfont=dict(family=PLOTLY_FONT),
        ),
        xaxis=dict(title=dict(text="", font=dict(family=PLOTLY_FONT)), tickfont=dict(family=PLOTLY_FONT, size=10)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.6)",
        margin=dict(t=56, b=72, l=50, r=30),
        font=dict(family=PLOTLY_FONT, color=HAI_MUTED),
        bargap=0.38,
        hoverlabel=dict(font=dict(family=PLOTLY_FONT, size=12)),
    )
    return fig


def build_recovery_journey(
    a1: Any,
    a2: Any,
    a3: Any | None = None,
    *,
    has_lab: bool = False,
    has_profile: bool = True,
) -> tuple[list[dict[str, Any]], int, str]:
    """
    康复阶段时间线：按档案病史、检验异常与病情自报分轨（科普级）。

    兼容两种调用方式（避免旧版 app 与新版 dashboard 混用时报错）：
    - 新版：build_recovery_journey(conn, medical_note, latest_daily, has_lab=...)
    - 旧版：build_recovery_journey(medical_note, latest_daily, has_profile=..., has_lab=...)
    """
    from core import db, recovery_path

    if isinstance(a1, sqlite3.Connection):
        conn = a1
        medical_note = str(a2 or "")
        latest_daily = a3 if isinstance(a3, (dict, type(None))) else None
    else:
        conn = db.get_conn()
        medical_note = str(a1 or "")
        latest_daily = a2 if isinstance(a2, (dict, type(None))) else None

    _ = has_profile  # 旧签名保留，逻辑已由 recovery_path 覆盖

    flags = _latest_lab_flags(conn)
    nodes, ci, axis = recovery_path.build_recovery_nodes(
        medical_note=medical_note,
        latest_daily=latest_daily,
        lab_flags=flags,
        has_lab_report=has_lab,
    )
    return nodes, ci, axis


def recovery_track_caption(axis_key: str) -> str:
    return {
        "healthy": "当前未识别登记病情：按「健康」状态展示；若有慢病请在智能档案补充。",
        "hypertension": "路径轨：原发性高血压管理（家庭血压、TLC、用药依从、靶器官保护）。",
        "diabetes": "路径轨：2 型糖尿病综合管理（MNT、运动与低血糖、急性代谢、并发症筛查）。",
        "postoperative": "路径轨：围手术期至出院后康复（创面、炎症期、渐进负荷、随访）。",
        "dyslipidemia": "路径轨：血脂异常与 ASCVD 风险管理。",
        "mixed": "路径轨：代谢性疾病多病共存（血压-血糖-血脂联动）。",
        "general_chronic": "路径轨：慢性非特异性疾病综合管理。",
    }.get(axis_key, "")


def recovery_axis_short(axis_key: str) -> str:
    return {
        "healthy": "一般健康",
        "hypertension": "高血压管理轨",
        "diabetes": "糖尿病管理轨",
        "postoperative": "术后康复轨",
        "dyslipidemia": "血脂管理轨",
        "mixed": "多病共存轨",
        "general_chronic": "慢病综合轨",
    }.get(axis_key, "")


def fig_recovery_timeline(
    nodes: list[dict[str, Any]],
    selected_idx: int,
    current_idx: int,
    *,
    track_hint: str = "",
) -> go.Figure:
    """横向时间线：连线 + 节点；当前阶段与选中节点有不同强调。"""
    n = len(nodes)
    if n == 0:
        return go.Figure()
    xs = list(range(n))
    y0 = [0.0] * n

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=y0,
            mode="lines",
            line=dict(color="rgba(27, 107, 74, 0.28)", width=8),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    if 0 <= selected_idx < n:
        fig.add_trace(
            go.Scatter(
                x=[selected_idx],
                y=[0.0],
                mode="markers",
                marker=dict(
                    size=40,
                    color="rgba(0,0,0,0)",
                    line=dict(color="rgba(201, 162, 39, 0.95)", width=3),
                ),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    colors: list[str] = []
    sizes: list[int] = []
    for i, node in enumerate(nodes):
        st = node.get("status", "future")
        if st == "current":
            colors.append(HAI_GREEN)
            sizes.append(28)
        elif st == "past":
            colors.append("#5cad7a")
            sizes.append(17)
        else:
            colors.append("#b0d9c4")
            sizes.append(17)

    # 悬停文本不用 HTML，避免部分环境下与字体回退叠加出现异常显示
    custom = [f"{nodes[i]['title']}\n{nodes[i]['summary']}" for i in range(n)]
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=y0,
            mode="markers+text",
            marker=dict(color=colors, size=sizes, line=dict(color="#ffffff", width=2)),
            text=[node["short"] for node in nodes],
            textposition="top center",
            textfont=dict(size=12, color=HAI_MUTED, family=PLOTLY_FONT),
            hovertemplate="%{customdata}<extra></extra>",
            customdata=custom,
        )
    )

    ann = []
    if 0 <= current_idx < n:
        ann.append(
            dict(
                x=current_idx,
                y=0.22,
                xref="x",
                yref="y",
                text="推荐当前阶段",
                showarrow=False,
                font=dict(size=11, color=HAI_GREEN, family=PLOTLY_FONT),
            )
        )

    title_main = "病情相关康复阶段路径（点击下方节点展开详解）"
    if track_hint:
        title_main = f"{title_main} · {track_hint}"
    fig.update_layout(
        title=dict(
            text=title_main,
            font=dict(size=15, color=HAI_GREEN, family=PLOTLY_FONT),
        ),
        xaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            range=[-0.55, (n - 1) + 0.55],
            fixedrange=True,
        ),
        yaxis=dict(visible=False, range=[-0.35, 0.42], fixedrange=True),
        margin=dict(t=56, b=28, l=24, r=24),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=PLOTLY_FONT, color=HAI_MUTED),
        showlegend=False,
        height=220,
        annotations=ann,
        hoverlabel=dict(font=dict(family=PLOTLY_FONT, size=12)),
    )
    return fig

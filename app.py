"""
嗨 Hai — 本地健康科普与档案演示（Streamlit）
运行：在项目根目录执行  streamlit run app.py
"""

from __future__ import annotations

import html
import importlib

import streamlit as st

from core import dashboard, db, ingest_report, llm_client, rag, recommend, rules, ui_styles, vitals

# 避免 Streamlit 热重载后仍持有旧版 dashboard（缺少康复路径 API）
if not hasattr(dashboard, "build_recovery_journey"):
    dashboard = importlib.reload(dashboard)

DISCLAIMER = (
    "免责声明：嗨 Hai 提供的内容为健康科普与生活方式参考，不构成诊疗建议，不用于急救决策，不能替代执业医师面诊。"
)

NAV_OPTIONS = ["总览", "智能档案", "明日规划", "体征与预警", "AI 助手"]

# 侧栏单列全宽按钮：Material 图标在按钮内左侧（需 Streamlit ≥1.38）
NAV_ICON_MATERIAL = {
    "总览": ":material/dashboard:",
    "智能档案": ":material/person:",
    "明日规划": ":material/calendar_month:",
    "体征与预警": ":material/monitor_heart:",
    "AI 助手": ":material/chat:",
}


@st.cache_resource
def get_conn():
    return db.get_conn()


def _render_sidebar_brand() -> None:
    st.sidebar.markdown(
        '<div class="hai-brand-mark">嗨 Hai</div>'
        '<div class="hai-brand-sub">全周期健康助手<br/>您的健康数据保存在本设备</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.divider()


def _render_sidebar_nav() -> str:
    """单列全宽导航条：图标与文字同在一条按钮内（无分栏）。"""
    if "hai_nav_page" not in st.session_state:
        legacy = st.session_state.get("hai_nav_radio", "总览")
        st.session_state.hai_nav_page = legacy if legacy in NAV_OPTIONS else "总览"
    for label in NAV_OPTIONS:
        selected = st.session_state.hai_nav_page == label
        ic = NAV_ICON_MATERIAL.get(label)
        common = dict(
            key=f"hai_nav_btn_{label}",
            use_container_width=True,
            type="primary" if selected else "secondary",
        )
        try:
            clicked = st.sidebar.button(label, **common, icon=ic)
        except TypeError:
            clicked = st.sidebar.button(label, **common)
        if clicked:
            st.session_state.hai_nav_page = label
            st.rerun()
    st.sidebar.divider()
    return st.session_state.hai_nav_page


def _recovery_detail_panel_html(node: dict[str, object], *, is_system_current: bool) -> str:
    badge_cls = "hai-rec-badge is-current" if is_system_current else "hai-rec-badge"
    badge_txt = "系统推荐 · 当前关注阶段" if is_system_current else "节点详解"
    title = html.escape(str(node.get("title", "")))
    summary = html.escape(str(node.get("summary", "")))
    advice_list = node.get("advice") or []
    items = "".join(f"<li>{html.escape(str(a))}</li>" for a in advice_list)
    aria = html.escape(str(node.get("title", "")), quote=True)
    return (
        f'<div class="hai-rec-detail-panel" role="region" aria-label="{aria}">'
        f'<span class="{badge_cls}">{html.escape(badge_txt)}</span>'
        f"<h3>{title}</h3>"
        f'<p class="hai-rec-summary">{summary}</p>'
        f"<ul>{items}</ul>"
        "</div>"
    )


def page_overview(conn) -> None:
    st.markdown("### 健康总览")
    st.caption(
        "饮食营养、运动负荷与康复路径三维度；数据来自「智能档案」、检验摘要、"
        "「明日规划」已保存的昨日回顾，以及「体征与预警」心率序列（若已加载）。"
    )
    prof = db.get_profile(conn)
    w = float(prof["weight_kg"]) if prof and prof.get("weight_kg") else None
    h = float(prof["height_cm"]) if prof and prof.get("height_cm") else None
    medical_note = (prof.get("medical_history") or "") if prof else ""
    diet_hint = (prof.get("diet_preferences") or "") if prof else ""

    logs_new_first = db.list_daily_wellness_logs(conn, limit=14)
    latest_daily = logs_new_first[0] if logs_new_first else None
    logs_chrono = list(reversed(logs_new_first))

    has_profile = bool(prof and prof.get("height_cm") and prof.get("weight_kg"))
    has_lab = bool(db.list_lab_reports(conn, limit=1))
    has_daily = bool(latest_daily)
    personal_nutrition = has_profile or has_lab or has_daily

    vdf = st.session_state.get("vitals_df")
    if vdf is None:
        vdf = vitals.load_sample_csv()
    elab, eser, ex_sub = dashboard.exercise_intensity_series(vdf, logs_chrono)
    is_demo_exercise = "演示数据" in ex_sub

    row1 = st.columns(2)
    with row1[0]:
        st.markdown("##### 饮食营养维度")
        if not personal_nutrition:
            st.info(
                "当前没有可用于个人化的档案或记录，暂不展示雷达图，避免误导。\n\n"
                "请先完成 **智能档案**（至少填写身高、体重），或上传检验摘要、在 **明日规划** 同步昨日回顾；"
                "保存后回到本页即可看到随数据变化的雷达。"
            )
        else:
            st.caption("结合 BMI、检验异常项与最近一次昨日回顾（若有）估算，仅供科普参考。")
            cats, vals = dashboard.nutrition_radar_scores(
                conn,
                weight_kg=w or 70.0,
                height_cm=h or 170.0,
                latest_daily=latest_daily,
                diet_hint=diet_hint,
            )
            st.plotly_chart(dashboard.fig_nutrition_radar(cats, vals), use_container_width=True)
    with row1[1]:
        st.markdown("##### 运动负荷")
        if is_demo_exercise:
            st.warning(
                "**尚无已保存的昨日回顾**，下图若出现仅为占位示例，不代表您的真实运动负荷。"
            )
            st.markdown(
                "请打开 **明日规划**，填写步数、有氧/力量、久坐与睡眠等，并点击 "
                "**「同步昨日回顾到总览」**（无需调用 AI）。保存后本图将改为您的记录；"
                "若在 **体征与预警** 加载心率数据，也会与回顾合并展示。"
            )
        else:
            st.caption(ex_sub)
            st.plotly_chart(
                dashboard.fig_exercise_bars(elab, eser, ex_sub),
                use_container_width=True,
            )

    st.markdown("---")
    st.markdown("##### 病情相关康复阶段")
    st.caption(
        "阶段名称与说明依据 **智能档案病史**、**检验异常** 与 **明日规划中的病情自报** 规则生成，为科普参考；"
        "深绿色为推荐当前关注点，可点选其他节点查看前后阶段。"
    )

    if "hai_recovery_follow" not in st.session_state:
        st.session_state.hai_recovery_follow = True

    nodes, cur_i, axis_key = dashboard.build_recovery_journey(
        conn,
        medical_note,
        latest_daily,
        has_lab=has_lab,
    )
    st.caption(dashboard.recovery_track_caption(axis_key))

    if st.session_state.hai_recovery_follow:
        st.session_state.hai_recovery_focus = cur_i

    sel = int(st.session_state.get("hai_recovery_focus", cur_i))
    sel = max(0, min(sel, len(nodes) - 1))

    st.plotly_chart(
        dashboard.fig_recovery_timeline(
            nodes,
            sel,
            cur_i,
            track_hint=dashboard.recovery_axis_short(axis_key),
        ),
        use_container_width=True,
    )

    ctrl1, ctrl2 = st.columns([1, 2])
    with ctrl1:
        if st.button("跟随推荐当前阶段", key="hai_rec_follow", help="将下方详情对齐到系统推断的当前节点"):
            st.session_state.hai_recovery_follow = True
            st.rerun()
    with ctrl2:
        st.caption("点击某一节点后，将停止自动跟随，直至您再次点击左侧按钮。")

    ncols = len(nodes)
    rcols = st.columns(ncols)
    for i, node in enumerate(nodes):
        with rcols[i]:
            on = i == sel
            if st.button(
                str(node["short"]),
                key=f"hai_rec_node_{i}",
                use_container_width=True,
                type="primary" if on else "secondary",
                help=str(node.get("summary", ""))[:120],
            ):
                st.session_state.hai_recovery_focus = i
                st.session_state.hai_recovery_follow = False
                st.rerun()

    st.markdown(
        _recovery_detail_panel_html(nodes[sel], is_system_current=(sel == cur_i)),
        unsafe_allow_html=True,
    )

    if latest_daily:
        st.success(
            f"已关联最近一条昨日回顾（{latest_daily.get('_date_label', '')}）。"
            "在「明日规划」继续同步或生成方案，总览会持续更新。"
        )
    elif not has_profile:
        st.info("完善「智能档案」基础信息后，营养雷达与康复路径会更有针对性。")
    elif not has_daily:
        st.info("档案已就绪；在「明日规划」同步昨日回顾后，运动柱图将使用真实记录。")

    st.caption("图示均为本地科普级可视化，不能替代诊疗决策。")
    ui_styles.disclaimer_block(DISCLAIMER)


def page_profile(conn) -> None:
    st.markdown("### 智能档案")
    st.caption("在此维护您的基本信息、饮食运动偏好与健康记录，供明日规划与总览分析使用。")
    prof = db.get_profile(conn) or {}

    with st.container(border=True):
        st.markdown("##### 基础体征")
        with st.form("profile_form"):
            name = st.text_input("称呼（可匿名）", value=prof.get("display_name") or "")
            c1, c2 = st.columns(2)
            with c1:
                height = st.number_input(
                    "身高 cm",
                    min_value=100.0,
                    max_value=230.0,
                    value=float(prof.get("height_cm") or 170.0),
                )
                age = st.number_input("年龄", min_value=10, max_value=120, value=int(prof.get("age") or 22))
            with c2:
                weight = st.number_input(
                    "体重 kg",
                    min_value=30.0,
                    max_value=200.0,
                    value=float(prof.get("weight_kg") or 65.0),
                )
                sex = st.selectbox(
                    "性别",
                    ["男", "女", "其他"],
                    index=["男", "女", "其他"].index(prof.get("sex") or "男"),
                )
            st.markdown("###### 饮食与运动偏好（供「明日规划」引用）")
            diet_pref = st.text_area(
                "饮食偏好与忌口",
                value=prof.get("diet_preferences") or "",
                height=88,
                placeholder="例如：少油、不吃牛肉、控制精制糖…",
                help="在明日规划中会避免推荐您忌口的食物，并参考这些偏好。",
            )
            exercise_pref = st.text_area(
                "运动偏好与禁忌",
                value=prof.get("exercise_preferences") or "",
                height=88,
                placeholder="例如：喜欢游泳、膝关节不好避免跑跳、每周可运动 4 天…",
            )
            medical_hist = st.text_area(
                "当前 / 过往病史与健康记录（脱敏）",
                value=prof.get("medical_history") or "",
                height=120,
                placeholder="例如：高血压服药中、2 型糖尿病、术后阑尾切除恢复期…（仅本地保存；写清病名后总览会切换为对应专科康复阶段）",
                help="总览「病情相关康复阶段」依赖此处的文字与检验异常；明日规划可补充每日体温、血压、血糖。",
            )
            submitted = st.form_submit_button("保存档案", type="primary", use_container_width=True)
            if submitted:
                db.upsert_profile(
                    conn,
                    height_cm=height,
                    weight_kg=weight,
                    age=age,
                    sex=sex,
                    display_name=name or None,
                    diet_preferences=diet_pref.strip() or None,
                    exercise_preferences=exercise_pref.strip() or None,
                    medical_history=medical_hist.strip() or None,
                )
                st.success("已保存到本地数据库。")

    with st.container(border=True):
        st.markdown("##### 紧急联系人")
        st.caption("紧急情况下的联系信息（演示环境不发送真实通知）。")
        ec1, ec2 = st.columns(2)
        with ec1:
            ename = st.text_input("姓名", key="ec_name", placeholder="例如：家属姓名")
        with ec2:
            ephone = st.text_input("电话", key="ec_phone", placeholder="手机号码")
        if st.button("添加联系人", use_container_width=True):
            if ename.strip() and ephone.strip():
                db.add_emergency_contact(conn, ename, ephone)
                st.toast("已添加联系人")
                st.rerun()
            else:
                st.warning("请填写姓名与电话")

        for row in db.list_emergency_contacts(conn):
            c1, c2, c3 = st.columns([4, 4, 1])
            with c1:
                st.text(row["name"])
            with c2:
                st.text(row["phone"])
            with c3:
                if st.button("删", key=f"del_ec_{row['id']}", type="secondary"):
                    db.delete_emergency_contact(conn, row["id"])
                    st.rerun()

    with st.container(border=True):
        st.markdown("##### 体检报告解析")
        st.caption("支持 PDF / TXT。可将 `data/samples/demo_report.txt` 另存后上传试用。")
        up = st.file_uploader("选择文件", type=["pdf", "txt"], label_visibility="collapsed")
        if up is not None:
            data = up.getvalue()
            result = ingest_report.analyze_upload(data, up.name)
            if not result["ok"]:
                st.error(result["error"])
            else:
                st.json({"检验项": result["items"], "相对参考范围": result["flags"]})
                if st.button("写入档案", type="primary"):
                    structured = {
                        "filename": up.name,
                        "items": result["items"],
                        "flags": result["flags"],
                    }
                    db.insert_lab_report(
                        conn,
                        source_name=up.name,
                        raw_text_snippet=result.get("raw_preview") or "",
                        structured=structured,
                    )
                    st.success("检验摘要已存档")

    with st.expander("最近档案记录", expanded=False):
        for rep in db.list_lab_reports(conn, limit=5):
            with st.expander(f"{rep['source_name']} — {rep['created_at']}", expanded=False):
                st.json(rep["structured"])

    ui_styles.disclaimer_block(DISCLAIMER)


def _hai_init_steps() -> None:
    if "hai_steps_num" not in st.session_state:
        st.session_state.hai_steps_num = 6000
    if "hai_steps_sld" not in st.session_state:
        st.session_state.hai_steps_sld = int(st.session_state.hai_steps_num)
    if int(st.session_state.hai_steps_num) != int(st.session_state.hai_steps_sld):
        st.session_state.hai_steps_sld = int(st.session_state.hai_steps_num)


def _hai_sync_steps_from_num() -> None:
    v = max(0, min(100_000, int(st.session_state.hai_steps_num)))
    st.session_state.hai_steps_num = v
    st.session_state.hai_steps_sld = v


def _hai_sync_steps_from_sld() -> None:
    v = max(0, min(100_000, int(st.session_state.hai_steps_sld)))
    st.session_state.hai_steps_num = v
    st.session_state.hai_steps_sld = v


def build_yesterday_payload() -> dict:
    """从表单状态组装昨日回顾 + 病情自报（写入 daily_wellness_log，供总览读取）。"""
    temp_raw = st.session_state.get("hai_daily_temp", 0.0)
    try:
        tval = float(temp_raw) if temp_raw is not None else None
    except (TypeError, ValueError):
        tval = None
    if tval is not None and tval < 34.0:
        tval = None

    sbp_raw = st.session_state.get("hai_daily_bp_sys", 0)
    dbp_raw = st.session_state.get("hai_daily_bp_dia", 0)
    try:
        sbp = int(sbp_raw) if sbp_raw else None
    except (TypeError, ValueError):
        sbp = None
    try:
        dbp = int(dbp_raw) if dbp_raw else None
    except (TypeError, ValueError):
        dbp = None
    if sbp is not None and sbp <= 0:
        sbp = None
    if dbp is not None and dbp <= 0:
        dbp = None

    g_raw = st.session_state.get("hai_daily_glucose", 0.0)
    try:
        gval = float(g_raw) if g_raw is not None else None
    except (TypeError, ValueError):
        gval = None
    if gval is not None and gval <= 0:
        gval = None

    return {
        "steps": int(st.session_state.get("hai_steps_num", 0)),
        "occ": st.session_state.get("hai_occ", "以久坐为主"),
        "activity": st.session_state.get("hai_activity", "久坐少动"),
        "aerobic_duration": st.session_state.get("hai_aerobic_dur", "几乎未做"),
        "aerobic_type": (st.session_state.get("hai_aerobic_type") or "").strip(),
        "strength_duration": st.session_state.get("hai_strength_dur", "未做"),
        "strength_focus": (st.session_state.get("hai_strength_focus") or "").strip(),
        "meals_yesterday": st.session_state.get("hai_meals", "3 顿"),
        "eating_out": st.session_state.get("hai_eating_out", "几乎在家吃"),
        "diet_yesterday": (st.session_state.get("hai_diet_yesterday") or "").strip(),
        "sleep_h": st.session_state.get("hai_sleep", "约 7–8 小时"),
        "sedentary": st.session_state.get("hai_sedentary", "约 1–2 小时"),
        "symptoms": (st.session_state.get("hai_symptoms") or "").strip(),
        "body_temp_c": tval,
        "bp_systolic": sbp,
        "bp_diastolic": dbp,
        "blood_glucose_mmol": gval,
        "condition_body": (st.session_state.get("hai_condition_body") or "").strip(),
    }


def build_yesterday_markdown(p: dict) -> str:
    lines = [
        "### 病情与体征自报（当日/昨日）",
        f"- 体温：{p.get('body_temp_c') if p.get('body_temp_c') is not None else '未测'} ℃",
        f"- 血压："
        + (
            f"{p.get('bp_systolic')}/{p.get('bp_diastolic')} mmHg"
            if p.get("bp_systolic") and p.get("bp_diastolic")
            else "未测"
        ),
        f"- 血糖：{p.get('blood_glucose_mmol') if p.get('blood_glucose_mmol') is not None else '未测'} mmol/L",
        f"- 当前身体状况：{p.get('condition_body') or '未填'}",
        "### 昨日活动与饮食回顾",
        f"- 昨日步数：{p['steps']} 步",
        f"- 日常工作活动：{p['occ']}",
        f"- 综合活动水平（自评）：{p['activity']}",
        f"- 有氧：{p['aerobic_duration']}；类型：{p['aerobic_type'] or '未说明'}",
        f"- 无氧/力量：{p['strength_duration']}；内容：{p['strength_focus'] or '未说明'}",
        f"- 昨日正餐顿数：{p['meals_yesterday']}",
        f"- 外食比例：{p['eating_out']}",
        f"- 昨日饮食内容：{p['diet_yesterday'] or '未填'}",
        f"- 睡眠：{p['sleep_h']}",
        f"- 最长连续久坐：{p['sedentary']}",
        f"- 不适/用药/事件：{p['symptoms'] or '无'}",
    ]
    return "\n".join(lines)


def page_recommend(conn) -> None:
    st.markdown("### 明日健康规划")
    st.caption(
        "先回顾「昨天」的真实情况，再结合档案中的长期偏好与病史，由大模型一次性生成「明天」的饮食、运动与生活习惯建议。"
    )
    prof = db.get_profile(conn)
    if not prof or not prof.get("height_cm") or not prof.get("weight_kg"):
        st.warning("请先在「智能档案」填写身高、体重等基础信息，并建议补充饮食偏好、运动偏好与病史摘要。")

    height = float(prof.get("height_cm") or 170) if prof else 170.0
    weight = float(prof.get("weight_kg") or 65) if prof else 65.0
    age = int(prof.get("age") or 22) if prof else 22
    sex = (prof.get("sex") or "男") if prof else "男"

    profile_md_parts = [
        f"- 称呼：{prof.get('display_name') or '未填'}",
        f"- 性别 / 年龄：{sex}，{age} 岁",
        f"- 身高 / 体重：{height} cm / {weight} kg",
        f"- 饮食偏好与忌口：{prof.get('diet_preferences') or '未填'}",
        f"- 运动偏好与禁忌：{prof.get('exercise_preferences') or '未填'}",
        f"- 病史与健康记录摘要：{prof.get('medical_history') or '未填'}",
    ]
    profile_markdown = "\n".join(profile_md_parts)

    with st.container(border=True):
        st.markdown("##### 病情与体征自报")
        st.caption(
            "填写后随「同步到总览」或生成方案一并保存，用于 **总览康复阶段** 与 AI 分析。"
            "体温/血压/血糖填 **0 表示未测**。"
        )
        r0a, r0b, r0c = st.columns(3)
        with r0a:
            st.number_input(
                "体温（℃）· 0=未测",
                min_value=0.0,
                max_value=42.0,
                value=0.0,
                step=0.1,
                key="hai_daily_temp",
            )
        with r0b:
            st.number_input("收缩压 · 0=未测", min_value=0, max_value=260, value=0, step=1, key="hai_daily_bp_sys")
            st.number_input("舒张压 · 0=未测", min_value=0, max_value=180, value=0, step=1, key="hai_daily_bp_dia")
        with r0c:
            st.number_input(
                "血糖 mmol/L · 0=未测",
                min_value=0.0,
                max_value=35.0,
                value=0.0,
                step=0.1,
                key="hai_daily_glucose",
            )
        st.text_area(
            "当前身体状况（症状、创面、用药反应等，请脱敏）",
            height=88,
            key="hai_condition_body",
            placeholder="例如：今日乏力明显、无发热；或术后切口干燥无渗液…",
        )

    with st.container(border=True):
        st.markdown("##### 昨日回顾（填写越具体，明日计划越贴合）")
        _hai_init_steps()
        c_step1, c_step2 = st.columns([1, 1])
        with c_step1:
            st.number_input(
                "昨日步数（0–100,000，手填与滑条同步）",
                min_value=0,
                max_value=100_000,
                step=100,
                key="hai_steps_num",
                on_change=_hai_sync_steps_from_num,
            )
        with c_step2:
            st.slider(
                "拖动选择昨日步数（与左侧数字同步）",
                0,
                100_000,
                key="hai_steps_sld",
                on_change=_hai_sync_steps_from_sld,
            )

        st.selectbox(
            "日常工作活动强度（与运动无关的久坐/走动）",
            ["以久坐为主", "间断走动", "站立或走动较多", "体力工作为主"],
            key="hai_occ",
        )
        st.selectbox(
            "综合活动水平（用于估算代谢，可多选偏高一档若昨日很累）",
            ["久坐少动", "轻度活动", "中度活动", "偏高强度", "很高强度"],
            key="hai_activity",
        )

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**昨日有氧**")
            st.selectbox(
                "有氧时长",
                ["几乎未做", "约 15 分钟内", "约 15–30 分钟", "约 30–60 分钟", "60 分钟以上"],
                key="hai_aerobic_dur",
            )
            st.text_input(
                "有氧类型（可选）",
                placeholder="快走、骑行、游泳、椭圆机…",
                key="hai_aerobic_type",
            )
        with c2:
            st.markdown("**昨日无氧 / 力量**")
            st.selectbox(
                "力量训练时长",
                ["未做", "约 20 分钟内", "约 20–45 分钟", "45 分钟以上"],
                key="hai_strength_dur",
            )
            st.text_input(
                "主要部位或动作（可选）",
                placeholder="下肢、核心、全身循环…",
                key="hai_strength_focus",
            )

        st.markdown("**昨日饮食概况**（非偏好；偏好请在档案中填写）")
        st.selectbox(
            "昨日正餐顿数（大致）",
            ["1 顿或更少", "2 顿", "3 顿", "4 顿及以上"],
            key="hai_meals",
        )
        st.selectbox(
            "外食 / 外卖比例（大致）",
            ["几乎在家吃", "约三分之一外食", "约一半外食", "多数外食"],
            key="hai_eating_out",
        )
        st.text_area(
            "昨日实际吃了什么（可选，越具体越好）",
            height=100,
            placeholder="早餐：… 午餐：… 零食：… 是否饮酒：…",
            key="hai_diet_yesterday",
        )

        c3, c4 = st.columns(2)
        with c3:
            st.selectbox(
                "昨夜睡眠（大致）",
                ["不足 5 小时", "约 5–6 小时", "约 6–7 小时", "约 7–8 小时", "8 小时以上"],
                key="hai_sleep",
            )
        with c4:
            st.selectbox(
                "昨日连续久坐最长一段（工作/学习）",
                ["少于 1 小时", "约 1–2 小时", "约 2–4 小时", "4 小时以上"],
                key="hai_sedentary",
            )

        st.text_area(
            "昨日不适、用药或特殊事件（可选，脱敏填写）",
            height=72,
            placeholder="例如：胃痛、熬夜加班、漏服药物等（本应用仅作记录，不诊断）",
            key="hai_symptoms",
        )

        y_payload = build_yesterday_payload()
        yesterday_md = build_yesterday_markdown(y_payload)

        btn_row = st.columns(2)
        with btn_row[0]:
            if st.button("同步昨日回顾到总览", use_container_width=True, help="不调用大模型，仅把当前表单写入本地并更新总览图表"):
                db.insert_daily_wellness_log(conn, y_payload)
                st.toast("已保存，请打开「总览」查看图表更新")
        with btn_row[1]:
            gen_clicked = st.button("生成明日健康方案（AI）", type="primary", use_container_width=True)

        if gen_clicked:
            ref = recommend.compute_reference_bundle(
                weight_kg=weight,
                height_cm=height,
                age=age,
                sex=sex,
                activity_level=y_payload["activity"],
                yesterday_steps=int(y_payload["steps"]),
            )
            rag.load_knowledge()
            rq = " ".join(
                x
                for x in [
                    (prof.get("medical_history") or "")[:300],
                    (y_payload.get("condition_body") or "")[:220],
                    (y_payload.get("symptoms") or "")[:200],
                    "饮食 运动 睡眠 血糖 血压 体温",
                ]
                if x
            )
            hits = rag.retrieve(rq.strip() or "健康饮食 运动", top_k=5)
            rag_ctx = rag.format_hits(hits)

            with st.spinner("正在结合档案与昨日回顾生成明日方案，请稍候…"):
                plan_md, meta = llm_client.generate_tomorrow_plan(
                    profile_markdown=profile_markdown,
                    yesterday_markdown=yesterday_md,
                    reference=ref,
                    rag_context=rag_ctx,
                )
            st.session_state["hai_tomorrow_plan"] = plan_md
            st.session_state["hai_tomorrow_meta"] = meta
            st.session_state["hai_tomorrow_ref"] = ref
            st.session_state["hai_tomorrow_rag"] = hits
            db.insert_daily_wellness_log(conn, y_payload)
            st.toast("方案已生成，昨日回顾已同步至总览")

        if st.session_state.get("hai_tomorrow_plan"):
            st.markdown("---")
            st.caption("以下为最近一次生成的方案；若您修改了昨日回顾，请再次点击上方按钮更新。")
            st.markdown(st.session_state["hai_tomorrow_plan"])
            meta = st.session_state.get("hai_tomorrow_meta") or {}
            prov = meta.get("provider")
            if prov == "deepseek":
                st.caption("智能方案已生成")
            else:
                st.caption("当前为离线说明摘要")

            with st.expander("查看本次使用的公式参考与知识库引用", expanded=False):
                st.json(st.session_state.get("hai_tomorrow_ref") or {})
                hits = st.session_state.get("hai_tomorrow_rag") or []
                if hits:
                    for h in hits:
                        st.markdown(f"**{h['source']}** · `{h['id']}`\n\n{h['body']}")

    ui_styles.disclaimer_block(DISCLAIMER)


def page_vitals(conn) -> None:
    st.markdown("### 体征与预警")
    st.caption("心率、血氧、血压、血糖时序（演示数据）+ 规则引擎；告警结果不替代真实医疗设备。")

    r1 = st.columns(2)
    with r1[0]:
        if st.button("加载示例 CSV", use_container_width=True):
            st.session_state.vitals_df = vitals.load_sample_csv()
    with r1[1]:
        if st.button("生成平稳数据", use_container_width=True):
            st.session_state.vitals_df = vitals.generate_series(n=100, seed=11, inject_anomaly=False)

    r2 = st.columns([2, 1])
    _inj_labels = {
        "tachycardia": "心动过速",
        "bradycardia": "心动过缓",
        "hypoxia": "低血氧",
        "hyperglycemia": "高血糖",
        "hypertensive": "血压急升（演示）",
    }
    with r2[0]:
        inj = st.selectbox(
            "注入异常类型（演示）",
            list(_inj_labels.keys()),
            format_func=lambda x: _inj_labels[x],
        )
    with r2[1]:
        st.write("")  # 对齐
        st.write("")
        if st.button("生成并注入", use_container_width=True):
            st.session_state.vitals_df = vitals.generate_series(
                n=100, seed=99, inject_anomaly=True, anomaly_type=inj
            )

    if "vitals_df" not in st.session_state:
        st.session_state.vitals_df = vitals.load_sample_csv()

    df = vitals.ensure_vitals_columns(st.session_state.vitals_df.copy())
    st.session_state.vitals_df = df

    with st.container(border=True):
        st.markdown("##### 最近数据")
        disp_cols = {c: vitals.VITAL_COLUMN_LABELS.get(c, c) for c in df.columns}
        st.dataframe(
            df.tail(15).rename(columns=disp_cols),
            use_container_width=True,
            hide_index=True,
        )
        avail = [c for c in vitals.VITAL_NUMERIC_COLS if c in df.columns]
        default_sel = [c for c in ("heart_rate", "spo2", "systolic_bp", "glucose_mmol") if c in avail]
        picked = st.multiselect(
            "作图指标（可多选）",
            avail,
            default=default_sel[:4],
            format_func=lambda c: vitals.VITAL_COLUMN_LABELS.get(c, c),
        )
        if picked:
            chart_df = df
            if "ts" in chart_df.columns:
                chart_df = chart_df.set_index("ts")[picked]
            else:
                chart_df = chart_df[picked]
            legend_names = {c: vitals.VITAL_COLUMN_LABELS.get(c, c) for c in picked}
            st.line_chart(chart_df.rename(columns=legend_names), use_container_width=True)
        else:
            st.info("请至少选择一项指标以绘制曲线。")

    critical, reason = rules.check_critical_vitals(df)
    if critical:
        st.error("规则引擎：检测到演示危急趋势 — " + reason)
        st.warning("演示环境非急救通道。")
        contacts = db.list_emergency_contacts(conn)
        if contacts:
            st.info("将通知（演示）：" + "；".join(f"{c['name']} {c['phone']}" for c in contacts))
        else:
            st.info("未配置紧急联系人，可在「智能档案」中添加（仅演示文案）。")
    else:
        st.success("当前序列未触发演示危急规则。")

    if st.button("将当前序列写入快照记录", use_container_width=True):
        db.insert_vitals_snapshot(conn, label="manual_snapshot", payload={"rows": int(len(df))})
        st.success("已记录")

    ui_styles.disclaimer_block(DISCLAIMER)


def page_chat(conn) -> None:
    st.markdown("### AI 助手")
    st.caption("结合权威科普摘录与智能分析，回答您的健康相关疑问。")
    rag.load_knowledge()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    with st.container(border=True):
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        q = st.chat_input("用一句话描述你的健康相关疑问（科普向）")
        if q:
            hits = rag.retrieve(q, top_k=4)
            ctx = rag.format_hits(hits)
            with st.chat_message("user"):
                st.markdown(q)
            st.session_state.messages.append({"role": "user", "content": q})

            hist = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
            with st.spinner("正在思考…"):
                answer, meta = llm_client.chat(q, context=ctx, history=hist)

            with st.chat_message("assistant"):
                if hits:
                    with st.expander("知识库引用", expanded=False):
                        for h in hits:
                            st.markdown(f"**{h['source']}** · `{h['id']}`\n\n{h['body']}")
                st.markdown(answer)
                prov = meta.get("provider")
                if prov == "deepseek":
                    st.caption("智能分析已生成")
                else:
                    st.caption("离线说明模式")

            st.session_state.messages.append({"role": "assistant", "content": answer})

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("清空对话"):
            st.session_state.messages = []
            st.rerun()

    ui_styles.disclaimer_block(DISCLAIMER)


def main() -> None:
    st.set_page_config(
        page_title="嗨 Hai · 健康助手",
        page_icon=":material/health_and_safety:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    ui_styles.inject_hai_styles()
    if not hasattr(dashboard, "build_recovery_journey"):
        st.error(
            "核心模块 `core.dashboard` 未包含康复路径接口。请确认已保存最新代码，"
            "删除项目内 `__pycache__` 文件夹后重新运行 `streamlit run app.py`。"
        )
        st.stop()
    conn = get_conn()
    rag.load_knowledge()

    _render_sidebar_brand()
    mode = _render_sidebar_nav()

    st.markdown(
        f'<h1 class="hai-main-page-title">{html.escape(mode)}</h1>',
        unsafe_allow_html=True,
    )
    st.caption("个人健康管理中心 · 饮食、运动与生活建议")
    st.markdown("<div style='height:0.85rem'></div>", unsafe_allow_html=True)

    if mode == "总览":
        page_overview(conn)
    elif mode == "智能档案":
        page_profile(conn)
    elif mode == "明日规划":
        page_recommend(conn)
    elif mode == "体征与预警":
        page_vitals(conn)
    else:
        page_chat(conn)


if __name__ == "__main__":
    main()

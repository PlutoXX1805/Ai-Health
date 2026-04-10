"""
嗨 Hai — 本地健康科普与档案演示（Streamlit）
运行：在项目根目录执行  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from core import db, ingest_report, llm_client, rag, recommend, rules, ui_styles, vitals

DISCLAIMER = (
    "免责声明：嗨 Hai 仅供课程演示与健康科普参考，不构成诊疗建议，不用于急救决策，不能替代执业医师面诊。"
)


@st.cache_resource
def get_conn():
    return db.get_conn()


def show_disclaimer() -> None:
    st.caption(DISCLAIMER)


def page_overview(conn) -> None:
    st.subheader("总览")
    st.markdown(
        """
        **嗨 Hai**（英文名 **Hai**，寓意 AI + Health）是本课程的本地 MVP：
        智能档案、检验单解析、规则化体征预警、轻量 **RAG**，以及 **DeepSeek** 云端推理（推荐）或 **Ollama** 本地回退。
        """
    )
    ds_ok = llm_client.deepseek_configured()
    ollama_ok = llm_client._ollama_available()
    rag.load_knowledge()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("DeepSeek API", "已配置" if ds_ok else "未配置")
    with c2:
        st.metric("Ollama（回退）", "可用" if ollama_ok else "未连接")
    with c3:
        st.metric("知识库段落", str(rag.knowledge_chunk_count()))
    st.info(
        "在项目根目录复制 `.env.example` 为 `.env`，填入 `DEEPSEEK_API_KEY` 后重启应用，即可使用 DeepSeek。"
        " 若 API 不可用且本机已装 [Ollama](https://ollama.com/)，将自动改用本地模型。"
    )
    prof = db.get_profile(conn)
    if prof:
        st.success("已保存用户档案，可在「智能档案」中修改。")
    show_disclaimer()


def page_profile(conn) -> None:
    st.subheader("智能档案")
    prof = db.get_profile(conn) or {}

    with st.form("profile_form"):
        name = st.text_input("称呼（可匿名）", value=prof.get("display_name") or "")
        height = st.number_input("身高 cm", min_value=100.0, max_value=230.0, value=float(prof.get("height_cm") or 170.0))
        weight = st.number_input("体重 kg", min_value=30.0, max_value=200.0, value=float(prof.get("weight_kg") or 65.0))
        age = st.number_input("年龄", min_value=10, max_value=120, value=int(prof.get("age") or 22))
        sex = st.selectbox("性别", ["男", "女", "其他"], index=["男", "女", "其他"].index(prof.get("sex") or "男"))
        submitted = st.form_submit_button("保存档案")
        if submitted:
            db.upsert_profile(
                conn,
                height_cm=height,
                weight_kg=weight,
                age=age,
                sex=sex,
                display_name=name or None,
            )
            st.success("档案已保存到本地 SQLite。")

    st.divider()
    st.markdown("**紧急联系人（演示：仅展示「将通知」，不发送真实消息）**")
    ec1, ec2 = st.columns(2)
    with ec1:
        ename = st.text_input("姓名", key="ec_name")
    with ec2:
        ephone = st.text_input("电话", key="ec_phone")
    if st.button("添加联系人"):
        if ename.strip() and ephone.strip():
            db.add_emergency_contact(conn, ename, ephone)
            st.success("已添加")
        else:
            st.warning("请填写姓名与电话")

    for row in db.list_emergency_contacts(conn):
        c1, c2, c3 = st.columns([3, 3, 1])
        c1.write(row["name"])
        c2.write(row["phone"])
        if c3.button("删", key=f"del_ec_{row['id']}"):
            db.delete_emergency_contact(conn, row["id"])
            st.rerun()

    st.divider()
    st.markdown("**上传体检报告（PDF / TXT，脱敏演示）**")
    st.caption("可使用 `data/samples/demo_report.txt` 作为示例内容另存上传。")
    up = st.file_uploader("选择文件", type=["pdf", "txt"])
    if up is not None:
        data = up.getvalue()
        result = ingest_report.analyze_upload(data, up.name)
        if not result["ok"]:
            st.error(result["error"])
        else:
            st.json({"检验项": result["items"], "相对参考范围": result["flags"]})
            if st.button("写入档案数据库"):
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
                st.success("已保存检验摘要")

    st.divider()
    st.markdown("**最近档案记录**")
    for rep in db.list_lab_reports(conn, limit=5):
        with st.expander(f"{rep['source_name']} — {rep['created_at']}"):
            st.json(rep["structured"])
    show_disclaimer()


def page_recommend(conn) -> None:
    st.subheader("多维推荐")
    prof = db.get_profile(conn)
    if not prof:
        st.warning("请先在「智能档案」填写身高体重等信息。")

    height = float(prof.get("height_cm") or 170) if prof else 170.0
    weight = float(prof.get("weight_kg") or 65) if prof else 65.0
    age = int(prof.get("age") or 22) if prof else 22
    sex = prof.get("sex") or "男" if prof else "男"

    activity = st.selectbox("活动水平", ["久坐少动", "轻度活动", "中度活动", "高强度"])
    steps = st.select_slider("今日步数等级（模拟）", options=["低", "中", "高"], value="中")
    diet = st.text_input("饮食偏好 / 忌口（可选）", "")

    if st.button("生成一日计划要点"):
        plan = recommend.build_daily_plan(
            weight_kg=weight,
            height_cm=height,
            age=age,
            sex=sex,
            activity_level=activity,
            diet_pref=diet,
            steps_level=steps,
        )
        st.session_state["last_plan"] = plan

    if "last_plan" in st.session_state:
        st.markdown(st.session_state["last_plan"])
        if st.button("使用大模型润色表述（可选）"):
            with st.spinner("润色中…"):
                polished, meta = llm_client.polish_plan(st.session_state["last_plan"])
            st.session_state["last_plan_polished"] = polished
            st.session_state["last_plan_meta"] = meta
        if st.session_state.get("last_plan_polished"):
            st.markdown("---")
            st.markdown(st.session_state["last_plan_polished"])
            meta = st.session_state.get("last_plan_meta") or {}
            prov = meta.get("provider")
            if prov == "deepseek":
                st.caption(f"已通过 DeepSeek `{meta.get('model')}` 润色。")
            elif prov == "ollama":
                st.caption(f"已通过 Ollama `{meta.get('model')}` 润色。")
            else:
                st.caption("离线模式：未调用大模型或调用失败，已显示原始要点。")

    show_disclaimer()


def page_vitals(conn) -> None:
    st.subheader("体征与预警（模拟）")
    st.caption("规则引擎判定危急趋势；演示环境不会真实通知任何人。")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("加载示例 CSV"):
            st.session_state.vitals_df = vitals.load_sample_csv()
    with c2:
        if st.button("生成平稳模拟数据"):
            st.session_state.vitals_df = vitals.generate_series(n=100, seed=11, inject_anomaly=False)
    with c3:
        inj = st.selectbox("注入异常类型", ["tachycardia", "bradycardia", "hypoxia"])
        if st.button("生成并注入异常"):
            st.session_state.vitals_df = vitals.generate_series(
                n=100, seed=99, inject_anomaly=True, anomaly_type=inj
            )

    if "vitals_df" not in st.session_state:
        st.session_state.vitals_df = vitals.load_sample_csv()

    df = st.session_state.vitals_df
    st.dataframe(df.tail(15), use_container_width=True)

    chart_df = df
    if "ts" in chart_df.columns:
        chart_df = chart_df.set_index("ts")[["heart_rate", "spo2"]]
    else:
        chart_df = chart_df[["heart_rate", "spo2"]]
    st.line_chart(chart_df)

    critical, reason = rules.check_critical_vitals(df)
    if critical:
        st.error("规则引擎：检测到演示用危急阈值 — " + reason)
        st.warning("演示环境非急救通道。")
        contacts = db.list_emergency_contacts(conn)
        if contacts:
            st.info("将通知（演示）：" + "；".join(f"{c['name']} {c['phone']}" for c in contacts))
        else:
            st.info("未配置紧急联系人；可在「智能档案」中添加（仍仅为演示文案）。")
    else:
        st.success("当前序列未触发演示危急规则。")

    if st.button("将当前序列快照写入数据库"):
        db.insert_vitals_snapshot(conn, label="manual_snapshot", payload={"rows": int(len(df))})
        st.success("已记录快照元数据")

    show_disclaimer()


def page_chat(conn) -> None:
    st.subheader("AI 助手（RAG + DeepSeek / Ollama）")
    rag.load_knowledge()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    q = st.chat_input("描述你的健康相关疑问（科普向）")
    if q:
        hits = rag.retrieve(q, top_k=4)
        ctx = rag.format_hits(hits)
        with st.chat_message("user"):
            st.markdown(q)
        st.session_state.messages.append({"role": "user", "content": q})

        hist = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
        with st.spinner("思考中…"):
            answer, meta = llm_client.chat(q, context=ctx, history=hist)

        with st.chat_message("assistant"):
            if hits:
                with st.expander("查看知识库引用"):
                    for h in hits:
                        st.markdown(f"**{h['source']}**（{h['id']}）\n\n{h['body']}")
            st.markdown(answer)
            prov = meta.get("provider")
            if prov == "deepseek":
                st.caption(f"DeepSeek · {meta.get('model')}")
            elif prov == "ollama":
                st.caption(f"Ollama · {meta.get('model')}")
            else:
                st.caption("离线模板 / 回退模式")

        st.session_state.messages.append({"role": "assistant", "content": answer})

    if st.button("清空对话"):
        st.session_state.messages = []
        st.rerun()

    show_disclaimer()


def main() -> None:
    st.set_page_config(page_title="嗨 Hai · 本地演示", page_icon="💚", layout="wide")
    ui_styles.inject_hai_styles()
    conn = get_conn()
    rag.load_knowledge()

    st.sidebar.title("嗨 Hai")
    st.sidebar.caption("AI + Health → Hai · 健康面板")
    if llm_client.deepseek_configured():
        st.sidebar.success("DeepSeek 已就绪")
    elif llm_client._ollama_available():
        st.sidebar.info("未配置 DeepSeek，将使用 Ollama")
    else:
        st.sidebar.warning("请配置 .env 的 DEEPSEEK_API_KEY，或启动 Ollama")
    mode = st.sidebar.radio(
        "导航",
        ["总览", "智能档案", "多维推荐", "体征与预警", "AI 助手"],
    )

    st.title("嗨 Hai — 全周期健康助手（MVP）")

    if mode == "总览":
        page_overview(conn)
    elif mode == "智能档案":
        page_profile(conn)
    elif mode == "多维推荐":
        page_recommend(conn)
    elif mode == "体征与预警":
        page_vitals(conn)
    else:
        page_chat(conn)


if __name__ == "__main__":
    main()

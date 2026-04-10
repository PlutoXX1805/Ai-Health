"""Streamlit 全局样式：Wellness / Health 面板（UI/UX Pro Max — Soft UI、4.5:1 对比、150–300ms 动效、减少装饰噪音）。"""

from __future__ import annotations

import html

import streamlit as st


def inject_hai_styles() -> None:
    st.markdown(
        r"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Noto+Sans+SC:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
  :root {
    --hai-green-950: #0d2818;
    --hai-green-800: #14523a;
    --hai-green-700: #1b6b4a;
    --hai-green-500: #2d8f63;
    --hai-green-200: #b8e0cc;
    --hai-green-100: #dff5ea;
    --hai-green-50: #f0faf4;
    --hai-surface: #ffffff;
    --hai-muted: #5c6f66;
    --hai-border: rgba(27, 107, 74, 0.14);
    --hai-shadow-sm: 0 1px 2px rgba(13, 40, 24, 0.05);
    --hai-shadow-md: 0 4px 20px rgba(13, 40, 24, 0.07);
    --hai-radius: 14px;
    --hai-radius-lg: 18px;
    --hai-ease: cubic-bezier(0.25, 0.1, 0.25, 1);
    --hai-duration: 220ms;
  }

  html {
    scroll-behavior: smooth;
  }

  @media (prefers-reduced-motion: reduce) {
    html { scroll-behavior: auto; }
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
  }

  .stApp {
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", "SimHei", sans-serif !important;
    background: radial-gradient(1200px 600px at 10% -10%, var(--hai-green-100) 0%, transparent 55%),
                radial-gradient(900px 500px at 100% 0%, #e8f4ef 0%, transparent 50%),
                linear-gradient(180deg, var(--hai-green-50) 0%, #fafcfb 38%, #f6f9f7 100%) !important;
    color: var(--hai-green-950);
  }

  .block-container {
    padding-top: 1.75rem;
    padding-bottom: 3.5rem;
    padding-left: 2.25rem;
    padding-right: 2.25rem;
    max-width: 1280px;
  }

  /* 主区大标题（单页一个 h1，符合层级） */
  h1.hai-main-page-title {
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", "DM Sans", sans-serif !important;
    font-weight: 700 !important;
    color: var(--hai-green-800) !important;
    font-size: clamp(1.85rem, 3.2vw, 2.45rem) !important;
    line-height: 1.2 !important;
    letter-spacing: -0.03em !important;
    margin: 0 0 0.35rem 0 !important;
    padding-bottom: 0.15rem !important;
    border-bottom: 1px solid var(--hai-border);
  }

  /* 侧栏全宽导航按钮（图标在按钮内左侧，整条贴齐侧栏内容区） */
  section[data-testid="stSidebar"] .stButton > button {
    min-height: 52px !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 0.55rem 0.75rem !important;
    box-shadow: var(--hai-shadow-sm) !important;
    justify-content: flex-start !important;
    text-align: left !important;
    width: 100% !important;
    transition: transform var(--hai-duration) var(--hai-ease), box-shadow var(--hai-duration) var(--hai-ease) !important;
  }
  section[data-testid="stSidebar"] .stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: var(--hai-shadow-md) !important;
  }
  section[data-testid="stSidebar"] .stButton > button:focus-visible {
    outline: 2px solid var(--hai-green-500) !important;
    outline-offset: 2px !important;
  }

  /* 康复路径：展开详情面板 */
  .hai-rec-detail-panel {
    margin-top: 0.75rem;
    padding: 1.35rem 1.5rem 1.45rem;
    border-radius: var(--hai-radius-lg);
    background: linear-gradient(145deg, rgba(255, 255, 255, 0.96) 0%, var(--hai-green-50) 55%, #e8f5ef 100%);
    border: 1px solid var(--hai-border);
    box-shadow: var(--hai-shadow-md);
  }
  .hai-rec-detail-panel h3 {
    margin: 0 0 0.5rem 0 !important;
    font-size: 1.28rem !important;
    color: var(--hai-green-800) !important;
  }
  .hai-rec-detail-panel .hai-rec-summary {
    color: var(--hai-muted);
    font-size: 0.95rem;
    line-height: 1.55;
    margin-bottom: 0.85rem;
  }
  .hai-rec-detail-panel ul {
    margin: 0;
    padding-left: 1.15rem;
    line-height: 1.65;
    color: var(--hai-green-950);
    font-size: 0.98rem;
  }
  .hai-rec-detail-panel li {
    margin-bottom: 0.4rem;
  }
  .hai-rec-badge {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    background: rgba(27, 107, 74, 0.12);
    color: var(--hai-green-700);
    margin-bottom: 0.5rem;
  }
  .hai-rec-badge.is-current {
    background: var(--hai-green-700);
    color: #fff;
  }

  /* 隐藏 Streamlit 默认顶栏（Deploy、⋯ 菜单等白条） */
  header[data-testid="stHeader"] {
    display: none !important;
    height: 0 !important;
    visibility: hidden !important;
    pointer-events: none !important;
  }
  /* 部分版本顶栏工具区单独挂载 */
  div[data-testid="stToolbar"] {
    display: none !important;
  }
  div[data-testid="stDecoration"] {
    display: none !important;
  }

  /* 侧边栏 */
  div[data-testid="stSidebar"] {
    background: linear-gradient(165deg, #ffffff 0%, var(--hai-green-50) 48%, #eef8f2 100%) !important;
    border-right: 1px solid var(--hai-border) !important;
    box-shadow: var(--hai-shadow-md);
  }
  div[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem;
    padding-left: 1.1rem;
    padding-right: 1.1rem;
  }

  /* 标题层级 */
  h1, h2, h3 {
    font-family: "Noto Sans SC", "DM Sans", sans-serif !important;
    letter-spacing: -0.02em;
    font-weight: 600 !important;
  }
  h1 {
    color: var(--hai-green-800) !important;
    font-weight: 700 !important;
    font-size: clamp(1.55rem, 3vw, 2rem) !important;
    line-height: 1.25 !important;
    margin-bottom: 0.35rem !important;
  }
  h2, h3 {
    color: var(--hai-green-950) !important;
    font-size: 1.15rem !important;
    margin-top: 0.5rem !important;
  }

  /* 指标卡片 */
  [data-testid="stMetric"] {
    background: var(--hai-surface) !important;
    border: 1px solid var(--hai-border) !important;
    border-radius: var(--hai-radius) !important;
    padding: 0.85rem 1rem !important;
    box-shadow: var(--hai-shadow-sm);
    transition: box-shadow var(--hai-duration) var(--hai-ease), transform var(--hai-duration) var(--hai-ease);
  }
  [data-testid="stMetric"]:hover {
    box-shadow: var(--hai-shadow-md);
    transform: translateY(-1px);
  }
  [data-testid="stMetric"] label {
    color: var(--hai-muted) !important;
    font-weight: 500 !important;
    font-size: 0.8rem !important;
  }
  [data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: var(--hai-green-800) !important;
    font-weight: 700 !important;
  }

  /* 分段控件（主导航） */
  div[data-testid="stSegmentedControl"] {
    background: rgba(255, 255, 255, 0.65) !important;
    border: 1px solid var(--hai-border) !important;
    border-radius: var(--hai-radius-lg) !important;
    padding: 4px !important;
    box-shadow: var(--hai-shadow-sm);
  }
  div[data-testid="stSegmentedControl"] button {
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: background var(--hai-duration) var(--hai-ease), color var(--hai-duration) var(--hai-ease) !important;
  }

  /* 按钮 */
  .stButton > button {
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: transform var(--hai-duration) var(--hai-ease), box-shadow var(--hai-duration) var(--hai-ease) !important;
  }
  .stButton > button:focus-visible {
    outline: 2px solid var(--hai-green-500) !important;
    outline-offset: 2px !important;
  }
  .stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: var(--hai-shadow-sm);
  }

  /* 表单控件 */
  .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
    border-radius: 10px !important;
    transition: border-color var(--hai-duration) var(--hai-ease), box-shadow var(--hai-duration) var(--hai-ease) !important;
  }
  .stTextInput input:focus, .stNumberInput input:focus {
    border-color: var(--hai-green-500) !important;
    box-shadow: 0 0 0 3px rgba(45, 143, 99, 0.15) !important;
  }

  /* 带边框容器 = 内容卡片 */
  div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--hai-surface) !important;
    border: 1px solid var(--hai-border) !important;
    border-radius: var(--hai-radius-lg) !important;
    box-shadow: var(--hai-shadow-sm) !important;
    padding: 1.1rem 1.25rem 1.25rem !important;
    margin-bottom: 1rem !important;
    transition: box-shadow var(--hai-duration) var(--hai-ease);
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: var(--hai-shadow-md);
  }

  /* Alert / info 块 */
  div[data-testid="stAlert"] {
    border-radius: var(--hai-radius) !important;
    border: 1px solid var(--hai-border) !important;
    box-shadow: var(--hai-shadow-sm);
  }

  /* Expander */
  div[data-testid="stExpander"] {
    border: 1px solid var(--hai-border) !important;
    border-radius: var(--hai-radius) !important;
    overflow: hidden;
    background: rgba(255, 255, 255, 0.85);
    box-shadow: var(--hai-shadow-sm);
  }
  div[data-testid="stExpander"] summary {
    font-weight: 500 !important;
  }

  /* 数据表 */
  div[data-testid="stDataFrame"] {
    border-radius: var(--hai-radius);
    overflow: hidden;
    border: 1px solid var(--hai-border);
    box-shadow: var(--hai-shadow-sm);
  }

  /* 图表区域 */
  [data-testid="stArrowVegaLiteChart"] {
    border-radius: var(--hai-radius);
  }

  /* 对话气泡 */
  [data-testid="stChatMessage"] {
    border-radius: var(--hai-radius) !important;
    border: 1px solid var(--hai-border) !important;
    background: rgba(255, 255, 255, 0.92) !important;
    box-shadow: var(--hai-shadow-sm);
    margin-bottom: 0.65rem !important;
    transition: box-shadow var(--hai-duration) var(--hai-ease);
  }
  [data-testid="stChatMessage"]:hover {
    box-shadow: var(--hai-shadow-md);
  }

  /* 聊天输入 */
  div[data-testid="stChatInput"] {
    border-radius: var(--hai-radius-lg) !important;
    border: 1px solid var(--hai-border) !important;
    box-shadow: var(--hai-shadow-md);
    background: rgba(255, 255, 255, 0.95) !important;
  }

  /* 隐藏 Streamlit 底部链接行（演示更干净；需要菜单可保留） */
  footer { visibility: hidden; height: 0; }

  /* 免责声明：弱化但不失对比 */
  .hai-disclaimer {
    color: var(--hai-muted);
    font-size: 0.78rem;
    line-height: 1.55;
    margin-top: 1.5rem;
    padding: 0.75rem 1rem;
    background: rgba(255, 255, 255, 0.6);
    border-radius: 10px;
    border: 1px solid var(--hai-border);
  }

  /* 品牌侧栏块（左上角「嗨 Hai」） */
  .hai-brand-mark {
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", "DM Sans", sans-serif;
    font-weight: 700;
    font-size: clamp(2.2rem, 5.2vw, 3.2rem);
    letter-spacing: -0.04em;
    color: var(--hai-green-800);
    line-height: 1.08;
    margin-bottom: 0.22rem;
  }
  .hai-brand-sub {
    font-size: 0.88rem;
    color: var(--hai-muted);
    line-height: 1.5;
    margin-bottom: 1rem;
  }

  /* 小节标签 */
  .hai-kicker {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--hai-green-500);
    margin-bottom: 0.35rem;
  }
</style>
        """,
        unsafe_allow_html=True,
    )


def disclaimer_block(text: str) -> None:
    """底部免责声明（带样式类，内容经转义）。"""
    st.markdown(
        f'<p class="hai-disclaimer">{html.escape(text)}</p>',
        unsafe_allow_html=True,
    )

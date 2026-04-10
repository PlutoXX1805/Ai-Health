"""Streamlit 局部样式：健康类产品面板（对齐 UI/UX Pro Max — Soft UI、清晰层次、避免花哨渐变）。"""

import streamlit as st


def inject_hai_styles() -> None:
    st.markdown(
        """
<style>
  .block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 1200px;
  }
  div[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #e8f5ef 0%, #f4faf7 55%, #ffffff 100%);
    border-right: 1px solid #c8e6d4;
  }
  div[data-testid="stSidebar"] .stMarkdown strong {
    color: #14523a;
  }
  h1 {
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #14523a !important;
  }
  h2, h3 {
    color: #1a2e26 !important;
  }
  [data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #c8e6d4;
    border-radius: 12px;
    padding: 0.5rem 0.75rem;
    box-shadow: 0 1px 2px rgba(20, 82, 58, 0.06);
  }
  div[data-testid="stExpander"] {
    border: 1px solid #d4e8dc;
    border-radius: 10px;
    overflow: hidden;
  }
</style>
        """,
        unsafe_allow_html=True,
    )

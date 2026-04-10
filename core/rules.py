"""规则引擎：检验项参考范围、体征危急值（最终以规则为准，不依赖 LLM 判危重）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

# 常规成人参考范围（演示用，非临床标准）
LAB_REF: dict[str, tuple[float | None, float | None, str]] = {
    "ALT": (9.0, 50.0, "U/L"),
    "AST": (15.0, 40.0, "U/L"),
    "TBIL": (5.0, 21.0, "μmol/L"),
    "CREA": (57.0, 111.0, "μmol/L"),
    "GLU": (3.9, 6.1, "mmol/L"),
    "TC": (3.1, 5.2, "mmol/L"),
    "TG": (0.45, 1.7, "mmol/L"),
    "HDL": (1.04, None, "mmol/L"),
    "LDL": (None, 3.4, "mmol/L"),
}


@dataclass
class LabFlag:
    code: str
    value: float
    low: float | None
    high: float | None
    unit: str
    status: str  # "正常" | "偏高" | "偏低"


def flag_labs(items: list[dict[str, Any]]) -> list[LabFlag]:
    """items: [{"code": "ALT", "value": 120.0, "unit": "U/L"}, ...]"""
    out: list[LabFlag] = []
    for it in items:
        code = str(it.get("code", "")).upper()
        if code not in LAB_REF:
            continue
        try:
            val = float(it["value"])
        except (KeyError, TypeError, ValueError):
            continue
        low, high, unit = LAB_REF[code]
        u = str(it.get("unit") or unit)
        if low is not None and val < low:
            status = "偏低"
        elif high is not None and val > high:
            status = "偏高"
        else:
            status = "正常"
        out.append(LabFlag(code=code, value=val, low=low, high=high, unit=u, status=status))
    return out


# 体征：连续 N 个点越界视为「演示危急」
DEFAULT_WINDOW = 5
HR_LOW, HR_HIGH = 45, 140
SPO2_LOW = 90
SBP_HIGH = 180
DBP_HIGH = 110
GLU_HIGH = 16.7


def check_critical_vitals(df: pd.DataFrame) -> tuple[bool, str]:
    """
    需要列：heart_rate（或 hr）、spo2（可选）。
    返回 (是否告警, 说明)。
    """
    if df is None or df.empty:
        return False, ""

    hr_col = "heart_rate" if "heart_rate" in df.columns else "hr" if "hr" in df.columns else None
    if hr_col is None:
        return False, ""

    hr = pd.to_numeric(df[hr_col], errors="coerce").dropna()
    if len(hr) < DEFAULT_WINDOW:
        return False, ""

    tail = hr.tail(DEFAULT_WINDOW)
    if (tail > HR_HIGH).all():
        return True, f"心率连续 {DEFAULT_WINDOW} 次高于 {HR_HIGH}（演示规则，非真实急救判定）"
    if (tail < HR_LOW).all():
        return True, f"心率连续 {DEFAULT_WINDOW} 次低于 {HR_LOW}（演示规则，非真实急救判定）"

    if "spo2" in df.columns:
        ox = pd.to_numeric(df["spo2"], errors="coerce").dropna()
        if len(ox) >= DEFAULT_WINDOW:
            ox_tail = ox.tail(DEFAULT_WINDOW)
            if (ox_tail < SPO2_LOW).all():
                return True, f"血氧连续 {DEFAULT_WINDOW} 次低于 {SPO2_LOW}%（演示规则）"

    if "systolic_bp" in df.columns and "diastolic_bp" in df.columns:
        sbp = pd.to_numeric(df["systolic_bp"], errors="coerce").dropna()
        dbp = pd.to_numeric(df["diastolic_bp"], errors="coerce").dropna()
        m = min(len(sbp), len(dbp))
        if m >= DEFAULT_WINDOW:
            sbp_t = sbp.tail(DEFAULT_WINDOW)
            dbp_t = dbp.tail(DEFAULT_WINDOW)
            if ((sbp_t > SBP_HIGH) & (dbp_t > DBP_HIGH)).all():
                return (
                    True,
                    f"血压连续 {DEFAULT_WINDOW} 次高于 {SBP_HIGH}/{DBP_HIGH} mmHg（演示规则，非高血压急症判定）",
                )

    if "glucose_mmol" in df.columns:
        glu = pd.to_numeric(df["glucose_mmol"], errors="coerce").dropna()
        if len(glu) >= DEFAULT_WINDOW:
            g_tail = glu.tail(DEFAULT_WINDOW)
            if (g_tail > GLU_HIGH).all():
                return True, f"血糖连续 {DEFAULT_WINDOW} 次高于 {GLU_HIGH} mmol/L（演示规则，请线下就医）"

    return False, ""

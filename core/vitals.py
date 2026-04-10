"""模拟体征序列：生成、注入异常、读写 CSV。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"
DEFAULT_CSV = SAMPLES_DIR / "vitals_demo.csv"

VITAL_NUMERIC_COLS = ("heart_rate", "spo2", "systolic_bp", "diastolic_bp", "glucose_mmol")

# 表格/多选下展示用中文名（列键仍为英文，避免作图键名乱码）
VITAL_COLUMN_LABELS: dict[str, str] = {
    "heart_rate": "心率 (次/分)",
    "spo2": "血氧 (%)",
    "systolic_bp": "收缩压 (mmHg)",
    "diastolic_bp": "舒张压 (mmHg)",
    "glucose_mmol": "血糖 (mmol/L)",
    "ts": "时间",
}


def ensure_vitals_columns(df: pd.DataFrame) -> pd.DataFrame:
    """为旧 CSV 或生成数据补齐血压、血糖列，便于统一作图与规则引擎。"""
    if df is None or df.empty:
        return df
    out = df.copy()
    n = len(out)
    rng = np.random.default_rng(hash(str(out.iloc[0].to_dict())) % (2**32))
    if "systolic_bp" not in out.columns:
        sbp = 118 + rng.normal(0, 6, size=n)
        out["systolic_bp"] = np.clip(np.round(sbp, 0), 95, 175)
    if "diastolic_bp" not in out.columns:
        dbp = 76 + rng.normal(0, 4, size=n)
        out["diastolic_bp"] = np.clip(np.round(dbp, 0), 55, 110)
    if "glucose_mmol" not in out.columns:
        g = 5.5 + rng.normal(0, 0.35, size=n)
        out["glucose_mmol"] = np.clip(np.round(g, 1), 3.9, 12.0)
    return out


def load_sample_csv(path: Path | None = None) -> pd.DataFrame:
    p = path or DEFAULT_CSV
    if not p.exists():
        return generate_series(n=120, seed=42, inject_anomaly=False)
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            df = pd.read_csv(p, encoding=enc)
            break
        except UnicodeDecodeError:
            df = None
    else:
        df = pd.read_csv(p, encoding="utf-8", encoding_errors="replace")
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    return ensure_vitals_columns(df)


def generate_series(
    n: int = 120,
    *,
    seed: int = 7,
    inject_anomaly: bool = False,
    anomaly_type: str = "tachycardia",
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = pd.date_range(end=pd.Timestamp.now(tz="UTC"), periods=n, freq="min")
    hr = 68 + rng.normal(0, 4, size=n).cumsum() * 0.05
    hr = np.clip(hr, 55, 95)
    spo2 = 97 + rng.normal(0, 0.6, size=n)
    spo2 = np.clip(spo2, 93, 99)
    sbp = 118 + hr * 0.35 + rng.normal(0, 3, size=n)
    sbp = np.clip(sbp, 95, 145)
    dbp = 74 + rng.normal(0, 2.5, size=n)
    dbp = np.clip(dbp, 55, 95)
    glu = 5.5 + rng.normal(0, 0.25, size=n)
    glu = np.clip(glu, 4.0, 7.5)

    if inject_anomaly:
        if anomaly_type == "tachycardia":
            hr[-8:] = rng.uniform(148, 165, size=8)
            sbp[-8:] = rng.uniform(145, 165, size=8)
            dbp[-8:] = rng.uniform(88, 98, size=8)
        elif anomaly_type == "bradycardia":
            hr[-8:] = rng.uniform(32, 40, size=8)
        elif anomaly_type == "hypoxia":
            spo2[-8:] = rng.uniform(82, 88, size=8)
        elif anomaly_type == "hyperglycemia":
            glu[-10:] = rng.uniform(14.0, 20.0, size=10)
        elif anomaly_type == "hypertensive":
            sbp[-8:] = rng.uniform(175, 195, size=8)
            dbp[-8:] = rng.uniform(105, 115, size=8)

    return pd.DataFrame(
        {
            "ts": base,
            "heart_rate": np.round(hr, 1),
            "spo2": np.round(spo2, 1),
            "systolic_bp": np.round(sbp, 0),
            "diastolic_bp": np.round(dbp, 0),
            "glucose_mmol": np.round(glu, 1),
        }
    )

"""模拟体征序列：生成、注入异常、读写 CSV。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"
DEFAULT_CSV = SAMPLES_DIR / "vitals_demo.csv"


def load_sample_csv(path: Path | None = None) -> pd.DataFrame:
    p = path or DEFAULT_CSV
    if not p.exists():
        return generate_series(n=120, seed=42, inject_anomaly=False)
    df = pd.read_csv(p)
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    return df


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

    if inject_anomaly:
        if anomaly_type == "tachycardia":
            hr[-8:] = rng.uniform(148, 165, size=8)
        elif anomaly_type == "bradycardia":
            hr[-8:] = rng.uniform(32, 40, size=8)
        elif anomaly_type == "hypoxia":
            spo2[-8:] = rng.uniform(82, 88, size=8)

    return pd.DataFrame(
        {
            "ts": base,
            "heart_rate": np.round(hr, 1),
            "spo2": np.round(spo2, 1),
        }
    )

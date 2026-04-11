"""数据校验与审计：输入验证、合规性检查与操作审计日志。"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_profile(
    *,
    height_cm: float | None,
    weight_kg: float | None,
    age: int | None,
    sex: str | None,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    if height_cm is not None:
        if height_cm < 50 or height_cm > 250:
            errors.append(f"身高 {height_cm} cm 超出合理范围（50-250）")
    if weight_kg is not None:
        if weight_kg < 20 or weight_kg > 300:
            errors.append(f"体重 {weight_kg} kg 超出合理范围（20-300）")
    if age is not None:
        if age < 1 or age > 150:
            errors.append(f"年龄 {age} 超出合理范围（1-150）")
        elif age < 14:
            warnings.append("本系统面向成年人群设计，未成年人建议参考分析需谨慎")
    if sex is not None and sex not in ("男", "女", "其他"):
        errors.append(f"性别 '{sex}' 不在有效选项内")
    return ValidationResult(ok=len(errors) == 0, errors=errors, warnings=warnings)


def validate_vitals_self_report(
    *,
    body_temp_c: float | None,
    bp_systolic: int | None,
    bp_diastolic: int | None,
    blood_glucose_mmol: float | None,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    if body_temp_c is not None and body_temp_c > 0:
        if body_temp_c < 34.0 or body_temp_c > 42.5:
            errors.append(f"体温 {body_temp_c}℃ 超出合理范围（34.0-42.5）")
        elif body_temp_c >= 38.5:
            warnings.append(f"体温 {body_temp_c}℃ 偏高，建议关注")
    if bp_systolic is not None and bp_systolic > 0:
        if bp_systolic < 60 or bp_systolic > 280:
            errors.append(f"收缩压 {bp_systolic} mmHg 超出合理范围")
        elif bp_systolic >= 180:
            warnings.append("收缩压 ≥180 mmHg，建议尽快就医复核")
    if bp_diastolic is not None and bp_diastolic > 0:
        if bp_diastolic < 30 or bp_diastolic > 180:
            errors.append(f"舒张压 {bp_diastolic} mmHg 超出合理范围")
        elif bp_diastolic >= 110:
            warnings.append("舒张压 ≥110 mmHg，建议尽快就医复核")
    if bp_systolic and bp_diastolic and bp_systolic > 0 and bp_diastolic > 0:
        if bp_systolic <= bp_diastolic:
            errors.append("收缩压应高于舒张压，请复核测量值")
    if blood_glucose_mmol is not None and blood_glucose_mmol > 0:
        if blood_glucose_mmol < 1.0 or blood_glucose_mmol > 35.0:
            errors.append(f"血糖 {blood_glucose_mmol} mmol/L 超出合理范围")
        elif blood_glucose_mmol >= 16.7:
            warnings.append("血糖显著偏高（≥16.7），建议紧急就医")
        elif blood_glucose_mmol < 3.0:
            warnings.append("血糖偏低（<3.0），请注意低血糖风险")
    return ValidationResult(ok=len(errors) == 0, errors=errors, warnings=warnings)


def init_audit_log(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            module TEXT NOT NULL,
            detail_json TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def write_audit(
    conn: sqlite3.Connection,
    *,
    action: str,
    module: str,
    detail: dict[str, Any] | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conn.execute(
        "INSERT INTO audit_log (action, module, detail_json, created_at) VALUES (?, ?, ?, ?)",
        (action, module, json.dumps(detail or {}, ensure_ascii=False), now),
    )
    conn.commit()


def list_audit_logs(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, action, module, detail_json, created_at FROM audit_log ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["detail"] = json.loads(d.pop("detail_json"))
        except (json.JSONDecodeError, KeyError):
            d["detail"] = {}
        out.append(d)
    return out


def audit_log_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()
    return int(row[0]) if row else 0

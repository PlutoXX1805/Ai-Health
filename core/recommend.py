"""参考摄入与代谢估算：供大模型对齐数量级（非医疗处方）。"""

from __future__ import annotations

from typing import Any


def bmr_mifflin_st_jeor(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    s = sex.strip()
    if s == "男":
        adj = 5.0
    elif s == "女":
        adj = -161.0
    else:
        adj = -78.0
    return 10.0 * weight_kg + 6.25 * height_cm - 5.0 * float(age) + adj


def activity_factor(level: str) -> float:
    return {
        "久坐少动": 1.2,
        "轻度活动": 1.375,
        "中度活动": 1.55,
        "偏高强度": 1.65,
        "很高强度": 1.725,
    }.get(level, 1.2)


def step_adjustment(steps: int) -> float:
    """根据昨日步数对消耗微调系数（演示用）。"""
    if steps < 3000:
        return -0.04
    if steps < 7000:
        return 0.0
    if steps < 12000:
        return 0.03
    return 0.06


def compute_reference_bundle(
    *,
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    activity_level: str,
    yesterday_steps: int,
) -> dict[str, Any]:
    bmr = bmr_mifflin_st_jeor(weight_kg, height_cm, age, sex)
    tdee = bmr * activity_factor(activity_level)
    adj = step_adjustment(yesterday_steps)
    target_kcal = max(1200.0, round(tdee * (1.0 + adj), 0))
    protein_g = round(1.2 * weight_kg, 1)
    fat_g = round(0.8 * weight_kg, 1)
    carb_kcal = max(target_kcal - protein_g * 4 - fat_g * 9, 0)
    carb_g = round(carb_kcal / 4, 1)
    return {
        "bmr_kcal_per_day_estimate": round(bmr, 0),
        "tdee_kcal_per_day_estimate": round(tdee, 0),
        "suggested_intake_kcal_next_day_estimate": target_kcal,
        "macro_grams_suggestion_estimate": {
            "protein_g": protein_g,
            "fat_g": fat_g,
            "carbohydrate_g": carb_g,
        },
        "note": "以上为公式估算，仅供生活方式参考，不构成诊疗或营养处方。",
    }

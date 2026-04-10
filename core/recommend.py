"""多维推荐：BMR/TDEE 估算 + 宏量营养素建议（演示级）。"""

from __future__ import annotations

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
        "高强度": 1.725,
    }.get(level, 1.2)


def build_daily_plan(
    *,
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    activity_level: str,
    diet_pref: str,
    steps_level: str,
) -> str:
    bmr = bmr_mifflin_st_jeor(weight_kg, height_cm, age, sex)
    tdee = bmr * activity_factor(activity_level)
    # 步数等级微调
    step_adj = {"低": -0.03, "中": 0.0, "高": 0.05}.get(steps_level, 0.0)
    target_kcal = max(1200.0, tdee * (1.0 + step_adj))

    protein_g = round(1.2 * weight_kg, 1)
    fat_g = round(0.8 * weight_kg, 1)
    carb_kcal = max(target_kcal - protein_g * 4 - fat_g * 9, 0)
    carb_g = round(carb_kcal / 4, 1)

    lines = [
        f"- 估算基础代谢 BMR：约 {bmr:.0f} kcal/日",
        f"- 结合活动系数后总消耗约 {tdee:.0f} kcal/日；本计划目标摄入约 {target_kcal:.0f} kcal/日（演示用）",
        f"- 蛋白质约 {protein_g} g，脂肪约 {fat_g} g，碳水化合物约 {carb_g} g",
        f"- 饮食偏好备注：{diet_pref or '无'}",
        f"- 活动与步数：{activity_level}；今日步数等级：{steps_level}",
        "- 运动建议：中等强度有氧 20–40 分钟/日或拆分为多次快走（非医疗处方）",
    ]
    return "\n".join(lines)

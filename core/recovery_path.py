"""根据档案病史、检验异常与「明日规划」病情自报，生成专科化康复阶段时间线（科普级）。"""

from __future__ import annotations

from typing import Any


def _lab_abnormal_codes(flags: list[dict[str, Any]]) -> set[str]:
    return {f.get("code") for f in flags if f.get("status") in ("偏高", "偏低") and f.get("code")}


def medical_history_is_meaningful(note: str) -> bool:
    """是否视为「有登记病情」：足够长的病史摘要或含常见慢病/术后关键词。"""
    t = (note or "").strip()
    if len(t) < 10:
        return False
    keys = (
        "高血压",
        "糖尿病",
        "血糖",
        "冠心病",
        "心衰",
        "房颤",
        "脑卒中",
        "卒中",
        "脑梗",
        "血脂",
        "胆固醇",
        "甘油三酯",
        "LDL",
        "术后",
        "手术",
        "康复",
        "慢阻肺",
        "COPD",
        "哮喘",
        "甲状腺",
        "肾病",
        "透析",
        "肿瘤",
        "癌",
        "服药",
        "用药",
        "处方",
        "诊断",
        "慢性病",
    )
    return any(k in t for k in keys)


def has_clinical_context(medical_note: str, lab_codes_abnormal: set[str]) -> bool:
    if medical_history_is_meaningful(medical_note):
        return True
    if lab_codes_abnormal & {"GLU", "TC", "TG", "LDL", "ALT", "AST", "CREA"}:
        return True
    return False


def _axis_from_note_and_lab(note: str, lab_abnormal: set[str]) -> str:
    """单主轨优先：术后 > 糖尿病相关 > 高血压 > 血脂，否则慢病综合管理。"""
    n = note or ""
    if any(x in n for x in ("术后", "手术", "切除", "缝合", "住院术")):
        return "postoperative"
    if "糖尿病" in n or "血糖" in n or "2型" in n or "1型" in n or "GLU" in lab_abnormal:
        return "diabetes"
    if "高血压" in n or "血压" in n:
        return "hypertension"
    if any(x in n for x in ("血脂", "胆固醇", "甘油三酯", "LDL", "HDL")) or (
        lab_abnormal & {"TC", "TG", "LDL", "HDL"}
    ):
        return "dyslipidemia"
    if medical_history_is_meaningful(note):
        return "general_chronic"
    if lab_abnormal:
        return "general_chronic"
    return "healthy"


def _daily_signals(d: dict[str, Any]) -> dict[str, Any]:
    """从昨日/当日病情自报解析数值信号。"""
    temp = d.get("body_temp_c")
    try:
        tval = float(temp) if temp is not None and temp != "" else None
    except (TypeError, ValueError):
        tval = None
    fever = tval is not None and tval >= 37.3

    g = d.get("blood_glucose_mmol")
    try:
        gval = float(g) if g is not None and g != "" else None
    except (TypeError, ValueError):
        gval = None
    hypergly = gval is not None and gval >= 11.1

    sbp = d.get("bp_systolic")
    dbp = d.get("bp_diastolic")
    try:
        sbp_v = int(float(sbp)) if sbp is not None and sbp != "" else None
    except (TypeError, ValueError):
        sbp_v = None
    try:
        dbp_v = int(float(dbp)) if dbp is not None and dbp != "" else None
    except (TypeError, ValueError):
        dbp_v = None
    bp_high = sbp_v is not None and sbp_v >= 160

    return {"fever": fever, "hypergly": hypergly, "bp_high": bp_high, "tval": tval, "gval": gval}


def _nodes_healthy() -> list[dict[str, Any]]:
    return [
        {
            "title": "当前健康状态",
            "short": "健康",
            "summary": "未识别到已登记的慢性病、术后状态或检验异常；按现有信息理解为一般健康管理人群。",
            "advice": [
                "您未在「智能档案」中填写可解析的病情摘要，且近期检验摘要无明确异常项时，系统按「当前健康」展示。",
                "若有确诊疾病（如高血压、糖尿病、术后恢复等），请在「智能档案」病史中补充；并在「明日规划」的「病情自报」中填写体温、血压、血糖等，以便总览切换为针对性康复阶段分析。",
                "任何新发或持续症状仍建议线下就医评估，本应用不替代诊疗。",
            ],
        }
    ]


def _nodes_hypertension(note: str, daily: dict[str, Any], sig: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [
        {
            "title": "家庭与诊室血压监测规范化",
            "short": "血压监测",
            "summary": "HBPM/规范测量与记录，为降压目标与随访提供依据（目标值个体化，以医嘱为准）。",
            "advice": [
                "建议固定时间、坐位休息后测量，记录收缩压/舒张压与测量情境（晨起、服药前后等）。",
                "若自述血压持续 ≥160/100 mmHg 或伴胸痛、意识改变等，应按急诊指征就医，而非仅依赖应用记录。",
            ],
        },
        {
            "title": "治疗性生活方式干预（TLC）",
            "short": "TLC",
            "summary": "限盐、DASH 型膳食模式、体重与饮酒管理，为降压药的疗效打基础。",
            "advice": [
                "钠摄入与体重控制对容量负荷型高血压尤为关键；与档案饮食偏好结合执行更易坚持。",
                "有氧运动需结合血压波动与心血管风险分层，具体强度以康复/心内科指导为准。",
            ],
        },
        {
            "title": "降压治疗依从与不良反应监测",
            "short": "用药依从",
            "summary": "坚持处方方案并识别低血压、干咳、电解质异常等信号，复诊时反馈医生。",
            "advice": [
                "勿自行停药或加倍剂量；漏服处理应遵循药品说明书或药师/医生建议。",
                "合并糖尿病或肾病时，部分药物选择需专科调整，请在档案中写明合并症。",
            ],
        },
        {
            "title": "靶器官保护与并发症筛查",
            "short": "靶器官",
            "summary": "长期高血压关注心、脑、肾、眼底等靶器官损害筛查时间表（科普级提醒）。",
            "advice": [
                "规律随访血脂、血糖、肾功能与尿蛋白等，与血压控制联合评估整体心血管风险。",
                "出现视物模糊、下肢水肿、活动耐量明显下降等应及时就诊。",
            ],
        },
    ]
    if sig.get("bp_high"):
        nodes[0]["advice"].insert(
            0,
            "您在「病情自报」中填写了较高收缩压读数：请优先排除测量误差并尽快联系医生评估，而非自行调药。",
        )
    if sig.get("fever"):
        nodes.insert(
            1,
            {
                "title": "发热对血压与容量状态的影响（鉴别）",
                "short": "发热相关",
                "summary": "感染或发热期可影响血压与心率，需与降压治疗相互作用区分。",
                "advice": [
                    "体温升高时建议增加水分与休息，监测血压波动；持续发热或伴呼吸道/泌尿道症状应就医明确病因。",
                    "本应用仅记录自报体温，不做感染或病因判断。",
                ],
            },
        )
    return nodes


def _nodes_diabetes(note: str, daily: dict[str, Any], sig: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [
        {
            "title": "医学营养治疗（MNT）与碳水化合物管理",
            "short": "MNT",
            "summary": "个体化能量与碳水分布，配合血糖自我监测模式（SMBG/CGM 概念，科普）。",
            "advice": [
                "关注进餐顺序、低升糖指数主食与膳食纤维；与档案饮食忌口一并执行。",
                "空腹与餐后血糖目标由医生根据病程与并发症设定，请勿仅凭单次读数调整胰岛素或口服药。",
            ],
        },
        {
            "title": "运动处方与低血糖风险管理",
            "short": "运动与低血糖",
            "summary": "有氧与抗阻训练改善胰岛素敏感性，需防范运动中及延迟性低血糖。",
            "advice": [
                "使用胰岛素或磺脲类药物者，运动前后注意加餐与血糖监测；出现心悸、出汗、饥饿感应立即测糖并处理。",
                "合并增殖性视网膜病变等时，剧烈运动需专科评估禁忌。",
            ],
        },
        {
            "title": "急性高血糖状态识别（科普）",
            "short": "急性代谢",
            "summary": "了解高血糖危象的警示表现，明确「需急诊」与「需门诊」的界限（科普，非诊断）。",
            "advice": [
                "明显口渴、多尿、乏力伴恶心呕吐、呼吸深快或意识改变时，应立即就医，不要等待应用分析。",
                "您在自报中若填写随机血糖显著升高，请同日复测并联系内分泌或急诊通路。",
            ],
        },
        {
            "title": "慢性并发症筛查节奏",
            "short": "并发症",
            "summary": "糖尿病肾病、视网膜病变、神经病变与外周血管病的随访窗口（概念性提醒）。",
            "advice": [
                "每年眼底与尿微量白蛋白等检查需按医嘱落实；与血脂、血压综合管理降低 ASCVD 风险。",
                "足部日常检查与鞋袜选择对预防溃疡很重要。",
            ],
        },
    ]
    if sig.get("hypergly"):
        nodes[2]["advice"].insert(
            0,
            f"本次自报血糖读数偏高（约 {sig.get('gval')} mmol/L）：建议尽快复测并联系医生，排除测量误差与急性诱因。",
        )
    if sig.get("fever"):
        nodes.insert(
            2,
            {
                "title": "感染/发热期的血糖波动管理",
                "short": "感染期血糖",
                "summary": "应激与感染可致胰岛素抵抗加重，血糖波动增大，需加强监测与液体摄入。",
                "advice": [
                    "发热期间按医嘱调整降糖方案，勿自行大幅增减胰岛素。",
                    "若食欲差仍使用胰岛素/促泌剂，需警惕低血糖。",
                ],
            },
        )
    return nodes


def _nodes_postoperative(note: str, daily: dict[str, Any], sig: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [
        {
            "title": "围手术期早期：生命体征与创面/引流观察",
            "short": "围术期",
            "summary": "术后早期关注体温曲线、切口渗液、疼痛评分与活动耐量（以手术团队宣教为准）。",
            "advice": [
                "发热、切口红肿渗液增多或突发剧痛需联系手术团队或急诊，而非仅依赖本应用记录。",
                "在「病情自报」中填写体温与血压有助于您自己观察趋势，不能替代病房监护。",
            ],
        },
        {
            "title": "炎症反应期管理与感染征象鉴别",
            "short": "炎症期",
            "summary": "术后可控的炎症反应与临床感染的区分思路（科普）。",
            "advice": [
                "体温单峰与持续高热、寒战、脓性分泌物等提示需医疗评估。",
                "遵医嘱使用抗生素，勿自行停药或延长疗程。",
            ],
        },
        {
            "title": "渐进性活动负荷与功能康复",
            "short": "渐进负荷",
            "summary": "在无痛或可耐受疼痛范围内逐步恢复步行与日常生活活动（ADL）。",
            "advice": [
                "不同术式有差异：骨科、胸腹腔手术需严格遵循康复处方与复查影像时机。",
                "明日规划中的步数与有氧记录可帮助您与康复师复盘进度。",
            ],
        },
        {
            "title": "出院后随访与并发症预防",
            "short": "随访",
            "summary": "拆线/复查、血栓预防停药时机、营养与用药调整等按随访计划执行。",
            "advice": [
                "合并高血压、糖尿病者，围术期血糖血压波动常见，需内外科协同管理。",
                "档案中写明手术名称与日期（脱敏）有助于本应用提示更贴合的复节点。",
            ],
        },
    ]
    if sig.get("fever"):
        nodes[0]["advice"].insert(
            0,
            "自报体温升高：术后 48h 内低热可能与术后吸收热相关，持续高热或伴寒战需尽快联系手术团队。",
        )
    return nodes


def _nodes_dyslipidemia(note: str, daily: dict[str, Any], sig: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "title": "血脂谱解读与治疗目标分层",
            "short": "血脂目标",
            "summary": "依据 ASCVD 危险分层设定 LDL-C 等目标（以最新指南与医生判断为准）。",
            "advice": [
                "检验摘要中的 TC、TG、LDL、HDL 需结合血压、血糖、吸烟史等综合评估风险。",
                "生活方式干预与他汀等药物治疗需遵医嘱，定期复查肝功能与肌酶（按处方要求）。",
            ],
        },
        {
            "title": "膳食模式与运动对脂质谱的影响",
            "short": "生活方式",
            "summary": "减少反式脂肪与精制糖，增加 ω-3 与可溶性纤维；规律有氧改善 TG。",
            "advice": [
                "减重 5–10% 常显著改善 TG 与 HDL；与明日规划运动记录联动观察。",
            ],
        },
        {
            "title": "药物疗效监测与不耐受处理",
            "short": "药物监测",
            "summary": "他汀肌痛、肝酶升高等不良反应的识别与就医时机。",
            "advice": [
                "出现持续肌痛、尿色加深等应停药并就医，勿自行替换品种或剂量。",
            ],
        },
        {
            "title": "复查与 ASCVD 风险再评估",
            "short": "再评估",
            "summary": "治疗 6–12 周后复查脂质谱，必要时调整方案。",
            "advice": [
                "上传新的检验摘要后，总览营养维度会参考异常方向；仍不能替代医生调药。",
            ],
        },
    ]


def _nodes_general_chronic(note: str, daily: dict[str, Any], sig: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "title": "慢病基线评估与个体化分层",
            "short": "基线评估",
            "summary": "在明确诊断与用药前提下，整理血压、血糖、体重等可量化指标作为自我管理基线。",
            "advice": [
                "请在档案中尽量写明疾病名称、主要用药与最近复查时间，便于模块给出更贴近的科普节点。",
                "「病情自报」中的体温、血压、血糖可帮助观察急性波动。",
            ],
        },
        {
            "title": "生活方式与依从性一体化管理",
            "short": "生活方式",
            "summary": "饮食、运动、睡眠与压力管理对多数慢病共有获益。",
            "advice": [
                "使用明日规划将目标拆成可执行日计划，并与昨日回顾闭环。",
            ],
        },
        {
            "title": "急性加重征象与就医指征（科普）",
            "short": "急性征象",
            "summary": "识别需尽快线下评估的红旗症状，而非依赖应用判断危重。",
            "advice": [
                "胸痛、呼吸困难、意识障碍、肢体无力、持续高热等请直接就医或拨打急救电话。",
            ],
        },
        {
            "title": "规律随访与方案再评估",
            "short": "随访",
            "summary": "按专科节奏复查化验与靶器官评估，避免长期不复查。",
            "advice": [
                "检验摘要上传后，可与体征时序、病情自报一并用于自我复盘（非自动诊疗）。",
            ],
        },
    ]


def _nodes_mixed_metabolic(note: str, daily: dict[str, Any], sig: dict[str, Any]) -> list[dict[str, Any]]:
    """高血压合并糖尿病或血脂异常时的多病共存轨。"""
    nodes = [
        {
            "title": "代谢综合征背景下的综合风险评估",
            "short": "综合风险",
            "summary": "血压、血糖与血脂相互影响，需一体化设定生活方式与药物目标（以医嘱为准）。",
            "advice": [
                "优先记录家庭血压与空腹/餐后血糖模式，避免只看单次门诊点值。",
                "档案中写明主要诊断与用药，有助于各模块引用一致。",
            ],
        },
        {
            "title": "营养与运动的一体化处方（MNT+运动）",
            "short": "营养运动",
            "summary": "限盐与碳水管理并行，运动强度需兼顾血压反应与低血糖风险。",
            "advice": [
                "减重同时改善血压、血糖与 TG；明日规划可跟踪步数与有氧时长。",
            ],
        },
        {
            "title": "多药共用时的依从性与相互作用关注",
            "short": "用药安全",
            "summary": "降压药、降糖药与降脂药联用时，注意低血压、低血糖与肾功能影响（科普）。",
            "advice": [
                "任何调药须由医生或药师指导；自报症状变化时携带完整用药清单就诊。",
            ],
        },
        {
            "title": "靶器官保护与并发症筛查",
            "short": "靶器官",
            "summary": "心、肾、眼、神经与外周血管的综合随访思路。",
            "advice": [
                "糖尿病合并高血压时，尿微量白蛋白与眼底检查尤为重要。",
            ],
        },
    ]
    if sig.get("hypergly") or sig.get("bp_high") or sig.get("fever"):
        nodes.insert(
            2,
            {
                "title": "当前自报指标异常的即时处理建议",
                "short": "指标复核",
                "summary": "对自报体温、血压或血糖明显异常时，优先复测与联系医生。",
                "advice": [
                    "排除测量误差（袖带、空腹定义、体温计校准等）后仍异常，请当日就医或致电门诊。",
                ],
            },
        )
    return nodes


def daily_log_has_self_report(d: dict[str, Any]) -> bool:
    """是否包含昨日回顾或病情自报的有效内容（用于阶段推进判断）。"""
    if not d:
        return False
    if d.get("steps") is not None and int(d.get("steps") or 0) > 0:
        return True
    t = d.get("body_temp_c")
    try:
        if t is not None and float(t) > 34:
            return True
    except (TypeError, ValueError):
        pass
    try:
        if int(d.get("bp_systolic") or 0) > 0 or int(d.get("bp_diastolic") or 0) > 0:
            return True
    except (TypeError, ValueError):
        pass
    g = d.get("blood_glucose_mmol")
    try:
        if g is not None and float(g) > 0:
            return True
    except (TypeError, ValueError):
        pass
    if (d.get("condition_body") or "").strip():
        return True
    if (d.get("symptoms") or "").strip():
        return True
    return False


def choose_current_index(
    n_nodes: int,
    *,
    has_daily: bool,
    has_lab: bool,
    concern: bool,
    sig: dict[str, Any],
) -> int:
    if n_nodes <= 0:
        return 0
    if n_nodes == 1:
        return 0
    # 优先突出「需要关注」的节点
    if sig.get("fever"):
        return min(1, n_nodes - 1)
    if sig.get("hypergly") or sig.get("bp_high"):
        return min(2, n_nodes - 1)
    if concern:
        return min(max(1, n_nodes // 2), n_nodes - 1)
    if not has_daily:
        return min(1, n_nodes - 1)
    if not has_lab:
        return min(n_nodes - 2, n_nodes - 1)
    return n_nodes - 1


def build_recovery_nodes(
    *,
    medical_note: str,
    latest_daily: dict[str, Any] | None,
    lab_flags: list[dict[str, Any]],
    has_lab_report: bool,
) -> tuple[list[dict[str, Any]], int, str]:
    """
    返回 (nodes, current_index, axis_key)。
    axis_key: healthy | hypertension | diabetes | postoperative | dyslipidemia | mixed | general_chronic
    """
    note = medical_note or ""
    d = {k: v for k, v in (latest_daily or {}).items() if not str(k).startswith("_")}
    lab_ab = _lab_abnormal_codes(lab_flags)
    sig = _daily_signals(d)

    if not has_clinical_context(note, lab_ab):
        nodes = _nodes_healthy()
        return nodes, 0, "healthy"

    axis = _axis_from_note_and_lab(note, lab_ab)
    htn = "高血压" in note or "血压" in note
    dm = "糖尿病" in note or "血糖" in note or "GLU" in lab_ab

    if axis == "postoperative":
        nodes = _nodes_postoperative(note, d, sig)
    elif axis == "diabetes":
        if htn:
            nodes = _nodes_mixed_metabolic(note, d, sig)
            axis = "mixed"
        else:
            nodes = _nodes_diabetes(note, d, sig)
    elif axis == "hypertension":
        if dm or "GLU" in lab_ab:
            nodes = _nodes_mixed_metabolic(note, d, sig)
            axis = "mixed"
        else:
            nodes = _nodes_hypertension(note, d, sig)
    elif axis == "dyslipidemia":
        if htn and dm:
            nodes = _nodes_mixed_metabolic(note, d, sig)
            axis = "mixed"
        else:
            nodes = _nodes_dyslipidemia(note, d, sig)
    else:
        nodes = _nodes_general_chronic(note, d, sig)
        axis = "general_chronic"

    concern = any(
        x in (d.get("symptoms") or "") + (d.get("condition_body") or "")
        for x in ("痛", "晕", "闷", "呼吸困难", "咯血", "意识", "抽搐", "血", "肿", "热", "烧")
    )
    has_self = daily_log_has_self_report(d)
    ci = choose_current_index(
        len(nodes),
        has_daily=has_self,
        has_lab=has_lab_report,
        concern=concern,
        sig=sig,
    )
    ci = max(0, min(ci, len(nodes) - 1))

    for i, node in enumerate(nodes):
        if i < ci:
            node["status"] = "past"
        elif i == ci:
            node["status"] = "current"
        else:
            node["status"] = "future"

    return nodes, ci, axis

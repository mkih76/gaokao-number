"""
学习路径生成引擎
基于诊断结果生成个性化学习路径（14天/21天/60天）
"""
import json
from typing import Optional
from src.question_db import QuestionDB


# 题型学习顺序（按优先级内置）
DEFAULT_PATH_21DAYS = [
    # 第1周：P0基础（和差倍比、工程、行程）
    {"day": 1,  "topics": ["和差倍比-基础方程", "工程问题-赋值法"], "difficulty": 1, "types": ["hecha-beibi", "gongcheng"]},
    {"day": 2,  "topics": ["和差倍比-比例法", "工程问题-效率关系"], "difficulty": 1, "types": ["hecha-beibi", "gongcheng"]},
    {"day": 3,  "topics": ["行程问题-基本公式", "行程问题-相遇追及"], "difficulty": 2, "types": ["xingcheng"]},
    {"day": 4,  "topics": ["和差倍比-综合练习", "错题复刷①"], "difficulty": 2, "types": ["hecha-beibi"]},
    {"day": 5,  "topics": ["行程问题-流水行船", "行程问题-比例行程"], "difficulty": 2, "types": ["xingcheng"]},
    {"day": 6,  "topics": ["P0题型综合模考①"], "difficulty": 2, "types": ["hecha-beibi", "gongcheng", "xingcheng"]},
    {"day": 7,  "topics": ["阶段复盘① + 错题复刷②"], "difficulty": 2},
    # 第2周：P1中档（排列组合、概率、几何、经济利润）
    {"day": 8,  "topics": ["排列组合-加法乘法原理", "排列组合-捆绑插空"], "difficulty": 3, "types": ["pailie-zuhe"]},
    {"day": 9,  "topics": ["概率问题-古典概型", "概率问题-条件概率"], "difficulty": 3, "types": ["gailv"]},
    {"day": 10, "topics": ["几何问题-基本公式", "几何问题-阴影面积"], "difficulty": 3, "types": ["jihe"]},
    {"day": 11, "topics": ["经济利润-成本定价", "经济利润-利润率"], "difficulty": 3, "types": ["jingji-lirun"]},
    {"day": 12, "topics": ["P1题型综合练习 + 错题复刷③"], "difficulty": 3, "types": ["pailie-zuhe", "gailv", "jihe", "jingji-lirun"]},
    {"day": 13, "topics": ["P0+P1综合模考②"], "difficulty": 3},
    {"day": 14, "topics": ["阶段复盘② + 错题复刷④"], "difficulty": 3},
    # 第3周：P2/P3 + 全真模拟
    {"day": 15, "topics": ["溶液问题-十字交叉法", "容斥原理-文氏图"], "difficulty": 3, "types": ["rongye", "rongchi"]},
    {"day": 16, "topics": ["日期年龄问题", "和定极值问题"], "difficulty": 3, "types": ["riqi-nianling", "heding-jizhi"]},
    {"day": 17, "topics": ["抽屉原理", "鸡兔同笼"], "difficulty": 4, "types": ["chouti", "jitu-tonglong"]},
    {"day": 18, "topics": ["全套题型模考③ + 时间控制训练", "难题取舍策略"], "difficulty": 4},
    {"day": 19, "topics": ["全真模拟④ + 错题复刷⑤"], "difficulty": 4},
    {"day": 20, "topics": ["考前冲刺-高频考点回顾", "考场时间分配策略"], "difficulty": 4},
    {"day": 21, "topics": ["毕业模考⑤ + 最终报告"], "difficulty": 4},
]

# 60天版：每类题型学3-5天，穿插更多练习
# 14天版：仅保留P0+P1题型，快速突击


def generate_path(diagnosis: dict, plan_type: str = "21days") -> list[dict]:
    """生成个性化学习路径

    Args:
        diagnosis: run_diagnosis() 的输出
        plan_type: 学习计划类型（14days/21days/60days）

    Returns:
        学习路径 [{day, topics, difficulty, types, status}]
    """
    # 选择模板
    if plan_type == "21days":
        template = DEFAULT_PATH_21DAYS
    elif plan_type == "14days":
        # 只保留前14天的P0+P1
        template = [d for d in DEFAULT_PATH_21DAYS if d["day"] <= 14]
    elif plan_type == "60days":
        # 扩展每个主题的学习天数
        template = _expand_to_60days()
    else:
        template = DEFAULT_PATH_21DAYS

    # 个性化调整：薄弱题型提前、多安排
    priority_list = diagnosis.get("priority", [])
    weak_types = [p["type"] for p in priority_list if p["urgency"] == "high"]

    path = []
    for day_plan in template:
        entry = dict(day_plan)
        entry["status"] = "pending"
        path.append(entry)

    # 如果用户有薄弱点，在路径中插入额外复习日
    if weak_types and len(path) > 10:
        insert_days = [4, 10, 16]
        for i, ins_day in enumerate(insert_days):
            if ins_day < len(path):
                review_entry = {
                    "day": path[ins_day]["day"],
                    "topics": [f"薄弱题型专攻：{t}" for t in weak_types[:2]],
                    "difficulty": 3,
                    "types": weak_types[:2],
                    "status": "pending",
                    "is_review": True,
                }
                # 在review日并入已有内容
                existing = path[ins_day]["topics"]
                path[ins_day]["topics"] = existing + review_entry["topics"]
                path[ins_day]["types"] = list(set(path[ins_day].get("types", []) + weak_types[:2]))

    return path


def get_day_tasks(path: list[dict], day: int) -> Optional[dict]:
    """获取某天的任务"""
    for entry in path:
        if entry["day"] == day:
            return entry
    return None


def _expand_to_60days() -> list[dict]:
    """60天路径：每个题型5天，穿插复习和模考，约60天"""
    expanded = []
    day = 1
    # P0题型各6天
    for base in ["hecha-beibi", "gongcheng", "xingcheng"]:
        name = QuestionDB.TYPE_NAMES.get(base, base)
        diff_levels = {"入门": 1, "基础": 1, "进阶": 2, "综合练习①": 2, "综合练习②": 3, "模考查漏": 3}
        for sub in ["入门", "基础", "进阶", "综合练习①", "综合练习②", "模考查漏"]:
            expanded.append({
                "day": day, "topics": [f"{name}-{sub}"],
                "difficulty": diff_levels.get(sub, 1), "types": [base], "status": "pending"
            })
            day += 1
    # P1题型各4天
    for base in ["pailie-zuhe", "gailv", "jihe", "jingji-lirun"]:
        name = QuestionDB.TYPE_NAMES.get(base, base)
        for sub in ["基础", "进阶", "综合", "阶段测试"]:
            expanded.append({
                "day": day, "topics": [f"{name}-{sub}"],
                "difficulty": 3, "types": [base], "status": "pending"
            })
            day += 1
    # P2题型各3天
    for base in ["rongye", "rongchi", "riqi-nianling"]:
        name = QuestionDB.TYPE_NAMES.get(base, base)
        for sub in ["基础", "进阶", "综合练习"]:
            expanded.append({
                "day": day, "topics": [f"{name}-{sub}"],
                "difficulty": 3, "types": [base], "status": "pending"
            })
            day += 1
    # P3题型各2天
    for base in ["chouti", "jitu-tonglong", "heding-jizhi"]:
        name = QuestionDB.TYPE_NAMES.get(base, base)
        for sub in ["基础", "综合练习"]:
            expanded.append({
                "day": day, "topics": [f"{name}-{sub}"],
                "difficulty": 4, "types": [base], "status": "pending"
            })
            day += 1
    # 最后14天全真模拟
    for i in range(1, 15):
        expanded.append({
            "day": day, "topics": [f"全真模考#{i}", "错题复盘"],
            "difficulty": 5, "types": [], "status": "pending"
        })
        day += 1
    return expanded

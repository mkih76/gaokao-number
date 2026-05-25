"""
薄弱点诊断引擎
接收15道诊断题的用户答案，输出薄弱点雷达图 + 建议
"""
import json
from typing import Optional
from src.question_db import QuestionDB


def run_diagnosis(user_answers: dict[str, str], db: QuestionDB) -> dict:
    """执行诊断分析

    Args:
        user_answers: 用户答案 {"q01": "A", "q02": "C", ...}
        db: 题库引擎实例

    Returns:
        诊断报告（薄弱点雷达 + 优先级排序 + 建议方案）
    """
    # 收集每题的实际情况
    detail = {}
    type_stats = {}  # question_type -> {"correct": 0, "total": 0}

    for qid, user_choice in user_answers.items():
        try:
            q = db.get_by_id(qid)
        except Exception:
            detail[qid] = 0
            continue

        # 每题每题得分
        is_correct = 1 if user_choice.upper() == q["answer"].upper() else 0
        detail[qid] = is_correct

        # 按题型统计
        qtype = q["question_type"]
        if qtype not in type_stats:
            type_stats[qtype] = {"correct": 0, "total": 0}
        type_stats[qtype]["total"] += 1
        if is_correct:
            type_stats[qtype]["correct"] += 1

    # 生成薄弱点
    weak_points = {}
    for qtype, stats in type_stats.items():
        rate = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        if rate >= 0.8:
            level = "strong"
        elif rate >= 0.5:
            level = "medium"
        else:
            level = "weak"
        weak_points[qtype] = {
            "correct": stats["correct"],
            "total": stats["total"],
            "rate": round(rate, 2),
            "level": level,
            "name": db.TYPE_NAMES.get(qtype, qtype),
        }

    # 总得分
    score = sum(detail.values())

    # 按薄弱程度排序
    priority = sorted(
        weak_points.items(),
        key=lambda x: (x[1]["rate"], db.PRIORITY.get(x[0], "P9"))
    )

    # 生成文字总结
    weak_list = [p[1]["name"] for p in priority if p[1]["level"] == "weak"]
    medium_list = [p[1]["name"] for p in priority if p[1]["level"] == "medium"]

    summary_parts = []
    if weak_list:
        summary_parts.append(f"需要重点攻克：{'、'.join(weak_list[:3])}")
    if medium_list:
        summary_parts.append(f"需要巩固：{'、'.join(medium_list[:3])}")

    summary = "、".join(summary_parts) if summary_parts else "基础不错，继续保持！"

    # 推荐学习计划
    weak_count = sum(1 for p in priority if p[1]["level"] == "weak")
    if score <= 5 or weak_count >= 4:
        recommended_plan = "60days"
    elif score <= 10:
        recommended_plan = "21days"
    else:
        recommended_plan = "14days"

    priority_list = [
        {
            "type": p[0],
            "name": p[1]["name"],
            "rate": p[1]["rate"],
            "urgency": "high" if p[1]["level"] == "weak" else ("medium" if p[1]["level"] == "medium" else "low"),
            "reason": f"{p[1]['rate']*100:.0f}%正确率" if p[1]["level"] != "strong" else "已掌握",
        }
        for p in priority
    ]

    return {
        "score": score,
        "total": len(user_answers),
        "detail": detail,
        "weak_points": weak_points,
        "summary": summary,
        "priority": priority_list,
        "recommended_plan": recommended_plan,
    }

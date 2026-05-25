"""
督学定时任务模块
生成每日任务推送、模考、周报等内容
"""
import random
import datetime
from typing import Optional
from src.question_db import QuestionDB
from src.path_planner import get_day_tasks


def generate_daily_tasks(user: dict, path: list[dict], db: QuestionDB) -> str:
    """生成当日学习任务推送文本

    Args:
        user: 用户数据
        path: 学习路径
        db: 题库引擎

    Returns:
        推送文本（Markdown格式）
    """
    day = user.get("current_day", 0) + 1
    day_plan = get_day_tasks(path, day)

    if not day_plan:
        return "🎉 恭喜！你已经完成所有学习计划！请发送 /mock 进行毕业模考。"

    topics = day_plan.get("topics", [])
    difficulty = day_plan.get("difficulty", 1)

    difficulty_stars = "⭐" * difficulty

    # 根据难度选练习题
    types = day_plan.get("types", [])
    practice_qs = []
    if types:
        for qtype in types:
            pool = db.get_by_type(qtype)
            pool = [q for q in pool if q.get("difficulty", 3) <= difficulty + 1]
            random.shuffle(pool)
            practice_qs.extend(pool[:2])

    text = f"""📅 **第 {day} 天学习任务** {difficulty_stars}

📌 **今日知识点**：
"""
    for t in topics:
        text += f"  · {t}\n"

    if practice_qs:
        text += f"\n📝 **练习题（{len(practice_qs)}道）**：\n"
        for i, q in enumerate(practice_qs, 1):
            text += f"\n**第{i}题**【{q.get('source', '')}】\n"
            text += f"{q['stem']}\n\n"
            for opt_key in ["A", "B", "C", "D"]:
                if opt_key in q.get("options", {}):
                    text += f"{opt_key}. {q['options'][opt_key]}\n"
            text += "\n"
    else:
        text += "\n📝 今日无练习题，请复习错题本。\n"

    text += f"\n💡 提交格式：`第X题答案 第Y题答案`（如：`A C`）"
    return text


def generate_mock_exam(user: dict, db: QuestionDB) -> dict:
    """生成阶段模考（10题，限时15分钟）

    Returns:
        {"questions": [...], "time_limit": 900, "text": "推送文本"}
    """
    # 从各题型中抽题
    wrong_types = set()
    wrong_ids = user.get("wrong_ids", [])
    if wrong_ids:
        try:
            wrong_qs = db.get_by_ids(wrong_ids)
            wrong_types = set(q["question_type"] for q in wrong_qs if "question_type" in q)
        except Exception:
            pass

    picks = []

    # 错题优先
    for qtype in wrong_types:
        pool = db.get_by_type(qtype)
        random.shuffle(pool)
        picks.extend(pool[:1])

    # 补齐到10题
    remaining = 10 - len(picks)
    if remaining > 0:
        extra = db.random_pick(remaining, exclude=[q["qid"] for q in picks])
        picks.extend(extra)

    random.shuffle(picks)

    text = "⏰ **阶段模考（10题 / 15分钟）**\n\n"
    for i, q in enumerate(picks, 1):
        text += f"**第{i}题**【{q.get('source', '')}】\n"
        text += f"{q['stem']}\n\n"
        for opt_key in ["A", "B", "C", "D"]:
            if opt_key in q.get("options", {}):
                text += f"{opt_key}. {q['options'][opt_key]}\n"
        text += "\n"

    text += "提交格式：`1.A 2.B 3.C 4.D 5.A 6.B 7.C 8.D 9.A 10.B`"

    return {
        "questions": picks,
        "time_limit": 900,
        "text": text,
    }


def generate_weekly_report(user: dict, db: QuestionDB) -> str:
    """生成周报"""
    logs = user.get("learning_logs", [])
    wrong_ids = user.get("wrong_ids", [])
    mock_log = user.get("mock_log", [])

    completed_days = sum(1 for l in logs if l.get("completed"))
    total_scores = [l.get("score", 0) for l in logs if l.get("score")]
    avg_score = sum(total_scores) / len(total_scores) if total_scores else 0

    text = f"""📊 **本周学习报告**
📅 {datetime.date.today().strftime('%Y-%m-%d')}

✅ **完成情况**：{completed_days}/7天
📈 **平均正确率**：{avg_score:.1f}%
📝 **累计错题**：{len(wrong_ids)}道
🏆 **模考次数**：{len(mock_log)}次

💪 下周继续加油！
"""
    return text

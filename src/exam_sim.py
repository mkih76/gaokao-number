"""
模考系统模块
生成模考题、分析成绩、追踪进步
"""
import random
from typing import Optional
from src.question_db import QuestionDB


def generate_mock(user: dict, db: QuestionDB, num_questions: int = 10) -> dict:
    """生成一套模考题

    策略：
    - 优先选错题类型的题
    - 按比例分配：P0:40%, P1:30%, P2:15%, P3:15%
    - 难度分布：难1:简单3:中等6

    Returns:
        {"questions": [...], "time_limit": 900, "text": "..."}
    """
    wrong_ids = user.get("wrong_ids", "[]")
    try:
        import json
        wrong_ids = json.loads(wrong_ids) if isinstance(wrong_ids, str) else wrong_ids
    except Exception:
        wrong_ids = []

    picks = []

    # 错题抽一半
    if wrong_ids:
        random.shuffle(wrong_ids)
        for w_id in wrong_ids[:num_questions // 2]:
            try:
                picks.append(db.get_by_id(w_id))
            except Exception:
                pass

    # 补齐
    remaining = num_questions - len(picks)
    if remaining > 0:
        # 按比例分配
        type_ratio = {
            "hecha-beibi": 0.12, "gongcheng": 0.12, "xingcheng": 0.12,
            "pailie-zuhe": 0.10, "gailv": 0.08, "jihe": 0.08, "jingji-lirun": 0.08,
            "rongye": 0.06, "rongchi": 0.06, "riqi-nianling": 0.06,
            "chouti": 0.04, "jitu-tonglong": 0.04, "heding-jizhi": 0.04,
        }
        exclude = [q["qid"] for q in picks]
        for qtype, ratio in type_ratio.items():
            count = max(1, int(remaining * ratio))
            pool = [q for q in db.get_by_type(qtype) if q["qid"] not in exclude]
            random.shuffle(pool)
            picks.extend(pool[:count])

    random.shuffle(picks)
    picks = picks[:num_questions]

    # 生成文本
    text = "⏰ **模考开始！**\n\n"
    text += f"📝 共 {len(picks)} 题，限时 **{len(picks) * 1.5:.0f} 分钟**\n"
    text += "➖" * 20 + "\n\n"
    for i, q in enumerate(picks, 1):
        text += f"**第{i}题**【{q.get('source', '')}】\n"
        text += f"{q['stem']}\n\n"
        for opt_key in ["A", "B", "C", "D"]:
            if opt_key in q.get("options", {}):
                text += f"{opt_key}. {q['options'][opt_key]}\n"
        text += "\n"

    return {
        "questions": picks,
        "time_limit": len(picks) * 90,
        "text": text,
    }


def analyze_mock(user_answers: dict, questions: list[dict]) -> dict:
    """分析模考成绩

    Returns:
        {
            "score": 7,
            "total": 10,
            "rate": 0.7,
            "type_stats": {...},
            "wrong_ids": [...],
            "time_analysis": "...",
            "advice": "..."
        }
    """
    wrong_ids = []
    type_correct = {}
    type_total = {}

    for q in questions:
        qid = q["qid"]
        qtype = q["question_type"]
        user_ans = user_answers.get(str(qid), user_answers.get(qid, "")).upper()
        correct_ans = q["answer"].upper()

        if qtype not in type_total:
            type_total[qtype] = 0
            type_correct[qtype] = 0
        type_total[qtype] += 1

        if user_ans == correct_ans:
            type_correct[qtype] += 1
        else:
            wrong_ids.append(qid)

    score = len(questions) - len(wrong_ids)
    rate = score / len(questions) if questions else 0

    type_stats = {}
    for t in type_total:
        correct = type_correct.get(t, 0)
        total = type_total[t]
        type_stats[t] = {
            "correct": correct,
            "total": total,
            "rate": round(correct / total, 2) if total else 0,
        }

    # 生成建议
    weak = [t for t, s in type_stats.items() if s["rate"] < 0.5]
    advice = "继续保持！" if not weak else f"需要加强：{'、'.join(weak)}"

    return {
        "score": score,
        "total": len(questions),
        "rate": round(rate, 2),
        "type_stats": type_stats,
        "wrong_ids": wrong_ids,
        "advice": advice,
    }

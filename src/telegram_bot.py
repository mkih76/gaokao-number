"""
Telegram Bot 交互模块
处理用户命令和对话流
"""
import json
import logging
from typing import Optional
from src.user_db import UserDB
from src.question_db import QuestionDB
from src.diagnose import run_diagnosis
from src.path_planner import generate_path
from src.cron_tasks import generate_daily_tasks
from src.exam_sim import generate_mock, analyze_mock


logger = logging.getLogger(__name__)


COMMANDS = {
    "/start": "欢迎页 + 注册引导",
    "/diagnose": "开始诊断（15题模拟测试）",
    "/path": "查看学习路径",
    "/today": "今天的任务",
    "/wrong": "错题本",
    "/mock": "开始模考",
    "/report": "本周学习报告",
    "/ask": "AI随时答疑",
    "/settings": "设置",
}


class GaokaoBot:
    """公考数量关系 Telegram Bot"""

    def __init__(self, user_db: UserDB, question_db: QuestionDB):
        self.user_db = user_db
        self.question_db = question_db
        # 用户会话状态
        self.sessions: dict[str, dict] = {}

    def handle_start(self, user_id: str, nickname: str) -> str:
        """处理 /start 命令"""
        self.user_db.create_user(user_id, nickname)
        return f"""🎯 **欢迎来到公考数量关系训练营！**

我是你的AI私教，帮你系统提升数量关系。

**我能做什么**：
📊 `/diagnose` — 薄弱点诊断（15题，30分钟）
📚 `/path` — 查看学习路径
📝 `/today` — 今天的任务
❌ `/wrong` — 错题本
🏆 `/mock` — 阶段模考
📈 `/report` — 学习报告
💬 `/ask 题目` — 随时提问

**开始第一步**：发送 /diagnose 开始诊断"""

    def handle_diagnose(self, user_id: str) -> str:
        """开始诊断"""
        questions = self.question_db.get_diagnosis_questions()
        self.sessions[user_id] = {
            "phase": "diagnosis",
            "questions": questions,
            "current": 0,
            "answers": {},
        }

        q = questions[0]
        text = f"""📊 **薄弱点诊断（第1/15题）**

{q['stem']}

"""
        for opt_key in ["A", "B", "C", "D"]:
            if opt_key in q.get("options", {}):
                text += f"{opt_key}. {q['options'][opt_key]}\n"

        text += "\n请回复答案字母（A/B/C/D）"
        return text

    def handle_diagnosis_answer(self, user_id: str, answer: str) -> str:
        """处理诊断答案"""
        session = self.sessions.get(user_id)
        if not session or session.get("phase") != "diagnosis":
            return "请先发送 /diagnose 开始诊断"

        answer = answer.strip().upper()
        if answer not in ["A", "B", "C", "D"]:
            return "请回复 A、B、C、D 中的一个"

        questions = session["questions"]
        current = session["current"]
        q = questions[current]

        session["answers"][q["qid"]] = answer
        session["current"] += 1

        # 下一题
        next_idx = session["current"]
        if next_idx < len(questions):
            q = questions[next_idx]
            text = f"""📊 **薄弱点诊断（第{next_idx + 1}/{len(questions)}题）**

{q['stem']}

"""
            for opt_key in ["A", "B", "C", "D"]:
                if opt_key in q.get("options", {}):
                    text += f"{opt_key}. {q['options'][opt_key]}\n"
            text += "\n请回复答案字母（A/B/C/D）"
            return text

        # 诊断完成
        result = run_diagnosis(session["answers"], self.question_db)
        self.user_db.record_diagnosis(
            user_id, result["score"],
            result["detail"], result["weak_points"],
            result["summary"]
        )

        # 生成薄弱点雷达文字版
        weak_texts = []
        for qtype, wp in result["weak_points"].items():
            bar = "█" * int(wp["rate"] * 10) + "░" * (10 - int(wp["rate"] * 10))
            weak_texts.append(f"{wp['name']:　>8s} {bar} {wp['correct']}/{wp['total']}")

        text = f"""✅ **诊断完成！**

**得分**：{result['score']}/{result['total']}

**薄弱点雷达**：
{chr(10).join(weak_texts)}

**分析**：{result['summary']}

**推荐方案**：{'📅 60天系统学习' if result['recommended_plan'] == '60days' else '📅 21天强化训练'}

发送 /path 生成学习路径
发送 /diagnose 重新诊断"""

        del self.sessions[user_id]
        return text

    def handle_path(self, user_id: str) -> str:
        """生成学习路径"""
        user = self.user_db.get_user(user_id)
        if not user:
            return "请先发送 /start 注册"

        # 检查是否有诊断记录
        history = self.user_db.get_diagnosis_history(user_id, 1)
        if not history:
            return "⚠️ 还没有诊断记录。请先发送 /diagnose 开始诊断。"

        diagnosis = {
            "score": history[0]["score"],
            "priority": [],
        }

        plan = user.get("plan", "21days")
        path = generate_path(diagnosis, plan)

        self.user_db.update_user(
            user_id,
            path_plan=json.dumps(path),
            phase="learning",
            current_day=0,
        )

        text = f"📚 **{plan}天学习路径已生成！**\n\n"
        for entry in path[:7]:
            text += f"  Day {entry['day']:2d} | {'、'.join(entry['topics'][:3])}\n"

        if len(path) > 7:
            text += f"  ... 共 {len(path)} 天\n\n"
        text += "发送 /today 开始第一天学习！"
        return text

    def handle_today(self, user_id: str) -> str:
        """查看今天任务"""
        user = self.user_db.get_user(user_id)
        if not user:
            return "请先发送 /start 注册"

        path = user.get("path_plan", "[]")
        try:
            path = json.loads(path) if isinstance(path, str) else path
        except Exception:
            return "还没有学习路径，请先发送 /path 生成"

        return generate_daily_tasks(user, path, self.question_db)

    def handle_wrong(self, user_id: str) -> str:
        """查看错题本"""
        wrong_ids = self.user_db.get_wrong_questions(user_id)
        if not wrong_ids:
            return "🎉 没有错题，继续保持！"

        wrong_qs = self.question_db.get_by_ids(wrong_ids)
        text = f"❌ **错题本（共{len(wrong_qs)}道）**\n\n"
        for i, q in enumerate(wrong_qs[:5], 1):
            text += f"{i}. {q['stem'][:60]}...\n   ✅ {q['answer']}. {q.get('options', {}).get(q['answer'], '')}\n\n"

        if len(wrong_qs) > 5:
            text += f"... 还有 {len(wrong_qs) - 5} 道\n\n"
        text += "发送 /mock 进行模考（含错题）"
        return text

    def handle_mock(self, user_id: str) -> str:
        """开始模考"""
        user = self.user_db.get_user(user_id)
        if not user:
            return "请先发送 /start 注册"

        result = generate_mock(user, self.question_db)
        self.sessions[user_id] = {
            "phase": "mock",
            "questions": result["questions"],
            "current": 0,
            "answers": {},
        }

        minutes = result["time_limit"] // 60
        seconds = result["time_limit"] % 60
        return f"⏰ **模考开始！**\n限时 {minutes}分{seconds}秒，共{len(result['questions'])}题\n\n" + "\n".join(
            result["text"].split("\n")[3:]  # 跳过标题
        )

    def handle_report(self, user_id: str) -> str:
        """周报"""
        from src.cron_tasks import generate_weekly_report
        user = self.user_db.get_user(user_id)
        if not user:
            return "请先发送 /start 注册"

        user["learning_logs"] = self.user_db.get_learning_logs(user_id, 7)
        return generate_weekly_report(user, self.question_db)

    def handle_ask(self, user_id: str, question_text: str) -> str:
        """AI答疑（占位，后续集成 Hermes Agent）"""
        return f"""💬 **AI答疑**

您的问题是：{question_text}

（AI解析功能即将上线，当前暂用关键词匹配）

**相关题型**：暂无法识别
**解析**：暂无

请发送 /diagnose 先进行薄弱点诊断"""

    def handle_settings(self, user_id: str) -> str:
        """设置"""
        user = self.user_db.get_user(user_id)
        if not user:
            return "请先发送 /start 注册"

        plan = user.get("plan", "21days")
        return f"""⚙️ **设置**

当前计划：{'21天强化' if plan == '21days' else '60天系统'}天

可选计划：
- /setplan 21days — 21天强化训练
- /setplan 60days — 60天系统学习"""

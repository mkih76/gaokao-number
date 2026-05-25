#!/usr/bin/env python3
"""
gaokao-number 交互 Demo
不需要 Telegram Token，直接在终端体验完整用户旅程
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.question_db import QuestionDB
from src.diagnose import run_diagnosis
from src.path_planner import generate_path
from src.exam_sim import generate_mock

db = QuestionDB("data/questions.json")

BANNER = """
╔══════════════════════════════════════════════╗
║     公考数量关系 AI 个性化学习系统 Demo        ║
║                                              ║
║  你正在与 @gaokao_number_bot 对话             ║
║                                              ║
║  [ 模拟用户输入，不耗 TG Token ]              ║
╚══════════════════════════════════════════════╝
"""

def simulate_bot_response(user_message: str, state: dict) -> tuple[str, dict]:
    """模拟 Bot 回复"""
    msg = user_message.strip().lower()

    # ── 状态机 ──────────────────────────────────────
    if msg in ["/start", "开始", "你好"]:
        return BANNER + """

👋 欢迎！我是你的数量关系专属教练。

我能帮你：
✅ 15题快速诊断，找出薄弱点
✅ 定制14/21/60天学习计划
✅ 每天推送学习任务+督学
✅ 随时提问，秒回解析
✅ 定期模考，追踪进步

👉 输入 /diagnose 开始诊断
👉 输入 /demo 查看演示数据
""", {**state, "phase": "menu"}

    elif msg == "/demo":
        return """
📊 当前 Demo 数据（已预置）

用户：上岸同学
学习天数：第 3 天 / 21天
连续打卡：3 天 🔥
本周正确率：67%

📌 薄弱点（诊断结果）：
   • 行程问题   0/2  ❌ 急需加强
   • 排列组合   0/1  ❌ 急需加强
   • 概率       1/2  ⚠️  不太稳定

🟢 优势：
   • 和差倍比   2/2  ✅ 掌握良好
   • 工程问题   2/2  ✅ 掌握良好

━━━━━━━━━━━━━━━━━━━━━━━

👉 输入 /plan 查看学习路径
👉 输入 /today 开始今天的学习
""", {**state, "phase": "menu"}

    elif msg == "/diagnose":
        qs = db.get_diagnosis_questions()
        state["diag_questions"] = qs
        state["diag_answers"] = {}
        state["diag_index"] = 0
        state["phase"] = "diagnosing"
        q = qs[0]
        opts = q.get("options", {})
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━
📊 薄弱点诊断（15题）
━━━━━━━━━━━━━━━━━━━━━━━

第 1/15 题 【{db.TYPE_NAMES.get(q['question_type'], q['question_type'])}】
难度：{'⭐' * q['difficulty']}
来源：{q['source']}

{q['stem']}

A. {opts.get('A', '-')}    B. {opts.get('B', '-')}
C. {opts.get('C', '-')}    D. {opts.get('D', '-')}

请回复选项（A/B/C/D）
""", state

    elif state.get("phase") == "diagnosing":
        idx = state["diag_index"]
        qs = state["diag_questions"]
        correct_answer = qs[idx]["answer"]
        user_answer = msg.upper()

        is_correct = user_answer == correct_answer.upper()
        state["diag_answers"][qs[idx]["qid"]] = user_answer

        feedback = "✅ 正确！" if is_correct else f"❌ 错了（正确答案：{correct_answer}）"
        state["diag_index"] = idx + 1

        if idx + 1 < len(qs):
            q = qs[idx + 1]
            opts = q.get("options", {})
            return f"""
{feedback}

━━━━━━━━━━━━━━━━━━━━━━━
📊 诊断进行中（{idx+2}/15）
━━━━━━━━━━━━━━━━━━━━━━━

第 {idx+2}/15 题 【{db.TYPE_NAMES.get(q['question_type'], q['question_type'])}】
难度：{'⭐' * q['difficulty']}
来源：{q['source']}

{q['stem']}

A. {opts.get('A', '-')}    B. {opts.get('B', '-')}
C. {opts.get('C', '-')}    D. {opts.get('D', '-')}

请回复选项（A/B/C/D）
""", state
        else:
            # 诊断完成
            result = run_diagnosis(state["diag_answers"], db)
            state["diagnosis"] = result
            state["phase"] = "diagnosis_done"

            weak = []
            for w in result.get("priority", []):
                weak.append(f"   • {w['name']}  {w['reason']}")

            return f"""
━━━━━━━━━━━━━━━━━━━━━━━
📊 诊断报告
━━━━━━━━━━━━━━━━━━━━━━━

得分：{result['score']}/{result['total']}（{int(result['score']/result['total']*100)}%）

🔴 薄弱点（需重点攻克）：
{chr(10).join(weak[:5])}

🟢 优势：
   • 和差倍比  掌握良好
   • 工程问题  掌握良好

📋 AI 备考建议：
{result['summary']}

📅 推荐计划：{result['recommended_plan']} 强化班
（根据你的薄弱点量身定制）

━━━━━━━━━━━━━━━━━━━━━━━

👉 输入 /plan 生成完整21天学习路径
👉 输入 /today 直接开始今天的学习
""", state

    elif msg == "/plan" and state.get("phase") == "diagnosis_done":
        result = state.get("diagnosis") or run_diagnosis(
            {"hecha-beibi_01": "B", "hecha-beibi_02": "B",
             "gongcheng_01": "C", "gongcheng_02": "D",
             "xingcheng_01": "C", "xingcheng_02": "B",
             "pailie-zuhe_01": "D", "pailie-zuhe_02": "A",
             "gailv_01": "C", "gailv_02": "B",
             "jihe_01": "A", "jihe_02": "B",
             "jingji-lirun_01": "B", "jingji-lirun_02": "B",
             "rongye_01": "B"},
            db
        )
        path = generate_path(result, "21days")
        state["path"] = path

        lines = ["""
━━━━━━━━━━━━━━━━━━━━━━━
📅 21天强化学习计划
━━━━━━━━━━━━━━━━━━━━━━━
"""]
        week = 1
        for entry in path:
            d = entry["day"]
            if d in [1, 8, 15]:
                lines.append(f"\n第{(d-1)//7+1}周：")
            topics_str = " + ".join(entry["topics"])
            lines.append(f"  Day {d:2d} │ {topics_str[:30]}")
        lines.append("""
━━━━━━━━━━━━━━━━━━━━━━━

每个学习日包含：
  📖 2-3道精选真题
  💡 1个核心公式/技巧卡片
  🔄 错题自动复刷

👉 输入 /today 开始 Day 1 学习
""")
        return "\n".join(lines), state

    elif msg == "/today":
        mock_result = generate_mock({"user_id": "demo"}, db, num_questions=3)
        state["mock"] = mock_result
        state["phase"] = "practicing"
        q = mock_result["questions"][0]
        opts = q.get("options", {})
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━
📚 今日任务（Day 1 / 21天）
━━━━━━━━━━━━━━━━━━━━━━━

📌 主题：和差倍比 + 工程问题
📊 难度：⭐
⏱️  建议用时：10分钟

━━━━━━━━━━━━━━━━━━━━━━━
【练习 1/3】

{q['source']}
{q['stem']}

A. {opts.get('A', '-')}    B. {opts.get('B', '-')}
C. {opts.get('C', '-')}    D. {opts.get('D', '-')}

请回复选项（A/B/C/D）
""", state

    elif state.get("phase") == "practicing":
        idx = state.get("practicing_idx", 0)
        mock = state.get("mock", {})
        qs = mock.get("questions", [])
        if idx >= len(qs):
            return "今日任务已完成！\n\n👉 输入 /report 查看今日报告", state

        correct = qs[idx]["answer"]
        user_ans = msg.upper()
        state["practicing_idx"] = idx + 1

        next_q = qs[idx + 1] if idx + 1 < len(qs) else None
        feedback = "✅ 正确！" if user_ans == correct.upper() else f"❌（答案：{correct}）"

        if next_q:
            opts = next_q.get("options", {})
            return f"""
{feedback}

━━━━━━━━━━━━━━━━━━━━━━━
【练习 {idx+2}/3】

{next_q['source']}
{next_q['stem']}

A. {opts.get('A', '-')}    B. {opts.get('B', '-')}
C. {opts.get('C', '-')}    D. {opts.get('D', '-')}

请回复选项（A/B/C/D）
""", state
        else:
            return f"""
{feedback}

━━━━━━━━━━━━━━━━━━━━━━━
✅ 今日任务完成！
━━━━━━━━━━━━━━━━━━━━━━━

得分：2/3

🏆 连续打卡：1天

💡 薄弱点已加入错题本，明日复习。

晚安，明天继续加油！💪
""", state

    elif msg == "/mock":
        mock_result = generate_mock({"user_id": "demo"}, db, num_questions=5)
        state["mock"] = mock_result
        state["phase"] = "mocking"
        q = mock_result["questions"][0]
        opts = q.get("options", {})
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━
📝 全真模拟考试（5题/10分钟）
━━━━━━━━━━━━━━━━━━━━━━━

第 1/5 题 【{db.TYPE_NAMES.get(q['question_type'], q['question_type'])}】
难度：{'⭐' * q['difficulty']}

{q['stem']}

A. {opts.get('A', '-')}    B. {opts.get('B', '-')}
C. {opts.get('C', '-')}    D. {opts.get('D', '-')}

请回复选项（限时作答）
""", state

    elif state.get("phase") == "mocking":
        idx = state.get("mocking_idx", 0)
        mock = state.get("mock", {})
        qs = mock.get("questions", [])
        correct = qs[idx]["answer"]
        user_ans = msg.upper()
        is_correct = user_ans == correct.upper()
        if "mock_answers" not in state:
            state["mock_answers"] = {}
        state["mock_answers"][qs[idx]["qid"]] = is_correct
        state["mocking_idx"] = idx + 1

        if idx + 1 < len(qs):
            q = qs[idx + 1]
            opts = q.get("options", {})
            return f"""
{'✅' if is_correct else f'❌（答案：{correct}）'}

━━━━━━━━━━━━━━━━━━━━━━━
第 {idx+2}/5 题

{q['stem']}

A. {opts.get('A', '-')}    B. {opts.get('B', '-')}
C. {opts.get('C', '-')}    D. {opts.get('D', '-')}
""", state
        else:
            score = sum(1 for v in state["mock_answers"].values() if v)
            return f"""
{'✅' if user_ans == correct.upper() else f'❌（答案：{correct}）'}

━━━━━━━━━━━━━━━━━━━━━━━
📊 模考成绩
━━━━━━━━━━━━━━━━━━━━━━━

得分：{score}/5（{score*20}%）
用时：约8分钟

📈 评价：
  {'🌟 优秀！' if score >= 4 else '👍 不错，继续保持' if score >= 3 else '💪 还需加强薄弱点'}

👉 输入 /report 查看本周总结
""", {**state, "phase": "menu"}

    elif msg == "/ask" or msg.startswith("/ask "):
        return """
💬 AI 随时答疑

请输入你的题目，例如：
/ask 甲乙两人相向而行，甲速是乙的2倍，相遇时甲走了120米，求全程

或者直接描述你的疑问：
""", state

    elif any(word in msg for word in ["相遇", "速度", "比例"]):
        if state.get("phase") in ["menu", "diagnosis_done"]:
            return """
💬 【行程问题-相遇类型】

核心公式：
  • 相遇：S = (V甲 + V乙) × t
  • 速度比 = 路程比（时间相同时）
  • 相遇点距中点：S = 2 × |S甲 - S中|

解题技巧：
  1. 设未知数，找等量关系
  2. 充分利用速度比=路程比
  3. 注意"超过中点"vs"不足中点"

【真题示例】
2024国考第68题：两人在距中点6km处相遇...
（发送 /question xingcheng 做专项练习）

━━━━━━━━━━━━━━━━━━━━━━━
💡 举一反三：
甲、乙从A、B同时出发相向而行，5分钟后相遇。
已知甲速度是乙的1.5倍，AB相距300米。
问乙的速度？

思路：设乙=x，则甲=1.5x
( x + 1.5x ) × 5 = 300 → x = 24 m/min
""", state
        return "请先发送 /diagnose 完成诊断，或直接描述你的疑问~", state

    elif msg in ["/help", "帮助", "菜单"]:
        return """
━━━━━━━━━━━━━━━━━━━━━━━
📋 全部命令
━━━━━━━━━━━━━━━━━━━━━━━

📌 核心功能：
  /diagnose  薄弱点诊断（15题）
  /plan      查看学习路径
  /today     今日学习任务
  /mock      全真模拟考试
  /ask       随时提问

📊 数据查看：
  /report    本周学习报告
  /wrong     错题本
  /streak    打卡记录

💡 快捷入口：
  直接描述题目 → AI自动分析
  直接发"相遇"/"概率" → 公式卡片

━━━━━━━━━━━━━━━━━━━━━━━
Demo 体验：输入 /demo 查看预置数据
""", state

    else:
        return """
🤔 没听懂？请发送 /help 查看全部命令

Demo 快捷体验：
  /demo   查看预置数据
  /diagnose  开始诊断
  /today   开始学习
  /mock    做一套模考题
""", state


def main():
    print(BANNER)
    print("💡 提示：输入 /help 查看全部命令\n")
    print("=" * 50)

    state = {"phase": "menu"}

    while True:
        try:
            user_input = input("\n👤 你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 再见！加油上岸！💪")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "退出"]:
            print("\n👋 再见！加油上岸！💪")
            break

        response, state = simulate_bot_response(user_input, state)
        print(f"\n🤖 Bot：{response}")


if __name__ == "__main__":
    main()

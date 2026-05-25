#!/usr/bin/env python3
"""
gaokao-number Web API Server
Flask 后端，提供 REST API 给前端调用
"""
import os
import json
import uuid
import sqlite3
from datetime import datetime, date
from flask import Flask, g, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")
app.config["DATABASE"] = os.path.join(os.path.dirname(__file__), "data", "users.db")
app.config["QUESTIONS_FILE"] = os.path.join(os.path.dirname(__file__), "data", "questions.json")

# ─── Database ────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# ─── User Auth ─────────────────────────────────────────────
def get_user_db():
    if "user_db" not in g:
        from src.user_db import UserDB
        g.user_db = UserDB(app.config["DATABASE"])
    return g.user_db

# ─── Questions ────────────────────────────────────────────
def load_questions():
    with open(app.config["QUESTIONS_FILE"], encoding="utf-8") as f:
        data = json.load(f)
    return {q["qid"]: q for q in data["questions"]}

def get_qdb():
    if "qdb" not in g:
        g.qdb = load_questions()
    return g.qdb

# ─── Diagnosis ────────────────────────────────────────────
def calc_diagnosis(answers: dict, qdb: dict) -> dict:
    """根据用户答案计算诊断结果"""
    qtype_stats = {}
    detail = {}
    total_correct = 0

    for qid, user_ans in answers.items():
        q = qdb.get(qid)
        if not q:
            continue
        qt = q["question_type"]
        correct = user_ans.upper() == q["answer"].upper()
        detail[qid] = 1 if correct else 0
        if correct:
            total_correct += 1

        if qt not in qtype_stats:
            qtype_stats[qt] = {"correct": 0, "total": 0, "name": qt}
        qtype_stats[qt]["total"] += 1
        if correct:
            qtype_stats[qt]["correct"] += 1

    # 计算每个题型的掌握程度
    weak_points = []
    strong_points = []
    for qt, stats in qtype_stats.items():
        rate = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        level = "strong" if rate >= 0.8 else "medium" if rate >= 0.5 else "weak"
        stats["rate"] = round(rate, 2)
        stats["level"] = level

        entry = {
            "type": qt,
            "name": _type_name(qt),
            "correct": stats["correct"],
            "total": stats["total"],
            "rate": stats["rate"],
            "level": level,
            "reason": f"{stats['correct']}/{stats['total']}",
        }
        if level == "weak":
            weak_points.append(entry)
        else:
            strong_points.append(entry)

    # 按薄弱程度排序
    weak_points.sort(key=lambda x: x["rate"])

    # 推荐计划
    score_rate = total_correct / max(len(answers), 1)
    if score_rate >= 0.8:
        recommended = "14days"
    elif score_rate >= 0.5:
        recommended = "21days"
    else:
        recommended = "60days"

    # 生成总结
    weak_names = [w["name"] for w in weak_points[:3]]
    strong_names = [s["name"] for s in strong_points[:3]]
    summary = ""
    if weak_names:
        summary += f"{'、'.join(weak_names)}是你的薄弱环节，需要重点突破。 "
    if strong_names:
        summary += f"{'、'.join(strong_names)}基础扎实，可以适当减少练习。"

    return {
        "score": total_correct,
        "total": len(answers),
        "detail": detail,
        "weak_points": weak_points,
        "strong_points": strong_points,
        "summary": summary or "继续保持，多练习巩固！",
        "recommended_plan": recommended,
        "priority": weak_points + strong_points,
    }

def _type_name(qt):
    names = {
        "hecha-beibi": "和差倍比",
        "gongcheng": "工程问题",
        "xingcheng": "行程问题",
        "pailie-zuhe": "排列组合",
        "gailv": "概率",
        "jihe": "几何",
        "jingji-lirun": "经济利润",
        "rongye": "溶液问题",
        "rongchi": "容斥原理",
        "riqi-nianling": "日期年龄",
        "chouti": "抽屉原理",
        "jitu-tonglong": "鸡兔同笼",
        "heding-jizhi": "和定极值",
    }
    return names.get(qt, qt)

# ─── Learning Path ────────────────────────────────────────
def generate_path(diagnosis: dict, plan_type: str = "21days") -> list:
    """生成学习路径"""
    day_count = {"14days": 14, "21days": 21, "60days": 60}[plan_type]

    # 优先学的题型（薄弱在前）
    weak_order = [w["type"] for w in diagnosis.get("weak_points", [])]
    strong_order = [s["type"] for s in diagnosis.get("strong_points", [])]
    priority_order = weak_order + strong_order

    # 题型名映射
    type_names = {
        "hecha-beibi": "和差倍比",
        "gongcheng": "工程问题",
        "xingcheng": "行程问题",
        "pailie-zuhe": "排列组合",
        "gailv": "概率",
        "jihe": "几何",
        "jingji-lirun": "经济利润",
        "rongye": "溶液问题",
        "rongchi": "容斥原理",
        "riqi-nianling": "日期年龄",
        "chouti": "抽屉原理",
        "jitu-tonglong": "鸡兔同笼",
        "heding-jizhi": "和定极值",
    }

    path = []
    day = 1

    # 安排薄弱题型在前面
    all_types = priority_order if priority_order else list(type_names.keys())

    while day <= day_count:
        # 确定本周类型
        week_type_idx = (day - 1) // 7
        type_idx = week_type_idx % len(all_types)
        qt = all_types[type_idx]

        # 确定难度（随天数递增）
        difficulty = min(1 + (day - 1) // 7, 5)

        # 题目内容
        topics = [f"{type_names.get(qt, qt)}"]

        # 复习日
        if day % 7 == 0:
            topics = ["本周错题复盘", "薄弱点专攻"]
            difficulty = max(difficulty, 3)

        path.append({
            "day": day,
            "topics": topics,
            "type": qt,
            "difficulty": difficulty,
            "status": "pending",
        })
        day += 1

    return path

# ─── API Routes ───────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

# ── 邀请码 API ──
@app.route("/api/invite/create", methods=["POST"])
def api_invite_create():
    """创建邀请码（管理员）"""
    data = request.json or {}
    user_db = get_user_db()
    code = user_db.create_invite_code(
        time_days=data.get("time_days", 30),
        max_users=data.get("max_users", 1),
        created_by=data.get("created_by", "admin"),
    )
    return jsonify({"code": code, "time_days": data.get("time_days", 30)})

@app.route("/api/invite/verify", methods=["POST"])
def api_invite_verify():
    """验证邀请码"""
    data = request.json or {}
    code = data.get("code", "").strip().upper()
    user_db = get_user_db()
    result = user_db.verify_invite_code(code)
    return jsonify(result)

# ── 用户 API ──
@app.route("/api/user/register", methods=["POST"])
def api_user_register():
    """用户注册"""
    data = request.json or {}
    user_id = data.get("user_id")
    nickname = data.get("nickname", "同学")
    invite_code = data.get("invite_code", "").strip().upper()

    if not user_id:
        return jsonify({"error": "user_id不能为空"}), 400

    user_db = get_user_db()
    try:
        user = user_db.create_user(user_id, nickname, invite_code or None)
        return jsonify({
            "success": True,
            "user_id": user["user_id"],
            "nickname": user["nickname"],
            "phase": user["phase"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/user/login", methods=["POST"])
def api_user_login():
    """用户登录（简单验证）"""
    data = request.json or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id不能为空"}), 400

    user_db = get_user_db()
    user = user_db.get_user(user_id)
    if not user:
        return jsonify({"error": "用户不存在，请先注册"}), 404
    return jsonify({
        "success": True,
        "user_id": user["user_id"],
        "nickname": user["nickname"],
        "phase": user["phase"],
        "current_day": user["current_day"],
        "plan": user["plan"],
    })

@app.route("/api/user/profile", methods=["GET"])
def api_user_profile():
    """获取用户资料"""
    user_id = request.args.get("user_id", "anonymous")
    user_db = get_user_db()
    user = user_db.get_user(user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404

    return jsonify({
        "user_id": user["user_id"],
        "nickname": user["nickname"],
        "plan": user["plan"],
        "phase": user["phase"],
        "current_day": user["current_day"],
        "streak_days": user["streak_days"],
        "total_score": user["total_score"],
    })

# ── 诊断 API ──
@app.route("/api/diagnose/start", methods=["GET"])
def api_diagnose_start():
    """开始诊断，返回15道诊断题"""
    user_id = request.args.get("user_id", "anonymous")
    qdb = get_qdb()
    questions = list(qdb.values())

    # 均衡选取各题型
    from collections import defaultdict
    by_type = defaultdict(list)
    for q in questions:
        by_type[q["question_type"]].append(q)

    selected = []
    type_order = [
        "hecha-beibi", "gongcheng", "xingcheng",
        "pailie-zuhe", "gailv", "jihe",
        "jingji-lirun", "rongye", "rongchi",
        "riqi-nianling", "chouti", "jitu-tonglong", "heding-jizhi"
    ]
    idx = 0
    while len(selected) < 15 and idx < 100:
        for qt in type_order:
            if qt in by_type and by_type[qt]:
                selected.append(by_type[qt][idx % len(by_type[qt])])
                if len(selected) >= 15:
                    break
        idx += 1

    selected = selected[:15]

    # 简化返回
    result = []
    for q in selected:
        result.append({
            "qid": q["qid"],
            "index": len(result) + 1,
            "type": q["question_type"],
            "type_name": _type_name(q["question_type"]),
            "difficulty": q["difficulty"],
            "source": q["source"],
            "stem": q["stem"],
            "options": q["options"],
        })

    session_id = str(uuid.uuid4())

    # 创建 session 记录
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO web_sessions (session_id, user_id, current_day) VALUES (?, ?, 0)",
        (session_id, user_id)
    )
    db.commit()

    return jsonify({"session_id": session_id, "questions": result})

@app.route("/api/diagnose/submit", methods=["POST"])
def api_diagnose_submit():
    """提交诊断答案，返回诊断报告"""
    data = request.json
    session_id = data.get("session_id", "anon")
    user_id = data.get("user_id", "anonymous")
    answers = data.get("answers", {})

    qdb = get_qdb()
    diagnosis = calc_diagnosis(answers, qdb)

    # 生成学习路径
    path = generate_path(diagnosis, diagnosis["recommended_plan"])

    # 保存到 web_sessions 表
    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO web_sessions (session_id, user_id, created_at, diagnosis, path_plan, current_day)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (session_id, user_id, datetime.now(),
          json.dumps(diagnosis, ensure_ascii=False), json.dumps(path, ensure_ascii=False)))
    db.commit()

    # 同时记录到 user_db 的 diagnoses 表（如果用户已注册）
    try:
        user_db = get_user_db()
        user = user_db.get_user(user_id)
        if user:
            user_db.record_diagnosis(
                user_id,
                diagnosis["score"],
                diagnosis["detail"],
                diagnosis["weak_points"],
                diagnosis.get("summary", "")
            )
            # 更新用户阶段为 learning
            user_db.update_user(user_id,
                phase="learning",
                plan=diagnosis["recommended_plan"],
                diagnosis=json.dumps(diagnosis, ensure_ascii=False),
                path_plan=json.dumps(path, ensure_ascii=False)
            )
    except Exception:
        pass  # 非注册用户跳过

    return jsonify({
        "diagnosis": diagnosis,
        "path": path,
        "session_id": session_id,
    })

# ── 学习 API ──
@app.route("/api/learn/today", methods=["GET"])
def api_learn_today():
    """获取今日学习任务（3道练习题）"""
    session_id = request.args.get("session_id", "default")
    day = int(request.args.get("day", 1))

    qdb = get_qdb()
    questions = list(qdb.values())

    # 简单随机选3题
    import random
    selected = random.sample(questions, min(3, len(questions)))

    result = []
    for q in selected:
        result.append({
            "qid": q["qid"],
            "type": q["question_type"],
            "type_name": _type_name(q["question_type"]),
            "difficulty": q["difficulty"],
            "source": q["source"],
            "stem": q["stem"],
            "options": q["options"],
        })

    return jsonify({
        "day": day,
        "questions": result,
    })

@app.route("/api/learn/submit", methods=["POST"])
def api_learn_submit():
    """提交练习答案"""
    data = request.json
    user_id = data.get("user_id", "anonymous")
    answers = data.get("answers", {})
    qdb = get_qdb()

    results = []
    wrong_ids = []
    for qid, user_ans in answers.items():
        q = qdb.get(qid)
        if not q:
            continue
        correct = user_ans.upper() == q["answer"].upper()
        results.append({
            "qid": qid,
            "correct": correct,
            "user_answer": user_ans,
            "right_answer": q["answer"],
            "solution": q["solution"],
            "type": q["question_type"],
            "type_name": _type_name(q["question_type"]),
            "method": q.get("method", ""),
        })
        if not correct:
            wrong_ids.append(qid)

    score = sum(1 for r in results if r["correct"])

    # 记录错题到用户数据库
    try:
        user_db = get_user_db()
        user = user_db.get_user(user_id)
        if user:
            for qid in wrong_ids:
                user_db.add_wrong_question(user_id, qid)
            # 更新总分
            current = user.get("total_score", 0)
            user_db.update_user(user_id, total_score=current + score)
    except Exception:
        pass

    return jsonify({
        "score": score,
        "total": len(results),
        "wrong_count": len(wrong_ids),
        "results": results,
    })

# ── 模考 API ──
@app.route("/api/mock/start", methods=["GET"])
def api_mock_start():
    """开始模考，返回10道题"""
    qdb = get_qdb()
    questions = list(qdb.values())

    import random
    selected = random.sample(questions, min(10, len(questions)))

    result = []
    for q in selected:
        result.append({
            "qid": q["qid"],
            "type": q["question_type"],
            "type_name": _type_name(q["question_type"]),
            "difficulty": q["difficulty"],
            "source": q["source"],
            "stem": q["stem"],
            "options": q["options"],
        })

    mock_id = str(uuid.uuid4())
    return jsonify({"mock_id": mock_id, "questions": result})

@app.route("/api/mock/submit", methods=["POST"])
def api_mock_submit():
    """提交模考答案"""
    data = request.json
    user_id = data.get("user_id", "anonymous")
    answers = data.get("answers", {})
    qdb = get_qdb()

    results = []
    wrong_ids = []
    for qid, user_ans in answers.items():
        q = qdb.get(qid)
        if not q:
            continue
        correct = user_ans.upper() == q["answer"].upper()
        results.append({
            "qid": qid,
            "correct": correct,
            "user_answer": user_ans,
            "right_answer": q["answer"],
            "solution": q["solution"],
            "stem": q["stem"],
            "type_name": _type_name(q["question_type"]),
            "type": q["question_type"],
        })
        if not correct:
            wrong_ids.append(qid)

    score = sum(1 for r in results if r["correct"])

    # 评级
    rate = score / max(len(results), 1)
    if rate >= 0.8:
        rating = "🌟 优秀！"
    elif rate >= 0.6:
        rating = "👍 良好"
    elif rate >= 0.4:
        rating = "💪 继续努力"
    else:
        rating = "📚 需要加强"

    return jsonify({
        "score": score,
        "total": len(results),
        "rating": rating,
        "results": results,
    })

@app.route("/api/wrong/list", methods=["GET"])
def api_wrong_list():
    """获取用户的错题列表"""
    user_id = request.args.get("user_id", "anonymous")
    try:
        user_db = get_user_db()
        user = user_db.get_user(user_id)
        if not user:
            return jsonify({"error": "用户不存在"}), 404

        wrong_ids = user_db.get_wrong_questions(user_id)
        qdb = get_qdb()

        wrong_questions = []
        for qid in wrong_ids:
            try:
                q = qdb.get(qid)
                wrong_questions.append({
                    "qid": q["qid"],
                    "type": q["question_type"],
                    "type_name": _type_name(q["question_type"]),
                    "difficulty": q["difficulty"],
                    "source": q["source"],
                    "stem": q["stem"],
                    "options": q["options"],
                    "answer": q["answer"],
                    "solution": q["solution"],
                    "method": q.get("method", ""),
                })
            except Exception:
                continue

        return jsonify({
            "total": len(wrong_questions),
            "wrong_questions": wrong_questions,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/wrong/remove", methods=["POST"])
def api_wrong_remove():
    """移除错题（已掌握）"""
    data = request.json
    user_id = data.get("user_id", "anonymous")
    qid = data.get("qid", "")

    try:
        user_db = get_user_db()
        user = user_db.get_user(user_id)
        if not user:
            return jsonify({"error": "用户不存在"}), 404

        wrong_ids = user_db.get_wrong_questions(user_id)
        if qid in wrong_ids:
            wrong_ids.remove(qid)
            user_db.update_user(user_id, wrong_ids=json.dumps(wrong_ids))

        return jsonify({"success": True, "remaining": len(wrong_ids)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── AI 问答 API ──
@app.route("/api/ai/ask", methods=["POST"])
def api_ai_ask():
    """AI 智能问答（Hermes 代理）"""
    data = request.json or {}
    question = data.get("question", "").strip()
    user_id = data.get("user_id", "anonymous")
    mode = data.get("mode", "teach")  # teach / speed / debug

    if not question:
        return jsonify({"error": "问题不能为空"}), 400

    try:
        from src.hermes_client import get_hermes
        hermes = get_hermes()
        result = hermes.ask_math(question, user_id=user_id, mode=mode)
        return jsonify({"success": True, "answer": result["answer"], "mode": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/health", methods=["GET"])
def api_ai_health():
    """检查 AI 服务状态"""
    try:
        from src.hermes_client import get_hermes
        hermes = get_hermes()
        ok = hermes.health_check()
        return jsonify({"status": "ok" if ok else "error"})
    except Exception:
        return jsonify({"status": "error"})

# ── 统计 API ──
@app.route("/api/stats", methods=["GET"])
def api_stats():
    """全局统计数据"""
    qdb = get_qdb()
    by_type = {}
    for q in qdb.values():
        qt = q["question_type"]
        if qt not in by_type:
            by_type[qt] = {"type": qt, "name": _type_name(qt), "count": 0}
        by_type[qt]["count"] += 1

    return jsonify({
        "total_questions": len(qdb),
        "by_type": list(by_type.values()),
    })

# ─── Init DB ─────────────────────────────────────────────
def init_db():
    """初始化数据库表结构（兼容user_db.py）"""
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    db = sqlite3.connect(app.config["DATABASE"])
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id       TEXT PRIMARY KEY,
            nickname      TEXT,
            created_at    DATETIME DEFAULT (datetime('now','localtime')),
            plan          TEXT DEFAULT '21days',
            phase         TEXT DEFAULT 'diagnosis',
            current_day   INT DEFAULT 0,
            streak_days   INT DEFAULT 0,
            total_score   REAL DEFAULT 0,
            diagnosis     TEXT,
            wrong_ids     TEXT DEFAULT '[]',
            mock_log      TEXT DEFAULT '[]',
            path_plan     TEXT DEFAULT '[]',
            settings      TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS diagnoses (
            user_id       TEXT NOT NULL,
            created_at    DATETIME DEFAULT (datetime('now','localtime')),
            score         INT NOT NULL,
            detail        TEXT NOT NULL,
            weak_points   TEXT NOT NULL,
            advice        TEXT,
            PRIMARY KEY (user_id, created_at)
        );
        CREATE TABLE IF NOT EXISTS learning_logs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       TEXT NOT NULL,
            day           INT NOT NULL,
            date          DATE NOT NULL,
            topics        TEXT NOT NULL,
            completed     INT DEFAULT 0,
            score         INT,
            wrong_ids     TEXT DEFAULT '[]',
            note          TEXT,
            UNIQUE(user_id, day)
        );
        CREATE TABLE IF NOT EXISTS web_sessions (
            session_id    TEXT PRIMARY KEY,
            user_id       TEXT,
            created_at    DATETIME DEFAULT (datetime('now','localtime')),
            diagnosis     TEXT,
            path_plan     TEXT,
            current_day   INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS invite_codes (
            code          TEXT PRIMARY KEY,
            time_days     INT DEFAULT 30,
            max_users     INT DEFAULT 1,
            used_count    INT DEFAULT 0,
            created_at    DATETIME DEFAULT (datetime('now','localtime')),
            created_by    TEXT,
            expired_at    DATETIME
        );
        CREATE INDEX IF NOT EXISTS idx_diagnoses_user ON diagnoses(user_id);
        CREATE INDEX IF NOT EXISTS idx_learning_user ON learning_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_learning_date ON learning_logs(date);
        CREATE INDEX IF NOT EXISTS idx_web_sessions_user ON web_sessions(user_id);
    """)
    db.commit()
    db.close()
    print(f"✅ 数据库初始化完成: {app.config['DATABASE']}")

if __name__ == "__main__":
    init_db()
    print("🚀 启动公考数量关系 AI 学习网站...")
    print("📍 访问地址: http://localhost:8789")
    app.run(host="0.0.0.0", port=8789, debug=True)

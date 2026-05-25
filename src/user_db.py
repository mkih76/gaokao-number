"""
用户状态管理模块
基于 SQLite 存储用户数据，支持 JSON 字段序列化
"""
import sqlite3
import json
import datetime
from typing import Optional


class UserNotFoundError(Exception):
    """用户不存在"""
    pass


class UserDB:
    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_table()

    def _init_table(self):
        self.conn.execute("""
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
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS diagnoses (
                user_id       TEXT NOT NULL,
                created_at    DATETIME DEFAULT (datetime('now','localtime')),
                score         INT NOT NULL,
                detail        TEXT NOT NULL,
                weak_points   TEXT NOT NULL,
                advice        TEXT,
                PRIMARY KEY (user_id, created_at)
            )
        """)
        self.conn.execute("""
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
            )
        """)
        self.conn.commit()

    def _json_load(self, s: str, default=None):
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            return default or {}

    def get_user(self, user_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            return None
        return dict(row)

    def create_user(self, user_id: str, nickname: str) -> dict:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (user_id, nickname) VALUES (?, ?)",
            (user_id, nickname)
        )
        self.conn.commit()
        return self.get_user(user_id)

    def update_user(self, user_id: str, **kwargs) -> dict:
        user = self.get_user(user_id)
        if not user:
            raise UserNotFoundError(f"用户 {user_id} 不存在")
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [user_id]
        self.conn.execute(
            f"UPDATE users SET {sets} WHERE user_id = ?", vals
        )
        self.conn.commit()
        return self.get_user(user_id)

    def get_wrong_questions(self, user_id: str) -> list:
        user = self.get_user(user_id)
        if not user:
            return []
        return self._json_load(user["wrong_ids"], [])

    def add_wrong_question(self, user_id: str, qid: str):
        wrong = self.get_wrong_questions(user_id)
        wrong.append(qid)
        self.update_user(user_id, wrong_ids=json.dumps(wrong))

    def get_diagnosis_history(self, user_id: str, limit: int = 5) -> list:
        rows = self.conn.execute(
            "SELECT * FROM diagnoses WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def record_diagnosis(self, user_id: str, score: int, detail: dict,
                         weak_points: dict, advice: str = ""):
        self.conn.execute(
            "INSERT INTO diagnoses (user_id, score, detail, weak_points, advice) VALUES (?, ?, ?, ?, ?)",
            (user_id, score, json.dumps(detail), json.dumps(weak_points), advice)
        )
        self.conn.commit()

    def get_learning_logs(self, user_id: str, limit: int = 30) -> list:
        rows = self.conn.execute(
            "SELECT * FROM learning_logs WHERE user_id = ? ORDER BY day DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def record_learning_log(self, user_id: str, day: int, topics: str,
                            completed: int = 1, score: int = 0,
                            wrong_ids: list = None, note: str = ""):
        today = datetime.date.today().isoformat()
        self.conn.execute(
            """INSERT OR REPLACE INTO learning_logs
               (user_id, day, date, topics, completed, score, wrong_ids, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, day, today, topics, completed, score,
             json.dumps(wrong_ids or []), note)
        )
        self.conn.commit()

    def get_active_users(self, days: int = 7) -> list:
        cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        rows = self.conn.execute(
            "SELECT DISTINCT user_id FROM learning_logs WHERE date >= ?", (cutoff,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()

-- ============================================
-- 公考数量关系 AI 学习系统 — 数据库结构
-- ============================================

-- 用户表
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

-- 诊断记录表
CREATE TABLE IF NOT EXISTS diagnoses (
    user_id       TEXT NOT NULL,
    created_at    DATETIME DEFAULT (datetime('now','localtime')),
    score         INT NOT NULL,
    detail        TEXT NOT NULL,
    weak_points   TEXT NOT NULL,
    advice        TEXT,
    PRIMARY KEY (user_id, created_at)
);

-- 学习日志表
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

-- 索引
CREATE INDEX IF NOT EXISTS idx_diagnoses_user ON diagnoses(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_user ON learning_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_date ON learning_logs(date);

-- 初始化标记
PRAGMA user_version = 1;

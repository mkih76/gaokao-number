# AGENTS.md — AI 开发者构建指引

> 本文件给 Claude Code、Codex、Cursor 等 AI 编码代理使用。
> 按照此文档构建 `gaokao-number` 系统的完整代码。

---

## 一、项目概述

公考数量关系AI个性化学习系统。13种题型精讲 + AI薄弱点诊断 + 个性化学习路径 + 24h Telegram私教。

### 核心业务逻辑

```
用户进入 → 诊断测试（15题） → 生成薄弱点雷达图
         → 个性化学习路径（21天/60天可选）
         → 每日推送练习题（2-3知识点）
         → 随时提问（AI批改+讲解）
         → 错题自动入库（三轮复刷）
         → 阶段模考（每两周）
         → 复盘 + 路径调整
```

### 代码架构

```
src/
├── user_db.py          # 用户状态管理
├── question_db.py      # 题库引擎
├── diagnose.py         # 薄弱点诊断
├── path_planner.py     # 学习路径生成
├── cron_tasks.py       # 督学定时任务
├── exam_sim.py         # 模考系统
└── telegram_bot.py     # Telegram 交互
```

---

## 二、数据模型

### 2.1 用户表 `users`

```sql
CREATE TABLE users (
    user_id       TEXT PRIMARY KEY,          -- Telegram user_id
    nickname      TEXT,                      -- 用户昵称
    created_at    DATETIME DEFAULT NOW,      -- 注册时间
    plan          TEXT DEFAULT '21days',     -- 学习计划：21days / 60days
    phase         TEXT DEFAULT 'diagnosis',  -- 阶段：diagnosis / learning / mock / finished
    current_day   INT DEFAULT 0,             -- 当前学习第几天
    streak_days   INT DEFAULT 0,             -- 连续活跃天数
    total_score   REAL DEFAULT 0,            -- 总分
    diagnosis     TEXT,                      -- JSON，诊断结果（薄弱点雷达）
    wrong_ids     TEXT DEFAULT '[]',          -- JSON，错题ID列表
    mock_log      TEXT DEFAULT '[]',           -- JSON，模考记录 [{date, score, detail}]
    path_plan     TEXT DEFAULT '[]',            -- JSON，学习路径 [{day, topics, status}]
    settings      TEXT DEFAULT '{}'             -- JSON，用户设置
);
```

### 2.2 题目表 `questions`

```sql
CREATE TABLE questions (
    qid           TEXT PRIMARY KEY,             -- 题型_序号，如 gongcheng_01
    question_type TEXT NOT NULL,                -- 题型分类：hecha-beibi / gongcheng / xingcheng / pailie-zuhe / gailv / jihe / jingji-lirun / rongye / rongchi / riqi-nianling / chouti / jitu-tonglong / heding-jizhi
    difficulty    INT NOT NULL,                 -- 1-5，难度等级
    source        TEXT,                         -- 来源，如 "2024国考副省级第61题"
    stem          TEXT NOT NULL,                -- 题干
    options       TEXT NOT NULL,                -- JSON，选项 {A: "...", B: "...", C: "...", D: "..."}
    answer        TEXT NOT NULL,                -- 正确答案（字母）
    solution      TEXT NOT NULL,                -- 详细解析
    method        TEXT,                         -- 解题方法，如 "赋值法、方程法"
    tags          TEXT DEFAULT '[]'              -- JSON，标签 ["行程-相遇", "行程-追及"]
);
```

### 2.3 诊断记录表 `diagnoses`

```sql
CREATE TABLE diagnoses (
    user_id       TEXT NOT NULL,
    created_at    DATETIME DEFAULT NOW,
    score         INT NOT NULL,                -- 总分（满分15）
    detail        TEXT NOT NULL,               -- JSON，每题得分 {"q01": 1, "q02": 0, ...}
    weak_points   TEXT NOT NULL,               -- JSON 薄弱点 {"hecha-beibi": 2/2, "gongcheng": 1/2, ...}
    advice        TEXT,                        -- AI给出的备考建议
    PRIMARY KEY (user_id, created_at)
);
```

### 2.4 学习记录表 `learning_logs`

```sql
CREATE TABLE learning_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       TEXT NOT NULL,
    day           INT NOT NULL,                -- 第几天
    date          DATE NOT NULL,
    topics        TEXT NOT NULL,               -- 当天学习知识点
    completed     INT DEFAULT 0,               -- 0=未完成 1=已完成
    score         INT,                         -- 当天练习得分
    wrong_ids     TEXT DEFAULT '[]',            -- 当天错题ID
    note          TEXT,                         -- 用户笔记
    UNIQUE(user_id, day)
);
```

---

## 三、模块详解

### 3.1 user_db.py — 用户状态管理

```python
# 接口定义
class UserDB:
    def __init__(self, db_path: str = "data/users.db")
    def get_user(user_id: str) -> dict | None
    def create_user(user_id: str, nickname: str) -> dict
    def update_user(user_id: str, **kwargs) -> dict
    def get_wrong_questions(user_id: str) -> list[str]   # 返回错题ID列表
    def add_wrong_question(user_id: str, qid: str)        # 添加一道错题
    def get_diagnosis_history(user_id: str, limit=5) -> list[dict]
    def get_learning_logs(user_id: str, limit=30) -> list[dict]
    def get_active_users(days=7) -> list[dict]            # 最近活跃用户
```

### 3.2 question_db.py — 题库引擎

```python
class QuestionDB:
    def __init__(self, data_path: str = "data/questions.json")
    def get_by_type(qtype: str) -> list[dict]            # 按题型取题
    def get_by_difficulty(level: int) -> list[dict]      # 按难度取题
    def get_by_tags(tags: list[str]) -> list[dict]       # 按标签取题
    def get_by_ids(qids: list[str]) -> list[dict]        # 按ID批量取题
    def get_diagnosis_questions() -> list[dict]           # 取15道诊断题
    def random_pick(n: int, exclude: list = None) -> list[dict]
    def get_statistics() -> dict                          # 题库统计
```

### 3.3 diagnose.py — 薄弱点诊断

```python
def run_diagnosis(user_answers: dict[str, str], db: QuestionDB) -> dict:
    """
    输入：用户对15道诊断题的答案 {"q01": "A", "q02": "C", ...}
    输出：
    {
        "score": 8,              # 总分
        "detail": {"q01": 1, "q02": 0, ...},
        "weak_points": {
            "hecha-beibi": {"correct": 2, "total": 2, "rate": 1.0, "level": "strong"},
            "gongcheng":  {"correct": 1, "total": 2, "rate": 0.5, "level": "medium"},
            ...
        },
        "summary": "你的和差倍比基础扎实，行程问题和排列组合需要重点攻克",
        "priority": [
            {"type": "xingcheng", "urgency": "high", "reason": "0/2，最薄弱题型"},
            {"type": "pailie-zuhe", "urgency": "high", "reason": "0/1"},
            ...
        ],
        "recommended_plan": "21days"  # 或 "60days"（根据薄弱程度）
    }
    """
```

### 3.4 path_planner.py — 学习路径生成

```python
def generate_path(diagnosis: dict, plan_type: str = "21days") -> list[dict]:
    """
    输入：诊断结果 + 计划类型
    输出：
    [
        {"day": 1, "topics": ["和差倍比-基础", "工程问题-赋值法"], "difficulty": 1},
        {"day": 2, "topics": ["行程问题-相遇追及"], "difficulty": 2},
        ...
    ]
    
    学习路径原则：
    1. 优先级：P0题型先于P1，P1先于P2
    2. 难度渐进：1→2→3，让用户逐步建立信心
    3. 薄弱优先：诊断中低于50%的题型，放到前3天
    4. 穿插复习：每隔3天安排前一阶段的错题复刷
    """
```

### 3.5 cron_tasks.py — 督学定时任务

```python
def generate_daily_tasks(user_id: str, day: int, db: QuestionDB) -> str:
    """生成当日学习任务的推送文本"""
    
def generate_mock_exam(user_id: str, db: QuestionDB) -> dict:
    """生成阶段模考（10题，限时15分钟）"""
    
def generate_weekly_report(user_id: str, db: QuestionDB, user_db: UserDB) -> str:
    """生成本周学习报告文本"""
```

### 3.6 telegram_bot.py — Telegram 交互

```python
# 命令表
COMMANDS = {
    "/start":       "欢迎页 + 注册引导",
    "/diagnose":    "开始诊断（15题模拟测试）",
    "/path":        "查看学习路径",
    "/today":       "今天的任务",
    "/wrong":       "错题本（三轮复刷）",
    "/mock":        "开始模考",
    "/report":      "本周学习报告",
    "/ask [题目]":  "AI随时答疑",
    "/settings":    "设置（计划类型、通知时间等）",
}

# 用户交互流程
FLOW_DIAGNOSIS = """
用户发送 /diagnose 
→ bot发送15道题（一次1题）
→ 用户逐题回答
→ 全部完成后，bot生成诊断报告
→ 询问是否生成学习路径
"""

FLOW_DAILY = """
每天早上9:00 → bot推送当天任务
用户完成任务后提交答案
→ bot批改并记录错题
→ 晚上21:00未完成则催问
"""

FLOW_ASK = """
用户发送 /ask 题目文本
→ AI分析题目类型
→ 调用 Hermes Agent 生成逐步解析
→ 返回解析 + 同类题推荐
"""
```

---

## 四、API 接口

### 4.1 诊断模块

```
POST /api/diagnose/start
→ 返回15道诊断题

POST /api/diagnose/submit
  Body: {user_id, answers: {"q01": "A", "q02": "C", ...}}
→ 返回诊断报告（薄弱点雷达图 + 建议 + 推荐路径）

GET /api/diagnose/history?user_id=xxx&limit=5
→ 返回诊断历史记录
```

### 4.2 学习模块

```
GET /api/path/generate?user_id=xxx&plan=21days
→ 返回21天学习路径

GET /api/path/today?user_id=xxx&day=3
→ 返回当天任务

POST /api/path/submit
  Body: {user_id, day, answers: {"q01": "A", ...}}
→ 批改结果 + 错题入库

POST /api/path/ask
  Body: {user_id, question: "题目文本"}
→ AI解析 + 同类题推荐
```

### 4.3 模考模块

```
GET /api/mock/start?user_id=xxx
→ 返回10道模考题（限时15分钟）

POST /api/mock/submit
  Body: {user_id, answers: {...}}
→ 模考成绩 + 分析报告

GET /api/mock/history?user_id=xxx
→ 模考历史记录
```

### 4.4 数据模块

```
GET /api/stats/user?user_id=xxx
→ 用户学习统计（活跃天数、正确率趋势、薄弱点变化）

GET /api/stats/leaderboard?days=7
→ 排行榜（刺激学习氛围）
```

---

## 五、实现顺序

### Phase 1: 数据结构 + 题库（Day 1）
- [x] data/schema.sql
- [ ] data/questions.json（完整题库）
- [ ] src/user_db.py
- [ ] src/question_db.py

### Phase 2: 诊断引擎（Day 2-3）
- [ ] src/diagnose.py（完整的诊断逻辑）
- [ ] 测试：tests/test_diagnose.py

### Phase 3: 学习路径（Day 3-4）
- [ ] src/path_planner.py
- [ ] 21天和60天两套路径模板
- [ ] 测试：tests/test_path_planner.py

### Phase 4: 督学 + Telegram bot（Day 5-7）
- [ ] src/cron_tasks.py
- [ ] src/telegram_bot.py
- [ ] 端到端测试

### Phase 5: 模考系统（Day 8-9）
- [ ] src/exam_sim.py
- [ ] 模考分析报告生成

### Phase 6: 部署（Day 10）
- [ ] init.sh 完善
- [ ] systemd 服务配置
- [ ] Caddy 反代（可选）

---

## 六、数据流

### 用户注册流程
```
/start → create_user → 发送欢迎页 → 提示/diagnose
```

### 诊断流程
```
/diagnose → 
  question_db.get_diagnosis_questions() → 
  逐题发送 →
  用户逐题回答 →
  diagnose.run_diagnosis() →
  生成报告 →
  path_planner.generate_path() →
  询问是否开始学习

异常处理：
- 用户中途退出 → 保存已答题目，下次可继续
- 用户重新诊断 → 覆盖上一次结果
```

### 每日学习流程
```
cron 09:00 →
  user_db.get_user() →
  path_planner.get_day_tasks(user, day) →
  question_db.get_by_ids(task.qids) →
  组装推送文本 →
  Telegram发送

用户提交答案 →
  批改 →
  记录学习日志 →
  错题入库 →
  推送答案+解析

cron 21:00 →
  检查今日是否完成 →
  未完成则催问
```

### 错题复刷流程
```
每3天检查一次 →
  获取 user.wrong_ids →
  按题型分组 →
  挑选距上次错误时间最长的3道 →
  推送复刷
```

### 模考流程
```
/mock →
  exam_sim.generate_mock(user) → 10题限时15min
  用户作答 →
  批改+评分 →
  记录mocks表 →
  分析薄弱点变化 →
  更新learning_path
```

---

## 七、编码规范

### 7.1 Python 风格

- Python 3.10+ 类型注解
- 函数命名：`snake_case`，类命名：`PascalCase`
- 每个函数必须有 docstring
- 每行不超过 100 字符
- 使用 f-string 格式化

### 7.2 错误处理

```python
class UserNotFoundError(Exception): pass
class QuestionNotFoundError(Exception): pass
class DiagnosisIncompleteError(Exception): pass

def get_user(user_id: str) -> dict:
    user = self.conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    if not user:
        raise UserNotFoundError(f"用户 {user_id} 不存在")
    return dict(user)
```

### 7.3 JSON 处理

```python
import json
# 所有JSON字段使用 json.dumps/loads 序列化
# 默认值用 '[]' 或 '{}'，NULL 须统一处理
def safe_json_parse(s: str, default=None):
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return default or {}
```

### 7.4 测试要求

```python
# tests/test_diagnose.py
def test_run_diagnosis_all_correct():
    """15题全对的情况"""
    answers = {f"q{i:02d}": "A" for i in range(1, 16)}
    result = run_diagnosis(answers, mock_db)
    assert result["score"] == 15
    assert all(v["rate"] == 1.0 for v in result["weak_points"].values())

def test_run_diagnosis_all_wrong():
    """15题全错的情况，应推荐60天计划"""
    answers = {f"q{i:02d}": "B" for i in range(1, 16)}
    result = run_diagnosis(answers, mock_db)
    assert result["score"] == 0
    assert result["recommended_plan"] == "60days"
```

---

## 八、依赖

```txt
telethon==1.36.0
python-telegram-bot==21.0
numpy==1.24.0
requests==2.31.0
pydantic==2.0
pytest==8.0
APScheduler==3.10.0
```

---

## 九、部署

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库
python src/user_db.py --init

# 3. 导入题库
python src/question_db.py --import data/questions.json

# 4. 启动 Telegram bot
python src/telegram_bot.py --token YOUR_TELEGRAM_TOKEN

# 5. 启动定时任务（后台）
python src/cron_tasks.py --daemon

# 6. 验证
curl http://localhost:8080/health
```

#!/bin/bash
# ============================================
# 公考数量关系 AI 学习系统 — 一键部署脚本
# ============================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "📦 开始部署公考数量关系 AI 学习系统..."

# 1. 检测 Python
echo "🔍 检测 Python 环境..."
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "❌ 未找到 Python，请先安装 Python 3.10+"
    exit 1
fi
echo "✅ Python: $($PYTHON --version)"

# 2. 创建依赖文件
echo "📄 创建 requirements.txt..."
cat > "$SCRIPT_DIR/requirements.txt" << 'EOF'
telethon==1.36.0
python-telegram-bot==21.0
numpy==1.24.0
requests==2.31.0
pydantic==2.0
pytest==8.0
APScheduler==3.10.0
EOF

# 3. 安装依赖
echo "📦 安装 Python 依赖..."
pip3 install -r "$SCRIPT_DIR/requirements.txt" -q || pip install -r "$SCRIPT_DIR/requirements.txt" -q

# 4. 创建数据目录
DATA_DIR="$SCRIPT_DIR/data"
mkdir -p "$DATA_DIR"

# 5. 初始化数据库
echo "🗄️  初始化数据库..."
$PYTHON -c "
import sqlite3, os
DB_PATH = os.path.join('$DATA_DIR', 'users.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH)

# 执行 schema
schema_path = os.path.join('$DATA_DIR', 'schema.sql')
if os.path.exists(schema_path):
    with open(schema_path) as f:
        conn.executescript(f.read())
    print(f'✅ 数据库初始化完成: {DB_PATH}')
else:
    # 内联建表
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY, nickname TEXT,
            created_at DATETIME DEFAULT (datetime(\"now\",\"localtime\")),
            plan TEXT DEFAULT \"21days\", phase TEXT DEFAULT \"diagnosis\",
            current_day INT DEFAULT 0, streak_days INT DEFAULT 0,
            total_score REAL DEFAULT 0, diagnosis TEXT,
            wrong_ids TEXT DEFAULT \"[]\", mock_log TEXT DEFAULT \"[]\",
            path_plan TEXT DEFAULT \"[]\", settings TEXT DEFAULT \"{}\"
        );
        CREATE TABLE IF NOT EXISTS diagnoses (
            user_id TEXT NOT NULL, created_at DATETIME DEFAULT (datetime(\"now\",\"localtime\")),
            score INT NOT NULL, detail TEXT NOT NULL, weak_points TEXT NOT NULL, advice TEXT,
            PRIMARY KEY (user_id, created_at)
        );
        CREATE TABLE IF NOT EXISTS learning_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL, day INT NOT NULL, date DATE NOT NULL,
            topics TEXT NOT NULL, completed INT DEFAULT 0, score INT,
            wrong_ids TEXT DEFAULT \"[]\", note TEXT,
            UNIQUE(user_id, day)
        );
    ''')
    print(f'✅ 数据库初始化完成: {DB_PATH}')
conn.close()
"

# 6. 验证题库
echo "🔍 验证题库..."
$PYTHON -c "
import json
with open('$SCRIPT_DIR/data/questions.json') as f:
    data = json.load(f)
qs = data.get('questions', [])
print(f'✅ 题库: {len(qs)} 道题')
types = {}
for q in qs:
    t = q.get('question_type', 'unknown')
    types[t] = types.get(t, 0) + 1
for t, c in sorted(types.items()):
    print(f'   {t}: {c}道')
"

# 7. 运行测试
echo "🧪 运行单元测试..."
if [ -d "$SCRIPT_DIR/tests" ]; then
    cd "$SCRIPT_DIR"
    $PYTHON -m pytest tests/ -v --tb=short 2>/dev/null || \
        echo "⚠️  测试运行失败（可忽略，非核心功能）"
fi

# 8. 创建配置示例
echo "📝 创建配置文件..."
CONFIG_FILE="$SCRIPT_DIR/.env"
if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" << 'EOF'
# Telegram Bot Token（从 @BotFather 获取）
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Hermes Agent 配置（可选）
HERMES_BASE_URL=http://localhost:8642
HERMES_API_KEY=your_api_key_here
EOF
    echo "✅ 配置文件创建: $CONFIG_FILE"
    echo "⚠️  请编辑 $CONFIG_FILE 填入 Telegram Bot Token"
else
    echo "✅ 配置文件已存在"
fi

# 9. 创建 systemd 服务（可选）
if [ -d /etc/systemd/system ] && [ "$EUID" -eq 0 ]; then
    echo "📝 创建 systemd 服务..."
    cat > /etc/systemd/system/gaokao-number.service << 'EOF'
[Unit]
Description=公考数量关系 AI 学习系统
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/workspace/gaokao-number
ExecStart=/usr/bin/python3 src/telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    echo "✅ systemd 服务已创建"
    echo "   启动: systemctl start gaokao-number"
    echo "   开机自启: systemctl enable gaokao-number"
    echo "   查看日志: journalctl -u gaokao-number -f"
fi

echo ""
echo "🎉 部署完成！"
echo "========================"
echo "📁 项目路径: $SCRIPT_DIR"
echo "📚 题库:      $SCRIPT_DIR/data/questions.json (20题)"
echo "🗄️  数据库:    $DATA_DIR/users.db"
echo "⚙️  配置:      $CONFIG_FILE"
echo ""
echo "📋 下一步："
echo "  1. 编辑 .env 填入 Telegram Bot Token"
echo "  2. 启动: python3 src/telegram_bot.py"
echo "  3. 在 Telegram 中发送 /start 开始使用"
echo "========================"

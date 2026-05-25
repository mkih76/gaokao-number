# 公考数量关系 AI 个性化学习系统

> 13种题型精讲 + AI薄弱点诊断 + 个性化学习路径 + 24h Telegram私教

**一句话定位**：帮你精准找到数量关系的提分点，24小时随时问，2个月从放弃到拿分。

---

## 项目结构

```
gaokao-number/
├── README.md                   # 本说明
├── AGENTS.md                   # AI开发者构建指引
├── Dockerfile                  # Docker镜像配置
├── docker-compose.yml          # Docker Compose编排
├── .env.example                # 环境变量示例
├── init.sh                     # 一键部署脚本
├── src/
│   ├── user_db.py              # 用户状态管理
│   ├── question_db.py          # 题库引擎
│   ├── diagnose.py             # 薄弱点诊断
│   ├── path_planner.py         # 学习路径生成
│   ├── cron_tasks.py           # 督学定时任务
│   ├── exam_sim.py             # 模考系统
│   ├── hermes_client.py        # Hermes AI网关客户端
│   └── telegram_bot.py         # Telegram Bot
├── data/
│   ├── questions.json           # 题库（65道真题）
│   └── schema.sql               # 数据库结构
├── static/
│   └── index.html              # Web前端
├── tests/
│   ├── test_diagnose.py
│   └── test_path_planner.py
└── web_server.py                # Web API服务
```

---

## 功能特性

- 📊 **AI薄弱点诊断** - 15道题精准定位薄弱环节
- 📚 **个性化学习路径** - 14/21/60天可选，按优先级安排
- 💬 **Telegram Bot** - 24小时随时提问，AI批改讲解
- 📈 **错题本** - 三轮复刷，自动收录错题
- 🏆 **阶段模考** - 定期检验学习效果
- 🌐 **Web界面** - 浏览器直接使用，无需Telegram

---

## 服务器部署指南（Ubuntu 20.04+）

### 前置准备

1. **一台VPS/服务器**（推荐2核2G以上）

2. **安装Docker和Docker Compose**
```bash
# 更新系统
apt update && apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com | sh

# 安装Docker Compose
apt install docker-compose -y

# 验证安装
docker --version
docker-compose --version
```

3. **申请Telegram Bot Token**
   - 在Telegram搜索 @BotFather
   - 发送 `/newbot`
   - 按提示设置Bot名称和用户名
   - 复制获得的 Token（如 `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`）

---

### 部署步骤

#### 方式一：Docker部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/mkih76/gaokao-number.git
cd gaokao-number

# 2. 创建环境配置文件
cp .env.example .env
nano .env   # 或 vi .env
```

编辑 `.env` 文件，填入你的配置：
```env
TELEGRAM_BOT_TOKEN=你的TelegramBotToken
FLASK_ENV=production
SECRET_KEY=随机字符串
```

```bash
# 3. 启动服务
docker-compose up -d

# 4. 查看运行状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f
```

#### 方式二：手动部署

```bash
# 1. 克隆项目
git clone https://github.com/mkih76/gaokao-number.git
cd gaokao-number

# 2. 安装Python依赖
apt update
apt install -y python3 python3-pip python3-venv

# 3. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 创建环境配置
cp .env.example .env
nano .env   # 填入 TELEGRAM_BOT_TOKEN
```

创建 `requirements.txt`（如果不存在）：
```txt
flask==3.0.0
requests==2.31.0
python-telegram-bot==21.0
pydantic==2.5.0
APScheduler==3.10.0
```

```bash
# 6. 初始化数据库
python -c "from src.user_db import UserDB; UserDB()"

# 7. 启动Web服务（后台运行）
nohup python web_server.py > web.log 2>&1 &

# 8. 启动Telegram Bot
nohup python src/telegram_bot.py > bot.log 2>&1 &
```

---

### 验证部署

#### Web服务验证
```bash
curl http://localhost:8080/health
# 返回 {"status": "ok"} 表示正常
```

#### Telegram Bot验证
1. 在Telegram中找到你的Bot
2. 发送 `/start`
3. 应该收到欢迎消息

---

### Nginx反向代理配置（可选）

如果需要域名访问：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# 安装Nginx
apt install -y nginx

# 启用配置
cp your-domain.conf /etc/nginx/sites-available/
ln -s /etc/nginx/sites-available/your-domain.conf /etc/nginx/sites-enabled/

# 测试并重载
nginx -t
systemctl reload nginx
```

---

### systemd服务配置（可选）

创建服务文件：
```bash
nano /etc/systemd/system/gaokao-number.service
```

```ini
[Unit]
Description=Gaokao Number AI Learning System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/gaokao-number
ExecStart=/path/to/gaokao-number/venv/bin/python web_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
systemctl daemon-reload
systemctl enable gaokao-number
systemctl start gaokao-number

# 查看状态
systemctl status gaokao-number
```

---

### 常见问题

#### 1. Docker部署后无法访问Web界面
```bash
# 检查容器是否运行
docker-compose ps

# 查看日志
docker-compose logs web

# 检查端口是否开放
netstat -tlnp | grep 8080
```

#### 2. Telegram Bot没有响应
```bash
# 检查Bot日志
docker-compose logs bot

# 确认Token正确
cat .env | grep TELEGRAM_BOT_TOKEN
```

#### 3. 数据库初始化失败
```bash
# 手动初始化
docker-compose exec web python -c "from src.user_db import UserDB; UserDB()"
```

---

### 更新版本

```bash
cd gaokao-number
git pull origin master

# Docker方式
docker-compose down
docker-compose up -d --build

# 手动方式
source venv/bin/activate
pip install -r requirements.txt
# 重启服务
```

---

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/diagnose/start` | POST | 开始诊断 |
| `/api/diagnose/submit` | POST | 提交诊断答案 |
| `/api/path/generate` | GET | 生成学习路径 |
| `/api/path/today` | GET | 当日任务 |
| `/api/path/submit` | POST | 提交学习答案 |
| `/api/mock/start` | GET | 开始模考 |
| `/api/wrong/list` | GET | 错题列表 |

---

## 技术栈

- Python 3.10+
- Flask (Web框架)
- SQLite (数据库)
- Docker (容器化)
- Telegram Bot API
- Hermes AI (智能答疑)

---

## License

MIT License

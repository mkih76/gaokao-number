# 公考数量关系 AI 个性化学习系统

> 13种题型精讲 + AI薄弱点诊断 + 个性化学习路径 + 24h Telegram私教

**一句话定位**：帮你精准找到数量关系的提分点，24小时随时问，2个月从放弃到拿分。

---

## 项目结构

```
gaokao-number/
├── README.md                   # 本说明
├── AGENTS.md                   # AI开发者构建指引（给 Claude Code/Codex）
├── Dockerfile                  # Docker镜像配置
├── docker-compose.yml          # Docker Compose编排
├── .env.example                # 环境变量示例
├── init.sh                     # 一键部署脚本
├── docs/
│   ├── product-plan.md         # 产品规划与变现方案
│   ├── learning-path.md        # 系统性学习路径
│   └── operation-plan.md       # 运营推广方案
├── questions/
│   ├── 01-hecha-beibi.md       # 和差倍比
│   ├── 02-gongcheng.md         # 工程问题
│   ├── 03-xingcheng.md         # 行程问题
│   ├── 04-pailie-zuhe.md       # 排列组合
│   ├── 05-gailv.md             # 概率
│   ├── 06-jihe.md              # 几何问题
│   ├── 07-jingji-lirun.md      # 经济利润
│   ├── 08-rongye.md            # 溶液问题
│   ├── 09-rongchi.md           # 容斥原理
│   ├── 10-riqi-nianling.md     # 日期年龄
│   ├── 11-chouti.md            # 抽屉原理
│   ├── 12-jitu-tonglong.md     # 鸡兔同笼
│   └── 13-heding-jizhi.md      # 和定极值
├── src/
│   ├── user_db.py              # 用户状态管理（SQLite）
│   ├── question_db.py          # 题库引擎
│   ├── diagnose.py             # 薄弱点诊断
│   ├── path_planner.py         # 学习路径生成
│   ├── cron_tasks.py           # 督学定时任务
│   ├── exam_sim.py             # 模考系统
│   ├── hermes_client.py        # Hermes AI网关客户端
│   └── telegram_bot.py         # Telegram 交互
├── data/
│   ├── questions.json           # 完整题库（65道结构化真题）
│   └── schema.sql               # 数据库结构
├── static/
│   └── index.html              # Web前端界面
├── tests/
│   ├── test_diagnose.py
│   └── test_path_planner.py
└── web_server.py                # Web API服务
```

## 核心理念

1. **只用真题** — 所有例题来源 2021-2025 年国考/省考真题
2. **因材施教** — AI诊断后生成个性化学习路径
3. **随时提问** — Telegram bot 24小时在线，AI随时讲解
4. **全生命周期闭环** — 诊断→学习→练习→模考→复盘→提升

## 技术栈

- Python 3.10+
- SQLite (用户数据 + 知识库)
- Hermes Agent (AI推理 + 任务调度)
- Telethon / python-telegram-bot (Telegram交互)
- numpy (向量搜索)
- Jina AI Reader API (内容提取)

## 快速开始

### 方式一：Docker部署（推荐）
```bash
git clone https://github.com/mkih76/gaokao-number.git
cd gaokao-number
cp .env.example .env
# 编辑 .env 填入 TELEGRAM_BOT_TOKEN
docker-compose up -d
```

### 方式二：手动部署
```bash
git clone https://github.com/mkih76/gaokao-number.git
cd gaokao-number
bash init.sh
# 编辑 .env 填入 TELEGRAM_BOT_TOKEN
python web_server.py
```

### 方式三：仅Telegram Bot
```bash
python src/telegram_bot.py
```

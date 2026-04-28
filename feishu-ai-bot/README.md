# 🤖 集品飞书 AI 机器人

> 让你的飞书群拥有 AI 超能力 — 智能对话 / AI 绘图 / 群聊总结 / 周报生成

[English](README_EN.md) | 中文

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Framework-Hermes_Agent-FF6B35" alt="Hermes Agent"/>
  <img src="https://img.shields.io/badge/SDK-lark--oapi-3370FF?logo=feishu" alt="Feishu"/>
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License"/>
</p>

---

## ✨ 功能亮点

| 功能 | 说明 |
|------|------|
| 💬 **AI 智能对话** | 群内 @机器人 即问即答，支持上下文记忆 |
| 🎨 **AI 绘图** | 自然语言描述即可生成图片（KIE nano-banana-2） |
| 📊 **群聊总结** | 自动汇总群聊关键信息 |
| 📝 **周报生成** | 一键生成团队周报 |
| ⏰ **定时推送** | 设定 cron 定时发送消息到群 |
| 🔌 **可扩展** | 基于 Hermes Agent，轻松添加新能力 |

---

## 🚀 快速开始

### 前置要求

- Python 3.11+
- 飞书开发者账号（[开放平台](https://open.feishu.cn/)）
- 飞书应用已创建并获取 App ID / App Secret

### 安装

```bash
git clone https://github.com/jipin-ai/ji_pin.git
cd ji_pin/feishu-ai-bot
pip install -r requirements.txt
```

### 配置

创建 `.env` 文件：

```bash
FEISHU_APP_ID=你的AppID
FEISHU_APP_SECRET=***
FEISHU_CONNECTION_MODE=websocket
```

### 启动

```bash
python bot.py
```

> 详细配置指南请查看 [docs/setup.md](docs/setup.md)

---

## 📁 项目结构

```
feishu-ai-bot/
├── src/
│   ├── bot.py           # 机器人主入口
│   ├── handlers/        # 消息处理器
│   └── utils/           # 工具函数
├── docs/                # 文档
├── screenshots/         # 功能截图
└── requirements.txt     # 依赖
```

---

## 🛠️ 技术栈

- [Hermes Agent](https://github.com/hermes-ai/hermes) — AI Agent 框架
- [lark-oapi](https://github.com/larksuite/oapi-sdk-python) — 飞书开放 API SDK
- Python 3.11+

---

## 📸 预览

> ⏳ 截图即将上线...

---

## 📄 许可证

MIT

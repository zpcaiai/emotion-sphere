---
title: Emotion Sphere 情感星球
emoji: 🌟
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
---

# Emotion Sphere 情感星球

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react)](https://reactjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 基于心理学、认知科学与行为科学的个人成长系统

## 🌟 核心特性

### 三层心理学引擎
- **L0 人格驱动层** - 识别完美主义、冒名顶替综合征等深层模式
- **L1 认知疗法层** - 完整CBT ABC模型（自动思维→中间信念→核心信念）
- **L2 状态调节层** - 实时心理状态监测与调节
- **L3/L4 叙事认同层** - Dan McAdams叙事认同理论（救赎/污染/转折点/稳定叙事）

### 四维崩溃检测
- 认知维度 - 注意力漂移、决策瘫痪
- 情绪维度 - 焦虑逃避、情绪崩塌
- 动机维度 - 拖延循环、目标断连
- 自我认知维度 - 自我否定、冒名顶替、完美主义冻结

### 架构增强
- 🔐 **安全** - 数据加密、GDPR合规、内容安全
- ⚡ **性能** - Redis缓存、连接池优化、异步数据库
- 📊 **可观测** - 结构化日志、性能监控、健康检查
- 🧪 **质量** - 代码质量工具、自动化测试、预提交钩子

## 📁 项目结构

```
emotion-sphere/
├── backend/              # FastAPI后端
│   ├── main.py          # API入口（限流、版本控制、标准化响应）
│   ├── psychology_engine.py  # 心理学引擎核心
│   ├── auth.py          # 认证模块
│   ├── security.py      # 加密/隐私/内容安全
│   ├── cache.py         # 缓存层
│   ├── db_pool.py       # 数据库连接池
│   ├── logging_config.py # 结构化日志
│   └── psychology_schema.sql  # 数据库Schema
├── src/                 # React前端
│   ├── main.jsx         # 应用入口
│   ├── router.jsx       # 路由配置
│   ├── api.js           # API客户端
│   ├── hooks/           # React Query Hooks
│   ├── providers/       # Query Provider
│   ├── components/      # UI组件
│   └── styles.css       # 全局样式
├── miniprogram/         # 微信小程序
├── tests/               # 测试用例
├── scripts/             # 工具脚本
│   ├── data-migration/  # 数据迁移脚本（历史）
│   └── utils/           # 工具脚本
├── docs/                # 文档
│   ├── architecture/    # 架构文档
│   ├── development/     # 开发文档
│   └── user/            # 用户文档
├── dist/                # 构建输出
└── public/              # 静态资源
```

## 🚀 快速开始

### 环境要求
- Python 3.9+
- Node.js 18+
- PostgreSQL 14+
- Redis (可选，用于缓存)

### 安装依赖

```bash
# 后端依赖
pip install -e ".[dev,test]"

# 前端依赖
npm install

# 预提交钩子
pre-commit install
```

### 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件配置数据库、密钥等
```

### 数据库初始化

```bash
# 初始化基础表
psql $DATABASE_URL -f db_init.sql

# 初始化心理学Schema
psql $DATABASE_URL -f backend/psychology_schema.sql
```

### 启动开发服务器

```bash
# 启动后端
uvicorn backend.main:app --reload --port 8000

# 启动前端（新终端）
npm run dev
```

访问 http://localhost:5173

## 📚 文档

- [架构文档](docs/architecture/SFDS_V2_ARCHITECTURE.md) - 系统设计文档
- [开发指南](docs/development/AUTH_FEATURES.md) - 功能实现详情
- [用户使用](docs/user/README.md) - 用户文档

## 🧪 测试

```bash
# 运行所有测试
pytest

# 带覆盖率
pytest --cov=backend --cov-report=html

# 代码质量检查
black backend/ src/
isort backend/ src/
flake8 backend/
mypy backend/
```

## 📦 部署

### Docker 部署

```bash
docker build -t emotion-sphere .
docker run -p 8000:8000 --env-file .env emotion-sphere
```

### 生产环境检查清单

- [ ] 设置强 `ENCRYPTION_KEY`
- [ ] 配置 `JWT_SECRET`
- [ ] 启用 HTTPS
- [ ] 配置 Redis 缓存
- [ ] 设置监控告警
- [ ] 配置日志收集

## 🤝 贡献

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

**注意**: 本项目涉及心理健康领域，仅作为自我成长工具使用，不可替代专业心理咨询。如有严重心理困扰，请寻求专业帮助。

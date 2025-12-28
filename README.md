# Scoop Easy

Windows 平台 [Scoop](https://scoop.sh/) 包管理器的图形化管理工具，增加 Scoop 的易用性。

![Vue](https://img.shields.io/badge/Vue-3.x-4FC08D?logo=vue.js)![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript)![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)

## 功能特性

- **软件管理** - 查看已安装软件、批量更新、卸载
- **版本控制** - 锁定版本、切换版本、切换关联应用
- **Bucket 管理** - 添加/移除软件源
- **软件搜索** - 搜索并安装新软件
- **操作日志** - 记录所有操作历史

## 环境要求

- Windows 10/11
- [Scoop](https://scoop.sh/) 已安装
- [Python](https://www.python.org/) 3.10+
- [Node.js](https://nodejs.org/) 18+
- [uv](https://github.com/astral-sh/uv) (Python 包管理)
- [pnpm](https://pnpm.io/) (Node.js 包管理)

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/scoop-easy.git
cd scoop-easy
```

### 2. 安装依赖

```bash
install.bat
```

### 3. 启动应用

**桌面模式（推荐）**

```bash
start-desktop.bat
```

双击即可启动独立窗口应用，无需浏览器。

**开发模式**

```bash
start-dev.bat
```

浏览器打开 http://localhost:5173

## 项目结构

```
scoop-easy/
├── backend/            # 后端 (FastAPI)
│   ├── main.py         # API 入口
│   ├── desktop.py      # 桌面模式入口
│   └── pyproject.toml
├── frontend/           # 前端 (Vue 3)
│   ├── src/
│   │   ├── api/        # API 调用
│   │   ├── components/
│   │   ├── stores/     # Pinia 状态管理
│   │   └── types/      # TypeScript 类型
│   └── package.json
├── install.bat         # 依赖安装脚本
├── start-dev.bat       # 开发模式启动
└── start-desktop.bat   # 桌面模式启动
```

## 技术栈

**前端**
- Vue 3 (Composition API)
- TypeScript
- Element Plus
- Pinia
- Vite

**后端**
- Python 3.10+
- FastAPI
- Pydantic
- PyWebView (桌面模式)

## License

MIT

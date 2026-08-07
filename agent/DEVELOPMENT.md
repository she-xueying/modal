# 全能智能体 - 开发文档

> **文档版本**: v1.0
> **最后更新**: 2026-08-04
> **核心原则**: 前一个阶段开发完成且验收通过后，方可进入下一阶段开发

---
后端: http://localhost:8000 
前端: http://localhost:5173 

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 需求拆解](#2-需求拆解)
- [3. 技术选型](#3-技术选型)
- [4. 项目目录结构](#4-项目目录结构)
- [5. 开发流程（6 阶段）](#5-开发流程6-阶段)
  - [阶段 1：基础搭建 + 对话中枢](#阶段-1基础搭建--对话中枢-)
  - [阶段 2：视觉理解 / OCR](#阶段-2视觉理解--ocr-)
  - [阶段 3：文档 / 对话总结](#阶段-3文档--对话总结-)
  - [阶段 4：周报生成引擎](#阶段-4周报生成引擎-)
  - [阶段 5：论文流程图生成](#阶段-5论文流程图生成-)
  - [阶段 6：统一路由 + RAG + 部署](#阶段-6统一路由--rag--部署-)
- [6. 周报模板规格](#6-周报模板规格)
- [7. 部署方案](#7-部署方案)
- [8. 验收检查清单总表](#8-验收检查清单总表)

---

## 1. 项目概述

### 1.1 项目定位

一个智能体助手，集成聊天问答、图片识别、周报生成、文档总结、论文流程图生成等能力，通过统一的 React 界面提供服务。

### 1.2 核心能力一览

| 能力 | 描述 |
|------|------|
| 对话中枢 | 多轮聊天，解决生活学习中的各种问题 |
| 视觉理解 | 图片文字识别（OCR）+ 图片内容理解 |
| 周报生成 | 接受碎片化工作记录，自动整理成符合公司模板的正式周报 |
| 文档总结 | 总结论文、文档、对话的关键信息 |
| 论文流程图 | 将论文方法论整理成流程图输出 |
| 统一入口 | 一个界面串联所有能力，自动路由到对应功能 |

---

## 2. 需求拆解

### 2.1 功能模块矩阵

| 模块 | 功能 | 输入 | 输出 | 关键技术点 |
|------|------|------|------|-----------|
| ① 对话中枢 | 聊天、问答 | 文本消息 | 文本回复（流式） | LLM + 多轮对话管理 + 长期记忆 |
| ② 视觉理解 | 图片识别 | 图片文件 | 文字内容 / 图片描述 | 多模态 LLM + OCR 引擎 |
| ③ 周报生成 | 碎片记录→正式周报 | 文本记录（多条） | .docx 周报文件 | 模板系统 + LangGraph 编排 + 信息聚合 |
| ④ 文档总结 | 关键信息提取 | PDF/Word/TXT/对话记录 | 结构化摘要 | 文档解析 + Map-Reduce 摘要 |
| ⑤ 论文流程图 | 方法论可视化 | 论文 PDF/文本 | Mermaid 流程图 | 结构化抽取 + Mermaid 生成 + 渲染 |
| ⑥ 统一入口 | 能力路由 | 用户自然语言输入 | 自动调用对应模块 | Agent 路由 + 前端集成 |

### 2.2 非功能需求

- **响应速度**: 对话首字延迟 < 2s，流式输出
- **中文优先**: 所有提示词、模板、摘要以中文输出
- **可扩展**: 新功能模块可插拔式接入
- **本地部署**: 支持 Docker Compose 一键部署

---

## 3. 技术选型

### 3.1 技术栈总表

| 层级 | 选型 | 用途 | 依据 |
|------|------|------|------|
| **LLM（主）** | GLM-4V (智谱) | 对话 + 视觉理解 | 中文能力强；多模态支持图片理解；API 稳定 |
| **LLM（备）** | DeepSeek-V3 | 推理/代码任务 | 性价比高、推理能力强，作为降级方案 |
| **Agent 编排** | LangGraph + LangChain | 多步骤任务编排 + 工具调用 | 状态图模型适配多步流程；LangChain 原生支持工具调用（搜索等） |
| **联网搜索** | Tavily API | 实时信息获取（天气/新闻/股价等） | 专为 AI Agent 设计，返回结构化结果，免费额度充足 |
| **OCR** | PaddleOCR | 图片纯文字识别 | 中文识别效果好、开源免费、支持印刷体/手写体 |
| **文档解析** | PyMuPDF + pdfplumber | PDF 解析 | PyMuPDF 速度快，pdfplumber 表格识别好，互补 |
| **文档解析** | python-docx | Word 读写 | .docx 读写标准库，用于周报导出 |
| **文档解析** | Unstructured | 通用格式解析 | 统一接口解析多种格式 |
| **流程图** | Mermaid.js | 流程图渲染 | 纯文本描述→自动渲染，LLM 擅长生成 Mermaid 语法 |
| **向量检索** | Chroma（开发）/ Qdrant（生产） | RAG 文档检索 | Chroma 轻量零配置；Qdrant 性能好支持过滤 |
| **Embedding** | bge-large-zh-v1.5 | 中文向量化 | 中文检索效果好、开源可本地部署 |
| **模板引擎** | Jinja2 | 周报模板渲染 | 成熟的 Python 模板引擎，灵活定义周报结构 |
| **数据库** | SQLite（开发）/ PostgreSQL（生产） | 数据持久化 | SQLite 零部署；存储碎片记录、对话历史、周报 |
| **缓存** | Redis（可选） | 短期对话缓存 | 加速多轮对话，可选组件 |
| **后端** | FastAPI (Python) | API 服务 | 异步高性能、自动生成文档、与 AI 生态同语言 |
| **前端** | React + TypeScript + Vite | 用户界面 | 组件生态丰富、TypeScript 类型安全、Vite 构建快 |
| **前端 UI 库** | Ant Design | 组件库 | 中文友好、企业级组件齐全（表格、上传、编辑器等） |
| **状态管理** | Zustand | 前端状态 | 轻量简洁，适合中型应用 |
| **部署** | Docker Compose | 容器化部署 | 一键启动前后端 + 数据库 |

### 3.2 技术架构图

```
┌──────────────────────────────────────────────────────────┐
│                    前端 (React + TypeScript)                │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐  │
│  │ 对话页  │ │ 图片页  │ │ 周报页  │ │ 总结页  │ │流程图页 │  │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘  │
├──────────────────────────────────────────────────────────┤
│                    后端 API (FastAPI)                      │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              统一 Agent 路由层（阶段6）                 │ │
│  └──────────────────────────────────────────────────────┘ │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────┐│
│  │对话服务  │ │视觉服务  │ │周报服务  │ │总结服务  │ │流程图 ││
│  │         │ │         │ │LangGraph│ │Map-Reduce│ │Mermaid││
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └──────┘│
├──────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐ │
│  │  LLM: GLM-4V (主) / DeepSeek-V3 (备)                  │ │
│  │  视觉: GLM-4V + PaddleOCR                             │ │
│  │  搜索: Tavily API (联网搜索)                           │ │
│  │  解析: PyMuPDF / pdfplumber / python-docx / Unstructured│
│  │  检索: Chroma + bge-large-zh-v1.5                     │ │
│  │  模板: Jinja2                                          │ │
│  │  存储: SQLite / PostgreSQL + Redis(可选)               │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## 4. 项目目录结构

```
d:\modal\agent\
├── DEVELOPMENT.md                 # 本文档
├── README.md
├── docker-compose.yml             # 部署编排
├── Dockerfile.backend
├── Dockerfile.frontend
├── .env.example                   # 环境变量模板
│
├── backend/                       # 后端
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI 入口
│   │   ├── config.py              # 配置管理（读取 .env）
│   │   │
│   │   ├── api/                   # 路由层
│   │   │   ├── __init__.py
│   │   │   ├── chat.py            # 对话接口        (阶段1)
│   │   │   ├── vision.py          # 图片识别接口     (阶段2)
│   │   │   ├── summary.py         # 文档总结接口     (阶段3)
│   │   │   ├── report.py          # 周报生成接口     (阶段4)
│   │   │   ├── flowchart.py       # 流程图生成接口   (阶段5)
│   │   │   └── router.py          # 统一路由         (阶段6)
│   │   │
│   │   ├── core/                  # 核心能力封装
│   │   │   ├── __init__.py
│   │   │   ├── llm.py             # LLM 客户端封装   (阶段1)
│   │   │   ├── search.py          # 联网搜索封装     (阶段1)
│   │   │   ├── ocr.py             # OCR 引擎封装     (阶段2)
│   │   │   ├── parser.py          # 文档解析封装     (阶段3)
│   │   │   ├── rag.py             # RAG 检索封装     (阶段6)
│   │   │   └── prompts.py         # 提示词模板       (阶段1起逐步补充)
│   │   │
│   │   ├── services/              # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── chat_service.py    # 对话服务         (阶段1)
│   │   │   ├── vision_service.py  # 视觉服务         (阶段2)
│   │   │   ├── summary_service.py # 总结服务         (阶段3)
│   │   │   ├── report_service.py  # 周报服务         (阶段4)
│   │   │   └── flowchart_service.py # 流程图服务     (阶段5)
│   │   │
│   │   └── models/                # 数据模型层
│   │       ├── __init__.py
│   │       ├── database.py        # 数据库连接与表定义 (阶段1)
│   │       └── schemas.py         # Pydantic 请求/响应模型 (阶段1起逐步补充)
│   │
│   └── templates/                 # 模板文件
│       └── weekly_report.py       # 周报 Jinja2 模板   (阶段4)
│
├── frontend/                      # 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx               # React 入口
│       ├── App.tsx                # 根组件 + 路由
│       │
│       ├── components/            # 通用组件
│       │   ├── ChatPanel.tsx      # 聊天面板          (阶段1)
│       │   ├── MessageBubble.tsx  # 消息气泡          (阶段1)
│       │   ├── ImageUpload.tsx    # 图片上传          (阶段2)
│       │   ├── DocUploader.tsx    # 文档上传          (阶段3)
│       │   ├── FragmentInput.tsx  # 碎片记录输入      (阶段4)
│       │   ├── ReportPreview.tsx  # 周报预览          (阶段4)
│       │   ├── FlowchartView.tsx  # 流程图渲染        (阶段5)
│       │   └── Sidebar.tsx        # 侧边栏导航        (阶段1)
│       │
│       ├── pages/                 # 页面
│       │   ├── ChatPage.tsx       # 对话页            (阶段1)
│       │   ├── VisionPage.tsx     # 图片识别页        (阶段2)
│       │   ├── SummaryPage.tsx    # 文档总结页        (阶段3)
│       │   ├── ReportPage.tsx     # 周报生成页        (阶段4)
│       │   └── FlowchartPage.tsx  # 流程图页          (阶段5)
│       │
│       ├── services/              # API 调用
│       │   └── api.ts             # 统一 API 封装     (阶段1起逐步补充)
│       │
│       ├── stores/                # 状态管理
│       │   └── useStore.ts        # Zustand 全局状态  (阶段1)
│       │
│       └── styles/                # 样式
│           └── global.css
│
└── config/
    └── settings.yaml              # 全局配置
```

> **说明**: 每个文件后标注的 `(阶段N)` 表示该文件在对应阶段创建。后续阶段可在已有文件基础上扩展。

---

## 5. 开发流程（6 阶段）

### 总览

| 阶段 | 名称 | 难度 | 预计工期 | 前置条件 |
|------|------|------|---------|---------|
| 1 | 基础搭建 + 对话中枢 | ★☆☆☆☆ | 2-3 天 | 无 |
| 2 | 视觉理解 / OCR | ★★☆☆☆ | 2-3 天 | 阶段1验收通过 |
| 3 | 文档 / 对话总结 | ★★★☆☆ | 3-4 天 | 阶段2验收通过 |
| 4 | 周报生成引擎 | ★★★★☆ | 3-4 天 | 阶段3验收通过 |
| 5 | 论文流程图生成 | ★★★★★ | 2-3 天 | 阶段4验收通过 |
| 6 | 统一路由 + RAG + 部署 | ★★★★★ | 2-3 天 | 阶段5验收通过 |

**总预计工期: 14-20 个工作日**

---

### 阶段 1：基础搭建 + 对话中枢 ★☆☆☆☆

#### 开发目标

搭建项目骨架，实现最基本的对话功能：前端发消息 -> 后端调 GLM-4V -> 流式返回响应。

#### 任务清单

```
1.1  后端初始化
     ├─ 1.1.1  创建 backend/ 目录结构
     ├─ 1.1.2  编写 requirements.txt（fastapi, uvicorn, httpx, python-dotenv, sqlalchemy, pydantic, langchain, langchain-community, tavily-python, sse-starlette）
     ├─ 1.1.3  编写 config.py 读取环境变量（API Key、模型名、数据库路径）
     ├─ 1.1.4  编写 .env.example
     └─ 1.1.5  编写 main.py（FastAPI 实例、CORS 配置、路由注册）

1.2  LLM 客户端封装
     ├─ 1.2.1  编写 core/llm.py：封装 GLM-4V API 调用
     ├─ 1.2.2  实现同步调用 + 流式调用两种模式
     └─ 1.2.3  实现错误处理与重试机制

1.3  数据库初始化
     ├─ 1.3.1  编写 models/database.py：SQLite 连接 + SQLAlchemy 基础
     ├─ 1.3.2  定义 Conversation 表（id, title, created_at）
     └─ 1.3.3  定义 Message 表（id, conversation_id, role, content, created_at）

1.4  对话 API
     ├─ 1.4.1  编写 api/chat.py
     ├─ 1.4.2  POST /api/chat：发送消息，返回流式响应（SSE）
     ├─ 1.4.3  GET /api/conversations：获取对话列表
     ├─ 1.4.4  GET /api/conversations/{id}：获取对话历史
     └─ 1.4.5  DELETE /api/conversations/{id}：删除对话

1.5  对话服务层
     ├─ 1.5.1  编写 services/chat_service.py
     ├─ 1.5.2  实现多轮对话上下文管理（维护消息历史，控制上下文窗口）
     └─ 1.5.3  实现对话持久化（存储到 SQLite）

1.6  前端初始化
     ├─ 1.6.1  使用 Vite 创建 React + TypeScript 项目
     ├─ 1.6.2  安装 Ant Design、Zustand、react-router-dom、react-markdown
     ├─ 1.6.3  配置 vite.config.ts（代理后端 API）
     └─ 1.6.4  编写 App.tsx 基础布局（侧边栏 + 主内容区）

1.7  前端对话界面
     ├─ 1.7.1  编写 components/Sidebar.tsx：对话列表 + 新建对话按钮
     ├─ 1.7.2  编写 components/ChatPanel.tsx：消息展示 + 输入框
     ├─ 1.7.3  编写 components/MessageBubble.tsx：消息气泡（支持 Markdown 渲染）
     ├─ 1.7.4  编写 services/api.ts：封装后端 API 调用（含 SSE 流式接收）
     ├─ 1.7.5  编写 stores/useStore.ts：对话状态管理
     └─ 1.7.6  编写 pages/ChatPage.tsx：组装对话页面

1.8  联调测试
     ├─ 1.8.1  前后端联调：发消息 -> 流式接收 -> 渲染
     ├─ 1.8.2  测试多轮对话上下文保持
     └─ 1.8.3  测试对话历史持久化（刷新页面后历史不丢失）

1.9  联网搜索能力
     ├─ 1.9.1  注册 Tavily API，获取 API Key
     ├─ 1.9.2  编写 core/search.py：封装 Tavily 搜索调用
     │         └─ tavily_search(query, max_results=5) -> 搜索结果列表
     ├─ 1.9.3  使用 LangChain Tools 定义 web_search 工具
     │         └─ 工具描述："当用户询问实时信息（天气、新闻、股价等）时调用此工具搜索"
     ├─ 1.9.4  在 chat_service 中集成工具调用：
     │         ├─ GLM-4V 判断是否需要搜索 -> 调用 web_search 工具
     │         ├─ 将搜索结果作为上下文传回 LLM 生成最终回答
     │         └─ 支持流式输出搜索后的回答
     └─ 1.9.5  前端无需改动（工具调用对用户透明，用户只看到最终回答）
```

#### 验收标准

> **以下全部通过才能进入阶段 2**

| # | 验收项 | 验证方式 |
|---|--------|---------|
| V1.1 | 前端启动后显示对话界面，侧边栏可新建/切换/删除对话 | 手动操作 |
| V1.2 | 输入消息后，后端调用 GLM-4V 并流式返回，前端逐字显示 | 发送消息观察流式效果 |
| V1.3 | 连续多轮对话中，LLM 能理解上下文 | 问"刚才我说了什么"验证 |
| V1.4 | 刷新浏览器后，对话历史仍存在 | 刷新页面检查 |
| V1.5 | API 返回的错误（如 Key 无效）在前端有友好提示 | 故意填错 Key 测试 |
| V1.6 | Markdown 格式的回复正确渲染（代码块、列表、表格） | 让 LLM 输出 Markdown 内容 |
| V1.7 | 问"今天天气怎么样"等实时问题，能联网搜索并回答 | 提问实时问题验证 |
| V1.8 | 问通用知识问题（如"什么是递归"），不触发搜索直接回答 | 提问通用知识验证 |

#### 产出物

- 可运行的 FastAPI 后端（端口 8000）
- 可运行的 React 前端（端口 5173）
- SQLite 数据库文件（对话历史）

---

### 阶段 2：视觉理解 / OCR ★★☆☆☆

#### 开发目标

用户可上传图片，智能体识别图片中的文字（OCR）或理解图片内容并回答问题。

#### 任务清单

```
2.1  后端 - 视觉服务
     ├─ 2.1.1  编写 core/ocr.py：封装 PaddleOCR
     │         ├─ init_paddleocr()：初始化引擎（中文模型）
     │         └─ extract_text(image_bytes) -> str：提取图片文字
     ├─ 2.1.2  扩展 core/llm.py：增加 vision_chat() 方法
     │         └─ 将图片 base64 编码 + 文本一起发送给 GLM-4V
     ├─ 2.1.3  编写 services/vision_service.py
     │         ├─ recognize_text(image) -> str：纯 OCR 文字提取
     │         ├─ understand_image(image, question) -> str：图片理解问答
     │         └─ hybrid_recognize(image, question) -> str：OCR + LLM 联合
     └─ 2.1.4  编写 api/vision.py
               ├─ POST /api/vision/ocr：上传图片，返回识别文字
               └─ POST /api/vision/understand：上传图片 + 提问，返回回答

2.2  前端 - 图片识别界面
     ├─ 2.2.1  编写 components/ImageUpload.tsx
     │         ├─ Ant Design Upload 组件（支持拖拽上传、粘贴）
     │         └─ 图片预览
     ├─ 2.2.2  编写 pages/VisionPage.tsx
     │         ├─ 左侧：图片上传 + 预览区
     │         ├─ 右侧：识别结果 / 问答区
     │         └─ 模式切换：纯 OCR / 图片理解
     ├─ 2.2.3  扩展 services/api.ts：增加 vision 相关 API 调用
     └─ 2.2.4  扩展 Sidebar.tsx：增加"图片识别"导航项

2.3  联调测试
     ├─ 2.3.1  上传含中文文字的图片，验证 OCR 识别准确率
     ├─ 2.3.2  上传截图/照片，提问图片内容，验证 GLM-4V 理解能力
     └─ 2.3.3  测试大图片（>5MB）上传与处理
```

#### 验收标准

> **以下全部通过才能进入阶段 3**

| # | 验收项 | 验证方式 |
|---|--------|---------|
| V2.1 | 上传含文字的图片，OCR 模式能提取出文字 | 上传文档截图验证 |
| V2.2 | 上传图片后切换"理解"模式，提问能得到关于图片内容的回答 | 上传照片提问验证 |
| V2.3 | 图片识别结果可一键复制 | 点击复制按钮验证 |
| V2.4 | 上传超大图片不崩溃，有 loading 状态 | 上传大图验证 |
| V2.5 | 非图片文件上传被拦截并提示 | 上传 .txt 文件验证 |

#### 产出物

- 图片识别 API（OCR + 视觉理解）
- 图片识别前端页面
- PaddleOCR 集成

---

### 阶段 3：文档 / 对话总结 ★★★☆☆

#### 开发目标

用户上传论文/文档（PDF/Word/TXT），或选择一段对话历史，智能体输出结构化的关键信息摘要。

#### 任务清单

```
3.1  后端 - 文档解析
     ├─ 3.1.1  编写 core/parser.py
     │         ├─ parse_pdf(file_bytes) -> str：PyMuPDF 提取文本
     │         ├─ parse_docx(file_bytes) -> str：python-docx 提取文本
     │         ├─ parse_txt(file_bytes) -> str：纯文本读取
     │         └─ parse_file(file) -> str：根据扩展名自动分发
     ├─ 3.1.2  实现文本分块（chunking）
     │         ├─ 按段落/标题分块
     │         └─ 支持配置块大小与重叠

3.2  后端 - 总结服务
     ├─ 3.2.1  编写 services/summary_service.py
     ├─ 3.2.2  实现三种总结模式：
     │         ├─ summarize_paper(text) -> PaperSummary
     │         │   提取：研究背景、研究方法、实验结果、结论、创新点
     │         ├─ summarize_document(text) -> DocSummary
     │         │   提取：核心观点、关键数据、行动项、待跟进问题
     │         └─ summarize_conversation(messages) -> ConvSummary
     │             提取：讨论主题、关键决策、待办事项、未解决问题
     └─ 3.2.3  实现 Map-Reduce 长文档摘要策略
               ├─ Map: 对每个分块调用 LLM 生成局部摘要
               └─ Reduce: 合并局部摘要生成全局摘要

3.3  后端 - 总结 API
     ├─ 3.3.1  编写 api/summary.py
     ├─ 3.3.2  POST /api/summary/document：上传文档 + 选择模式，返回摘要
     └─ 3.3.3  POST /api/summary/conversation：传入对话 ID，返回摘要

3.4  后端 - 提示词
     ├─ 3.4.1  编写 core/prompts.py 中的总结提示词
     │         ├─ PAPER_SUMMARY_PROMPT：论文结构化摘要
     │         ├─ DOC_SUMMARY_PROMPT：文档关键信息提取
     │         └─ CONV_SUMMARY_PROMPT：对话要点总结

3.5  前端 - 总结界面
     ├─ 3.5.1  编写 components/DocUploader.tsx
     │         └─ 支持拖拽上传 PDF/Word/TXT
     ├─ 3.5.2  编写 pages/SummaryPage.tsx
     │         ├─ 上传区：文件上传 + 模式选择（论文/文档/对话）
     │         ├─ 结果区：结构化展示摘要（分区显示）
     │         └─ 操作区：复制摘要 / 重新总结 / 导出
     ├─ 3.5.3  扩展 Sidebar.tsx：增加"文档总结"导航项
     └─ 3.5.4  扩展 api.ts：增加 summary 相关调用

3.6  联调测试
     ├─ 3.6.1  上传一篇学术论文 PDF，验证论文摘要结构完整性
     ├─ 3.6.2  上传一个 Word 文档，验证文档摘要提取
     ├─ 3.6.3  选择一段已有对话，验证对话总结
     └─ 3.6.4  上传超长文档（>50页），验证 Map-Reduce 分块摘要效果
```

#### 验收标准

> **以下全部通过才能进入阶段 4**

| # | 验收项 | 验证方式 |
|---|--------|---------|
| V3.1 | 上传 PDF 论文，输出包含"研究背景/方法/实验/结论"的结构化摘要 | 上传真实论文验证 |
| V3.2 | 上传 Word 文档，输出核心观点和关键数据 | 上传工作文档验证 |
| V3.3 | 选择已有对话，输出讨论主题和待办事项 | 选一段对话验证 |
| V3.4 | 超长文档（>50页）不超时不报错，摘要覆盖全文要点 | 上传长文档验证 |
| V3.5 | 摘要结果可复制、可导出为文本 | 点击导出验证 |
| V3.6 | 不支持的文件格式有友好提示 | 上传 .xlsx 验证 |

#### 产出物

- 文档解析模块（PDF/Word/TXT）
- 三种总结模式（论文/文档/对话）
- Map-Reduce 长文档摘要
- 文档总结前端页面

---

### 阶段 4：周报生成引擎 ★★★★☆

#### 开发目标

用户随时记录碎片化工作内容（文本/语音转文字/图片提取），周末一键生成符合公司模板的正式 Word 周报。

#### 任务清单

```
4.1  后端 - 数据模型
     ├─ 4.1.1  扩展 models/database.py
     │         ├─ Fragment 表：id, content, category, tags, created_at, week_of
     │         └─ Report 表：id, week_of, content, docx_path, created_at
     └─ 4.1.2  定义 Pydantic 模型（schemas.py）
               ├─ FragmentCreate, FragmentResponse
               └─ ReportGenerateRequest, ReportResponse

4.2  后端 - 碎片记录管理
     ├─ 4.2.1  编写 api/fragment.py（或合并到 report.py）
     │         ├─ POST /api/fragments：新增碎片记录
     │         ├─ GET /api/fragments?week_of=：按周查询
     │         ├─ DELETE /api/fragments/{id}：删除
     │         └─ PUT /api/fragments/{id}：编辑
     └─ 4.2.2  实现 LLM 自动分类
               └─ 新增碎片时，LLM 自动打标签（业务开发/问题修复/工程优化/其他）

4.3  后端 - 周报模板系统
     ├─ 4.3.1  编写 templates/weekly_report.py
     │         ├─ 定义 Jinja2 模板字符串（严格匹配公司模板格式，见第6节）
     │         └─ 定义字段映射：碎片记录 -> 模板各字段
     └─ 4.3.2  编写 core/prompts.py 中的周报提示词
               ├─ CLASSIFY_PROMPT：碎片分类提示词
               └─ REPORT_GENERATE_PROMPT：周报生成提示词

4.4  后端 - LangGraph 周报生成流程
     ├─ 4.4.1  编写 services/report_service.py
     ├─ 4.4.2  定义 LangGraph 状态图：
     │
     │   [开始] -> [节点A: 拉取本周碎片] -> [节点B: LLM分类归纳]
     │                                                |
     │           [节点D: 导出docx] <- [节点C: 填充模板生成正文]
     │                |
     │             [结束]
     │
     ├─ 4.4.3  节点A：按 week_of 拉取所有碎片记录
     ├─ 4.4.4  节点B：LLM 将碎片分类归纳到模板四个板块
     │         ├─ 已完成工作（业务开发/问题修复/工程优化/其他）
     │         ├─ 进行中工作
     │         ├─ 遇到问题与解决方案
     │         └─ 下周工作计划（LLM 根据进行中工作推断）
     ├─ 4.4.5  节点C：Jinja2 渲染模板，生成正式周报文本
     └─ 4.4.6  节点D：python-docx 生成 .docx 文件

4.5  后端 - 周报 API
     ├─ 4.5.1  编写 api/report.py
     │         ├─ POST /api/report/generate：生成周报（可选指定周日期）
     │         ├─ GET /api/report/list：周报历史列表
     │         ├─ GET /api/report/{id}：查看周报内容
     │         └─ GET /api/report/{id}/download：下载 .docx
     └─ 4.5.2  支持生成后人工编辑修正再保存

4.6  前端 - 周报界面
     ├─ 4.6.1  编写 components/FragmentInput.tsx
     │         ├─ 快速输入框（支持回车快速提交）
     │         ├─ 碎片列表（按时间倒序，显示标签）
     │         └─ 编辑/删除单条碎片
     ├─ 4.6.2  编写 components/ReportPreview.tsx
     │         ├─ 预览生成的周报（Markdown/富文本渲染）
     │         ├─ 支持手动编辑修正
     │         └─ 下载 .docx 按钮
     ├─ 4.6.3  编写 pages/ReportPage.tsx
     │         ├─ 左侧：碎片记录输入 + 列表
     │         ├─ 右侧：周报预览 + 编辑
     │         └─ 顶部：周选择器 + "生成周报"按钮
     ├─ 4.6.4  扩展 Sidebar.tsx：增加"周报管理"导航项
     └─ 4.6.5  扩展 api.ts：增加 fragment + report 相关调用

4.7  联调测试
     ├─ 4.7.1  录入 10+ 条碎片记录（覆盖不同类别）
     ├─ 4.7.2  点击"生成周报"，验证输出符合公司模板格式
     ├─ 4.7.3  下载 .docx，在 Word 中打开验证格式正确
     ├─ 4.7.4  编辑修正周报后保存，验证更新生效
     └─ 4.7.5  切换不同周，验证历史周报可查看
```

#### 验收标准

> **以下全部通过才能进入阶段 5**

| # | 验收项 | 验证方式 |
|---|--------|---------|
| V4.1 | 可快速录入碎片记录，自动打标签分类 | 录入多条记录验证 |
| V4.2 | 点击"生成周报"后，输出严格符合公司模板四大板块 | 对照模板检查 |
| V4.3 | 周报内容涵盖本周所有碎片记录，无遗漏 | 对照录入内容检查 |
| V4.4 | "下周工作计划"由 LLM 根据进行中工作合理推断 | 检查计划合理性 |
| V4.5 | 下载的 .docx 在 Word 中打开格式正确（标题/缩进/编号） | 下载后用 Word 打开 |
| V4.6 | 可手动编辑周报内容并保存 | 编辑后刷新验证 |
| V4.7 | 可查看历史周的周报 | 切换周验证 |
| V4.8 | 碎片记录为零时，有友好提示而非生成空周报 | 不录入直接生成验证 |

#### 产出物

- 碎片记录管理（增删改查 + 自动分类）
- LangGraph 周报生成流程
- Jinja2 周报模板（匹配公司格式）
- .docx 导出功能
- 周报管理前端页面

---

### 阶段 5：论文流程图生成 ★★★★★

#### 开发目标

用户上传论文，智能体自动提取方法论/实验流程，生成 Mermaid 流程图，支持编辑和导出。

#### 任务清单

```
5.1  后端 - 流程图生成服务
     ├─ 5.1.1  编写 services/flowchart_service.py
     ├─ 5.1.2  定义 LangGraph 状态图：
     │
     │   [开始] -> [节点A: 论文解析提取方法章节] -> [节点B: LLM识别步骤与关系]
     │                                                      |
     │           [节点D: 语法校验] <- [节点C: 生成Mermaid代码]
     │                |
     │         (校验失败?) -- 是 --> [节点C: 重新生成] (最多重试3次)
     │            |
     │           否
     │            v
     │         [结束: 返回Mermaid代码]
     │
     ├─ 5.1.3  节点A：调用阶段3的 parser 解析论文，定位方法/实验章节
     ├─ 5.1.4  节点B：LLM 提取关键步骤、决策点、流转关系
     │         输出结构化 JSON：{steps: [{id, name, type, next, condition}]}
     ├─ 5.1.5  节点C：LLM 将结构化步骤转为 Mermaid flowchart 语法
     └─ 5.1.6  节点D：Mermaid 语法校验（正则 + 结构检查）

5.2  后端 - 提示词
     ├─ 5.2.1  编写 core/prompts.py 中的流程图提示词
     │         ├─ EXTRACT_STEPS_PROMPT：从论文文本提取方法步骤
     │         └─ MERMAID_GENERATE_PROMPT：将步骤转为 Mermaid 代码
     └─ 5.2.2  提示词约束：
               ├─ 只使用 Mermaid flowchart 语法
               ├─ 节点命名简洁（<15字）
               ├─ 决策分支用菱形节点
               └─ 输出纯 Mermaid 代码（不含 ```mermaid 标记）

5.3  后端 - 流程图 API
     └─ 5.3.1  编写 api/flowchart.py
               ├─ POST /api/flowchart/generate：上传论文，返回 Mermaid 代码
               └─ POST /api/flowchart/validate：校验 Mermaid 语法

5.4  前端 - 流程图界面
     ├─ 5.4.1  安装 mermaid.js（npm install mermaid）
     ├─ 5.4.2  编写 components/FlowchartView.tsx
     │         ├─ Mermaid 代码编辑器（左）
     │         ├─ 流程图实时渲染（右）
     │         └─ 编辑后实时刷新预览
     ├─ 5.4.3  编写 pages/FlowchartPage.tsx
     │         ├─ 顶部：论文上传区
     │         ├─ 中部：Mermaid 代码 + 流程图预览（左右分栏）
     │         └─ 底部：导出按钮（PNG / SVG / .mmd 文件）
     ├─ 5.4.4  扩展 Sidebar.tsx：增加"论文流程图"导航项
     └─ 5.4.5  扩展 api.ts：增加 flowchart 相关调用

5.5  联调测试
     ├─ 5.5.1  上传一篇方法论文（如 ResNet 论文），验证流程图生成
     ├─ 5.5.2  手动修改 Mermaid 代码，验证实时预览刷新
     ├─ 5.5.3  导出 PNG/SVG，验证图片清晰完整
     └─ 5.5.4  上传非方法类论文（如综述），验证降级处理（提示无法提取流程）
```

#### 验收标准

> **以下全部通过才能进入阶段 6**

| # | 验收项 | 验证方式 |
|---|--------|---------|
| V5.1 | 上传论文 PDF，自动生成 Mermaid 流程图 | 上传真实论文验证 |
| V5.2 | 流程图逻辑与论文方法步骤基本一致 | 人工对照论文检查 |
| V5.3 | 流程图节点命名简洁，布局清晰 | 视觉检查 |
| V5.4 | Mermaid 代码可手动编辑，实时刷新预览 | 修改代码验证 |
| V5.5 | 可导出 PNG 和 SVG 格式 | 点击导出验证 |
| V5.6 | 非方法类论文有友好降级提示 | 上传综述论文验证 |
| V5.7 | 生成的 Mermaid 语法无错误（渲染不报错） | 检查渲染结果 |

#### 产出物

- 论文方法提取服务
- Mermaid 流程图生成（含语法校验与重试）
- 流程图渲染 + 编辑前端页面
- PNG/SVG 导出功能

---

### 阶段 6：统一路由 + RAG + 部署 ★★★★★

#### 开发目标

将所有能力整合为统一入口，用户用自然语言描述需求，智能体自动路由到对应功能。搭建 RAG 知识库增强文档问答。Docker 一键部署。

#### 任务清单

```
6.1  统一 Agent 路由
     ├─ 6.1.1  编写 api/router.py
     │         ├─ POST /api/agent：统一入口，接收自然语言 + 可选附件
     │         └─ LLM 意图识别 -> 路由到对应 service
     ├─ 6.1.2  定义意图分类提示词
     │         ├─ chat：日常聊天问答
     │         ├─ vision：图片识别（检测到图片附件）
     │         ├─ summary：文档总结（检测到文档附件）
     │         ├─ report：周报生成（关键词：周报/本周工作/碎片）
     │         └─ flowchart：流程图（关键词：论文/流程图/方法图）
     └─ 6.1.3  前端 ChatPage 升级：支持在对话中直接上传文件
               └─ 根据附件类型 + 文本意图自动触发对应功能

6.2  RAG 知识库（可选增强）
     ├─ 6.2.1  编写 core/rag.py
     │         ├─ 初始化 Chroma 向量库
     │         ├─ add_documents(text, metadata)：添加文档
     │         └─ search(query, top_k)：相似度检索
     ├─ 6.2.2  集成 bge-large-zh-v1.5 embedding 模型
     ├─ 6.2.3  在对话服务中增加 RAG 增强
     │         └─ 用户提问 -> 先检索知识库 -> 带检索结果调用 LLM
     └─ 6.2.4  前端增加"知识库管理"入口（上传文档到知识库）

6.3  错误处理与降级
     ├─ 6.3.1  LLM 超时/限流：自动切换到备用模型（DeepSeek-V3）
     ├─ 6.3.2  OCR 失败：降级到 GLM-4V 视觉识别
     ├─ 6.3.3  文档解析失败：提示用户检查格式
     └─ 6.3.4  全局异常处理中间件

6.4  性能优化
     ├─ 6.4.1  大文档处理改为异步任务（后台处理 + 轮询结果）
     ├─ 6.4.2  对话流式输出优化（SSE 连接管理）
     └─ 6.4.3  前端懒加载（各功能页面按需加载）

6.5  Docker 部署
     ├─ 6.5.1  编写 Dockerfile.backend（Python + PaddleOCR + 依赖）
     ├─ 6.5.2  编写 Dockerfile.frontend（Node 构建 + Nginx 托管）
     ├─ 6.5.3  编写 docker-compose.yml
     │         ├─ backend 服务（端口 8000）
     │         ├─ frontend 服务（端口 80）
     │         └─ 数据卷挂载（数据库、上传文件、知识库）
     ├─ 6.5.4  编写 .env.example（所有配置项）
     └─ 6.5.5  编写 README.md 部署说明

6.6  最终测试
     ├─ 6.6.1  在对话中直接上传图片，验证自动识别
     ├─ 6.6.2  在对话中直接上传论文，验证自动总结 + 流程图生成
     ├─ 6.6.3  在对话中说"帮我生成本周周报"，验证路由到周报功能
     ├─ 6.6.4  Docker Compose 一键启动，所有功能正常
     └─ 6.6.5  压力测试：连续对话 + 文件上传不崩溃
```

#### 验收标准

> **最终验收**

| # | 验收项 | 验证方式 |
|---|--------|---------|
| V6.1 | 对话中上传图片，自动识别无需切换页面 | 对话中上传图片验证 |
| V6.2 | 对话中上传论文，自动提示是否总结/生成流程图 | 上传论文验证 |
| V6.3 | 对话中提到"周报"，自动路由到周报功能 | 输入周报关键词验证 |
| V6.4 | LLM 主模型超时时，自动降级到备用模型 | 模拟超时验证 |
| V6.5 | docker compose up 一键启动，所有功能可用 | Docker 部署验证 |
| V6.6 | 知识库上传文档后，对话能引用知识库内容回答 | 上传文档后提问验证 |

#### 产出物

- 统一 Agent 路由
- RAG 知识库
- 错误降级机制
- Docker 部署方案
- 完整可用的智能体系统

---

## 6. 周报模板规格

### 6.1 公司周报模板（原文）

```
一、本周工作内容
已完成工作
（1）业务需求开发：填写具体页面、功能、接口联调、组件开发；
（2）问题修复：线上 bug、本地编译异常、兼容性问题、之前打包依赖缺失等问题整改；
（3）工程优化：代码重构、依赖整理、打包环境调试、构建报错修复；
（4）其他：需求评审、对接测试、对接后端 / 产品沟通、文档整理。
进行中工作
当前未收尾需求、正在调试的功能、待自测内容。
二、遇到问题与解决方案
问题描述：
例：项目打包持续报 npm 依赖缺失、Babel 警告刷屏、webpack 编译报错；
处理方式：逐一安装缺失依赖、补全开发环境依赖、重置 node_modules 重装依赖；
后续规避：新项目拉取代码先执行完整 npm install，提交代码保证 package.json 依赖齐全。
三、下周工作计划
承接 XX 需求迭代开发；
遗留 bug 闭环、自测提测；
优化打包构建环境、清理无用告警；
按需学习新技术 / 完成自研小工具调试。
四、其他备注
加班情况、需要同事 / 领导协调支持事项、资源诉求。
```

### 6.2 Jinja2 模板字段映射

碎片记录将被 LLM 分类归纳到以下字段，再通过 Jinja2 渲染：

```jinja2
一、本周工作内容

已完成工作

（1）业务需求开发：{{ completed.business_dev }};
（2）问题修复：{{ completed.bug_fix }};
（3）工程优化：{{ completed.engineering_opt }};
（4）其他：{{ completed.others }}。

进行中工作
{{ in_progress }}

二、遇到问题与解决方案
{% for item in problems %}
问题描述：{{ item.description }};
处理方式：{{ item.solution }};
后续规避：{{ item.prevention }}。
{% endfor %}

三、下周工作计划
{% for plan in next_week_plans %}
{{ plan }};
{% endfor %}

四、其他备注
{{ remarks }}
```

### 6.3 LLM 分类标签定义

碎片记录提交时，LLM 自动打以下标签之一：

| 标签 | 对应模板位置 | 说明 |
|------|------------|------|
| `business_dev` | 已完成工作-(1) | 业务需求开发相关 |
| `bug_fix` | 已完成工作-(2) | 问题修复相关 |
| `engineering_opt` | 已完成工作-(3) | 工程优化相关 |
| `others` | 已完成工作-(4) | 评审、沟通、文档等 |
| `in_progress` | 进行中工作 | 未完成、进行中的任务 |
| `problem` | 遇到问题与解决方案 | 遇到的问题及处理方式 |
| `plan` | 下周工作计划 | 下周计划（通常由 LLM 推断） |
| `remark` | 其他备注 | 加班、协调事项等 |

---

## 7. 部署方案

### 7.1 开发环境

```
前端:  cd frontend && npm run dev        -> http://localhost:5173
后端:  cd backend && uvicorn app.main:app --reload  -> http://localhost:8000
数据库: SQLite 文件 (backend/data/app.db)
```

### 7.2 生产部署 (Docker Compose)

```yaml
# docker-compose.yml (规划，阶段6实现)
version: '3.8'
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - GLM_API_KEY=${GLM_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./data:/app/data          # 数据库 + 上传文件
      - ./knowledge:/app/knowledge # RAG 知识库

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "80:80"
    depends_on:
      - backend
```

### 7.3 环境变量清单

```env
# .env
GLM_API_KEY=your_glm_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
GLM_MODEL=glm-4v
DEEPSEEK_MODEL=deepseek-v3
TAVILY_API_KEY=your_tavily_api_key
DATABASE_URL=sqlite:///data/app.db
UPLOAD_DIR=./data/uploads
CHROMA_DIR=./data/chroma
```

---

## 8. 验收检查清单总表

| 阶段 | 验收项数 | 关键验收点 | 状态 |
|------|---------|-----------|------|
| 阶段1 | 8 项 | 流式聊天 + 多轮上下文 + 历史持久化 + 联网搜索 | ⬜ 未开始 |
| 阶段2 | 5 项 | OCR 识别 + 图片理解 | ⬜ 未开始 |
| 阶段3 | 6 项 | 论文/文档/对话三种总结 + 长文档处理 | ⬜ 未开始 |
| 阶段4 | 8 项 | 碎片->模板周报 + docx 导出 | ⬜ 未开始 |
| 阶段5 | 7 项 | 论文->Mermaid 流程图 + 编辑导出 | ⬜ 未开始 |
| 阶段6 | 6 项 | 统一路由 + RAG + Docker 部署 | ⬜ 未开始 |

> **规则**: 每个阶段所有验收项全部通过 (✅) 后，才能开始下一阶段。任一验收项未通过，需修复后重新验收。

---

## 附录：开发环境要求

| 工具 | 版本要求 | 用途 |
|------|---------|------|
| Python | >= 3.11 | 后端运行时 |
| Node.js | >= 18 | 前端构建 |
| npm | >= 9 | 前端包管理 |
| Git | 任意 | 版本控制 |
| Docker | >= 24 | 部署（阶段6） |
| Docker Compose | >= 2.20 | 部署编排（阶段6） |

# 项目交接文档 handoff.md

> 本文档面向全新会话，提供完整的项目背景、当前进度、卡点、下一步计划及踩坑记录。
> 最后更新时间：2026-08-07

---

## 一、项目概述

这是一个"全能型"AI 智能体（Agent）项目，目标是构建一个具备以下能力的对话式助手：

- 流式对话（SSE 流式输出）
- 联网搜索（Tavily）
- 地图查询（地点定位、当前时间、出行时长）
- 图像识别
- 周报生成
- 文档总结
- 论文流程图生成

项目遵循 `DEVELOPMENT.md` 中定义的 6 阶段开发计划，当前处于 **Phase 1（核心聊天框架）已完成、地图功能已集成** 的阶段。

### 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI、Python、SQLite/SQLAlchemy、SSE 流式 |
| LLM | 火山引擎 ARK API（`https://ark.cn-beijing.volces.com/api/v3`），模型 `glm-5-2-260617` |
| 搜索 | Tavily API（联网搜索） |
| 地图后端 | Nominatim（地理编码）、timezonefinder（离线时区）、OSRM（路径规划） |
| 前端 | React 18、TypeScript、Vite、Ant Design、Zustand、react-markdown |
| 地图前端 | Leaflet + react-leaflet@4 |

---

## 二、当前任务与进度

### 已完成的功能

1. **对话管理 CRUD**：创建、列表、详情、删除、标题编辑（PATCH）、批量删除（batch-delete）、按索引删除消息
2. **SSE 流式聊天**：支持流式输出、中断（AbortController）、工具调用（OpenAI 兼容 function calling）
3. **工具集成**：
   - `web_search`（Tavily）— 代码完成，**未测试**（Tavily API Key 未配置）
   - `map_search`（Nominatim + timezonefinder + OSRM）— 代码完成，**未端到端测试**
4. **地图功能**：当用户询问某地点时，前端展示 Leaflet 地图，显示地点坐标、当前当地时间、星期、以及不同交通工具（驾车/步行/骑行/飞行）的耗时
5. **消息操作**：
   - 用户消息右下侧：删除按钮（带 Popconfirm 确认）
   - 智能体消息左下侧：删除按钮 + 重新生成按钮（ReloadOutlined 旋转图标）
6. **侧边栏**：批量删除模式（Checkbox 多选 + 批量删除工具栏）、已移除"智能体"标题
7. **UI 调整**：
   - 侧边栏"新对话"按钮和搜索框高度 1.5 倍
   - 右侧输入框高度 5 倍（minRows: 5）
   - 发送图标改为向上箭头（ArrowUpOutlined），圆形按钮，绝对定位在输入框右下角
   - placeholder："描述您的需求，点击发送即可"

### 当前状态

- 后端服务运行在 **端口 8000**（uvicorn）
- 前端 Vite 运行在 **端口 5177**（注意：5173-5176 可能被遗留的 Vite 进程占用）
- 地图功能代码已全部完成，但**尚未进行端到端测试**
- 地图数据（MapData）仅存在于前端内存中（SSE 流），**未持久化到数据库**——这是已知限制

---

## 三、关键文件清单

### 后端

| 文件 | 说明 |
|---|---|
| `backend/app/core/map_service.py` | **新增**：地图服务核心（geocode、timezone、travel_info、map_search） |
| `backend/app/core/search.py` | 工具定义，含 `WEB_SEARCH_TOOL` 和 `MAP_SEARCH_TOOL` |
| `backend/app/services/chat_service.py` | **重写**：流式聊天，支持 map 工具特殊处理（yield dict） |
| `backend/app/api/chat.py` | SSE 端点 + batch-delete + delete message by index |
| `backend/app/models/schemas.py` | `ChatRequest` 增加 `user_lat`/`user_lon` |
| `backend/app/core/prompts.py` | 系统提示词增加地图能力说明（第 3 项） |
| `backend/.env` | 环境变量（ARK API Key 等） |

### 前端

| 文件 | 说明 |
|---|---|
| `frontend/src/components/MapView.tsx` | **新增**：Leaflet 地图组件 |
| `frontend/src/components/ChatPanel.tsx` | 聊天主面板，含 geolocation、删除、重新生成、地图回调 |
| `frontend/src/components/MessageBubble.tsx` | 消息气泡，含删除/重新生成按钮、地图渲染 |
| `frontend/src/components/Sidebar.tsx` | 侧边栏，含批量删除模式 |
| `frontend/src/services/api.ts` | API 服务，含 MapData 类型、onMap 回调、SSE 处理 |
| `frontend/src/stores/useStore.ts` | Zustand store，含 setLastAssistantMapData、removeMessage、removeConversations |
| `frontend/src/styles/global.css` | 全局样式，含地图、批量工具栏、输入框等样式 |
| `frontend/src/main.tsx` | 入口，引入 `leaflet/dist/leaflet.css` |

### 文档

| 文件 | 说明 |
|---|---|
| `DEVELOPMENT.md` | 6 阶段开发计划（**不要覆盖**） |
| `handoff.md` | 本文档（交接文档） |

---

## 四、卡点与已知问题

1. **Tavily API Key 未配置**：`web_search` 工具代码完成但无法测试，需在 `backend/.env` 中配置 `TAVILY_API_KEY`
2. **地图功能未端到端测试**：代码完成，但尚未用实际用户查询验证完整流程（LLM 调用 map_search → 后端 yield map 数据 → 前端渲染地图）
3. **地图数据未持久化**：MapData 仅在 SSE 流中传递，刷新页面后丢失。数据库 `messages` 表只存文本内容。如需持久化，需扩展 schema
4. **多个 Vite 进程遗留**：5173-5176 端口可能被旧进程占用，重启前需 `taskkill /F /IM node.exe`
5. **react-leaflet 版本约束**：项目使用 React 18，必须用 `react-leaflet@4`（v5 要求 React 19），安装时需加 `--legacy-peer-deps`

---

## 五、下一步计划

按 `DEVELOPMENT.md` 的阶段规划：

### 立即应做
- [ ] 端到端测试地图功能（启动后端，前端提问"北京在哪里"验证）
- [ ] 配置 Tavily API Key 并测试 web_search
- [ ] 清理遗留的 Vite 进程

### Phase 2：图像识别
- 集成多模态模型（GPT-4V / 火山引擎视觉模型）
- 前端支持图片上传
- 后端处理图片 + 文本混合消息

### Phase 3：周报生成
- 数据源接入
- 模板化生成
- 导出功能

### Phase 4：文档总结
- PDF/Word 解析
- 长文本摘要

### Phase 5：论文流程图
- 论文解析
- 流程图生成（Mermaid / Graphviz）

### Phase 6：优化与部署
- 性能优化
- 部署上线

---

## 六、可避免的坑（踩坑记录）

### 1. react-leaflet 版本不兼容
- **问题**：`npm install react-leaflet` 默认装 v5，要求 React 19，项目用 React 18 导致安装失败
- **解决**：`npm install leaflet react-leaflet@4 @types/leaflet --legacy-peer-deps`
- **教训**：安装依赖前先检查 peerDependencies

### 2. Vite HMR 无法解析新依赖
- **问题**：安装 leaflet 后 Vite 报 "Failed to resolve import 'leaflet'"
- **解决**：杀掉 Vite 进程后重启
- **教训**：新增依赖后必须重启 dev server，HMR 不会自动识别新包

### 3. 端口冲突
- **问题**：多次启动 Vite 导致 5173-5176 被占用，新实例只能用 5177
- **解决**：`taskkill /F /IM node.exe` 清理所有 Node 进程后重启
- **教训**：重启前先清理进程，避免端口累积占用

### 4. 后端工具调用特殊处理
- **问题**：`map_search` 需要同时向前端推送地图数据（dict）和向后端 LLM 推送文本结果（str），两种数据类型不同
- **解决**：`chat_service.py` 的 `chat_stream()` 改为 `AsyncGenerator[Any, None]`，yield dict（地图）或 str（文本）；API 层用 `isinstance(chunk, dict)` 区分
- **教训**：设计工具调用时考虑"前端可视化 + LLM 上下文"双通道需求

### 5. 浏览器定位需要用户授权
- **问题**：地图出行时长需要用户位置，`navigator.geolocation` 需要用户授权
- **现状**：前端在 mount 时调用 `getCurrentPosition`，未授权时出行时长为空
- **教训**：应有降级方案（让用户手动输入位置），当前未实现

### 6. 地图数据未持久化
- **问题**：刷新后地图消失
- **原因**：SSE 流只传到前端内存，DB 只存文本
- **教训**：如需持久化，应在 Message 模型增加 `map_data` JSON 字段

---

## 七、环境与启动方式

### 环境变量（backend/.env）
```
ARK_API_KEY=your_ark_api_key
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_MODEL=glm-5-2-260617
TAVILY_API_KEY=your_tavily_key  # 未配置
```

### 启动后端
```bash
cd d:\modal\agent\backend
.venv\Scripts\activate
python -m uvicorn app.main:app --reload --port 8000
```

### 启动前端
```bash
cd d:\modal\agent\frontend
npm run dev
```

### 前端代理
Vite 配置了 `/api` 代理到 `http://localhost:8000`，前端通过 `/api/...` 访问后端。

---

## 八、SSE 事件协议

前端 `streamChat()` 处理以下 SSE 事件类型：

| type | 字段 | 说明 |
|---|---|---|
| `conversation` | `id` | 新建对话时返回对话 ID |
| `message` | `content` | 流式文本块 |
| `map` | `data`（MapData） | 地图数据（地点、坐标、时间、出行信息） |
| `error` | `content` | 错误信息 |
| `done` | — | 流结束 |

---

_本文档由会话总结生成，供新会话快速恢复上下文。如需了解完整开发计划，请参阅 `DEVELOPMENT.md`。_

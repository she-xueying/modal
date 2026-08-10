# 项目交接文档 handoff.md

> 本文档面向全新会话，提供完整的项目背景、当前进度、卡点、下一步计划及踩坑记录。
> 最后更新时间：2026-08-09

---

## ⚠️ 当前正在做什么（新会话必读）

**当前任务：docx 文件编辑功能的缺陷修复（已应用，待提交）**

用户反馈了两个问题：
1. 上传 docx 后，**用户消息气泡不显示上传的文件**
2. 助手有时**不显示回复 / 修改后文件的下载卡片**

排查结论：
- **后端本身正常**：助手消息已正确生成 `xxx_modified.docx`（新文件，原文件未动）并写入 `Message.file_data`
- **根因 1**：后端只持久化了**助手消息**的 file_data，**用户消息**未保存上传文件引用 → 用户气泡看不到附件、刷新后丢失
- **根因 2**：Vite dev server 中途退出过，浏览器可能拿到旧前端代码

已做的修复（在 `backend/app/api/chat.py`）：
- 保存用户消息时也写入 file_data（文件ID/文件名/下载URL），已端到端验证（用户消息 file_data=YES、助手生成修改文件、原文档内容未变）

**待办（新会话第一步）**：
1. 让用户在浏览器 **Ctrl+F5 硬刷新** 后重新测试 docx 上传→修改→下载
2. `question.md` 中"文档编辑功能"章节的"遇到的问题"里补一条"用户消息文件未持久化"（上次因审批超时未写入）

---

## 一、项目概述

这是一个"全能型"AI 智能体（Agent）项目，目标是构建一个具备以下能力的对话式助手：

- 流式对话（SSE 流式输出）
- 联网搜索（Tavily）
- 地图查询（地点定位、当前时间、出行时长）
- 天气查询（实时天气、7天预报、24小时、详情指标、默认地点）
- 文档编辑（上传 docx、对话式修改、下载修改后文档）
- 图像识别 / 周报生成 / 文档总结 / 论文流程图（未开发）

项目遵循 `DEVELOPMENT.md` 的 6 阶段计划；当前 **Phase 1（核心聊天框架 + 地图 + 天气 + 文档编辑）已完成**。

### 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI、Python 3.14、SQLite/SQLAlchemy、SSE 流式 |
| LLM | 火山引擎 ARK API（`https://ark.cn-beijing.volces.com/api/v3`），模型 `glm-5-2-260617` |
| 搜索 | Tavily API（联网搜索，key 未配置） |
| 天气 | Open-Meteo（免费，无需 API key） |
| 地图后端 | Nominatim（地理编码）、timezonefinder（离线时区）、OSRM（路径规划） |
| 文档编辑 | python-docx（docx 解析与修改）、python-multipart（文件上传） |
| 前端 | React 18、TypeScript、Vite、Ant Design、Zustand、react-markdown |
| 地图前端 | Leaflet + react-leaflet@4（内嵌国内地图瓦片 + WGS84→GCJ02） |

---

## 二、本次会话全程小结（任务目标与过程）

**任务目标**：根据上一版 handoff.md，在 `F:\modal\modal\agent` 继续开发智能体项目，重点完成地图/天气/docx 编辑等 Phase 1 功能并修复缺陷。

**已完成（按时间顺序，均有提交）**：
1. **环境重建**：系统 Python 损坏（`C:\Users\HP\python.exe` 缺 DLL），改用 `F:\python\python.exe`（3.14）重建 `backend\.venv`，安装依赖（含 tzdata、python-multipart、python-docx）
2. **地图功能**：端到端测试通过；地图数据持久化（`Message.map_data`）；地图改为内嵌国内地图瓦片（高德）+ WGS84→GCJ02 坐标转换，移除"百度地图"按钮
3. **天气功能**：Open-Meteo 集成（免费无 key）、前端天气卡片、`weather_data` 持久化；升级为详细面板（7天/24小时/紫外线/气压/能见度/日出日落）；用户可配置默认地点（settings 表 + API）；地点引导流程（无地点时模型主动询问；无定位用默认地点；有定位用定位）
4. **docx 编辑功能**：上传（输入框左下角图标）、对话式修改（LLM docx_edit 工具 + python-docx 副本修改）、下载修改后文档、`file_data` 持久化
5. **question.md**：新增"开发过程记录"复盘文档（纯文本、多功能可追加格式）
6. **仓库卫生**：新增 .gitignore，移除误提交的 node_modules/.env/__pycache__/日志/数据库等

**当前进度**：所有 Phase 1 功能已实现并通过后端端到端测试；前端构建通过；唯一未提交的是 docx 缺陷修复（用户消息 file_data 持久化）。

---

## 三、已完成功能清单

1. **对话管理 CRUD**：创建、列表、详情、删除、标题编辑（PATCH）、批量删除（batch-delete）、按索引删除消息
2. **SSE 流式聊天**：流式输出、中断（AbortController）、工具调用（OpenAI 兼容 function calling）
3. **工具集成**：
   - `web_search`（Tavily）— 代码完成，降级路径已验证（真实 key 未配置）
   - `map_search`（Nominatim + timezonefinder + OSRM）— 已端到端测试
   - `weather_search`（Open-Meteo）— 已集成并测试
   - `docx_edit`（python-docx）— 已集成并测试
4. **地图功能**：Leaflet 内嵌国内地图瓦片，显示坐标、当地时间、星期、出行耗时（驾车/步行/骑行/飞行）
5. **天气功能**：详细天气面板（当前详情/24小时/7天预报/默认地点）；地点解析优先级：明确地点 → 用户定位 → 默认地点 → 引导用户
6. **文档编辑**：上传 docx → 对话式修改 → 生成新文件下载（原文件不动）
7. **消息操作**：删除、重新生成、编辑；侧边栏批量删除模式
8. **UI 调整**：侧边栏、输入框（5行、右下角发送）、placeholder 等

---

## 四、当前状态

- 后端服务运行在 **端口 8000**（uvicorn，Python 3.14，venv 位于 `backend/.venv`）
- 前端 Vite 运行在 **端口 5173**（绑定 `[::1]`；测试脚本需 `NO_PROXY=127.0.0.1,localhost,::1`）
- 地图/天气/docx 数据均已持久化（`Message.map_data/weather_data/file_data`），刷新可还原
- 数据库：`conversations`、`messages`、`settings`（默认地点）、`files`（上传/生成文件）
- 上传文件存储：`backend/data/uploads/`（已加入 .gitignore）
- 待办：提交 docx 缺陷修复 → 浏览器验证

---

## 五、卡点与已知问题

1. **TAVILY_API_KEY 未配置**：`backend/.env` 里仍是占位符，web_search 无法真实联网（已加占位符检测，会明确提示）
2. **浏览器显示类问题**：docx 上传后用户消息附件显示依赖前端最新代码 + 用户消息 file_data 持久化（已修，待提交）；出现"看不到"问题先硬刷新
3. **react-leaflet 版本约束**：React 18 必须用 react-leaflet@4（v5 要求 React 19）
4. **地图瓦片**：百度瓦片有反盗链（空白），使用高德瓦片；坐标需 WGS84→GCJ02
5. **默认地点兜底已启用**：无地点且无定位时按用户设置的默认地点查询；都没有时模型引导用户提供城市

---

## 六、下一步计划

### 立即做
- [ ] 提交 docx 缺陷修复（唯一未提交：`backend/app/api/chat.py`）
- [ ] 浏览器硬刷新验证 docx 上传→修改→下载
- [ ] question.md 补充"用户消息文件未持久化"问题记录
- [ ] 配置真实 TAVILY_API_KEY 并测试 web_search

### 后续（按 DEVELOPMENT.md）
- Phase 2：图像识别（多模态模型 + 图片上传）
- Phase 3：周报生成
- Phase 4：文档总结
- Phase 5：论文流程图
- Phase 6：优化与部署

---

## 七、可避免的坑（踩坑记录）

### 1. 本机 Python 损坏 / venv 重建
- **问题**：`C:\Users\HP\python.exe` 报 DLL 缺失（STATUS_DLL_NOT_FOUND），`py` 找不到 Python
- **解决**：用 `F:\python\python.exe`（Python 3.14.4）`python -m venv backend\.venv`；依赖用最新版（旧 pins 在 3.14 可能无 wheel）
- **教训**：环境异常先确认可用的解释器路径

### 2. 测试脚本请求走代理（Privoxy）返回 500
- **问题**：httpx 测 `/api/chat` 返回 `500 Internal Privoxy Error`
- **解决**：`$env:NO_PROXY="127.0.0.1,localhost,::1"`
- **教训**：本机调试注意系统代理对 SSE 的影响（非应用 bug）

### 3. 流式 LLM 异常逃逸
- **问题**：流式调用抛非 LLMError 异常 → 空 error 事件 + 消息不持久化
- **解决**：`llm.py` 的 `chat_stream` 把流式/网络异常统一包装成 `LLMError`，调用方优雅降级并保留持久化
- **教训**：跨层异常统一类型，避免底层异常破坏上层收尾（持久化）

### 4. LLM 工具调用不可靠（不调工具、凭记忆编造）
- **问题**：天气/搜索等实时类问题，模型有时不调用工具直接编造
- **解决**：强化工具描述与系统提示词（"必须调用、不得编造"）；工具决策 temperature 降至 0.2
- **教训**：实时数据类功能需"提示词 + 低采样温度"双重约束

### 5. Windows 时区解析失败（zoneinfo）
- **问题**：`ZoneInfo('Asia/Shanghai')` 报 No time zone found
- **解决**：`pip install tzdata` 并加入 requirements.txt；`get_location_time` 增加 UTC 兜底

### 6. 前端 tsc -b 构建报错
- **问题**：TS6306/TS6310（referenced 项目需 composite，TS5.9 不允许 composite+noEmit）
- **解决**：`tsconfig.node.json` 改 `composite: true + emitDeclarationOnly: true`，输出到 node_modules/.tmp

### 7. FastAPI 文件上传缺 python-multipart
- **问题**：导入 app 报 Form data requires python-multipart
- **解决**：`pip install python-multipart`
- **教训**：装依赖要覆盖 requirements 全部，不能只装核心

### 8. PowerShell 补丁脚本被截断（heredoc）
- **问题**：`@'...'@ | Set-Content` 后 Python 补丁打印 OK 但文件没写入（末尾写文件语句未执行）
- **解决**：补丁脚本加 `WRITE DONE` 标记 + 写入后立即 grep 目标文件验证
- **教训**：任何"改文件"脚本都要校验目标文件内容，不能只看脚本退出码

### 9. Vite dev server 中途退出
- **问题**：连接 localhost:5173 被拒（WinError 10061）
- **解决**：`Get-Process | Stop-Process`（node/python）后重启 `npm run dev`、`uvicorn`
- **教训**：长会话中 dev server 可能退出，测试前先确认端口监听

### 10. 用户消息附件未持久化
- **问题**：上传文件后用户消息不显示附件，刷新后丢失
- **解决**：后端保存用户消息时也写入 file_data（本次修复，待提交）
- **教训**：用户主动上传的附件也要持久化；"看不到"先排除浏览器缓存

### 11. 百度/OpenStreetMap 瓦片问题
- **问题**：百度瓦片反盗链返回空白；OSM 不含国内 POI
- **解决**：改用高德瓦片 + WGS84→GCJ02 坐标转换
- **教训**：国内地图优先高德/腾讯瓦片，注意坐标系

### 12. 端口冲突 / react-leaflet 版本
- **问题**：多次启动 Vite 端口累积占用；react-leaflet 默认装 v5 不兼容 React 18
- **解决**：重启前清理进程；`npm install leaflet react-leaflet@4 @types/leaflet --legacy-peer-deps`

---

## 八、环境与启动方式

### 环境变量（backend/.env）
```
GLM_API_KEY=ark-...（已配置，勿外传/勿提交）
GLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
GLM_MODEL=glm-5-2-260617
TAVILY_API_KEY=your_tavily_api_key_here  # 未配置
```

### 启动后端
```bash
cd F:\modal\modal\agent\backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 启动前端
```bash
cd F:\modal\modal\agent\frontend
npm run dev   # 默认端口 5173
```

### 前端代理
Vite `/api` 代理到 `http://localhost:8000`；前端通过 `/api/...` 访问后端。

### 常用验证
```bash
# 健康检查
curl http://127.0.0.1:8000/health
# 上传/下载文件
curl -F "file=@x.docx" http://127.0.0.1:8000/api/files/upload
curl http://127.0.0.1:8000/api/files/{id}/download
# 默认地点
curl http://127.0.0.1:8000/api/settings/default-location
```

---

## 九、SSE 事件协议

前端 `streamChat()` 处理以下 SSE 事件类型：

| type | 字段 | 说明 |
|---|---|---|
| `conversation` | `id` | 新建对话时返回对话 ID |
| `message` | `content` | 流式文本块 |
| `map` | `data`（MapData） | 地图数据（地点、坐标、时间、出行信息） |
| `weather` | `data`（WeatherData） | 天气数据（当前、7天、24小时、详情指标） |
| `file` | `data`（FileData） | 生成的文件（docx 编辑结果，含下载 URL） |
| `error` | `content` | 错误信息 |
| `done` | — | 流结束 |

---

## 十、关键文件清单

### 后端
- `app/core/file_service.py`：**新增**，docx 上传保存、段落提取、副本修改（python-docx）
- `app/core/weather_service.py`：**新增**，Open-Meteo 查询、7天/24小时/详情、weather_search、默认地点兜底
- `app/core/map_service.py`：地图服务（geocode、timezone、travel_info、map_search）
- `app/core/search.py`：工具定义（WEB/MAP/WEATHER/DOCX_EDIT）
- `app/core/llm.py`：LLM 客户端，流式异常包装为 LLMError
- `app/services/chat_service.py`：流式聊天，各工具特殊处理（yield dict）+ 持久化
- `app/api/chat.py`：SSE / CRUD / 文件上传下载 / 默认地点；**本次修复点（用户消息 file_data）**
- `app/models/database.py`：Conversation/Message/Setting/File 模型 + 自动迁移
- `app/models/schemas.py`：请求/响应 schema（含 map_data/weather_data/file_data 解析）

### 前端
- `src/components/ChatPanel.tsx`：聊天主面板，含文件上传图标、附件、onFile 回调
- `src/components/MessageBubble.tsx`：消息气泡 + 地图/天气/文件卡片渲染
- `src/components/MapView.tsx`：地图（国内瓦片 + GCJ02 转换）
- `src/components/WeatherCard.tsx`：详细天气面板 + 设为默认地点
- `src/services/api.ts`：类型 + API + SSE 处理（含 file 事件）
- `src/stores/useStore.ts`：状态（含 fileData、默认地点）
- `src/styles/global.css`：全局样式

### 文档
- `DEVELOPMENT.md`：6 阶段开发计划（不要覆盖）
- `question.md`：开发过程复盘（多功能模板，纯文本）
- `handoff.md`：本文档

---

_本文档由会话总结生成，供新会话快速恢复上下文。_
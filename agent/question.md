# 天气功能开发复盘 question.md

> 记录"天气"功能的开发过程：怎么开始实现的、遇到了哪些问题、后来如何解决。
> 对应提交：`d65a1785`（天气功能集成）、`60399c93`（详细预报 + 默认地点）。
> 与 `handoff.md`（交接文档）同级，本文侧重"过程 + 踩坑"。

---

## 一、功能概述

需求：**用户询问天气时，智能体要能给出真实、实时的天气，而不是凭记忆编造。**

最终实现的能力：

1. LLM 通过函数调用触发 `weather_search` 工具
2. 后端用 **Open-Meteo**（免费、无需 API key）获取实时天气
3. 前端渲染天气卡片 / 详细天气面板
4. 天气数据持久化到数据库（`Message.weather_data`），刷新页面不丢失
5. 用户可把某个地点设为"默认地点"（可配置，不做自动兜底）

技术选型：

| 环节 | 方案 |
|---|---|
| 天气数据源 | Open-Meteo（免费、无 key、支持 7 天 + 逐小时 + 详情指标） |
| 地理编码 | 复用 `map_service.geocode_location`（Nominatim） |
| 工具链路 | OpenAI 兼容 function calling + SSE 流式（与地图功能同架构） |
| 前端 | React 组件 `WeatherCard`，与地图卡片同风格 |
| 持久化 | `Message` 模型增加 `weather_data` JSON 字段 + SQLite 自动迁移 |

---

## 二、实现过程（从 0 到 1）

### 2.1 选型：为什么用 Open-Meteo

- 天气类 API 大多要 key：OpenWeatherMap、和风天气、心知天气都需要注册。
- **Open-Meteo 完全免费、无需 API key**，字段齐全（当前天气、7 天逐日、逐小时、紫外线、气压、能见度、日出日落等），够用且稳定。
- 先在命令行验证接口可用、字段符合预期，再动代码。

### 2.2 后端：天气服务模块

新建 `backend/app/core/weather_service.py`：

1. `weather_search(place, user_lat, user_lon)`：解析坐标
   - 用户给了地点 → `geocode_location(place)`（复用地图模块的 Nominatim 地理编码）
   - 没给地点但前端传了定位 → 用 `user_lat/user_lon`
   - 都没有 → 抛出 `WeatherError("缺少地点信息")`
2. 调 Open-Meteo `v1/forecast`，组装 `current / daily / hourly`
3. `weather_result_to_text()`：把天气结果转成文本，作为 LLM 的 tool result 上下文

### 2.3 工具接入

- `search.py`：新增 `WEATHER_SEARCH_TOOL` 定义，加入 `ALL_TOOLS`
- `chat_service.py`：`weather_search` 做**特殊处理**（与 `map_search` 一样）：
  - `yield {"type": "weather", "data": {...}}` → 推给前端渲染天气卡片
  - 同时把文本结果喂回 LLM 生成回答（"前端可视化 + LLM 上下文"双通道）
- `prompts.py`：系统提示词增加"天气查询"能力说明

### 2.4 前端

- `api.ts`：`WeatherData` 类型、SSE `weather` 事件、`onWeather` 回调
- `WeatherCard.tsx`：天气卡片（地点 + 当前温度 + 体感 + 湿度/风力/降水 + 今日最高最低）
- `useStore / ChatPanel / MessageBubble`：天气数据状态、流式回调、卡片渲染
- `global.css`：天气卡片样式

### 2.5 持久化

- `database.py`：`Message` 增加 `weather_data` 列；`_ensure_columns()` 自动 `ALTER TABLE` 迁移
- `schemas.py`：`MessageOut.weather_data` + field_validator 把 JSON 字符串解析成对象
- `api/chat.py`：`get_conversation` 用 `MessageOut.model_validate` 校验消息
- 前端 `getConversation` 把 `weather_data` 还原为 `weatherData`，刷新后天气卡片仍在

---

## 三、遇到的问题与解决（重点）

### 问题 1：LLM 工具调用不可靠（凭记忆编造天气）

- **现象**：同一句话 "北京今天天气怎么样"，有时触发 `weather_search`，有时**不调用工具**、直接凭训练知识回答天气。
- **原因**：LLM 工具调用本身有非确定性；工具描述和系统提示词约束不够强；`temperature=0.7` 偏高。
- **解决**：
  1. 强化 `WEATHER_SEARCH_TOOL` 描述：明确"**必须**调用此工具获取实时天气，不要根据训练知识编造天气数据"
  2. 强化系统提示词：天气问题务必调用 `weather_search`
  3. 把**工具决策**调用的 `temperature` 从 0.7 降到 **0.2**（决策更稳定）
  4. 连测北京/上海/杭州 3 条天气问题 → **100% 触发成功**
- **教训**：涉及"必须实时数据"的功能，光有工具定义不够，要从**提示词 + 采样温度**双管齐下。

### 问题 2：端到端测试报 500（Privoxy 代理干扰）

- **现象**：测试脚本 POST `/api/chat` 返回 500，响应体是 `500 Internal Privoxy Error`。
- **原因**：本机配置了系统代理（Privoxy），httpx 默认（`trust_env`）把对 `127.0.0.1` 的请求也走代理，Privoxy 处理不了 SSE 流式连接。
- **解决**：测试时设置 `NO_PROXY=127.0.0.1,localhost,::1`，本地请求绕过代理。（这是**测试环境问题，不是应用 bug**——应用本身的 LLM/天气外呼都正常。）
- **教训**：本机调试要确认代理环境变量；代理对 SSE 流式连接可能不兼容。

### 问题 3：流式 LLM 偶发失败 → 空错误事件 + 不持久化

- **现象**：weather 事件已正常推送，随后出现 `content: ""` 的**空 error 事件**；数据库里该对话只有 1 条 user 消息，assistant 消息**没被持久化**。
- **原因**（排查过程）：
  1. 直接调用 `chat_stream` 复现 → 正常，说明不是业务逻辑问题
  2. 逐层看：`llm_client.chat_stream()` 抛出的是**非 `LLMError` 的异常**（如流式网络错误）
  3. `chat_service` 只 `except LLMError` → 捕获不到 → 异常逃逸到 API 层
  4. API 层 `except Exception` 捕获 → 生成空 error 事件；且异常发生在末尾 `save_message` **之前** → 跳过持久化
- **解决**：在 `llm.py` 的 `chat_stream()` 里，把流式/网络异常统一包装成 `LLMError`：
  ```python
  except LLMError:
      raise
  except Exception as e:
      raise LLMError(f"LLM 流式请求失败: {e}") from e
  ```
  这样调用方 `except LLMError` 就能优雅降级：提示"生成回复失败"、**保留部分回复**、天气数据**正常持久化**。
- **教训**：跨层异常要设计统一异常类型，避免底层异常逃逸破坏上层收尾逻辑（尤其持久化、记账类操作）。

### 问题 4：antd 图标不存在（TS2724）

- **现象**：前端构建报 `@ant-design/icons has no exported member 'ThermometerOutlined'/'DropOutlined'`。
- **原因**：误用了不存在的图标名。
- **解决**：详情图标改用 **emoji**（💧 湿度 / 🌬️ 风力 / ☔ 降水），只保留 `EnvironmentOutlined`。
- **教训**：用 antd 图标前先查包内实际导出（`node_modules/@ant-design/icons/es/icons`）。

### 问题 5：PowerShell 管道传中文乱码（?）

- **现象**：用 `@'...'@ | python -` 传中文补丁脚本，中文全变成 `?`（U+003F），导致代码/文档匹配失败。
- **原因**：PowerShell 把 heredoc 内容经 stdin 管道传给原生进程时按系统 ANSI/GBK 编码，和 Python 读取的编码不一致。
- **解决**：改用 `Set-Content -Encoding UTF8` 把脚本**写成文件再执行**；能纯 ASCII 替换的就用 ASCII 锚点。
- **教训**：Windows 下往原生进程传中文，优先走"文件 + UTF-8"，避免 stdin 管道编码损耗。

### 问题 6：补丁脚本字符串引号冲突

- **现象**：写 handoff 补丁时，在 Python 双引号字符串里又写了 ASCII 双引号（`"设为默认地点"`），触发 `SyntaxError`。
- **解决**：改用中文引号/调整字符串拼接。
- **教训**：模板字符串里嵌入引号要留意分隔符冲突。

---

## 四、后续升级：详细预报 + 默认地点

按用户需求（提交 `60399c93`）：

1. **详细天气**：未来 7 天逐日预报、未来 24 小时逐 3 小时、紫外线/云量/气压/能见度/降雨概率/日出日落
2. **默认地点（用户可配置）**：
   - `settings` 表 + `GET/PUT/DELETE /api/settings/default-location`
   - 天气卡片"设为默认地点"按钮（Popconfirm 确认、可清除、显示当前默认）
   - 按需求**不做自动兜底**（未指定地点仍走浏览器定位或报错），默认地点先存着备用

---

## 五、相关文件

| 文件 | 说明 |
|---|---|
| `backend/app/core/weather_service.py` | 天气服务核心（Open-Meteo 查询、weather_search、结果格式化） |
| `backend/app/core/search.py` | `WEATHER_SEARCH_TOOL` 工具定义 |
| `backend/app/services/chat_service.py` | weather 特殊处理（yield 数据 + 持久化） |
| `backend/app/core/llm.py` | 流式调用加固（异常包装为 LLMError） |
| `backend/app/models/database.py` | `Message.weather_data` 列 + `settings` 表 |
| `backend/app/api/chat.py` | SSE 天气事件 + 默认地点 GET/PUT/DELETE |
| `frontend/src/components/WeatherCard.tsx` | 详细天气面板 + 设为默认地点 |
| `frontend/src/services/api.ts` | 天气类型 + 默认地点 API |
| `frontend/src/stores/useStore.ts` | 默认地点状态 |
| `frontend/src/styles/global.css` | 天气面板样式 |

---

_本文档随天气功能迭代同步更新。_
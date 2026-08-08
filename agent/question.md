# 开发过程记录 question.md

> 记录各功能开发过程中遇到的问题、解决方案，以及涉及修改的文件。
> 新增功能时：概述功能 → 列出遇到的问题（现象/原因/解决/教训）→ 列出修改的文件及改动要点。

---

## 天气功能

> 简介：实时天气查询（Open-Meteo，免费无 key），含详细预报与用户可配置默认地点。
> 对应提交：d65a1785（集成）、60399c93（详细预报 + 默认地点）

### 遇到的问题

1. LLM 工具调用不可靠，会凭记忆编造天气
   - 现象：同一句天气问题有时触发 weather_search，有时直接凭训练知识回答
   - 原因：工具描述/系统提示词约束弱；工具决策 temperature 0.7 偏高
   - 解决：强化工具描述与提示词（必须调用、不得编造）；工具决策 temperature 降至 0.2；连测 3 地 100% 触发
   - 教训：实时数据类功能需"提示词 + 低采样温度"双重约束

2. 端到端测试返回 500（Privoxy 代理）
   - 现象：httpx 测试 /api/chat 返回 500 Internal Privoxy Error
   - 原因：系统代理把对 127.0.0.1 的请求也转发，Privoxy 不支持 SSE 流式
   - 解决：测试脚本设 NO_PROXY=127.0.0.1,localhost,::1
   - 教训：本机调试注意代理环境变量对 SSE 的影响（测试环境问题，非应用 bug）

3. 流式 LLM 异常逃逸，导致空错误事件 + 消息不持久化
   - 现象：weather 事件推送后出现空 error，assistant 消息未写入数据库
   - 原因：llm_client.chat_stream 抛非 LLMError 异常，chat_service 的 except LLMError 捕不到，异常逃逸到 API 层并跳过末尾 save_message
   - 解决：在 llm.py 的 chat_stream 中把流式/网络异常统一包装成 LLMError，调用方优雅降级（提示 + 保留部分回复 + 正常持久化）
   - 教训：跨层异常统一类型，避免底层异常破坏上层收尾（持久化）

4. antd 图标不存在（TS2724）
   - 现象：构建报 ThermometerOutlined / DropOutlined 不存在
   - 原因：误用不存在的图标名
   - 解决：详情图标改用 emoji（💧 湿度 / 🌬️ 风力 / ☔ 降水）
   - 教训：用 antd 图标前先查包内实际导出

5. PowerShell 管道传中文乱码
   - 现象：heredoc 传中文给 python 变 ?，字符串匹配失败
   - 原因：stdin 管道按系统 ANSI/GBK 编码，与 Python 读取编码不一致
   - 解决：用 Set-Content -Encoding UTF8 写文件再执行；纯替换用 ASCII 锚点
   - 教训：Windows 往原生进程传中文用文件方式

6. 补丁脚本字符串引号冲突
   - 现象：字符串内嵌 ASCII 双引号导致 SyntaxError
   - 解决：改用中文引号 / 调整拼接
   - 教训：模板字符串注意引号分隔符冲突

### 修改的文件

- backend/app/core/weather_service.py：新增，天气服务核心，负责地理编码、Open-Meteo 查询（当前/7天/24小时/详情指标）与结果格式化
- backend/app/core/search.py：新增 weather_search 工具定义，并加入 ALL_TOOLS
- backend/app/services/chat_service.py：对 weather_search 做特殊处理（向前端 yield 天气数据 + 向 LLM 喂文本），并持久化天气数据
- backend/app/core/llm.py：流式调用加固，把网络/流式异常统一包装成 LLMError
- backend/app/core/prompts.py：系统提示词增加天气能力说明，引导天气问题调用 weather_search
- backend/app/models/database.py：Message 增加 weather_data 字段；新增 settings 表（存默认地点）
- backend/app/models/schemas.py：MessageOut 增加 weather_data；新增 DefaultLocation schema
- backend/app/api/chat.py：新增默认地点 GET/PUT/DELETE 接口；消息返回时解析 weather_data
- frontend/src/components/WeatherCard.tsx：新增，详细天气面板（当前详情、24小时、7天预报、设为默认地点）
- frontend/src/services/api.ts：新增天气类型、SSE weather 事件、默认地点 API；加载对话时还原 weather_data
- frontend/src/stores/useStore.ts：新增默认地点状态与操作
- frontend/src/components/ChatPanel.tsx：挂载时加载默认地点；处理 weather 流式回调
- frontend/src/components/MessageBubble.tsx：渲染天气卡片
- frontend/src/styles/global.css：新增天气面板样式
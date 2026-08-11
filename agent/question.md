# 开发过程记录 question.md

> 记录各功能开发过程中遇到的问题、解决方案，以及涉及修改的文件。
> 新增功能时：概述功能 → 描述开发流程与优化 → 列出遇到的问题 → 列出修改的文件及改动要点。

---

## 天气功能

> 简介：实时天气查询（Open-Meteo，免费无 key），含详细预报、地点引导与用户可配置默认地点。
> 对应提交：d65a1785（集成）、60399c93（详细预报 + 默认地点）

### 开发流程

#### 阶段一：初始问题——用户问"今天天气如何"，模型不知道用户在哪里

- 现象：用户只问"今天天气如何"，没有说城市。模型没有用户所在位置的信息，不知道按哪里查询，结果要么无法回答，要么凭训练知识产生幻觉、编造天气。
- 根因：天气查询需要具体坐标/地点，但模型不知道用户在哪个城市，系统也没有缺省处理。

#### 阶段二：优化一——没给地点时，模型引导用户给出具体地点再回答

- 目标：用户没给地点时不再报错或编造，而是先引导用户说出城市。
- 实现方式：
  - 系统提示词（prompts.py）增加规则：天气问题若缺少地点信息，应主动询问用户要查询哪个城市/地点，不要猜测用户位置或编造天气。
  - weather_service 在"无地点、无定位、无默认地点"时返回明确的"缺少地点信息"错误。
  - 该错误作为工具结果喂回模型，模型按提示词把失败转成一句引导语，例如"请问您想知道哪个城市或地点的天气？"。
- 效果：模型会先追问地点，等用户给出城市后再查询，不再凭记忆编造。

#### 阶段三：优化二——更具体的地址：引导开定位；无定位用默认地点，有定位用定位

- 目标：用户想查询更具体的当前位置天气时，引导开启定位；未开定位用默认地点，开了定位用定位地点。
- 实现方式：
  - 前端挂载时调用浏览器定位（navigator.geolocation），授权后把 user_lat/user_lon 随消息传给后端。
  - 后端 weather_search 按优先级解析地点：用户明确给的地点 → 用户定位 → 用户设置的默认地点。
  - 默认地点由用户在天气卡片上点击"设为默认地点"写入 settings 表。
  - 三者都没有时，模型按阶段二的规则引导用户提供地点或开启定位。
- 效果：开了定位按定位地点回答；没开定位但有默认地点按默认地点回答；都没有则引导用户。

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

- backend/app/core/weather_service.py：新增，天气服务核心，负责地理编码、Open-Meteo 查询（当前/7天/24小时/详情指标）与结果格式化；地点解析顺序为"地点 → 用户定位 → 默认地点"，都无则报缺少地点
- backend/app/core/search.py：新增 weather_search 工具定义，并加入 ALL_TOOLS
- backend/app/services/chat_service.py：对 weather_search 做特殊处理（向前端 yield 天气数据 + 向 LLM 喂文本），并持久化天气数据；从 settings 表读取默认地点传入 weather_search
- backend/app/core/llm.py：流式调用加固，把网络/流式异常统一包装成 LLMError
- backend/app/core/prompts.py：系统提示词增加天气能力说明与"缺少地点时引导用户给出城市"的规则
- backend/app/models/database.py：Message 增加 weather_data 字段；新增 settings 表（存默认地点）
- backend/app/models/schemas.py：MessageOut 增加 weather_data；新增 DefaultLocation schema
- backend/app/api/chat.py：新增默认地点 GET/PUT/DELETE 接口；消息返回时解析 weather_data
- frontend/src/components/WeatherCard.tsx：新增，详细天气面板（当前详情、24小时、7天预报、设为默认地点）
- frontend/src/services/api.ts：新增天气类型、SSE weather 事件、默认地点 API；加载对话时还原 weather_data
- frontend/src/stores/useStore.ts：新增默认地点状态与操作
- frontend/src/components/ChatPanel.tsx：挂载时请求定位并加载默认地点；处理 weather 流式回调
- frontend/src/components/MessageBubble.tsx：渲染天气卡片
- frontend/src/styles/global.css：新增天气面板样式


---

## 文档编辑功能（docx）

> 简介：用户上传 docx 文档，对话式让助手修改文档某处，返回修改后的文档供下载（原文件不动）。
> 前端在输入框左下角提供"选择文件"图标。

### 开发流程

- 输入框左下角"选择文件"图标 → 选择 .docx → 后端存盘并返回文件ID
- 发送消息时带上 file_id，后端把文档内容（带段落索引）注入 LLM 上下文
- LLM 通过 docx_edit 工具指定要改的段落索引和新内容
- 后端用 python-docx 在副本上应用修改（保留原段落样式），生成新文件
- SSE 推送 file 事件 → 前端消息卡片显示"下载修改后的文档"
- 原文档从未被改动

### 遇到的问题

1. FastAPI 文件上传缺少 python-multipart
   - 现象：导入 app 报 Form data requires python-multipart
   - 原因：新 venv 未安装该依赖（requirements.txt 有但未装）
   - 解决：pip install python-multipart
   - 教训：装依赖要覆盖 requirements 全部，不能只装核心

2. 前端补丁脚本未写入（heredoc 截断）
   - 现象：api.ts / useStore.ts 补丁打印 OK 但文件未变，构建报缺 FileData / uploadFile
   - 原因：PowerShell here-string 内容被截断，脚本末尾写文件语句未执行
   - 解决：重写补丁并校验文件末尾完整（加 WRITE DONE 标记 + 写入后 grep 验证）
   - 教训：脚本改文件后要立即校验目标文件内容

3. Vite 开发服务器意外退出
   - 现象：连接 localhost:5173 被拒（WinError 10061）
   - 解决：重新启动 npm run dev
   - 教训：长会话中 dev server 可能退出，测试前先确认端口监听

4. 用户消息附件未持久化
   - 现象：上传 docx 后用户消息气泡不显示附件，刷新后丢失
   - 原因：后端只持久化了助手消息的 file_data，用户消息未保存上传文件引用
   - 解决：后端保存用户消息时也写入 file_data（文件ID/文件名/下载URL）
   - 教训：用户主动上传的附件也要持久化；"看不到"先排除浏览器缓存（Ctrl+F5 硬刷新）

### 修改的文件

- backend/app/core/file_service.py：新增，docx 上传保存、段落提取、副本修改（python-docx）
- backend/app/models/database.py：新增 files 表；Message 增加 file_data 字段
- backend/app/api/chat.py：新增 /api/files/upload 与 /api/files/{id}/download
- backend/app/core/search.py：新增 docx_edit 工具定义
- backend/app/services/chat_service.py：注入文档内容、处理 docx_edit、持久化 file_data
- backend/requirements.txt：新增 python-docx；补装 python-multipart
- frontend/src/components/ChatPanel.tsx：输入框左下角上传图标、附件、onFile 回调
- frontend/src/components/MessageBubble.tsx：文件卡片（上传附件 + 下载按钮）
- frontend/src/services/api.ts：FileData 类型、uploadFile、file 事件
- frontend/src/stores/useStore.ts：setLastAssistantFileData
- frontend/src/styles/global.css：上传图标/附件/文件卡片样式

---

## 错别字处理

> 简介：用户输入含错别字（如“北jing”“天汽”“知能体”）时，模型能根据上下文理解真实意图，纠正后再回答或调用工具，避免被错别字误导。

### 背景

用户打字容易出错，把地点、关键词或文档中的目标文字写错（如“杭洲”“天汽”“知能体”）。如果不做容错处理：
- 模型可能被错别字误导，把写错的词当成独立实体，导致答非所问；
- 带错别字的地点/关键词直接传给地图/天气/搜索工具，查询失败或返回错误结果；
- 让模型修改 docx 时，用户描述的目标文字和文档实际文字对不上，模型改错段落或找不到要改的地方。

### 使用的方法

1. 系统提示词（prompts.py）增加错别字容错规则：先根据上下文理解真实意图；调用工具前把地点名、搜索关键词、要匹配的文本先纠正再传参；无法确定时礼貌提示“您说的是否是XXX”。
2. 各工具参数描述（search.py）明确“先纠正错别字再传入准确内容”，引导模型把纠正后的值传给工具，而不是把错字原样传入。
3. docx_edit 工具新增 match_text 参数：模型不确定段落索引时，可填文档中实际存在的正确文字，后端按该文字模糊定位段落后再修改；paragraph_index 改为可选。
4. file_service 新增 find_paragraph_index 模糊定位（忽略空白/大小写），apply_docx_edit 支持 match_text 定位，并返回该段原文本与最终段落索引。
5. chat_service 支持 match_text 定位，工具结果回显“修改位置/原文/修改后”，让模型能核对是否改对了。

### 开发中遇到的难点

1. 模型会被错别字误导
   - 现象：把“知能体”当成无关内容、“杭洲”等地名不经纠正直接查询
   - 解决：提示词 + 工具描述双重约束，规定“先纠正再传参”，端到端验证通过

2. 真实 LLM 偶发瞬时故障（非代码问题）
   - 现象：偶发把 tool call 当文本输出（回复中出现 `{lng{weather_search}(...)` 之类），或连接报 “All connection attempts failed”
   - 原因：多为限流/瞬时波动
   - 解决：重试即可；自动化测试连测多次确认稳定性，勿因单次失败误判

3. docx 同一轮多次编辑生成多个“部分修改”文件
   - 现象：文档含两处“智能体”，模型连续调用两次 docx_edit，生成两个文件、每个只改了一处，助手却声称“两处已全部替换”
   - 原因：每次 docx_edit 都基于原始上传文件生成新文件，多次修改互不叠加
   - 解决：chat_service 记录“当前工作文件”，后续修改基于上一次生成的副本继续累积；整个回合只在末尾推送一次最终文件

4. 测试环境网络受限
   - 现象：后端在受限环境启动后 LLM 调用报 “All connection attempts failed”（直连 ARK 被 WinError 10013 阻断）
   - 解决：后端/需真实 LLM 的测试在无沙箱（提权）环境启动；测试脚本设 NO_PROXY=127.0.0.1,localhost,::1

### 修改的文件

- backend/app/core/prompts.py：系统提示词增加错别字容错规则（理解真实意图、纠正后再传参、不确定时礼貌确认）
- backend/app/core/search.py：地图/天气/搜索工具参数描述提示先纠正错别字；docx_edit 新增 match_text 参数，paragraph_index 改为可选
- backend/app/core/file_service.py：新增 find_paragraph_index 模糊定位；apply_docx_edit 支持 match_text 定位，返回原文本与最终段落索引
- backend/app/services/chat_service.py：docx_edit 支持 match_text；多次编辑基于上一次副本累积，最终只推送一个文件；工具结果回显修改位置/原文/修改后

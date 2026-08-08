import React from 'react'
import { Input, Button, message } from 'antd'
import { ArrowUpOutlined, RobotOutlined, MenuFoldOutlined, MenuUnfoldOutlined, StopOutlined } from '@ant-design/icons'
import { useStore } from '../stores/useStore'
import { streamChat, getConversation, truncateConversation, deleteMessage as deleteMessageApi, Message as ApiMessage } from '../services/api'
import MessageBubble from './MessageBubble'

const { TextArea } = Input

const ChatPanel: React.FC = () => {
  const {
    activeConversationId,
    messages,
    streaming,
    setMessages,
    addMessage,
    updateLastAssistantMessage,
    setLastAssistantMapData,
    setLastAssistantWeatherData,
    setActiveConversation,
    setStreaming,
    addConversation,
    conversations,
    sidebarCollapsed,
    toggleSidebar,
    truncateMessages,
    removeMessage,
    fetchDefaultLocation,
  } = useStore()

  const [input, setInput] = React.useState('')
  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  const inputRef = React.useRef<any>(null)
  const abortControllerRef = React.useRef<AbortController | null>(null)
  const userLocationRef = React.useRef<{ lat: number; lon: number } | null>(null)

  // Get user geolocation on mount (for map travel time)
  // Load saved default weather location on mount
  React.useEffect(() => {
    fetchDefaultLocation()
  }, [fetchDefaultLocation])

  React.useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          userLocationRef.current = {
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
          }
        },
        () => {
          // User denied or error - silently ignore, travel info won't be available
        },
        { timeout: 5000 }
      )
    }
  }, [])

  // Load messages when active conversation changes
  React.useEffect(() => {
    if (activeConversationId) {
      loadMessages(activeConversationId)
    }
  }, [activeConversationId])

  // Auto-scroll to bottom
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadMessages = async (convId: string) => {
    try {
      const detail = await getConversation(convId)
      setMessages(detail.messages)
    } catch (e) {
      console.error('Failed to load messages:', e)
    }
  }

  const sendMessage = async (text: string, convId: string | null) => {
    // Add user message to UI immediately
    const userMsg: ApiMessage = { role: 'user', content: text }
    addMessage(userMsg)

    // Add empty assistant message for streaming
    const assistantMsg: ApiMessage = { role: 'assistant', content: '' }
    addMessage(assistantMsg)
    setStreaming(true)

    let accumulated = ''
    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const userLoc = userLocationRef.current
      await streamChat(text, convId, {
        onConversationId: (id) => {
          if (!convId) {
            setActiveConversation(id)
            if (!conversations.find((c) => c.id === id)) {
              addConversation({
                id,
                title: text.slice(0, 30) + (text.length > 30 ? '…' : ''),
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                message_count: 0,
              })
            }
          }
        },
        onMessage: (chunk) => {
          accumulated += chunk
          updateLastAssistantMessage(accumulated)
        },
        onMap: (data) => {
          setLastAssistantMapData(data)
        },
        onWeather: (data) => {
          setLastAssistantWeatherData(data)
        },
        onError: (err) => {
          updateLastAssistantMessage(`[错误] ${err}`)
          message.error('生成回复时出错')
        },
        onDone: () => {
          setStreaming(false)
        },
      }, controller.signal, userLoc?.lat, userLoc?.lon)
    } catch (e: any) {
      if (e.name === 'AbortError') {
        // User stopped - keep partial response
        if (!accumulated) {
          updateLastAssistantMessage('[已停止]')
        }
      } else {
        updateLastAssistantMessage(`[错误] ${e.message}`)
        message.error('请求失败，请检查后端服务是否启动')
      }
    } finally {
      setStreaming(false)
      abortControllerRef.current = null
      inputRef.current?.focus()
    }
  }

  const handleSend = async () => {
    const text = input.trim()
    if (!text || streaming) return
    setInput('')
    await sendMessage(text, activeConversationId)
  }

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }

  const handleEdit = async (index: number, newContent: string) => {
    if (streaming) {
      message.warning('请等待当前回复完成')
      return
    }
    // Truncate messages in UI: remove edited message and everything after it
    truncateMessages(index)
    // Truncate messages in backend database to keep them in sync
    if (activeConversationId) {
      try {
        await truncateConversation(activeConversationId, index)
      } catch (e) {
        console.error('Failed to truncate conversation:', e)
      }
    }
    // Send the edited message as a new message (streaming)
    await sendMessage(newContent, activeConversationId)
  }

  const handleDelete = async (index: number) => {
    if (streaming) {
      message.warning('请等待当前回复完成')
      return
    }
    // Delete from backend first
    if (activeConversationId) {
      try {
        await deleteMessageApi(activeConversationId, index)
      } catch (e) {
        console.error('Failed to delete message:', e)
        message.error('删除消息失败')
        return
      }
    }
    // Remove from UI
    removeMessage(index)
    message.success('已删除')
  }

  const handleRegenerate = async (assistantIndex: number) => {
    if (streaming) {
      message.warning('请等待当前回复完成')
      return
    }
    // Find the preceding user message
    const userIndex = assistantIndex - 1
    if (userIndex < 0 || messages[userIndex]?.role !== 'user') {
      message.error('无法重新生成：找不到对应的用户消息')
      return
    }
    const userContent = messages[userIndex].content
    // Truncate to remove both the user message and the assistant message
    truncateMessages(userIndex)
    if (activeConversationId) {
      try {
        await truncateConversation(activeConversationId, userIndex)
      } catch (e) {
        console.error('Failed to truncate conversation:', e)
      }
    }
    // Re-send the original user message to get a new response
    await sendMessage(userContent, activeConversationId)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const ToggleButton = (
    <span
      className="chat-header-toggle"
      onClick={toggleSidebar}
      title={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'}
    >
      {sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
    </span>
  )

  // Empty state: no messages (either new conversation or first visit)
  if (messages.length === 0) {
    return (
      <div className="app-main">
        <div className="chat-header">
          {ToggleButton}
          <span className="chat-header-title">新对话</span>
        </div>
        <div className="empty-state">
          <RobotOutlined className="empty-state-icon" />
          <div className="empty-state-text">
            您好呀，我是您的智能体助手，有什么可以帮助您的嘛
          </div>
          <div style={{ fontSize: 13, color: '#bbb' }}>
            可以问我天气、编程问题、生活建议等，很乐意为您解答
          </div>
        </div>
        <ChatInput
          input={input}
          setInput={setInput}
          handleSend={handleSend}
          handleKeyDown={handleKeyDown}
          streaming={streaming}
          onStop={handleStop}
          inputRef={inputRef}
        />
      </div>
    )
  }

  return (
    <div className="app-main">
      <div className="chat-header">
        {ToggleButton}
        <span className="chat-header-title">
          {conversations.find((c) => c.id === activeConversationId)?.title || '对话'}
        </span>
      </div>
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <MessageBubble
            key={msg.id || idx}
            role={msg.role as 'user' | 'assistant'}
            content={msg.content}
            streaming={streaming && idx === messages.length - 1 && msg.role === 'assistant'}
            index={idx}
            mapData={msg.mapData}
            weatherData={msg.weatherData}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onRegenerate={handleRegenerate}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>
      <ChatInput
        input={input}
        setInput={setInput}
        handleSend={handleSend}
        handleKeyDown={handleKeyDown}
        streaming={streaming}
        onStop={handleStop}
        inputRef={inputRef}
      />
    </div>
  )
}

// --------------------------------------------------------------------------- //

interface ChatInputProps {
  input: string
  setInput: (v: string) => void
  handleSend: () => void
  handleKeyDown: (e: React.KeyboardEvent) => void
  streaming: boolean
  onStop: () => void
  inputRef: React.RefObject<any>
}

const ChatInput: React.FC<ChatInputProps> = ({
  input,
  setInput,
  handleSend,
  handleKeyDown,
  streaming,
  onStop,
  inputRef,
}) => (
  <div className="chat-input-area">
    <div className="chat-input-wrapper">
      <TextArea
        ref={inputRef}
        className="chat-input"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="描述您的需求，点击发送即可"
        autoSize={{ minRows: 5, maxRows: 12 }}
        disabled={streaming}
      />
      {streaming ? (
        <Button
          danger
          icon={<StopOutlined />}
          onClick={onStop}
          className="chat-send-btn"
          shape="circle"
        />
      ) : (
        <Button
          type="primary"
          icon={<ArrowUpOutlined />}
          onClick={handleSend}
          disabled={!input.trim()}
          className="chat-send-btn"
          shape="circle"
        />
      )}
    </div>
  </div>
)

export default ChatPanel

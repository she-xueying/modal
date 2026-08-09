import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { RobotOutlined, UserOutlined, CopyOutlined, EditOutlined, CheckOutlined, CloseOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons'
import { message as antdMessage, Input, Popconfirm } from 'antd'
import { MapData, WeatherData, FileData } from '../services/api'
import MapView from './MapView'
import WeatherCard from './WeatherCard'

const { TextArea } = Input

interface MessageBubbleProps {
  role: 'user' | 'assistant' | 'system'
  content: string
  streaming?: boolean
  index?: number
  mapData?: MapData
  weatherData?: WeatherData
  fileData?: FileData
  onEdit?: (index: number, newContent: string) => void
  onDelete?: (index: number) => void
  onRegenerate?: (index: number) => void
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ role, content, streaming, index, mapData, weatherData, fileData, onEdit, onDelete, onRegenerate }) => {
  const isUser = role === 'user'
  const [editing, setEditing] = React.useState(false)
  const [editValue, setEditValue] = React.useState(content)
  const [copied, setCopied] = React.useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      antdMessage.success('已复制')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      antdMessage.error('复制失败')
    }
  }

  const handleStartEdit = () => {
    setEditValue(content)
    setEditing(true)
  }

  const handleSaveEdit = () => {
    const trimmed = editValue.trim()
    if (!trimmed) {
      antdMessage.warning('内容不能为空')
      return
    }
    if (index !== undefined && onEdit) {
      onEdit(index, trimmed)
    }
    setEditing(false)
  }

  const handleCancelEdit = () => {
    setEditing(false)
    setEditValue(content)
  }

  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      <div className={`message-avatar ${isUser ? 'user' : 'assistant'}`}>
        {isUser ? <UserOutlined /> : <RobotOutlined />}
      </div>
      <div className="message-content-wrapper">
        {editing ? (
          <div className="message-edit-area">
            <TextArea
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              autoSize={{ minRows: 1, maxRows: 8 }}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSaveEdit()
                }
                if (e.key === 'Escape') {
                  handleCancelEdit()
                }
              }}
            />
            <div className="message-edit-actions">
              <span className="message-action-btn save" onClick={handleSaveEdit} title="保存">
                <CheckOutlined />
              </span>
              <span className="message-action-btn cancel" onClick={handleCancelEdit} title="取消">
                <CloseOutlined />
              </span>
            </div>
          </div>
        ) : (
          <>
            {mapData && <MapView data={mapData} />}
            {weatherData && <WeatherCard data={weatherData} />}
            {fileData && (
              <div className={`file-card${isUser ? ' user' : ''}`}>
                <span className="file-card-icon">📄</span>
                <div className="file-card-info">
                  <div className="file-card-name">{fileData.filename}</div>
                  <div className="file-card-desc">
                    {isUser ? '已上传文档' : '修改后的文档，可下载'}
                  </div>
                </div>
                <a className="file-card-download" href={fileData.url} download>
                  下载
                </a>
              </div>
            )}
            <div className={`message-bubble ${isUser ? 'user' : 'assistant'}`}>
              {isUser ? (
                <span>{content}</span>
              ) : (
                <>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code({ node, className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '')
                        const isInline = !match && !String(children).includes('\n')
                        return isInline ? (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        ) : (
                          <SyntaxHighlighter
                            style={oneDark as any}
                            language={match ? match[1] : 'text'}
                            PreTag="pre"
                            {...props}
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        )
                      },
                    }}
                  >
                    {content || (streaming ? '...' : '')}
                  </ReactMarkdown>
                  {streaming && !content && (
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  )}
                </>
              )}
            </div>
            {/* Action bar */}
            {!streaming && content && (
              <div className="message-actions">
                <span className="message-action-btn" onClick={handleCopy} title="复制">
                  {copied ? <CheckOutlined /> : <CopyOutlined />}
                </span>
                {isUser && onEdit && index !== undefined && (
                  <span className="message-action-btn" onClick={handleStartEdit} title="编辑">
                    <EditOutlined />
                  </span>
                )}
                {!isUser && onRegenerate && index !== undefined && (
                  <span className="message-action-btn regenerate" onClick={() => onRegenerate(index)} title="重新生成">
                    <ReloadOutlined />
                  </span>
                )}
                {onDelete && index !== undefined && (
                  <Popconfirm
                    title="确定删除这条消息吗？"
                    onConfirm={() => onDelete(index)}
                    okText="删除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                  >
                    <span className="message-action-btn delete" title="删除">
                      <DeleteOutlined />
                    </span>
                  </Popconfirm>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default MessageBubble

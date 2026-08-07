import React from 'react'
import { Button, Popconfirm, message, Input, Checkbox } from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  MessageOutlined,
  SearchOutlined,
  CheckSquareOutlined,
  CloseOutlined,
} from '@ant-design/icons'
import { useStore } from '../stores/useStore'
import {
  listConversations,
  createConversation,
  deleteConversation,
  updateConversationTitle,
  batchDeleteConversations,
} from '../services/api'

const Sidebar: React.FC = () => {
  const {
    sidebarCollapsed,
    conversations,
    activeConversationId,
    setConversations,
    setActiveConversation,
    setMessages,
    removeConversation,
    removeConversations,
    addConversation,
    updateConversationTitle: updateStoreTitle,
  } = useStore()

  const [loading, setLoading] = React.useState(false)
  const [searchKeyword, setSearchKeyword] = React.useState('')
  const [editingId, setEditingId] = React.useState<string | null>(null)
  const [editValue, setEditValue] = React.useState('')
  const editInputRef = React.useRef<any>(null)

  // Batch delete state
  const [batchMode, setBatchMode] = React.useState(false)
  const [selectedIds, setSelectedIds] = React.useState<Set<string>>(new Set())

  // Load conversation list on mount
  React.useEffect(() => {
    loadConversations()
  }, [])

  // Focus edit input when editing starts
  React.useEffect(() => {
    if (editingId) {
      setTimeout(() => editInputRef.current?.focus(), 50)
    }
  }, [editingId])

  const loadConversations = async () => {
    setLoading(true)
    try {
      const convos = await listConversations()
      setConversations(convos)
    } catch (e) {
      console.error('Failed to load conversations:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleNewChat = async () => {
    try {
      const conv = await createConversation('新对话')
      addConversation(conv)
      setActiveConversation(conv.id)
      setMessages([])
    } catch (e) {
      message.error('创建对话失败')
    }
  }

  const handleSelect = (id: string) => {
    if (editingId) return // Don't switch while editing
    setActiveConversation(id)
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await deleteConversation(id)
      removeConversation(id)
      message.success('已删除')
    } catch (e) {
      message.error('删除失败')
    }
  }

  const handleStartEdit = (id: string, title: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingId(id)
    setEditValue(title)
  }

  const handleSaveTitle = async () => {
    if (!editingId) return
    const trimmed = editValue.trim()
    if (!trimmed) {
      message.warning('标题不能为空')
      return
    }
    try {
      await updateConversationTitle(editingId, trimmed)
      updateStoreTitle(editingId, trimmed)
      message.success('已更新')
    } catch (e) {
      message.error('更新失败')
    }
    setEditingId(null)
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setEditValue('')
  }

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSaveTitle()
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      handleCancelEdit()
    }
  }

  // ---- Batch delete handlers ----
  const handleEnterBatchMode = () => {
    setBatchMode(true)
    setSelectedIds(new Set())
    setEditingId(null)
  }

  const handleExitBatchMode = () => {
    setBatchMode(false)
    setSelectedIds(new Set())
  }

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleSelectAll = () => {
    if (selectedIds.size === filteredConversations.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredConversations.map((c) => c.id)))
    }
  }

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) {
      message.warning('请先选择要删除的对话')
      return
    }
    const ids = Array.from(selectedIds)
    try {
      await batchDeleteConversations(ids)
      removeConversations(ids)
      message.success(`已删除 ${ids.length} 个对话`)
      handleExitBatchMode()
    } catch (e) {
      message.error('批量删除失败')
    }
  }

  // Filter conversations by search keyword
  const filteredConversations = React.useMemo(() => {
    if (!searchKeyword.trim()) return conversations
    const kw = searchKeyword.toLowerCase()
    return conversations.filter((c) =>
      c.title.toLowerCase().includes(kw)
    )
  }, [conversations, searchKeyword])

  return (
    <div className={`app-sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="sidebar-header-actions">
          {!batchMode ? (
            <>
              <Button
                size="middle"
                icon={<CheckSquareOutlined />}
                onClick={handleEnterBatchMode}
                title="批量删除"
              />
              <Button
                type="primary"
                size="middle"
                icon={<PlusOutlined />}
                onClick={handleNewChat}
                loading={loading}
              >
                新对话
              </Button>
            </>
          ) : (
            <Button
              size="middle"
              icon={<CloseOutlined />}
              onClick={handleExitBatchMode}
              title="退出批量"
            />
          )}
        </div>
      </div>

      {batchMode && (
        <div className="sidebar-batch-toolbar">
          <Checkbox
            checked={selectedIds.size === filteredConversations.length && filteredConversations.length > 0}
            indeterminate={selectedIds.size > 0 && selectedIds.size < filteredConversations.length}
            onChange={handleSelectAll}
          >
            全选
          </Checkbox>
          <Popconfirm
            title={`确定删除选中的 ${selectedIds.size} 个对话吗？`}
            onConfirm={handleBatchDelete}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            disabled={selectedIds.size === 0}
          >
            <Button
              danger
              size="small"
              icon={<DeleteOutlined />}
              disabled={selectedIds.size === 0}
            >
              删除选中({selectedIds.size})
            </Button>
          </Popconfirm>
        </div>
      )}

      <div className="sidebar-search">
        <Input
          placeholder="搜索对话..."
          prefix={<SearchOutlined style={{ color: '#bbb' }} />}
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          allowClear
          size="middle"
          disabled={batchMode}
        />
      </div>

      <div className="sidebar-list">
        {filteredConversations.length === 0 && !loading && (
          <div style={{ textAlign: 'center', color: '#999', padding: '24px 8px', fontSize: 13 }}>
            {searchKeyword.trim() ? '未找到匹配的对话' : '点击"新对话"开始聊天'}
          </div>
        )}
        {filteredConversations.map((conv) => (
          <div
            key={conv.id}
            className={`sidebar-item ${activeConversationId === conv.id ? 'active' : ''} ${batchMode && selectedIds.has(conv.id) ? 'selected' : ''}`}
            onClick={() => batchMode ? handleToggleSelect(conv.id) : handleSelect(conv.id)}
          >
            {batchMode ? (
              <Checkbox
                checked={selectedIds.has(conv.id)}
                onChange={() => handleToggleSelect(conv.id)}
                onClick={(e) => e.stopPropagation()}
                style={{ marginRight: 8, flexShrink: 0 }}
              />
            ) : (
              <MessageOutlined style={{ marginRight: 8, fontSize: 14, flexShrink: 0 }} />
            )}
            {editingId === conv.id ? (
              <Input
                ref={editInputRef}
                size="small"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={handleEditKeyDown}
                onBlur={handleSaveTitle}
                onClick={(e) => e.stopPropagation()}
                style={{ flex: 1, marginRight: 4 }}
              />
            ) : (
              <span className="sidebar-item-title">{conv.title}</span>
            )}
            {!batchMode && editingId !== conv.id && (
              <div className="sidebar-item-actions">
                <span
                  className="sidebar-item-edit"
                  onClick={(e) => handleStartEdit(conv.id, conv.title, e)}
                  style={{ cursor: 'pointer', color: '#999', padding: '0 4px' }}
                  title="编辑标题"
                >
                  <EditOutlined />
                </span>
                <Popconfirm
                  title="确定删除这个对话吗？"
                  onConfirm={(e) => {
                    e?.stopPropagation()
                    handleDelete(conv.id, e as any)
                  }}
                  onCancel={(e) => e?.stopPropagation()}
                >
                  <span
                    className="sidebar-item-delete"
                    onClick={(e) => e.stopPropagation()}
                    style={{ cursor: 'pointer', color: '#ff4d4f', padding: '0 4px' }}
                  >
                    <DeleteOutlined />
                  </span>
                </Popconfirm>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default Sidebar

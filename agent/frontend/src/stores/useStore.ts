import { create } from 'zustand'
import { Conversation, Message, MapData, WeatherData, DefaultLocation, getDefaultLocation, setDefaultLocation, removeDefaultLocation } from '../services/api'

interface ChatState {
  // Sidebar
  sidebarCollapsed: boolean
  toggleSidebar: () => void

  // Conversation list
  conversations: Conversation[]
  activeConversationId: string | null

  // Messages of the active conversation
  messages: Message[]

  // Loading states
  loadingConversations: boolean
  loadingMessages: boolean
  streaming: boolean

  // Actions
  setConversations: (convos: Conversation[]) => void
  setActiveConversation: (id: string | null) => void
  setMessages: (msgs: Message[]) => void
  addMessage: (msg: Message) => void
  updateLastAssistantMessage: (content: string) => void
  setLastAssistantMapData: (data: MapData) => void
  setLastAssistantWeatherData: (data: WeatherData) => void
  truncateMessages: (upToIndex: number) => void
  updateMessage: (index: number, content: string) => void
  setLoadingConversations: (v: boolean) => void
  setLoadingMessages: (v: boolean) => void
  setStreaming: (v: boolean) => void

  // Default weather location
  defaultLocation: DefaultLocation | null
  fetchDefaultLocation: () => Promise<void>
  setDefaultWeatherLocation: (loc: DefaultLocation) => Promise<void>
  clearDefaultWeatherLocation: () => Promise<void>
  removeConversation: (id: string) => void
  removeConversations: (ids: string[]) => void
  addConversation: (conv: Conversation) => void
  updateConversationTitle: (id: string, title: string) => void
  removeMessage: (index: number) => void
}

export const useStore = create<ChatState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  conversations: [],
  activeConversationId: null,
  messages: [],
  loadingConversations: false,
  loadingMessages: false,
  streaming: false,

  setConversations: (convos) => set({ conversations: convos }),
  setActiveConversation: (id) => set({ activeConversationId: id }),
  setMessages: (msgs) => set({ messages: msgs }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateLastAssistantMessage: (content) =>
    set((s) => {
      const msgs = [...s.messages]
      const lastIdx = msgs.length - 1
      if (lastIdx >= 0 && msgs[lastIdx].role === 'assistant') {
        msgs[lastIdx] = { ...msgs[lastIdx], content }
      }
      return { messages: msgs }
    }),
  setLastAssistantMapData: (data) =>
    set((s) => {
      const msgs = [...s.messages]
      const lastIdx = msgs.length - 1
      if (lastIdx >= 0 && msgs[lastIdx].role === 'assistant') {
        msgs[lastIdx] = { ...msgs[lastIdx], mapData: data }
      }
      return { messages: msgs }
    }),
  setLastAssistantWeatherData: (data) =>
    set((s) => {
      const msgs = [...s.messages]
      const lastIdx = msgs.length - 1
      if (lastIdx >= 0 && msgs[lastIdx].role === 'assistant') {
        msgs[lastIdx] = { ...msgs[lastIdx], weatherData: data }
      }
      return { messages: msgs }
    }),
  truncateMessages: (upToIndex) =>
    set((s) => ({ messages: s.messages.slice(0, upToIndex) })),
  updateMessage: (index, content) =>
    set((s) => {
      const msgs = [...s.messages]
      if (index >= 0 && index < msgs.length) {
        msgs[index] = { ...msgs[index], content }
      }
      return { messages: msgs }
    }),
  setLoadingConversations: (v) => set({ loadingConversations: v }),
  setLoadingMessages: (v) => set({ loadingMessages: v }),
  setStreaming: (v) => set({ streaming: v }),

  defaultLocation: null,
  fetchDefaultLocation: async () => {
    try {
      const loc = await getDefaultLocation()
      set({ defaultLocation: loc })
    } catch {
      // ignore network errors
    }
  },
  setDefaultWeatherLocation: async (loc) => {
    await setDefaultLocation(loc)
    set({ defaultLocation: loc })
  },
  clearDefaultWeatherLocation: async () => {
    await removeDefaultLocation()
    set({ defaultLocation: null })
  },
  removeConversation: (id) =>
    set((s) => ({
      conversations: s.conversations.filter((c) => c.id !== id),
      activeConversationId:
        s.activeConversationId === id ? null : s.activeConversationId,
      messages: s.activeConversationId === id ? [] : s.messages,
    })),
  removeConversations: (ids) =>
    set((s) => {
      const idSet = new Set(ids)
      const remaining = s.conversations.filter((c) => !idSet.has(c.id))
      const activeCleared = s.activeConversationId && idSet.has(s.activeConversationId)
      return {
        conversations: remaining,
        activeConversationId: activeCleared ? null : s.activeConversationId,
        messages: activeCleared ? [] : s.messages,
      }
    }),
  addConversation: (conv) =>
    set((s) => ({ conversations: [conv, ...s.conversations] })),
  updateConversationTitle: (id, title) =>
    set((s) => ({
      conversations: s.conversations.map((c) =>
        c.id === id ? { ...c, title } : c
      ),
    })),
  removeMessage: (index) =>
    set((s) => ({
      messages: s.messages.filter((_, i) => i !== index),
    })),
}))

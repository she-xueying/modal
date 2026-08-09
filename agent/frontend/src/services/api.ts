/**
 * API service: communicates with the FastAPI backend.
 * Includes SSE streaming for chat responses.
 */

const API_BASE = '/api'

// --------------------------------------------------------------------------- //
//  Types
// --------------------------------------------------------------------------- //

export interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

export interface TravelInfo {
  mode: string
  icon: string
  distance_km: number
  duration_hours: number
  duration_text: string
}

export interface MapData {
  place: string
  lat: number
  lon: number
  display_name: string
  timezone: string
  local_time: string
  weekday: string
  travel_info: TravelInfo[]
}

export interface CurrentWeather {
  temperature: number | null
  apparent_temperature: number | null
  humidity: number | null
  precipitation: number | null
  wind_speed: number | null
  wind_direction: number | null
  wind_dir_text: string
  weather_code: number | null
  condition: string
  is_day: boolean
  uv_index: number | null
  cloud_cover: number | null
  pressure: number | null
  visibility: number | null
  precipitation_probability: number | null
}

export interface DailyWeather {
  date?: string
  weather_code: number | null
  condition: string
  temp_max: number | null
  temp_min: number | null
  precip_prob?: number | null
  sunrise?: string | null
  sunset?: string | null
}

export interface HourlyWeather {
  time: string | null
  temperature: number | null
  weather_code: number | null
  condition: string
  precip_prob: number | null
}

export interface WeatherData {
  place: string
  display_name: string
  lat: number
  lon: number
  current: CurrentWeather
  daily: DailyWeather[]
  hourly: HourlyWeather[]
  /** Backward compat: old persisted data may have a single-day `today`. */
  today?: DailyWeather
}

export interface DefaultLocation {
  place: string
  display_name: string
  lat: number
  lon: number
}

export interface FileData {
  id: string
  filename: string
  url: string
}

export interface Message {
  id?: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at?: string
  mapData?: MapData
  map_data?: MapData | string | null
  weatherData?: WeatherData
  weather_data?: WeatherData | string | null
  fileData?: FileData
  file_data?: FileData | string | null
}

// --------------------------------------------------------------------------- //
//  Conversation CRUD
// --------------------------------------------------------------------------- //

export async function listConversations(): Promise<Conversation[]> {
  const resp = await fetch(`${API_BASE}/conversations`)
  if (!resp.ok) throw new Error('获取对话列表失败')
  return resp.json()
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  const resp = await fetch(`${API_BASE}/conversations/${id}`)
  if (!resp.ok) throw new Error('获取对话详情失败')
  const detail = (await resp.json()) as ConversationDetail
  // Restore persisted map_data (object or JSON string) into mapData
  detail.messages = (detail.messages || []).map((m) => {
    if (m.map_data) {
      m.mapData =
        typeof m.map_data === 'string' ? JSON.parse(m.map_data) : m.map_data
    }
    if (m.weather_data) {
      m.weatherData =
        typeof m.weather_data === 'string'
          ? JSON.parse(m.weather_data)
          : m.weather_data
    }
    if (m.file_data) {
      m.fileData =
        typeof m.file_data === 'string' ? JSON.parse(m.file_data) : m.file_data
    }
    return m
  })
  return detail
}

export async function createConversation(title: string = '新对话'): Promise<Conversation> {
  const resp = await fetch(`${API_BASE}/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  if (!resp.ok) throw new Error('创建对话失败')
  return resp.json()
}

export async function deleteConversation(id: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/conversations/${id}`, { method: 'DELETE' })
  if (!resp.ok) throw new Error('删除对话失败')
}

export async function updateConversationTitle(id: string, title: string): Promise<Conversation> {
  const resp = await fetch(
    `${API_BASE}/conversations/${id}?title=${encodeURIComponent(title)}`,
    { method: 'PATCH' },
  )
  if (!resp.ok) throw new Error('更新标题失败')
  return resp.json()
}

export async function truncateConversation(conversationId: string, keepCount: number): Promise<void> {
  const resp = await fetch(
    `${API_BASE}/conversations/${conversationId}/truncate?keep_count=${keepCount}`,
    { method: 'POST' },
  )
  if (!resp.ok) throw new Error('截断对话失败')
}

export async function batchDeleteConversations(ids: string[]): Promise<void> {
  const resp = await fetch(`${API_BASE}/conversations/batch-delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  })
  if (!resp.ok) throw new Error('批量删除失败')
}

export async function deleteMessage(conversationId: string, messageIndex: number): Promise<void> {
  const resp = await fetch(
    `${API_BASE}/conversations/${conversationId}/messages/${messageIndex}`,
    { method: 'DELETE' },
  )
  if (!resp.ok) throw new Error('删除消息失败')
}

// --------------------------------------------------------------------------- //
//  Default weather location
// --------------------------------------------------------------------------- //

export async function getDefaultLocation(): Promise<DefaultLocation | null> {
  const resp = await fetch(`${API_BASE}/settings/default-location`)
  if (!resp.ok) throw new Error('获取默认地点失败')
  const data = await resp.json()
  return data.default ?? null
}

export async function setDefaultLocation(loc: DefaultLocation): Promise<void> {
  const resp = await fetch(`${API_BASE}/settings/default-location`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(loc),
  })
  if (!resp.ok) throw new Error('设置默认地点失败')
}

export async function removeDefaultLocation(): Promise<void> {
  const resp = await fetch(`${API_BASE}/settings/default-location`, {
    method: 'DELETE',
  })
  if (!resp.ok) throw new Error('清除默认地点失败')
}

// --------------------------------------------------------------------------- //
//  File upload / download
// --------------------------------------------------------------------------- //

export async function uploadFile(file: File): Promise<FileData> {
  const form = new FormData()
  form.append('file', file)
  const resp = await fetch(`${API_BASE}/files/upload`, {
    method: 'POST',
    body: form,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => null)
    throw new Error(err?.detail || '上传文件失败')
  }
  const data = await resp.json()
  return { id: data.id, filename: data.filename, url: `${API_BASE}/files/${data.id}/download` }
}

// --------------------------------------------------------------------------- //
//  Streaming Chat (SSE)
// --------------------------------------------------------------------------- //

export interface ChatStreamCallbacks {
  onConversationId?: (id: string) => void
  onMessage: (chunk: string) => void
  onMap?: (data: MapData) => void
  onWeather?: (data: WeatherData) => void
  onFile?: (data: FileData) => void
  onError?: (error: string) => void
  onDone?: () => void
}

export async function streamChat(
  message: string,
  conversationId: string | null,
  callbacks: ChatStreamCallbacks,
  signal?: AbortSignal,
  userLat?: number,
  userLon?: number,
  fileId?: string | null,
): Promise<void> {
  const body: Record<string, any> = {
    conversation_id: conversationId,
    message,
  }
  if (userLat != null && userLon != null) {
    body.user_lat = userLat
    body.user_lon = userLon
  }
  if (fileId) {
    body.file_id = fileId
  }

  const resp = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })

  if (!resp.ok) {
    throw new Error(`请求失败: ${resp.status}`)
  }

  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // Process complete SSE events (separated by \n\n)
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || '' // Keep incomplete part in buffer

    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data: ')) continue

      const jsonStr = line.slice(6)
      try {
        const data = JSON.parse(jsonStr)

        switch (data.type) {
          case 'conversation':
            callbacks.onConversationId?.(data.id)
            break
          case 'message':
            callbacks.onMessage(data.content)
            break
          case 'map':
            callbacks.onMap?.(data.data)
            break
          case 'weather':
            callbacks.onWeather?.(data.data)
            break
          case 'file':
            callbacks.onFile?.(data.data)
            break
          case 'error':
            callbacks.onError?.(data.content)
            break
          case 'done':
            callbacks.onDone?.()
            return
        }
      } catch {
        // Ignore malformed JSON
      }
    }
  }

  callbacks.onDone?.()
}

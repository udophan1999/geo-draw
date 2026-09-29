// Typed client for the FastAPI server in api/. Cookies carry the session, so every call
// is same-origin (Vite proxies /api in dev; FastAPI serves the built app in production).

export type User = { id: string; name: string }
export type Me = {
  user: User | null
  quota: { used: number; limit: number }
  ai_available: boolean
}
export type Conversation = { id: string; title: string; created_at: number; updated_at: number }
export type Role = 'user' | 'assistant'
export type Message = {
  id: string
  conversation_id: string
  role: Role
  text: string
  created_at: number
  image_url: string | null
  video_url: string | null
  has_drawing: boolean
  has_log: boolean
}
export type ConversationDetail = { conversation: Conversation; messages: Message[] }
export type Settings = {
  mode: 'ai' | 'parser'
  model: 'deepseek-v4-flash' | 'deepseek-v4-pro'
  quality: 'l' | 'm' | 'h'
  animate: boolean
}
export type Example = { name: string; problem: string }
export type ManualEdits = {
  hidden_labels: string[]
  hidden_points: string[]
  hidden_segments: string[]
  added_segments: string[]
  segment_widths: Record<string, number>
  constructions: Record<string, string>[]
}
export type LabelOffsets = Record<string, [number, number]>
export type EditorState = {
  labels: string[]
  segments: string[]
  label_offsets: LabelOffsets
  manual_edits: ManualEdits
}
export type Progress = { stage: string; label: string }

export class ApiError extends Error {
  status: number
  suggestions: string[]

  constructor(status: number, message: string, suggestions: string[] = []) {
    super(message)
    this.status = status
    this.suggestions = suggestions
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(`/api${path}`, { ...init, headers, credentials: 'same-origin' })
  if (!response.ok) {
    let message = 'Có lỗi xảy ra. Hãy thử lại.'
    let suggestions: string[] = []
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') message = body.detail
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) message = body.detail[0].msg
      suggestions = body.suggestions ?? []
    } catch {
      // not JSON: keep the generic message
    }
    throw new ApiError(response.status, message, suggestions)
  }
  if (response.status === 204) return undefined as T
  const type = response.headers.get('content-type') ?? ''
  return (type.includes('application/json') ? response.json() : response.text()) as Promise<T>
}

const json = (body: unknown) => JSON.stringify(body)

export const api = {
  me: () => request<Me>('/auth/me'),
  login: (username: string, password: string) =>
    request<Me>('/auth/login', { method: 'POST', body: json({ username, password }) }),
  register: (username: string, password: string) =>
    request<Me>('/auth/register', { method: 'POST', body: json({ username, password }) }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),

  settings: () => request<Settings>('/settings'),
  saveSettings: (settings: Settings) =>
    request<Settings>('/settings', { method: 'PUT', body: json(settings) }),
  examples: () => request<Example[]>('/examples'),
  help: () => request<{ markdown: string }>('/help'),

  conversations: () => request<Conversation[]>('/conversations'),
  conversation: (id: string) => request<ConversationDetail>(`/conversations/${id}`),
  renameConversation: (id: string, title: string) =>
    request<Conversation>(`/conversations/${id}`, { method: 'PATCH', body: json({ title }) }),
  deleteConversation: (id: string) =>
    request<void>(`/conversations/${id}`, { method: 'DELETE' }),

  sendMessage: (input: { text: string; conversationId?: string; image?: File | null }) => {
    const form = new FormData()
    form.set('text', input.text)
    if (input.conversationId) form.set('conversation_id', input.conversationId)
    if (input.image) form.set('image', input.image)
    return request<{ conversation: Conversation; job_id: string }>('/messages', {
      method: 'POST',
      body: form,
    })
  },

  scene: (messageId: string) => request<string>(`/messages/${messageId}/scene`),
  log: (messageId: string) => request<string>(`/messages/${messageId}/log`),
  editor: (messageId: string) => request<EditorState>(`/messages/${messageId}/editor`),
  render: (messageId: string, label_offsets: LabelOffsets, manual_edits: ManualEdits) =>
    request<Message>(`/messages/${messageId}/render`, {
      method: 'POST',
      body: json({ label_offsets, manual_edits }),
    }),
}

export type JobHandlers = {
  onMessage: (message: Message) => void
  onProgress: (progress: Progress) => void
  onDone: () => void
  onFailed: (detail: string) => void
}

/** Follow a drawing job over SSE. Returns a function that stops listening. */
export function followJob(jobId: string, handlers: JobHandlers): () => void {
  const source = new EventSource(`/api/jobs/${jobId}/events`)
  let finished = false
  const finish = () => {
    finished = true
    source.close()
  }
  source.addEventListener('message', (event) => handlers.onMessage(JSON.parse(event.data)))
  source.addEventListener('progress', (event) => handlers.onProgress(JSON.parse(event.data)))
  source.addEventListener('done', () => {
    finish()
    handlers.onDone()
  })
  source.addEventListener('failed', (event) => {
    finish()
    handlers.onFailed(JSON.parse(event.data).detail)
  })
  // Connection trouble: EventSource retries by itself; give up only if it closed for good.
  source.onerror = () => {
    if (!finished && source.readyState === EventSource.CLOSED) {
      finish()
      handlers.onFailed('Mất kết nối tới máy chủ. Tải lại trang để xem kết quả.')
    }
  }
  return finish
}

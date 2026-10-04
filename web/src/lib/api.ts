// Typed client for the FastAPI server in api/. Cookies carry the session, so every call
// is same-origin (Vite proxies /api in dev; FastAPI serves the built app in production).

export type User = { id: string; name: string; role: 'user' | 'admin' }
export type Me = {
  user: User | null
  quota: { used: number; limit: number }
  ai_available: boolean
}
export type TutorMode = 'hint' | 'solution'
export type Conversation = {
  id: string
  title: string
  created_at: number
  updated_at: number
  problem: string
  mode: TutorMode
  hint_level: number
  /** The student reached the final answer (reported by the tutor in hint mode). */
  solved: boolean
  is_geometry: boolean
}
export type Role = 'user' | 'assistant'
export type Channel = 'chat' | 'figure'
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
  /** "chat": the tutor conversation. "figure": drawing requests and drawings. */
  channel: Channel
  meta: { mode?: TutorMode; hint_level?: number; solved?: boolean; error?: boolean }
}
export type ConversationDetail = { conversation: Conversation; messages: Message[] }
export type Settings = {
  mode: 'ai' | 'parser'
  model: 'deepseek-v4-flash' | 'deepseek-v4-pro'
  quality: 'l' | 'm' | 'h'
  animate: boolean
}
export type Example = { topic: string; name: string; problem: string }
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

export type AdminUser = {
  id: string
  name: string
  role: 'user' | 'admin'
  disabled: boolean
  created_at: number
  last_login: number | null
  /** The latest change to one of the user's conversations. */
  last_active: number | null
  conversations: number
  /** ``custom``: the admin set this user's own limit instead of the server default. */
  quota: { used: number; limit: number; custom: boolean }
}
export type AdminUserList = { users: AdminUser[]; default_limit: number }
export type AdminUserUpdate = {
  role?: 'user' | 'admin'
  disabled?: boolean
  daily_limit?: number
  reset_limit?: boolean
}
export type PromptInfo = {
  key: string
  label: string
  description: string
  default: string
  value: string
  custom: boolean
  updated_at: number | null
  updated_by: string | null
}
export type AdminStats = {
  days: string[]
  series: { new_users: number[]; new_conversations: number[]; ai_users: number[]; ai_guests: number[] }
  totals: {
    users: number; admins: number; locked: number; new_users: number; active_users: number
    conversations: number; new_conversations: number; ai_turns: number; ai_guest_turns: number
  }
  outcomes: { solved: number; solution: number; in_progress: number }
  top_users: { id: string; name: string; ai_turns: number; conversations: number }[]
}
export type AdminUserDetail = AdminUser & {
  default_limit: number
  days: string[]
  series: { ai: number[]; questions: number[] }
  totals: {
    ai_turns: number; ai_turns_range: number; questions: number; questions_range: number
    conversations: number; conversations_range: number; drawings: number; active_days: number
  }
  outcomes: { solved: number; solution: number; in_progress: number }
  /** Conversations by the hint level they reached (index 0 = level 1). */
  hint_levels: number[]
  recent_conversations: {
    id: string; title: string; created_at: number; updated_at: number; mode: TutorMode
    hint_level: number; solved: boolean; questions: number; drawings: number
  }[]
}
export type PromptList = { prompts: PromptInfo[]; fixed: { label: string; text: string }[] }
export type TutorAction = 'ask' | 'deeper' | 'solution' | 'hint'

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

  /** A message to the tutor; ``action`` is "deeper", "solution" or "hint" for the buttons. */
  sendMessage: (input: { text: string; conversationId?: string; image?: File | null; action?: TutorAction }) => {
    const form = new FormData()
    form.set('text', input.text)
    if (input.conversationId) form.set('conversation_id', input.conversationId)
    if (input.image) form.set('image', input.image)
    if (input.action) form.set('action', input.action)
    return request<{ conversation: Conversation; job_id: string }>('/messages', {
      method: 'POST',
      body: form,
    })
  },
  /** Draw the figure (empty text) or refine it with a request. */
  drawFigure: (conversationId: string, text = '') =>
    request<{ job_id: string }>(`/conversations/${conversationId}/figure`, {
      method: 'POST',
      body: json({ text }),
    }),

  admin: {
    stats: (days: number) => request<AdminStats>(`/admin/stats?days=${days}`),
    user: (id: string, days: number) => request<AdminUserDetail>(`/admin/users/${id}?days=${days}`),
    users: (q = '') => request<AdminUserList>(`/admin/users?q=${encodeURIComponent(q)}`),
    updateUser: (id: string, update: AdminUserUpdate) =>
      request<AdminUser>(`/admin/users/${id}`, { method: 'PATCH', body: json(update) }),
    resetPassword: (id: string, password: string) =>
      request<void>(`/admin/users/${id}/password`, { method: 'POST', body: json({ password }) }),
    deleteUser: (id: string) => request<void>(`/admin/users/${id}`, { method: 'DELETE' }),
    prompts: () => request<PromptList>('/admin/prompts'),
    savePrompt: (key: string, value: string) =>
      request<PromptList>(`/admin/prompts/${encodeURIComponent(key)}`, { method: 'PUT', body: json({ value }) }),
    resetPrompt: (key: string) =>
      request<PromptList>(`/admin/prompts/${encodeURIComponent(key)}`, { method: 'DELETE' }),
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
  /** A piece of the tutor's reply as it is written. */
  onDelta?: (text: string) => void
  onConversation?: (conversation: Conversation) => void
  /** The first message of a geometry problem started a drawing job. */
  onFigureJob?: (jobId: string) => void
  onFigureSkipped?: (detail: string) => void
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
  source.addEventListener('delta', (event) => handlers.onDelta?.(JSON.parse(event.data).text))
  source.addEventListener('conversation', (event) => handlers.onConversation?.(JSON.parse(event.data)))
  source.addEventListener('figure_job', (event) => handlers.onFigureJob?.(JSON.parse(event.data).job_id))
  source.addEventListener('figure_skipped', (event) =>
    handlers.onFigureSkipped?.(JSON.parse(event.data).detail),
  )
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

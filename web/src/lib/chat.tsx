// Tracks running drawing turns above the routes, so progress survives navigating from
// "/" to "/c/:id" when a new conversation is created.
import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'

import { ApiError, api, followJob } from '@/lib/api'
import { keys, upsertMessage } from '@/lib/queries'

export type PendingTurn = {
  text: string
  imagePreview: string | null
  label: string
  userSaved: boolean // the server has stored the user message (it is in the list now)
}

type ChatContextValue = {
  pending: Record<string, PendingTurn>
  /** Resolves true once the server accepted the message (the job then runs on). */
  send: (input: { text: string; image?: File | null; conversationId?: string }) => Promise<boolean>
  sending: boolean
}

const ChatContext = createContext<ChatContextValue | null>(null)

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const client = useQueryClient()
  const navigate = useNavigate()
  const [pending, setPending] = useState<Record<string, PendingTurn>>({})
  const [sending, setSending] = useState(false)
  const stops = useRef<(() => void)[]>([])

  useEffect(() => () => stops.current.forEach((stop) => stop()), [])

  const update = useCallback((id: string, patch: Partial<PendingTurn> | null) => {
    setPending((old) => {
      const next = { ...old }
      if (patch === null) delete next[id]
      else next[id] = { ...old[id], ...patch }
      return next
    })
  }, [])

  const send = useCallback<ChatContextValue['send']>(
    async ({ text, image, conversationId }) => {
      setSending(true)
      let started
      try {
        started = await api.sendMessage({ text, image, conversationId })
      } catch (error) {
        toast.error(error instanceof ApiError ? error.message : 'Không gửi được tin nhắn.')
        return false
      } finally {
        setSending(false)
      }
      const id = started.conversation.id
      const preview = image ? URL.createObjectURL(image) : null
      update(id, { text, imagePreview: preview, label: 'Đang gửi...', userSaved: false })
      if (!conversationId) {
        client.setQueryData(keys.conversation(id), { conversation: started.conversation, messages: [] })
        client.invalidateQueries({ queryKey: keys.conversations })
        navigate(`/c/${id}`)
      }
      const finish = () => {
        update(id, null)
        if (preview) URL.revokeObjectURL(preview)
        // Re-read from the server: a page load racing the SSE events may have missed one.
        client.invalidateQueries({ queryKey: keys.conversation(id) })
        client.invalidateQueries({ queryKey: keys.conversations })
        client.invalidateQueries({ queryKey: keys.me })
      }
      stops.current.push(
        followJob(started.job_id, {
          onMessage: (message) => {
            upsertMessage(client, message)
            if (message.role === 'user') update(id, { userSaved: true })
          },
          onProgress: ({ label }) => update(id, { label }),
          onDone: finish,
          onFailed: (detail) => {
            toast.error(detail)
            finish()
          },
        }),
      )
      return true
    },
    [client, navigate, update],
  )

  return <ChatContext.Provider value={{ pending, send, sending }}>{children}</ChatContext.Provider>
}

export function useChat() {
  const value = useContext(ChatContext)
  if (!value) throw new Error('useChat must be used inside ChatProvider')
  return value
}

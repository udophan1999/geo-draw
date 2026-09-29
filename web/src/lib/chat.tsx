// Tracks running turns above the routes, so progress survives navigating from "/" to
// "/c/:id" when a new conversation is created. Two kinds run independently:
// - tutor turns (chat channel): optimistic user bubble, then the reply streaming in;
// - figure turns (figure channel): drawing progress shown in the drawing panel.
import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'

import { ApiError, api, followJob, type ConversationDetail, type TutorAction } from '@/lib/api'
import { keys, upsertMessage } from '@/lib/queries'

export type PendingTurn = {
  text: string
  imagePreview: string | null
  label: string
  userSaved: boolean // the server has stored the user message (it is in the list now)
  reply: string // the tutor's reply so far
}
export type PendingFigure = { label: string }

type ChatContextValue = {
  pending: Record<string, PendingTurn>
  figures: Record<string, PendingFigure>
  /** Resolves true once the server accepted the message (the job then runs on). */
  send: (input: { text: string; image?: File | null; conversationId?: string; action?: TutorAction }) => Promise<boolean>
  drawFigure: (conversationId: string, text?: string) => Promise<boolean>
  sending: boolean
}

const ChatContext = createContext<ChatContextValue | null>(null)

function useRecord<T>() {
  const [record, setRecord] = useState<Record<string, T>>({})
  const update = useCallback((id: string, patch: Partial<T> | null) => {
    setRecord((old) => {
      const next = { ...old }
      if (patch === null) delete next[id]
      else next[id] = { ...old[id], ...patch }
      return next
    })
  }, [])
  return [record, update] as const
}

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const client = useQueryClient()
  const navigate = useNavigate()
  const [pending, updateTurn] = useRecord<PendingTurn>()
  const [figures, updateFigure] = useRecord<PendingFigure>()
  const [sending, setSending] = useState(false)
  const stops = useRef<(() => void)[]>([])

  useEffect(() => () => stops.current.forEach((stop) => stop()), [])

  const refresh = useCallback(
    (id: string) => {
      // Re-read from the server: a page load racing the SSE events may have missed one.
      client.invalidateQueries({ queryKey: keys.conversation(id) })
      client.invalidateQueries({ queryKey: keys.conversations })
      client.invalidateQueries({ queryKey: keys.me })
    },
    [client],
  )

  const followFigure = useCallback(
    (conversationId: string, jobId: string) => {
      updateFigure(conversationId, { label: 'Đang vẽ hình...' })
      const finish = () => {
        updateFigure(conversationId, null)
        refresh(conversationId)
      }
      stops.current.push(
        followJob(jobId, {
          onMessage: (message) => upsertMessage(client, message),
          onProgress: ({ label }) => updateFigure(conversationId, { label }),
          onDone: finish,
          onFailed: (detail) => {
            toast.error(detail)
            finish()
          },
        }),
      )
    },
    [client, refresh, updateFigure],
  )

  const send = useCallback<ChatContextValue['send']>(
    async ({ text, image, conversationId, action }) => {
      setSending(true)
      let started
      try {
        started = await api.sendMessage({ text, image, conversationId, action })
      } catch (error) {
        toast.error(error instanceof ApiError ? error.message : 'Không gửi được tin nhắn.')
        return false
      } finally {
        setSending(false)
      }
      const id = started.conversation.id
      const preview = image ? URL.createObjectURL(image) : null
      updateTurn(id, { text, imagePreview: preview, label: 'Đang gửi...', userSaved: false, reply: '' })
      if (!conversationId) {
        client.setQueryData<ConversationDetail>(keys.conversation(id), { conversation: started.conversation, messages: [] })
        client.invalidateQueries({ queryKey: keys.conversations })
        navigate(`/c/${id}`)
      }
      let reply = ''
      const finish = () => {
        updateTurn(id, null)
        if (preview) URL.revokeObjectURL(preview)
        refresh(id)
      }
      stops.current.push(
        followJob(started.job_id, {
          onMessage: (message) => {
            upsertMessage(client, message)
            if (message.role === 'user') updateTurn(id, { userSaved: true })
            else updateTurn(id, { reply: '', label: '' }) // the saved reply replaces the stream
          },
          onDelta: (piece) => {
            reply += piece
            updateTurn(id, { reply })
          },
          onProgress: ({ label }) => updateTurn(id, { label }),
          onConversation: (conversation) => {
            client.setQueryData<ConversationDetail>(keys.conversation(id), (old) =>
              old ? { ...old, conversation } : old,
            )
            client.invalidateQueries({ queryKey: keys.conversations })
          },
          onFigureJob: (jobId) => followFigure(id, jobId),
          onFigureSkipped: (detail) => toast.info(`Chưa vẽ hình: ${detail}`),
          onDone: finish,
          onFailed: (detail) => {
            toast.error(detail)
            finish()
          },
        }),
      )
      return true
    },
    [client, followFigure, navigate, refresh, updateTurn],
  )

  const drawFigure = useCallback<ChatContextValue['drawFigure']>(
    async (conversationId, text = '') => {
      try {
        const { job_id } = await api.drawFigure(conversationId, text)
        followFigure(conversationId, job_id)
        return true
      } catch (error) {
        toast.error(error instanceof ApiError ? error.message : 'Không vẽ được hình.')
        return false
      }
    },
    [followFigure],
  )

  return (
    <ChatContext.Provider value={{ pending, figures, send, drawFigure, sending }}>{children}</ChatContext.Provider>
  )
}

export function useChat() {
  const value = useContext(ChatContext)
  if (!value) throw new Error('useChat must be used inside ChatProvider')
  return value
}

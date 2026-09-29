// "/" (new chat) and "/c/:conversationId": chat on the left, the drawing on the right.
import { useState } from 'react'
import { Navigate, useParams } from 'react-router'

import { Composer } from '@/components/chat/Composer'
import { MessageList } from '@/components/chat/MessageList'
import { DrawingPanel } from '@/components/drawing/DrawingPanel'
import { ApiError } from '@/lib/api'
import { useChat } from '@/lib/chat'
import { acceptImage } from '@/lib/images'
import { useConversation } from '@/lib/queries'
import { cn } from '@/lib/utils'

export function ChatPage() {
  const { conversationId } = useParams()
  const conversation = useConversation(conversationId)
  const { pending, send } = useChat()
  const turn = conversationId ? pending[conversationId] : undefined
  const messages = conversation.data?.messages ?? []
  const drawings = messages.filter((m) => m.has_drawing && m.image_url)

  // A pick only holds for the conversation and drawing count it was made in, so a new
  // conversation or a new drawing shows the newest version again.
  const pickKey = `${conversationId}:${drawings.length}`
  const [pick, setPick] = useState<{ key: string; id: string } | null>(null)
  const picked = pick?.key === pickKey ? pick.id : null
  const [image, setImage] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [mobileView, setMobileView] = useState<'chat' | 'drawing'>('chat')

  if (conversation.error instanceof ApiError && conversation.error.status === 404) {
    return <Navigate to="/" replace />
  }
  const shown = drawings.find((d) => d.id === picked) ?? drawings.at(-1) ?? null
  const showDrawing = (id: string) => {
    setPick({ key: pickKey, id })
    setMobileView('drawing')
  }
  const sendMessage = (text: string, file: File | null) => send({ text, image: file, conversationId })

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex gap-1 border-b p-2 lg:hidden">
        {(['chat', 'drawing'] as const).map((view) => (
          <button
            key={view}
            type="button"
            onClick={() => setMobileView(view)}
            className={cn('flex-1 rounded-lg py-1.5 text-sm', mobileView === view ? 'bg-muted font-medium' : 'text-muted-foreground')}
          >
            {view === 'chat' ? 'Trò chuyện' : `Hình vẽ${drawings.length ? ` (${drawings.length})` : ''}`}
          </button>
        ))}
      </div>
      <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <section
          className={cn('relative flex min-h-0 flex-col lg:border-r', mobileView !== 'chat' && 'hidden lg:flex')}
          onDragOver={(event) => {
            if (event.dataTransfer.types.includes('Files')) {
              event.preventDefault()
              setDragging(true)
            }
          }}
          onDragLeave={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false)
          }}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            const file = acceptImage(event.dataTransfer.files[0])
            if (file) setImage(file)
          }}
        >
          <div className="min-h-0 flex-1 overflow-y-auto">
            <MessageList
              messages={messages}
              pending={turn}
              loading={Boolean(conversationId) && conversation.isPending}
              shownDrawingId={shown?.id ?? null}
              onShowDrawing={showDrawing}
              onExample={(example) => void sendMessage(example.problem, null)}
            />
          </div>
          <Composer
            image={image}
            onImage={setImage}
            onSend={sendMessage}
            busy={Boolean(turn)}
            placeholder={messages.length ? 'Yêu cầu chỉnh hình, vd: vẽ thêm đường cao AH' : 'Nhập đề bài hoặc đính kèm ảnh đề…'}
          />
          {dragging && (
            <div className="pointer-events-none absolute inset-3 flex items-center justify-center rounded-2xl border-2 border-dashed border-primary bg-primary/5 text-sm font-medium text-primary">
              Thả ảnh đề bài vào đây
            </div>
          )}
        </section>
        <section className={cn('min-h-0 overflow-y-auto bg-muted/30', mobileView !== 'drawing' && 'hidden lg:block')}>
          <DrawingPanel drawings={drawings} shown={shown} onShow={showDrawing} busy={Boolean(turn)} />
        </section>
      </div>
    </div>
  )
}

// "/" (new problem) and "/c/:conversationId": the tutor chat, plus the figure panel on the
// right for geometry problems (or once a figure was drawn on request).
import { PenTool } from 'lucide-react'
import { useState } from 'react'
import { Navigate, useParams } from 'react-router'

import { Composer } from '@/components/chat/Composer'
import { MessageList } from '@/components/chat/MessageList'
import { TutorBar } from '@/components/chat/TutorBar'
import { DrawingPanel } from '@/components/drawing/DrawingPanel'
import { Button } from '@/components/ui/button'
import { ApiError, type TutorAction } from '@/lib/api'
import { useChat } from '@/lib/chat'
import { acceptImage } from '@/lib/images'
import { useConversation } from '@/lib/queries'
import { cn } from '@/lib/utils'

export function ChatPage() {
  const { conversationId } = useParams()
  const conversation = useConversation(conversationId)
  const { pending, figures, send, drawFigure } = useChat()
  const turn = conversationId ? pending[conversationId] : undefined
  const figureTurn = conversationId ? figures[conversationId] : undefined
  const detail = conversation.data
  const messages = detail?.messages ?? []
  const chatMessages = messages.filter((m) => m.channel === 'chat')
  const figureMessages = messages.filter((m) => m.channel === 'figure')
  const drawings = figureMessages.filter((m) => m.has_drawing && m.image_url)

  const [pick, setPick] = useState<{ key: string; id: string } | null>(null)
  const [image, setImage] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [mobileView, setMobileView] = useState<'chat' | 'drawing'>('chat')

  if (conversation.error instanceof ApiError && conversation.error.status === 404) {
    return <Navigate to="/" replace />
  }

  // A pick only holds for the conversation and drawing count it was made in, so a new
  // drawing shows the newest version again.
  const pickKey = `${conversationId}:${drawings.length}`
  const picked = pick?.key === pickKey ? pick.id : null
  const shown = drawings.find((d) => d.id === picked) ?? drawings.at(-1) ?? null
  const showDrawing = (id: string) => {
    setPick({ key: pickKey, id })
    setMobileView('drawing')
  }

  const info = detail?.conversation
  const hasFigurePanel = Boolean(figureMessages.length || figureTurn || info?.is_geometry)
  const legacyProblem = chatMessages.length === 0 && figureMessages.length > 0 ? info?.problem : undefined
  const busy = Boolean(turn)

  const sendMessage = (text: string, file: File | null) => send({ text, image: file, conversationId })
  const act = (action: TutorAction) => void send({ text: '', conversationId, action })
  const refine = async (text: string) => {
    if (!conversationId) return false
    setMobileView('drawing')
    return drawFigure(conversationId, text)
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {hasFigurePanel && (
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
      )}
      {/* minmax(0,…) columns: a long display formula scrolls inside its message instead of
          widening the whole page (which pushed the send button off narrow screens). */}
      <div className={cn('grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)]',
                         hasFigurePanel && 'lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]')}>
        <section
          className={cn('relative flex min-h-0 min-w-0 flex-col', hasFigurePanel && 'lg:border-r',
                        hasFigurePanel && mobileView !== 'chat' && 'hidden lg:flex')}
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
              messages={chatMessages}
              pending={turn}
              legacyProblem={legacyProblem}
              loading={Boolean(conversationId) && conversation.isPending}
              onExample={(example) => void sendMessage(example.problem, null)}
            />
          </div>
          <Composer
            image={image}
            onImage={setImage}
            onSend={sendMessage}
            busy={busy}
            header={info && (chatMessages.length > 0 || legacyProblem)
              ? <TutorBar conversation={info} busy={busy} onAction={act} />
              : undefined}
            actions={info && !hasFigurePanel && (
              <Button variant="ghost" size="sm" className="text-muted-foreground" disabled={Boolean(figureTurn)}
                      onClick={() => void refine('')}>
                <PenTool /> {figureTurn ? 'Đang vẽ…' : 'Vẽ hình'}
              </Button>
            )}
            placeholder={info ? 'Trả lời câu hỏi của trợ giảng, hoặc hỏi thêm…' : 'Nhập đề bài hoặc đính kèm ảnh đề…'}
          />
          {dragging && (
            <div className="pointer-events-none absolute inset-3 flex items-center justify-center rounded-2xl border-2 border-dashed border-primary bg-primary/5 text-sm font-medium text-primary">
              Thả ảnh đề bài vào đây
            </div>
          )}
        </section>
        {hasFigurePanel && (
          <section className={cn('min-h-0 min-w-0 overflow-y-auto bg-muted/30', mobileView !== 'drawing' && 'hidden lg:block')}>
            <DrawingPanel
              figureMessages={figureMessages}
              drawings={drawings}
              shown={shown}
              onShow={showDrawing}
              busyLabel={figureTurn?.label ?? null}
              onRefine={refine}
            />
          </section>
        )}
      </div>
    </div>
  )
}

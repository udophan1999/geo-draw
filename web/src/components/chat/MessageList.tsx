import { Eye, Lightbulb, Loader2 } from 'lucide-react'
import { useEffect, useRef } from 'react'
import Markdown from 'react-markdown'

import { Logo } from '@/components/Logo'
import { Badge } from '@/components/ui/badge'
import type { Example, Message } from '@/lib/api'
import type { PendingTurn } from '@/lib/chat'
import { useExamples } from '@/lib/queries'
import { cn } from '@/lib/utils'

type Props = {
  messages: Message[]
  pending?: PendingTurn
  shownDrawingId: string | null
  onShowDrawing: (messageId: string) => void
  onExample: (example: Example) => void
  loading: boolean
}

export function MessageList({ messages, pending, shownDrawingId, onShowDrawing, onExample, loading }: Props) {
  const bottom = useRef<HTMLDivElement>(null)
  const count = messages.length
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [count, pending?.label, pending?.userSaved])

  if (!loading && count === 0 && !pending) return <Welcome onExample={onExample} />

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-5 px-4 py-6">
      {messages.map((message) =>
        message.role === 'user' ? (
          <UserBubble key={message.id} text={message.text} image={message.image_url} />
        ) : (
          <AssistantRow key={message.id}>
            <div className="prose-chat text-sm leading-relaxed">
              <Markdown>{message.text}</Markdown>
            </div>
            {message.has_drawing && message.image_url && (
              <button
                type="button"
                onClick={() => onShowDrawing(message.id)}
                className={cn(
                  'group relative mt-2 block w-56 overflow-hidden rounded-xl border bg-white transition hover:shadow-md',
                  shownDrawingId === message.id && 'ring-2 ring-primary',
                )}
              >
                <img src={message.image_url} alt="Hình vẽ" className="aspect-video w-full object-contain" />
                <span className="absolute right-2 bottom-2">
                  {shownDrawingId === message.id ? (
                    <Badge>Đang xem</Badge>
                  ) : (
                    <Badge variant="secondary" className="opacity-0 transition group-hover:opacity-100">
                      <Eye /> Xem hình này
                    </Badge>
                  )}
                </span>
              </button>
            )}
          </AssistantRow>
        ),
      )}
      {pending && !pending.userSaved && <UserBubble text={pending.text} image={pending.imagePreview} />}
      {pending && (
        <AssistantRow>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            {pending.label}
          </div>
        </AssistantRow>
      )}
      <div ref={bottom} />
    </div>
  )
}

function UserBubble({ text, image }: { text: string; image: string | null }) {
  return (
    <div className="flex justify-end">
      <div className="grid max-w-[85%] gap-2 rounded-2xl rounded-br-md bg-primary/10 px-4 py-2.5">
        {image && <img src={image} alt="Ảnh đề bài" className="max-h-56 rounded-lg border bg-white object-contain" />}
        {text && <p className="text-sm leading-relaxed whitespace-pre-wrap">{text}</p>}
      </div>
    </div>
  )
}

function AssistantRow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <Logo className="size-8 rounded-lg" />
      <div className="min-w-0 flex-1 pt-1">{children}</div>
    </div>
  )
}

function Welcome({ onExample }: { onExample: (example: Example) => void }) {
  const examples = useExamples()
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col justify-center px-4 py-10">
      <h2 className="text-2xl font-semibold tracking-tight">Chào bạn! 👋</h2>
      <p className="mt-2 text-muted-foreground">
        Gửi một đề hình học phẳng — gõ trực tiếp, dán ảnh (Ctrl+V) hoặc bấm 📎 để đính kèm ảnh chụp đề.
        Sau khi có hình, nhắn thêm yêu cầu như <em>“vẽ thêm đường tròn ngoại tiếp”</em> để chỉnh tiếp.
      </p>
      <p className="mt-6 mb-2 text-sm font-medium text-muted-foreground">Thử một đề mẫu</p>
      <div className="grid gap-2 sm:grid-cols-2">
        {examples.data?.map((example) => (
          <button
            key={example.name}
            type="button"
            onClick={() => onExample(example)}
            className="rounded-xl border bg-background p-3 text-left transition hover:border-primary/50 hover:bg-primary/5"
          >
            <span className="flex items-center gap-1.5 text-sm font-medium">
              <Lightbulb className="size-4 text-amber-500" /> {example.name}
            </span>
            <span className="mt-1 line-clamp-2 text-xs text-muted-foreground">{example.problem}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

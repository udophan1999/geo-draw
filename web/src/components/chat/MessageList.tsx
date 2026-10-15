import { EditorContent } from '@tiptap/react'
import { Check, Copy, Loader2, Pencil, Sigma } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'

import { useMathEditor } from '@/components/chat/useMathEditor'
import { Logo } from '@/components/Logo'
import { MathMarkdown } from '@/components/MathMarkdown'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { copyText } from '@/lib/clipboard'
import { toMessageText } from '@/lib/messageText'
import type { Example, Message } from '@/lib/api'
import type { PendingTurn } from '@/lib/chat'
import { useExamples } from '@/lib/queries'
import { cn } from '@/lib/utils'

type Props = {
  /** Chat-channel messages only (the drawings live in the drawing panel). */
  messages: Message[]
  pending?: PendingTurn
  /** Set for conversations made before the tutor existed (drawings only). */
  legacyProblem?: string
  onExample: (example: Example) => void
  loading: boolean
  /** Edit the student's last message (the tutor answers it again); absent while busy. */
  onEdit?: (messageId: string, text: string) => Promise<boolean>
}

// Keep the student's line breaks (Markdown would join single newlines).
const withBreaks = (text: string) => text.replace(/\n/g, '  \n')

export function MessageList({ messages, pending, legacyProblem, onExample, loading, onEdit }: Props) {
  const bottom = useRef<HTMLDivElement>(null)
  const count = messages.length
  // Only the student's last message can be edited.
  const editableId = onEdit ? messages.findLast((m) => m.role === 'user')?.id : undefined
  const [editingId, setEditingId] = useState<string | null>(null)
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [count, pending?.label, pending?.userSaved, pending?.reply])

  if (!loading && count === 0 && !pending && !legacyProblem) return <Welcome onExample={onExample} />

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5 px-4 py-6">
      {legacyProblem && count === 0 && !pending && (
        <div className="rounded-xl border bg-muted/40 p-4 text-sm">
          <p className="font-medium">Đề bài</p>
          <MathMarkdown className="mt-1 text-muted-foreground">{withBreaks(legacyProblem)}</MathMarkdown>
          <p className="mt-3 text-muted-foreground">
            Cuộc trò chuyện này được tạo trước khi có trợ giảng. Nhắn một câu bất kỳ (ví dụ “em nên bắt đầu từ đâu?”)
            để được gợi ý giải.
          </p>
        </div>
      )}
      {messages.map((message) =>
        message.role === 'user' ? (
          editingId === message.id && onEdit ? (
            <EditBubble
              key={message.id}
              text={message.text}
              image={message.image_url}
              onCancel={() => setEditingId(null)}
              onSave={async (text) => {
                const ok = await onEdit(message.id, text)
                if (ok) setEditingId(null)
              }}
            />
          ) : (
            <UserBubble
              key={message.id}
              text={message.text}
              image={message.image_url}
              onEdit={message.id === editableId ? () => setEditingId(message.id) : undefined}
            />
          )
        ) : (
          <AssistantRow key={message.id}>
            <MathMarkdown
              className={cn(
                'text-sm leading-relaxed',
                message.meta.error && 'rounded-lg bg-destructive/10 px-3 py-2 text-destructive',
              )}
            >
              {message.text}
            </MathMarkdown>
            {message.meta.mode === 'solution' && !message.meta.error && (
              <Badge variant="secondary" className="mt-2">Lời giải chi tiết</Badge>
            )}
          </AssistantRow>
        ),
      )}
      {pending && !pending.userSaved && <UserBubble text={pending.text} image={pending.imagePreview} />}
      {pending && (pending.reply || pending.label) && (
        <AssistantRow>
          {pending.reply ? (
            <MathMarkdown className="text-sm leading-relaxed">{pending.reply + ' ▍'}</MathMarkdown>
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              {pending.label}
            </div>
          )}
        </AssistantRow>
      )}
      <div ref={bottom} />
    </div>
  )
}

// Message tools: shown on hover with a mouse, always on touch screens (no hover there).
const TOOL = 'text-muted-foreground opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100 [@media(hover:none)]:opacity-100'

function UserBubble({ text, image, onEdit }: { text: string; image: string | null; onEdit?: () => void }) {
  return (
    <div className="group flex items-start justify-end gap-1">
      <div className="mt-1 flex">
        {text && <CopyButton text={text} />}
        {onEdit && (
          <Button variant="ghost" size="icon-sm" aria-label="Sửa tin nhắn" title="Sửa tin nhắn" onClick={onEdit} className={TOOL}>
            <Pencil />
          </Button>
        )}
      </div>
      <div className="grid max-w-[85%] gap-2 rounded-2xl rounded-br-md bg-primary/10 px-4 py-2.5">
        {image && <img src={image} alt="Ảnh đề bài" className="max-h-56 rounded-lg border bg-white object-contain" />}
        {text && <MathMarkdown className="text-sm leading-relaxed">{withBreaks(text)}</MathMarkdown>}
      </div>
    </div>
  )
}

/** Copies the message as typed: text with $latex$ formulas, which the message box (and most
 *  math-aware apps) turn back into formulas when it is pasted. */
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    if (!copied) return
    const timer = window.setTimeout(() => setCopied(false), 1500)
    return () => window.clearTimeout(timer)
  }, [copied])
  const label = copied ? 'Đã sao chép' : 'Sao chép tin nhắn'
  return (
    <Button variant="ghost" size="icon-sm" aria-label={label} title={label}
            className={copied ? 'text-emerald-600 dark:text-emerald-400' : TOOL}
            onClick={async () => {
              if (await copyText(text)) setCopied(true)
              else toast.error('Trình duyệt không cho sao chép. Hãy bôi đen rồi chép bằng tay.')
            }}>
      {copied ? <Check /> : <Copy />}
    </Button>
  )
}

/** The last message being edited in place: same editor as the message box. */
function EditBubble({ text, image, onCancel, onSave }: {
  text: string; image: string | null; onCancel: () => void; onSave: (text: string) => Promise<void>
}) {
  const [saving, setSaving] = useState(false)
  const save = async () => {
    if (!editor || editor.isEmpty || saving) return
    setSaving(true)
    await onSave(toMessageText(editor.state.doc).trim())
    setSaving(false)
  }
  const { editor, empty, openFormula, formulaDialog } = useMathEditor({
    label: 'Sửa tin nhắn',
    placeholder: 'Nhập lại tin nhắn…',
    className: 'block max-h-[240px] min-h-[2.25rem] w-full overflow-y-auto px-3 py-2 text-sm outline-none',
    initialText: text,
    onSubmit: () => void save(),
    onEscape: onCancel,
  })
  useEffect(() => {
    editor?.commands.focus('end')
  }, [editor])

  return (
    <div className="flex justify-end">
      <div role="group" aria-label="Đang sửa tin nhắn"
           className="grid w-full max-w-[85%] gap-2 rounded-2xl border border-primary/40 bg-background p-2 shadow-sm ring-3 ring-primary/10">
        {image && <img src={image} alt="Ảnh đề bài" className="max-h-40 rounded-lg border bg-white object-contain" />}
        <EditorContent editor={editor} />
        <div className="flex items-center gap-1.5">
          <Button variant="ghost" size="icon-sm" aria-label="Nhập công thức" onClick={openFormula}>
            <Sigma />
          </Button>
          <span className="mr-auto hidden text-[11px] text-muted-foreground sm:inline">MathMate sẽ trả lời lại tin nhắn này</span>
          <span className="mr-auto sm:hidden" />
          <Button variant="ghost" size="sm" onClick={onCancel} disabled={saving}>Hủy</Button>
          <Button size="sm" onClick={() => void save()} disabled={empty || saving}>
            {saving && <Loader2 className="animate-spin" />}
            Gửi
          </Button>
        </div>
        {formulaDialog}
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
    <div className="mx-auto flex w-full max-w-3xl flex-col justify-center px-4 py-10">
      <h2 className="text-2xl font-semibold tracking-tight">Chào bạn! 👋</h2>
      <p className="mt-2 text-muted-foreground">
        Gửi một bài toán bất kỳ — đại số, phương trình, hàm số hay hình học. Mình sẽ gợi ý từng bước để bạn tự giải
        (hoặc xem lời giải chi tiết khi cần). Bài hình học được vẽ hình tự động ở khung bên cạnh.
      </p>
      <p className="mt-1 text-sm text-muted-foreground">Gõ đề, dán ảnh (Ctrl+V) hoặc bấm nút đính kèm để gửi ảnh chụp đề.</p>
      <p className="mt-6 mb-2 text-sm font-medium text-muted-foreground">Thử một đề mẫu</p>
      <div className="grid gap-2 sm:grid-cols-2">
        {examples.data?.map((example) => (
          <button
            key={example.name}
            type="button"
            onClick={() => onExample(example)}
            className="rounded-xl border bg-background p-3 text-left transition hover:border-primary/50 hover:bg-primary/5"
          >
            <span className="flex items-center gap-2 text-sm font-medium">
              <Badge variant="secondary" className="font-normal">{example.topic}</Badge>
              {example.name}
            </span>
            <span className="mt-1.5 line-clamp-2 text-xs text-muted-foreground">
              {example.problem.replace(/\$/g, '')}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

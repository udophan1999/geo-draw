import { EditorContent } from '@tiptap/react'
import { ArrowUp, ImagePlus, Loader2, Omega, Sigma, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { SymbolBar } from '@/components/chat/MathInput'
import { useMathEditor } from '@/components/chat/useMathEditor'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { IMAGE_TYPES, acceptImage } from '@/lib/images'
import { toMessageText } from '@/lib/messageText'

type Props = {
  image: File | null
  onImage: (file: File | null) => void
  onSend: (text: string, image: File | null) => Promise<boolean>
  busy: boolean
  placeholder: string
  /** Shown as a strip on top of the box (the tutor controls). */
  header?: React.ReactNode
  /** Extra buttons next to "Gửi" (e.g. "Vẽ hình"). */
  actions?: React.ReactNode
}

export function Composer({ image, onImage, onSend, busy, placeholder, header, actions }: Props) {
  const [submitting, setSubmitting] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const [showSymbols, setShowSymbols] = useState(false)
  const { editor, empty, insertText, openFormula, formulaDialog } = useMathEditor({
    label: 'Tin nhắn',
    placeholder,
    className: 'block max-h-[200px] min-h-[2.25rem] w-full overflow-y-auto px-4 pt-3 pb-1 text-sm outline-none',
    onSubmit: () => void submit(),
    onImage,
  })

  const preview = useMemo(() => (image ? URL.createObjectURL(image) : null), [image])
  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview)
  }, [preview])

  const disabled = busy || submitting
  const canSend = !disabled && (!empty || image !== null)

  const submit = async () => {
    if (!canSend || !editor) return
    setSubmitting(true)
    const ok = await onSend(toMessageText(editor.state.doc).trim(), image)
    setSubmitting(false)
    if (ok) {
      editor.commands.clearContent(true)
      onImage(null)
    }
    editor.commands.focus()
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-3">
      <div className="overflow-hidden rounded-2xl border bg-background shadow-sm transition focus-within:border-primary/50 focus-within:ring-3 focus-within:ring-primary/10">
        {header}
        {preview && (
          <div className="px-3 pt-3">
            <div className="relative inline-block">
              <img src={preview} alt="Ảnh đính kèm" className="h-20 rounded-lg border bg-white object-contain" />
              <button
                type="button"
                aria-label="Bỏ ảnh"
                onClick={() => onImage(null)}
                className="absolute -top-2 -right-2 flex size-5 items-center justify-center rounded-full bg-foreground text-background"
              >
                <X className="size-3" />
              </button>
            </div>
          </div>
        )}
        {showSymbols && <SymbolBar onInsert={insertText} />}
        <EditorContent editor={editor} />
        <div className="flex items-center justify-between px-2 pb-2">
          <div className="flex items-center gap-0.5">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" aria-label="Đính kèm ảnh đề" onClick={() => fileInput.current?.click()}>
                  <ImagePlus />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Đính kèm ảnh đề (hoặc dán Ctrl+V, kéo thả)</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant={showSymbols ? 'secondary' : 'ghost'} size="icon" aria-label="Ký hiệu toán"
                        aria-pressed={showSymbols} onClick={() => setShowSymbols((on) => !on)}>
                  <Omega />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Ký hiệu toán: ², √, π, ≤, ⊥, ∠…</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" aria-label="Nhập công thức" onClick={openFormula}>
                  <Sigma />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Nhập công thức (phân số, căn, số mũ…), hoặc gõ $x^2$</TooltipContent>
            </Tooltip>
          </div>
          <input
            ref={fileInput}
            type="file"
            accept={IMAGE_TYPES.join(',')}
            className="hidden"
            onChange={(event) => {
              onImage(acceptImage(event.target.files?.[0]))
              event.target.value = ''
            }}
          />
          <div className="flex items-center gap-1.5">
            {actions}
            <Button size="icon" className="rounded-full" aria-label="Gửi" disabled={!canSend} onClick={() => void submit()}>
              {disabled ? <Loader2 className="animate-spin" /> : <ArrowUp />}
            </Button>
          </div>
        </div>
      </div>
      <p className="mt-1.5 hidden text-center text-[11px] text-muted-foreground/70 sm:block">
        Enter để gửi · Shift+Enter để xuống dòng · gõ $x^2$ để viết công thức
      </p>
      {formulaDialog}
    </div>
  )
}

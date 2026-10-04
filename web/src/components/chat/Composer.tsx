import { ArrowUp, ImagePlus, Loader2, Omega, Sigma, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { FormulaDialog, SymbolBar } from '@/components/chat/MathInput'
import { MathMarkdown } from '@/components/MathMarkdown'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { IMAGE_TYPES, acceptImage } from '@/lib/images'
import { latexToPlain } from '@/lib/plainMath'

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
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const textarea = useRef<HTMLTextAreaElement>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const [showSymbols, setShowSymbols] = useState(false)
  const [formulaOpen, setFormulaOpen] = useState(false)

  /** Put ``snippet`` at the caret (replacing any selection) and keep typing after it. */
  const insert = (snippet: string, spaced = false) => {
    const el = textarea.current
    const start = el?.selectionStart ?? text.length
    const end = el?.selectionEnd ?? text.length
    if (spaced) {
      // A formula is a word of its own: keep it apart from the text around it.
      if (start > 0 && !/\s/.test(text[start - 1])) snippet = ' ' + snippet
      if (!/^\s/.test(text.slice(end))) snippet += ' '
    }
    setText(text.slice(0, start) + snippet + text.slice(end))
    requestAnimationFrame(() => {
      el?.focus()
      el?.setSelectionRange(start + snippet.length, start + snippet.length)
    })
  }
  const preview = useMemo(() => (image ? URL.createObjectURL(image) : null), [image])
  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview)
  }, [preview])

  // Grow with the text, up to a limit.
  useEffect(() => {
    const el = textarea.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [text])

  const disabled = busy || submitting
  const canSend = !disabled && (text.trim().length > 0 || image !== null)

  const submit = async () => {
    if (!canSend) return
    setSubmitting(true)
    const ok = await onSend(text.trim(), image)
    setSubmitting(false)
    if (ok) {
      setText('')
      onImage(null)
    }
    textarea.current?.focus()
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
        {showSymbols && <SymbolBar onInsert={insert} />}
        {/\$|\\\(|\\\[/.test(text) && (
          // The textarea shows LaTeX source; show how the message will look.
          <div className="mx-3 mt-2 rounded-lg bg-muted/60 px-3 py-1.5" aria-label="Xem trước">
            <span className="text-[11px] font-medium text-muted-foreground">Xem trước</span>
            <MathMarkdown className="text-sm leading-relaxed">{text.replace(/\n/g, '  \n')}</MathMarkdown>
          </div>
        )}
        <textarea
          ref={textarea}
          rows={1}
          value={text}
          placeholder={placeholder}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            // Vietnamese IMEs compose with Enter too; only send outside composition.
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault()
              void submit()
            }
          }}
          onPaste={(event) => {
            const file = Array.from(event.clipboardData.files).find((f) => f.type.startsWith('image/'))
            if (file) {
              event.preventDefault()
              onImage(acceptImage(file))
            }
          }}
          className="block max-h-[200px] w-full resize-none bg-transparent px-4 pt-3 pb-1 text-sm outline-none placeholder:text-muted-foreground"
        />
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
                <Button variant="ghost" size="icon" aria-label="Nhập công thức" onClick={() => setFormulaOpen(true)}>
                  <Sigma />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Nhập công thức (phân số, căn, số mũ…)</TooltipContent>
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
        Enter để gửi · Shift+Enter để xuống dòng
      </p>
      <FormulaDialog open={formulaOpen} onOpenChange={setFormulaOpen} onInsert={(latex) => insert(latexToPlain(latex) ?? `$${latex}$`, true)} />
    </div>
  )
}

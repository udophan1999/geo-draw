import { ArrowUp, ImagePlus, Loader2, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { IMAGE_TYPES, acceptImage } from '@/lib/images'

type Props = {
  image: File | null
  onImage: (file: File | null) => void
  onSend: (text: string, image: File | null) => Promise<boolean>
  busy: boolean
  placeholder: string
}

export function Composer({ image, onImage, onSend, busy, placeholder }: Props) {
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const textarea = useRef<HTMLTextAreaElement>(null)
  const fileInput = useRef<HTMLInputElement>(null)
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
    <div className="mx-auto w-full max-w-2xl px-4 pb-4">
      <div className="rounded-2xl border bg-background shadow-sm transition focus-within:border-primary/50 focus-within:ring-3 focus-within:ring-primary/10">
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
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Đính kèm ảnh đề" onClick={() => fileInput.current?.click()}>
                <ImagePlus />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Đính kèm ảnh đề (hoặc dán Ctrl+V, kéo thả)</TooltipContent>
          </Tooltip>
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
          <Button size="icon" className="rounded-full" aria-label="Gửi" disabled={!canSend} onClick={() => void submit()}>
            {disabled ? <Loader2 className="animate-spin" /> : <ArrowUp />}
          </Button>
        </div>
      </div>
      <p className="mt-2 text-center text-xs text-muted-foreground">
        Enter để gửi · Shift+Enter để xuống dòng
      </p>
    </div>
  )
}

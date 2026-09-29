// Typing math without knowing LaTeX: a bar of common symbols (inserted as Unicode) and a
// visual formula editor (MathLive) that inserts $LaTeX$, rendered by KaTeX in the chat.
import { Loader2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

const SYMBOLS: [string, string][] = [
  ['²', 'Bình phương'], ['³', 'Lập phương'], ['√', 'Căn bậc hai'], ['∛', 'Căn bậc ba'],
  ['π', 'Pi'], ['±', 'Cộng trừ'], ['×', 'Nhân'], ['÷', 'Chia'], ['≠', 'Khác'],
  ['≤', 'Nhỏ hơn hoặc bằng'], ['≥', 'Lớn hơn hoặc bằng'], ['≈', 'Xấp xỉ'], ['°', 'Độ'],
  ['∠', 'Góc'], ['△', 'Tam giác'], ['⊥', 'Vuông góc'], ['∥', 'Song song'], ['∽', 'Đồng dạng'],
  ['∈', 'Thuộc'], ['∉', 'Không thuộc'], ['⊂', 'Tập con'], ['∪', 'Hợp'], ['∩', 'Giao'],
  ['∅', 'Tập rỗng'], ['⇒', 'Suy ra'], ['⇔', 'Tương đương'], ['∞', 'Vô cực'],
  ['α', 'Alpha'], ['β', 'Beta'], ['Δ', 'Delta'],
]

export function SymbolBar({ onInsert }: { onInsert: (text: string) => void }) {
  return (
    <div className="flex flex-wrap gap-1 px-3 pt-2" role="toolbar" aria-label="Ký hiệu toán">
      {SYMBOLS.map(([symbol, name]) => (
        <Tooltip key={symbol}>
          <TooltipTrigger asChild>
            <button
              type="button"
              aria-label={name}
              // Keep the caret in the textarea while clicking.
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => onInsert(symbol)}
              className="flex h-7 min-w-7 items-center justify-center rounded-md border bg-background px-1.5 text-sm transition hover:border-primary/50 hover:bg-primary/5"
            >
              {symbol}
            </button>
          </TooltipTrigger>
          <TooltipContent>{name}</TooltipContent>
        </Tooltip>
      ))}
    </div>
  )
}

type MathField = HTMLElement & { getValue: (format?: string) => string; focus: () => void }

/** Visual formula editor; ``onInsert`` receives ``$…$`` ready to put in the message. */
export function FormulaDialog({ open, onOpenChange, onInsert }: {
  open: boolean; onOpenChange: (open: boolean) => void; onInsert: (text: string) => void
}) {
  const host = useRef<HTMLDivElement>(null)
  const field = useRef<MathField | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    void (async () => {
      // Loaded on demand: MathLive is large and most messages need no formula editor.
      const { MathfieldElement } = await import('mathlive')
      if (cancelled || !host.current) return
      // The chat page already loads KaTeX's fonts, which MathLive uses; no CDN, no sounds.
      MathfieldElement.fontsDirectory = null
      MathfieldElement.soundsDirectory = null
      const element = new MathfieldElement() as unknown as MathField
      element.setAttribute('aria-label', 'Công thức')
      element.style.cssText = 'display:block;width:100%;font-size:1.4rem;padding:0.5rem 0.75rem;' +
        'border:1px solid var(--border);border-radius:0.6rem;'
      host.current.replaceChildren(element)
      field.current = element
      setReady(true)
      requestAnimationFrame(() => element.focus())
    })()
    return () => {
      cancelled = true
      setReady(false)
      field.current = null
    }
  }, [open])

  const insert = () => {
    const latex = field.current?.getValue('latex').trim()
    if (latex) onInsert(`$${latex}$`)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Nhập công thức</DialogTitle>
          <DialogDescription>
            Gõ như viết trên giấy: <kbd>/</kbd> để tạo phân số, <kbd>^</kbd> cho số mũ, gõ <kbd>sqrt</kbd> cho căn.
            Trên điện thoại, dùng bàn phím toán hiện ra bên dưới.
          </DialogDescription>
        </DialogHeader>
        <div ref={host} className="min-h-14" onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            insert()
          }
        }} />
        {!ready && <Loader2 className="mx-auto animate-spin text-muted-foreground" />}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Hủy</Button>
          <Button onClick={insert} disabled={!ready}>Chèn vào tin nhắn</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

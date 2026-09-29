// Typing math without knowing LaTeX: a bar of common symbols (inserted as Unicode) and a
// visual formula editor (MathLive). The composer inserts its formula as plain Unicode when
// possible (lib/plainMath.ts), else as $LaTeX$ with a rendered preview.
import katex from 'katex'
import { Loader2 } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { FORMULA_GROUPS } from '@/components/chat/formulaTemplates'
import { cn } from '@/lib/utils'

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

type InsertOptions = { focus?: boolean; selectionMode?: 'placeholder' | 'after' }
type MathField = HTMLElement & {
  getValue: (format?: string) => string
  insert: (latex: string, options?: InsertOptions) => boolean
  focus: () => void
}

/** A template drawn as it will look, with empty slots shown as boxes. */
function TemplatePreview({ latex, large = false }: { latex: string; large?: boolean }) {
  // Tiles use \displaystyle: full-size fractions and roots, as in Word's gallery.
  const html = useMemo(
    () => katex.renderToString((large ? '\\displaystyle ' : '') + latex.replace(/#[?@]/g, '\\square'),
                               { throwOnError: false, strict: false }),
    [latex, large],
  )
  return <span className="pointer-events-none whitespace-nowrap" dangerouslySetInnerHTML={{ __html: html }} />
}

/** Visual formula editor with a Word-like gallery; ``onInsert`` receives the formula's LaTeX. */
export function FormulaDialog({ open, onOpenChange, onInsert }: {
  open: boolean; onOpenChange: (open: boolean) => void; onInsert: (latex: string) => void
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
      element.style.cssText = 'display:block;width:100%;min-height:4.5rem;font-size:1.75rem;' +
        'padding:0.75rem 1rem;border:1px solid var(--border);border-radius:0.75rem;'
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

  const add = (latex: string) => {
    field.current?.insert(latex, { focus: true, selectionMode: 'placeholder' })
  }
  const insert = () => {
    const latex = field.current?.getValue('latex').trim()
    if (latex) onInsert(latex)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92svh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Nhập công thức</DialogTitle>
          <DialogDescription>
            Chọn mẫu bên dưới rồi điền vào các ô trống, hoặc gõ trực tiếp: <kbd>/</kbd> tạo phân số,
            <kbd>^</kbd> số mũ, <kbd>Tab</kbd> chuyển sang ô trống kế tiếp.
          </DialogDescription>
        </DialogHeader>
        <div
          ref={host}
          className="min-h-[4.5rem] min-w-0"
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              insert()
            }
          }}
        />
        {!ready && <Loader2 className="mx-auto animate-spin text-muted-foreground" />}
        {/* min-w-0: inside the dialog's grid, the wide tab list must scroll, not stretch it. */}
        <Tabs defaultValue={FORMULA_GROUPS[0].id} className="w-full min-w-0">
          {/* Scrolls sideways on narrow screens instead of wrapping over the gallery. */}
          <TabsList className="w-full max-w-full min-w-0 justify-start overflow-x-auto">
            {FORMULA_GROUPS.map((group) => (
              <TabsTrigger key={group.id} value={group.id} className="flex-none">{group.name}</TabsTrigger>
            ))}
          </TabsList>
          {FORMULA_GROUPS.map((group) => (
            <TabsContent key={group.id} value={group.id} className="min-h-72 pt-2">
              <div className={group.wide
                ? 'grid gap-2 sm:grid-cols-2'
                : 'grid grid-cols-3 gap-2 sm:grid-cols-6'}>
                {group.items.map((item) => (
                  <Tooltip key={item.label}>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        aria-label={item.label}
                        disabled={!ready}
                        // Keep the focus (and caret) inside the formula while clicking.
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => add(item.latex)}
                        className={cn(
                          'flex items-center rounded-lg border bg-background px-2 transition',
                          'hover:border-primary/50 hover:bg-primary/5 disabled:opacity-50',
                          group.wide
                            ? 'min-h-14 flex-col items-start gap-1 py-2 text-left text-base sm:flex-row sm:items-center sm:justify-between sm:gap-3'
                            : 'min-h-20 flex-col justify-center gap-1 py-2 text-lg',
                        )}
                      >
                        {group.wide && <span className="text-xs text-muted-foreground">{item.label}</span>}
                        <TemplatePreview latex={item.latex} large={!group.wide} />
                        {!group.wide && (
                          <span className="line-clamp-1 text-[11px] leading-tight text-muted-foreground">
                            {item.label}
                          </span>
                        )}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>{item.label}</TooltipContent>
                  </Tooltip>
                ))}
              </div>
            </TabsContent>
          ))}
        </Tabs>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Hủy</Button>
          <Button onClick={insert} disabled={!ready}>Chèn vào tin nhắn</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

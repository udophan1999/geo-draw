import { useQuery } from '@tanstack/react-query'
import { ChevronDown, Loader2, RotateCcw, Send, TriangleAlert } from 'lucide-react'
import { useState } from 'react'

import { Logo } from '@/components/Logo'
import { ManualEditor } from '@/components/drawing/ManualEditor'
import { ZoomImage } from '@/components/drawing/ZoomImage'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { api, type Message } from '@/lib/api'
import { keys } from '@/lib/queries'
import { cn } from '@/lib/utils'

type Props = {
  /** Figure-channel messages: drawing requests (user) and drawings or failures (assistant). */
  figureMessages: Message[]
  drawings: Message[]
  shown: Message | null
  onShow: (messageId: string) => void
  /** Progress label while a drawing runs, else null. */
  busyLabel: string | null
  onRefine: (text: string) => Promise<boolean>
}

export function DrawingPanel({ figureMessages, drawings, shown, onShow, busyLabel, onRefine }: Props) {
  const busy = busyLabel !== null
  const requests = figureMessages.filter((m) => m.role === 'user')
  const last = figureMessages.at(-1)
  const failure = !busy && last?.role === 'assistant' && !last.has_drawing ? last : null

  const refineBox = <RefineBox busy={busy} hasDrawing={Boolean(shown)} requests={requests.map((r) => r.text)} onRefine={onRefine} />
  const status = busy ? (
    <p className="flex items-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" /> {busyLabel}
    </p>
  ) : failure ? (
    <div className="flex items-start gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
      <TriangleAlert className="mt-0.5 size-4 shrink-0" />
      <span className="flex-1">{failure.text}</span>
      <Button variant="ghost" size="xs" onClick={() => void onRefine('')}>
        <RotateCcw /> Vẽ lại
      </Button>
    </div>
  ) : null

  if (!shown) {
    return (
      <div className="mx-auto flex h-full min-h-80 w-full max-w-3xl flex-col gap-4 p-4 lg:p-6">
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center text-muted-foreground">
          {busy ? <Loader2 className="size-10 animate-spin opacity-50" /> : <Logo className="size-14 opacity-30 grayscale" />}
          <p className="text-sm">{busy ? busyLabel : 'Hình vẽ sẽ hiện ở đây'}</p>
          {!busy && !failure && (
            <Button variant="outline" size="sm" className="mt-2" onClick={() => void onRefine('')}>
              Vẽ hình
            </Button>
          )}
          {failure && <div className="mt-3 w-full max-w-md text-left">{status}</div>}
        </div>
      </div>
    )
  }
  const index = drawings.findIndex((d) => d.id === shown.id)
  const isLatest = index === drawings.length - 1

  return (
    <div className="mx-auto grid w-full max-w-3xl gap-4 p-4 lg:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="font-semibold">Hình vẽ</h2>
          <p className="text-xs text-muted-foreground">
            {isLatest ? 'Phiên bản mới nhất' : `Phiên bản ${index + 1}/${drawings.length}`}
          </p>
        </div>
        {drawings.length > 1 && (
          <div className="flex items-center gap-1" role="group" aria-label="Phiên bản hình">
            {drawings.map((drawing, i) => (
              <Button
                key={drawing.id}
                size="xs"
                variant={drawing.id === shown.id ? 'default' : 'outline'}
                className={cn('min-w-7')}
                onClick={() => onShow(drawing.id)}
              >
                {i + 1}
              </Button>
            ))}
          </div>
        )}
      </div>

      {status}
      <ZoomImage src={shown.image_url!} alt="Hình vẽ" />
      {refineBox}
      {shown.video_url && (
        <video src={shown.video_url} controls className="w-full rounded-xl border bg-black" />
      )}

      <AdvancedOptions key={shown.id} drawing={shown} />
    </div>
  )
}

function TextFile({ queryKey, load }: { queryKey: readonly unknown[]; load: () => Promise<string> }) {
  const file = useQuery({ queryKey, queryFn: load, staleTime: Infinity })
  if (file.isPending) return <Loader2 className="mx-auto my-6 animate-spin text-muted-foreground" />
  return (
    <pre className="max-h-96 overflow-auto rounded-xl border bg-muted/50 p-4 font-mono text-xs leading-relaxed">
      {file.data ?? file.error?.message}
    </pre>
  )
}

function RefineBox({ busy, hasDrawing, requests, onRefine }: {
  busy: boolean; hasDrawing: boolean; requests: string[]; onRefine: (text: string) => Promise<boolean>
}) {
  const [text, setText] = useState('')
  if (!hasDrawing) return null
  const submit = async () => {
    if (!text.trim() || busy) return
    if (await onRefine(text.trim())) setText('')
  }
  return (
    <div className="grid gap-2">
      <form
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault()
          void submit()
        }}
      >
        <Input
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Yêu cầu chỉnh hình, vd: vẽ thêm đường cao AH"
          maxLength={2000}
          className="h-9 bg-background"
        />
        <Button type="submit" size="icon" className="size-9" aria-label="Gửi yêu cầu chỉnh hình" disabled={busy || !text.trim()}>
          {busy ? <Loader2 className="animate-spin" /> : <Send />}
        </Button>
      </form>
      {requests.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Đã yêu cầu: {requests.map((request, i) => <span key={i}>{i > 0 && ' · '}“{request}”</span>)}
        </p>
      )}
    </div>
  )
}

/** Manual editor, scene code and render log: tools most students never need, so folded away.
 *  The editor tab only appears for drawings it can edit (AI geometry with named points). */
function AdvancedOptions({ drawing }: { drawing: Message }) {
  const [open, setOpen] = useState(false)
  const editor = useQuery({
    queryKey: keys.editor(drawing.id), queryFn: () => api.editor(drawing.id), enabled: open,
  })
  const editable = (editor.data?.labels.length ?? 0) > 0

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <Button variant="ghost" size="sm" className="-ml-2 text-muted-foreground">
          Tùy chọn nâng cao
          <ChevronDown className={cn('transition-transform', open && 'rotate-180')} />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className="pt-2">
        {editor.isPending ? (
          <Loader2 className="mx-auto my-6 animate-spin text-muted-foreground" />
        ) : (
          <Tabs key={String(editable)} defaultValue={editable ? 'edit' : 'code'} className="w-full">
            <TabsList>
              {editable && <TabsTrigger value="edit">Chỉnh hình</TabsTrigger>}
              <TabsTrigger value="code">Mã Manim</TabsTrigger>
              {drawing.has_log && <TabsTrigger value="log">Log render</TabsTrigger>}
            </TabsList>
            {editable && (
              <TabsContent value="edit" className="pt-2">
                <ManualEditor message={drawing} />
              </TabsContent>
            )}
            <TabsContent value="code" className="pt-2">
              <TextFile queryKey={keys.scene(drawing.id)} load={() => api.scene(drawing.id)} />
            </TabsContent>
            {drawing.has_log && (
              <TabsContent value="log" className="pt-2">
                <TextFile queryKey={keys.log(drawing.id)} load={() => api.log(drawing.id)} />
              </TabsContent>
            )}
          </Tabs>
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}

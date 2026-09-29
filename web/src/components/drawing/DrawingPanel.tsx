import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'

import { ManualEditor } from '@/components/drawing/ManualEditor'
import { ZoomImage } from '@/components/drawing/ZoomImage'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { api, type Message } from '@/lib/api'
import { keys } from '@/lib/queries'
import { cn } from '@/lib/utils'

type Props = {
  drawings: Message[]
  shown: Message | null
  onShow: (messageId: string) => void
  busy: boolean
}

export function DrawingPanel({ drawings, shown, onShow, busy }: Props) {
  if (!shown) {
    return (
      <div className="flex h-full min-h-80 flex-col items-center justify-center gap-2 p-8 text-center text-muted-foreground">
        {busy ? <Loader2 className="size-10 animate-spin opacity-50" /> : <div className="text-5xl opacity-40">📐</div>}
        <p className="text-sm">{busy ? 'Đang vẽ hình…' : 'Hình vẽ sẽ hiện ở đây'}</p>
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
            {busy && ' · đang vẽ phiên bản mới…'}
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

      <ZoomImage src={shown.image_url!} alt="Hình vẽ" />
      {shown.video_url && (
        <video src={shown.video_url} controls className="w-full rounded-xl border bg-black" />
      )}

      <Tabs defaultValue="edit" className="w-full">
        <TabsList>
          <TabsTrigger value="edit">Chỉnh hình</TabsTrigger>
          <TabsTrigger value="code">Mã Manim</TabsTrigger>
          {shown.has_log && <TabsTrigger value="log">Log render</TabsTrigger>}
        </TabsList>
        <TabsContent value="edit" className="pt-2">
          <ManualEditor key={shown.id} message={shown} />
        </TabsContent>
        <TabsContent value="code" className="pt-2">
          <TextFile queryKey={keys.scene(shown.id)} load={() => api.scene(shown.id)} />
        </TabsContent>
        {shown.has_log && (
          <TabsContent value="log" className="pt-2">
            <TextFile queryKey={keys.log(shown.id)} load={() => api.log(shown.id)} />
          </TabsContent>
        )}
      </Tabs>
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

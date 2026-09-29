// "Chỉnh hình thủ công": re-render the same scene locally with label offsets and edits
// (no DeepSeek). Edits are only committed once the server re-render succeeds.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Eye, EyeOff, Loader2, RotateCcw, Undo2,
} from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { api, type EditorState, type LabelOffsets, type ManualEdits, type Message } from '@/lib/api'
import { keys, upsertMessage } from '@/lib/queries'

const STEPS = [
  { value: 0.08, label: 'Nhỏ' },
  { value: 0.12, label: 'Vừa' },
  { value: 0.18, label: 'Lớn' },
  { value: 0.25, label: 'Rất lớn' },
]
const TOOLS = {
  perpendicular: 'Hạ đường vuông góc',
  angle_bisector: 'Tia phân giác',
  perpendicular_bisector: 'Đường trung trực',
  median: 'Đường trung tuyến',
} as const
type Tool = keyof typeof TOOLS

const emptyEdits = (): ManualEdits => ({
  hidden_labels: [], hidden_points: [], hidden_segments: [], added_segments: [],
  segment_widths: {}, constructions: [],
})
const toggle = (list: string[], value: string) =>
  list.includes(value) ? list.filter((v) => v !== value) : [...list, value]
const segmentName = (a: string, b: string) => [a, b].sort().join('')

function suggestPointName(names: string[], edits: ManualEdits, preferred: string) {
  const used = new Set([...names, ...edits.constructions.map((c) => c.name ?? '')])
  return [...(preferred + 'MNPKQRESTUVXYZ')].find((c) => !used.has(c)) ?? ''
}

function Choice({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (value: string) => void
}) {
  return (
    <div className="grid gap-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
        <SelectContent>
          {options.map((option) => <SelectItem key={option} value={option}>{option}</SelectItem>)}
        </SelectContent>
      </Select>
    </div>
  )
}

export function ManualEditor({ message }: { message: Message }) {
  const state = useQuery({ queryKey: keys.editor(message.id), queryFn: () => api.editor(message.id) })
  if (state.isPending) return <Loader2 className="mx-auto my-6 animate-spin text-muted-foreground" />
  if (state.isError) return <p className="text-sm text-destructive">{state.error.message}</p>
  if (state.data.labels.length === 0) {
    return (
      <p className="rounded-xl border bg-muted/40 p-4 text-sm text-muted-foreground">
        Hình vẽ bằng Parser chưa hỗ trợ chỉnh thủ công — chỉ hình do DeepSeek AI tạo mới chỉnh được.
      </p>
    )
  }
  return <Editor message={message} state={state.data} />
}

function Editor({ message, state }: { message: Message; state: EditorState }) {
  const client = useQueryClient()
  const names = state.labels
  const edits = { ...emptyEdits(), ...state.manual_edits }
  const offsets = state.label_offsets

  const render = useMutation({
    mutationFn: (next: { offsets: LabelOffsets; edits: ManualEdits }) =>
      api.render(message.id, next.offsets, next.edits),
    onSuccess: (updated) => {
      upsertMessage(client, updated)
      client.invalidateQueries({ queryKey: keys.editor(message.id) })
    },
    onError: (error) => toast.error(error.message),
  })
  const apply = (next: { offsets?: LabelOffsets; edits?: ManualEdits }) =>
    render.mutate({ offsets: next.offsets ?? offsets, edits: next.edits ?? edits })
  const busy = render.isPending

  const [label, setLabel] = useState(names[0])
  const [step, setStep] = useState(0.12)
  const [point, setPoint] = useState(names[0])
  const [first, setFirst] = useState(names[0])
  const [second, setSecond] = useState(names[1] ?? names[0])
  const segment = segmentName(first, second)
  const [width, setWidth] = useState<number | null>(null)
  const segmentWidth = width ?? edits.segment_widths[segment] ?? 2

  const move = (dx: number, dy: number) => {
    const [x, y] = offsets[label] ?? [0, 0]
    apply({ offsets: { ...offsets, [label]: [x + dx, y + dy] } })
  }

  return (
    <div className="grid gap-3 rounded-xl border p-4">
      <p className="text-xs text-muted-foreground">
        Chỉ render lại trên máy chủ, không gọi DeepSeek. Tọa độ hình học gốc được giữ nguyên.
      </p>
      <Tabs defaultValue="labels">
        <TabsList className="w-full">
          <TabsTrigger value="labels">Tên điểm</TabsTrigger>
          <TabsTrigger value="points">Điểm</TabsTrigger>
          <TabsTrigger value="segments">Đoạn thẳng</TabsTrigger>
          <TabsTrigger value="construct">Dựng hình</TabsTrigger>
        </TabsList>

        <TabsContent value="labels" className="grid gap-4 pt-3">
          <div className="grid grid-cols-2 gap-3">
            <Choice label="Tên điểm cần chỉnh" value={label} options={names} onChange={setLabel} />
            <div className="grid gap-1.5">
              <Label className="text-xs text-muted-foreground">Bước dịch</Label>
              <Select value={String(step)} onValueChange={(v) => setStep(Number(v))}>
                <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {STEPS.map((s) => <SelectItem key={s.value} value={String(s.value)}>{s.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="grid grid-cols-3 gap-1">
              <span />
              <Button variant="outline" size="icon-sm" aria-label="Dịch lên" disabled={busy} onClick={() => move(0, step)}><ArrowUp /></Button>
              <span />
              <Button variant="outline" size="icon-sm" aria-label="Dịch trái" disabled={busy} onClick={() => move(-step, 0)}><ArrowLeft /></Button>
              <Button variant="outline" size="icon-sm" aria-label="Dịch xuống" disabled={busy} onClick={() => move(0, -step)}><ArrowDown /></Button>
              <Button variant="outline" size="icon-sm" aria-label="Dịch phải" disabled={busy} onClick={() => move(step, 0)}><ArrowRight /></Button>
            </div>
            <Button variant="outline" size="sm" disabled={busy}
                    onClick={() => apply({ edits: { ...edits, hidden_labels: toggle(edits.hidden_labels, label) } })}>
              {edits.hidden_labels.includes(label) ? <><Eye /> Hiện tên</> : <><EyeOff /> Ẩn tên</>}
            </Button>
            <Button variant="ghost" size="sm" disabled={busy}
                    onClick={() => {
                      const rest = { ...offsets }
                      delete rest[label]
                      apply({ offsets: rest, edits: { ...edits, hidden_labels: edits.hidden_labels.filter((l) => l !== label) } })
                    }}>
              <RotateCcw /> Đặt lại
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="points" className="grid gap-3 pt-3">
          <Choice label="Điểm cần ẩn/hiện" value={point} options={names} onChange={setPoint} />
          <div>
            <Button variant="outline" size="sm" disabled={busy}
                    onClick={() => apply({ edits: { ...edits, hidden_points: toggle(edits.hidden_points, point) } })}>
              {edits.hidden_points.includes(point) ? <><Eye /> Hiện chấm điểm</> : <><EyeOff /> Ẩn chấm điểm</>}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">Ẩn chấm điểm không xóa các đường đang đi qua điểm đó.</p>
        </TabsContent>

        <TabsContent value="segments" className="grid gap-4 pt-3">
          <div className="grid grid-cols-2 gap-3">
            <Choice label="Điểm đầu" value={first} options={names}
                    onChange={(v) => { setFirst(v); setWidth(null); if (v === second) setSecond(names.find((n) => n !== v) ?? v) }} />
            <Choice label="Điểm cuối" value={second} options={names.filter((n) => n !== first)}
                    onChange={(v) => { setSecond(v); setWidth(null) }} />
          </div>
          <div className="grid gap-2">
            <Label className="text-xs text-muted-foreground">Độ đậm nét đoạn {segment}: {segmentWidth.toFixed(1)}</Label>
            <Slider min={1} max={6} step={0.5} value={[segmentWidth]} onValueChange={([v]) => setWidth(v)} />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" disabled={busy}
                    onClick={() => apply({ edits: {
                      ...edits,
                      added_segments: edits.added_segments.includes(segment) ? edits.added_segments : [...edits.added_segments, segment],
                      hidden_segments: edits.hidden_segments.filter((s) => s !== segment),
                      segment_widths: { ...edits.segment_widths, [segment]: segmentWidth },
                    } })}>
              Thêm đoạn
            </Button>
            <Button variant="outline" size="sm" disabled={busy}
                    onClick={() => apply({ edits: { ...edits, hidden_segments: edits.hidden_segments.includes(segment) ? edits.hidden_segments : [...edits.hidden_segments, segment] } })}>
              Ẩn đoạn
            </Button>
            <Button variant="outline" size="sm" disabled={busy}
                    onClick={() => apply({ edits: { ...edits, hidden_segments: edits.hidden_segments.filter((s) => s !== segment) } })}>
              Hiện đoạn
            </Button>
            <Button variant="outline" size="sm" disabled={busy}
                    onClick={() => apply({ edits: { ...edits, segment_widths: { ...edits.segment_widths, [segment]: segmentWidth } } })}>
              Áp dụng nét
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="construct" className="pt-3">
          <Constructions names={names} segments={state.segments} edits={edits} busy={busy}
                         onChange={(constructions) => apply({ edits: { ...edits, constructions } })} />
        </TabsContent>
      </Tabs>

      <div className="flex items-center justify-between border-t pt-3">
        <span className="flex items-center gap-2 text-xs text-muted-foreground">
          {busy && <><Loader2 className="size-3.5 animate-spin" /> Đang cập nhật hình…</>}
        </span>
        <Button variant="ghost" size="sm" disabled={busy}
                onClick={() => apply({ offsets: {}, edits: emptyEdits() })}>
          <RotateCcw /> Khôi phục toàn bộ chỉnh sửa
        </Button>
      </div>
    </div>
  )
}

function Constructions({ names, segments, edits, busy, onChange }: {
  names: string[]; segments: string[]; edits: ManualEdits; busy: boolean
  onChange: (constructions: Record<string, string>[]) => void
}) {
  const [tool, setTool] = useState<Tool>('perpendicular')
  const [point, setPoint] = useState(names[0])
  const [side, setSide] = useState(segments[0] ?? '')
  const [side2, setSide2] = useState(segments[1] ?? segments[0] ?? '')
  const [name, setName] = useState<string | null>(null)
  const constructions = edits.constructions

  if (segments.length === 0) {
    return <p className="text-sm text-muted-foreground">Hình hiện tại chưa có đoạn thẳng để dùng làm cạnh tham chiếu.</p>
  }
  const needsName = tool !== 'angle_bisector'
  const suggested = suggestPointName(names, edits, tool === 'perpendicular' ? 'H' : 'M')
  const newName = (name ?? suggested).toUpperCase()

  let spec: Record<string, string> | null = null
  let warning: string | null = null
  if (tool === 'perpendicular') spec = { type: tool, point, segment: side, name: newName }
  else if (tool === 'perpendicular_bisector') spec = { type: tool, segment: side, name: newName }
  else if (tool === 'median') {
    spec = { type: tool, point, segment: side, name: newName }
    if (side.includes(point)) warning = 'Cạnh đối diện không được chứa đỉnh đã chọn.'
  } else {
    spec = { type: tool, side1: side, side2 }
    if (new Set([...side].filter((c) => side2.includes(c))).size !== 1)
      warning = 'Hai cạnh được chọn phải có chung đúng một đỉnh của góc.'
  }
  const used = new Set([...names, ...constructions.map((c) => c.name ?? '')])
  if (!warning && needsName) {
    if (!/^[A-Z]$/.test(newName)) warning = 'Tên điểm mới phải là một chữ cái.'
    else if (used.has(newName)) warning = `Tên điểm ${newName} đã được sử dụng.`
  }
  const duplicate = constructions.some((c) => JSON.stringify(c) === JSON.stringify(spec))

  return (
    <div className="grid gap-3">
      <div className="grid gap-1.5">
        <Label className="text-xs text-muted-foreground">Công cụ</Label>
        <Select value={tool} onValueChange={(v) => { setTool(v as Tool); setName(null) }}>
          <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
          <SelectContent>
            {(Object.keys(TOOLS) as Tool[]).map((t) => <SelectItem key={t} value={t}>{TOOLS[t]}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {(tool === 'perpendicular' || tool === 'median') && (
          <Choice label={tool === 'median' ? 'Đỉnh' : 'Điểm đi qua'} value={point} options={names} onChange={setPoint} />
        )}
        <Choice
          label={tool === 'angle_bisector' ? 'Cạnh thứ nhất' : tool === 'median' ? 'Cạnh đối diện' : tool === 'perpendicular' ? 'Đường thẳng/cạnh' : 'Đoạn thẳng'}
          value={side} options={segments} onChange={setSide} />
        {tool === 'angle_bisector' && (
          <Choice label="Cạnh thứ hai" value={side2} options={segments.filter((s) => s !== side)} onChange={setSide2} />
        )}
        {needsName && (
          <div className="grid gap-1.5">
            <Label className="text-xs text-muted-foreground">
              {tool === 'perpendicular' ? 'Tên chân đường vuông góc' : tool === 'median' ? 'Tên trung điểm cạnh' : 'Tên trung điểm'}
            </Label>
            <Input value={newName} maxLength={1} onChange={(e) => setName(e.target.value)} className="uppercase" />
          </div>
        )}
      </div>
      {warning && <p className="text-xs text-destructive">{warning}</p>}
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" disabled={busy || Boolean(warning) || duplicate}
                onClick={() => { onChange([...constructions, spec!]); setName(null) }}>
          Dựng đối tượng
        </Button>
        <Button variant="outline" size="sm" disabled={busy || constructions.length === 0}
                onClick={() => onChange(constructions.slice(0, -1))}>
          <Undo2 /> Xóa thao tác cuối
        </Button>
        {constructions.length > 0 && (
          <span className="text-xs text-muted-foreground">Đã thêm {constructions.length} phép dựng thủ công.</span>
        )}
      </div>
    </div>
  )
}

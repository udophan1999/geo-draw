// Small SVG charts for the admin overview: columns (stacked or single), an area line and
// horizontal bars. Specs: columns at most 24px with a 4px rounded data end, 2px lines with
// a 10% area wash, hairline gridlines, a tooltip on hover and keyboard focus, and every
// chart card can show its numbers as a table. Colors come from the --viz-* tokens.
import { Table2 } from 'lucide-react'
import { useLayoutEffect, useRef, useState, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

export type Series = { key: string; label: string; color: string; values: number[] }

const HEIGHT = 200
const PAD = { top: 12, right: 12, bottom: 24, left: 36 }
const number = new Intl.NumberFormat('vi-VN')

/** "2026-10-02" -> "02/10". */
export const shortDay = (day: string) => `${day.slice(8, 10)}/${day.slice(5, 7)}`

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)
  useLayoutEffect(() => {
    if (!ref.current) return
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)))
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])
  return [ref, width] as const
}

/** About four clean ticks from 0: whole-number steps of 1, 2 or 5 × 10^k (these are counts). */
function niceTicks(max: number): number[] {
  if (max <= 0) return [0, 1]
  const rough = max / 4
  const power = 10 ** Math.floor(Math.log10(rough))
  const step = Math.max(1, [1, 2, 5, 10].map((m) => m * power).find((s) => s >= rough) ?? rough)
  const ticks = []
  for (let v = 0; v <= max + step * 0.001; v += step) ticks.push(Math.round(v))
  if (ticks[ticks.length - 1] < max) ticks.push(ticks[ticks.length - 1] + step)
  return ticks.filter((v, i, all) => all.indexOf(v) === i)
}

/** A column whose top corners are rounded (the data end); the baseline stays square. */
function columnPath(x: number, y: number, w: number, h: number, round: boolean): string {
  const r = round ? Math.min(4, w / 2, h) : 0
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`
}

function Axes({ width, labels, ticks, y }: {
  width: number; labels: string[]; ticks: number[]; y: (v: number) => number
}) {
  const plot = width - PAD.left - PAD.right
  const step = Math.max(1, Math.ceil(labels.length / Math.max(2, Math.floor(plot / 64))))
  const band = plot / labels.length
  return (
    <g className="text-[11px]" fill="currentColor">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)}
                stroke={t === 0 ? 'var(--viz-axis)' : 'var(--viz-grid)'} strokeWidth={1} />
          <text x={PAD.left - 6} y={y(t)} dy="0.32em" textAnchor="end" className="fill-muted-foreground tabular-nums">
            {number.format(t)}
          </text>
        </g>
      ))}
      {/* Counted back from the last day, so today always has a label. */}
      {labels.map((label, i) => (labels.length - 1 - i) % step === 0 ? (
        <text key={label} x={PAD.left + band * (i + 0.5)} y={HEIGHT - 6} textAnchor="middle"
              className="fill-muted-foreground tabular-nums">
          {shortDay(label)}
        </text>
      ) : null)}
    </g>
  )
}

type Tip = { x: number; y: number; title: string; rows: { label: string; color: string; value: number }[] }

function Tooltip({ tip, width }: { tip: Tip | null; width: number }) {
  if (!tip) return null
  const left = Math.min(Math.max(tip.x, 70), width - 70)
  return (
    <div role="status" className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg border bg-popover px-3 py-2 text-xs shadow-md"
         style={{ left, top: tip.y - 8 }}>
      <p className="mb-1 text-muted-foreground">{tip.title}</p>
      {tip.rows.map((row) => (
        <p key={row.label} className="flex items-center gap-2 whitespace-nowrap">
          <span className="h-0.5 w-3 rounded-full" style={{ background: row.color }} />
          <span className="font-semibold tabular-nums">{number.format(row.value)}</span>
          <span className="text-muted-foreground">{row.label}</span>
        </p>
      ))}
    </div>
  )
}

/** Daily columns; with two or more series they stack (first series at the bottom). */
export function ColumnChart({ days, series }: { days: string[]; series: Series[] }) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const [tip, setTip] = useState<Tip | null>(null)
  const [active, setActive] = useState<number | null>(null)
  const totals = days.map((_, i) => series.reduce((sum, s) => sum + s.values[i], 0))
  const ticks = niceTicks(Math.max(...totals, 0))
  const top = ticks[ticks.length - 1]
  const plotH = HEIGHT - PAD.top - PAD.bottom
  const y = (v: number) => PAD.top + plotH - (v / top) * plotH
  const band = (width - PAD.left - PAD.right) / days.length
  const barW = Math.max(2, Math.min(24, band * 0.62))

  const show = (i: number) => {
    setActive(i)
    setTip({
      x: PAD.left + band * (i + 0.5), y: y(totals[i]),
      title: `Ngày ${shortDay(days[i])}`,
      rows: [...series].reverse().map((s) => ({ label: s.label, color: s.color, value: s.values[i] })),
    })
  }
  const hide = () => { setActive(null); setTip(null) }

  return (
    <div ref={ref} className="relative text-muted-foreground">
      {width > 0 && (
        <svg width={width} height={HEIGHT} role="img" aria-label="Biểu đồ cột theo ngày" onPointerLeave={hide}>
          <Axes width={width} labels={days} ticks={ticks} y={y} />
          {days.map((day, i) => {
            const x = PAD.left + band * i + (band - barW) / 2
            let base = y(0)
            const drawn = series.filter((s) => s.values[i] > 0)
            return (
              <g key={day} opacity={active === null || active === i ? 1 : 0.55}>
                {drawn.map((s, k) => {
                  const h = Math.max(1, y(0) - y(s.values[i]) - (k > 0 ? 2 : 0))  // 2px surface gap
                  const yTop = base - h - (k > 0 ? 2 : 0)
                  const path = columnPath(x, yTop, barW, h, k === drawn.length - 1)
                  base = yTop
                  return <path key={s.key} d={path} fill={s.color} />
                })}
                {/* The hit target: the whole day's band, taller and wider than the mark. */}
                <rect x={PAD.left + band * i} y={PAD.top} width={band} height={plotH} fill="transparent"
                      tabIndex={0} aria-label={`${shortDay(day)}: ${series.map((s) => `${s.label} ${s.values[i]}`).join(', ')}`}
                      onPointerEnter={() => show(i)} onFocus={() => show(i)} onBlur={hide}
                      className="outline-none" />
              </g>
            )
          })}
        </svg>
      )}
      <Tooltip tip={tip} width={width} />
    </div>
  )
}

/** One series over days: a 2px line with a light area wash, crosshair and end label. */
export function AreaChart({ days, series }: { days: string[]; series: Series }) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const [index, setIndex] = useState<number | null>(null)
  const values = series.values
  const ticks = niceTicks(Math.max(...values, 0))
  const top = ticks[ticks.length - 1]
  const plotH = HEIGHT - PAD.top - PAD.bottom
  const y = (v: number) => PAD.top + plotH - (v / top) * plotH
  const band = (width - PAD.left - PAD.right) / days.length
  const x = (i: number) => PAD.left + band * (i + 0.5)
  const line = values.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join('')
  const area = `${line}L${x(values.length - 1)},${y(0)}L${x(0)},${y(0)}Z`
  const last = values.length - 1

  const pick = (clientX: number, rect: DOMRect) => {
    const i = Math.round((clientX - rect.left - PAD.left) / band - 0.5)
    setIndex(Math.min(Math.max(i, 0), last))
  }
  const tip: Tip | null = index === null ? null : {
    x: x(index), y: y(values[index]), title: `Ngày ${shortDay(days[index])}`,
    rows: [{ label: series.label, color: series.color, value: values[index] }],
  }

  return (
    <div ref={ref} className="relative text-muted-foreground">
      {width > 0 && (
        <svg width={width} height={HEIGHT} role="img" aria-label={`${series.label} theo ngày`} tabIndex={0}
             className="outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
             onPointerMove={(e) => pick(e.clientX, e.currentTarget.getBoundingClientRect())}
             onPointerLeave={() => setIndex(null)} onBlur={() => setIndex(null)}
             onFocus={() => setIndex(last)}
             onKeyDown={(e) => {
               if (e.key === 'ArrowLeft') setIndex((i) => Math.max((i ?? last) - 1, 0))
               if (e.key === 'ArrowRight') setIndex((i) => Math.min((i ?? last) + 1, last))
             }}>
          <Axes width={width} labels={days} ticks={ticks} y={y} />
          <path d={area} fill={series.color} opacity={0.1} />
          <path d={line} fill="none" stroke={series.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          {index !== null && (
            <line x1={x(index)} x2={x(index)} y1={PAD.top} y2={y(0)} stroke="var(--viz-axis)" strokeWidth={1} />
          )}
          {[index ?? last].map((i) => (
            <circle key={i} cx={x(i)} cy={y(values[i])} r={4} fill={series.color} stroke="var(--card)" strokeWidth={2} />
          ))}
          {index === null && (
            <text x={x(last) - 8} y={y(values[last]) - 10} textAnchor="end" className="fill-foreground text-[11px] font-semibold tabular-nums">
              {number.format(values[last])}
            </text>
          )}
        </svg>
      )}
      <Tooltip tip={tip} width={width} />
    </div>
  )
}

/** Category magnitudes as horizontal bars in one hue, value at the tip. */
export function BarList({ items, color }: { items: { label: string; value: number }[]; color: string }) {
  const max = Math.max(...items.map((i) => i.value), 1)
  return (
    <ul className="grid gap-3">
      {items.map((item) => (
        <li key={item.label} className="grid gap-1">
          <div className="flex items-baseline justify-between gap-2 text-sm">
            <span>{item.label}</span>
            <span className="font-semibold tabular-nums">{number.format(item.value)}</span>
          </div>
          <div className="h-2.5 rounded-full bg-muted" aria-hidden="true">
            <div className="h-full rounded-full" style={{ width: `${(item.value / max) * 100}%`, background: color, minWidth: item.value ? 4 : 0 }} />
          </div>
        </li>
      ))}
    </ul>
  )
}

/** A card holding a chart: title, subtitle, legend (2+ series) and a table view. */
export function ChartCard({ title, subtitle, legend, table, children, className }: {
  title: string; subtitle?: string; legend?: { label: string; color: string }[]
  table?: { columns: string[]; rows: (string | number)[][] }; children: ReactNode; className?: string
}) {
  const [asTable, setAsTable] = useState(false)
  return (
    <section className={cn('grid content-start gap-3 rounded-xl border bg-card p-4', className)}>
      <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
        <div className="min-w-0">
          <h3 className="font-medium">{title}</h3>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        <div className="ml-auto flex items-center gap-3">
          {legend && legend.length > 1 && legend.map((item) => (
            <span key={item.label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="size-2.5 rounded-[3px]" style={{ background: item.color }} /> {item.label}
            </span>
          ))}
          {table && (
            <button type="button" onClick={() => setAsTable((v) => !v)} aria-pressed={asTable}
                    className={cn('flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted',
                                  asTable && 'bg-muted text-foreground')}>
              <Table2 className="size-3.5" /> Bảng số liệu
            </button>
          )}
        </div>
      </div>
      {asTable && table ? (
        <div className="max-h-[200px] overflow-auto rounded-lg border">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-muted text-left text-muted-foreground">
              <tr>{table.columns.map((c, i) => <th key={c} className={cn('px-2 py-1 font-medium', i > 0 && 'text-right')}>{c}</th>)}</tr>
            </thead>
            <tbody>
              {table.rows.map((row) => (
                <tr key={String(row[0])} className="border-t">
                  {row.map((cell, i) => (
                    <td key={i} className={cn('px-2 py-1', i > 0 && 'text-right tabular-nums')}>
                      {typeof cell === 'number' ? number.format(cell) : cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : children}
    </section>
  )
}

/** A headline number with its label and one line of context. */
export function StatTile({ label, value, detail, icon }: {
  label: string; value: number; detail?: string; icon?: ReactNode
}) {
  return (
    <div className="grid gap-1 rounded-xl border bg-card p-4">
      <p className="flex items-center gap-2 text-sm text-muted-foreground">{icon}{label}</p>
      <p className="text-3xl font-semibold tracking-tight">{number.format(value)}</p>
      {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
    </div>
  )
}

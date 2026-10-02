// The 7 / 30 / 90 days switch on top of the admin pages with charts.
import { cn } from '@/lib/utils'

export const RANGES = [7, 30, 90] as const
export type Range = (typeof RANGES)[number]

export function RangeSwitch({ value, onChange }: { value: Range; onChange: (days: Range) => void }) {
  return (
    <div className="flex rounded-lg border bg-card p-0.5" role="group" aria-label="Khoảng thời gian">
      {RANGES.map((n) => (
        <button key={n} type="button" onClick={() => onChange(n)} aria-pressed={value === n}
                className={cn('rounded-md px-3 py-1 text-sm transition',
                              value === n ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground')}>
          {n} ngày
        </button>
      ))}
    </div>
  )
}

// Dates for the admin pages, in Vietnamese.

const relative = new Intl.RelativeTimeFormat('vi', { numeric: 'auto' })
const STEPS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 31_536_000], ['month', 2_592_000], ['day', 86_400], ['hour', 3_600], ['minute', 60],
]

/** "3 giờ trước", "Hôm qua"…; "Chưa có" for none. */
export function ago(seconds: number | null): string {
  if (!seconds) return 'Chưa có'
  const diff = seconds - Date.now() / 1000
  for (const [unit, size] of STEPS) {
    if (Math.abs(diff) >= size) return relative.format(Math.round(diff / size), unit)
  }
  return 'Vừa xong'
}

/** 2/10/2026 */
export const date = (seconds: number) => new Date(seconds * 1000).toLocaleDateString('vi-VN')

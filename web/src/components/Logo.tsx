import { cn } from '@/lib/utils'

/** The app mark (web/public/logo.svg): a right triangle inscribed in a circle (Thales). */
export function Logo({ className }: { className?: string }) {
  return <img src="/logo.svg" alt="" aria-hidden="true" draggable={false} className={cn('size-7 shrink-0', className)} />
}

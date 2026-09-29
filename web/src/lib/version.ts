// Tell a long-open tab that a new build was deployed: its JavaScript would otherwise keep
// talking to a newer API with an older UI.
import { useEffect } from 'react'
import { toast } from 'sonner'

declare const __BUILD_ID__: string

const CHECK_EVERY_MS = 5 * 60 * 1000

async function latestBuild(): Promise<string | null> {
  try {
    const response = await fetch('/version.json', { cache: 'no-store' })
    if (!response.ok) return null
    const data = await response.json()
    return typeof data.build === 'string' ? data.build : null
  } catch {
    return null // dev server (no version.json) or offline
  }
}

export function useNewVersionNotice() {
  useEffect(() => {
    let notified = false
    const check = async () => {
      if (notified || document.visibilityState !== 'visible') return
      const latest = await latestBuild()
      if (latest && latest !== __BUILD_ID__) {
        notified = true
        toast('Đã có phiên bản mới của geo-draw', {
          description: 'Tải lại trang để dùng giao diện mới nhất.',
          duration: Infinity,
          action: { label: 'Tải lại', onClick: () => window.location.reload() },
        })
      }
    }
    const timer = window.setInterval(check, CHECK_EVERY_MS)
    document.addEventListener('visibilitychange', check)
    void check()
    return () => {
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', check)
    }
  }, [])
}

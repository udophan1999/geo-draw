import { Loader2, Menu } from 'lucide-react'
import { useState } from 'react'
import { Navigate, Outlet } from 'react-router'

import { Logo } from '@/components/Logo'
import { Sidebar } from '@/components/Sidebar'
import { Button } from '@/components/ui/button'
import { ChatProvider } from '@/lib/chat'
import { isGuestMode } from '@/lib/guest'
import { useMe } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { APP_NAME } from '@/lib/brand'

/** Signed-in users and guests who chose "Dùng thử" get the app; everyone else /login. */
export function AppLayout() {
  const me = useMe()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  if (me.isPending) {
    return (
      <div className="flex h-svh items-center justify-center">
        <Loader2 className="animate-spin text-muted-foreground" />
      </div>
    )
  }
  if (!me.data?.user && !isGuestMode()) return <Navigate to="/login" replace />

  return (
    <ChatProvider>
      <div className="flex h-svh overflow-hidden">
        {/* Desktop: fixed column. Mobile: slide-over opened from the top bar. */}
        <div
          className={cn(
            'fixed inset-y-0 left-0 z-40 w-72 border-r transition-transform md:static md:w-64 md:translate-x-0',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          <Sidebar onNavigate={() => setSidebarOpen(false)} />
        </div>
        {sidebarOpen && (
          <button
            aria-label="Đóng menu"
            className="fixed inset-0 z-30 bg-black/30 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
        <main className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-center gap-2 border-b px-3 py-2 md:hidden">
            <Button variant="ghost" size="icon" aria-label="Mở menu" onClick={() => setSidebarOpen(true)}>
              <Menu />
            </Button>
            <Logo className="size-6" />
            <span className="font-semibold">{APP_NAME}</span>
          </div>
          <Outlet />
        </main>
      </div>
    </ChatProvider>
  )
}

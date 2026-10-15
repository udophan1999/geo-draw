// /admin/*: a left sidebar with one entry per section; admins only (others go to "/").
import { ArrowLeft, LayoutDashboard, Loader2, Menu, MessageSquareText, Users } from 'lucide-react'
import { useState } from 'react'
import { Link, Navigate, NavLink, Outlet } from 'react-router'

import { Logo } from '@/components/Logo'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { APP_NAME } from '@/lib/brand'
import { useMe } from '@/lib/queries'
import { cn } from '@/lib/utils'

const SECTIONS = [
  { to: '/admin', label: 'Tổng quan', icon: LayoutDashboard, end: true },
  { to: '/admin/users', label: 'Người dùng', icon: Users, end: false },
  { to: '/admin/prompts', label: 'System prompt', icon: MessageSquareText, end: false },
]

export function AdminLayout() {
  const me = useMe()
  const [open, setOpen] = useState(false)

  if (me.isPending) {
    return (
      <div className="flex h-svh items-center justify-center">
        <Loader2 className="animate-spin text-muted-foreground" />
      </div>
    )
  }
  const user = me.data?.user
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'admin') return <Navigate to="/" replace />

  const sidebar = (
    <nav className="flex h-full flex-col bg-sidebar" aria-label="Quản trị">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <Logo className="size-7" />
        <div className="leading-tight">
          <p className="font-semibold">{APP_NAME}</p>
          <p className="text-xs text-muted-foreground">Quản trị</p>
        </div>
      </div>
      <ul className="grid gap-0.5 px-2">
        {SECTIONS.map(({ to, label, icon: Icon, end }) => (
          <li key={to}>
            <NavLink to={to} end={end} onClick={() => setOpen(false)}
                     className={({ isActive }) => cn(
                       'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition',
                       isActive ? 'bg-sidebar-accent font-medium text-foreground' : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground',
                     )}>
              <Icon className="size-4" /> {label}
            </NavLink>
          </li>
        ))}
      </ul>
      <div className="mt-auto grid gap-2 border-t p-3">
        <div className="flex items-center gap-2.5 px-1">
          <Avatar className="size-7">
            <AvatarFallback className="bg-primary text-xs text-primary-foreground">
              {user.name.slice(0, 1).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <span className="truncate text-sm font-medium">{user.name}</span>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link to="/"><ArrowLeft /> Về trang học</Link>
        </Button>
      </div>
    </nav>
  )

  return (
    <div className="flex h-svh overflow-hidden">
      <aside className={cn('fixed inset-y-0 left-0 z-40 w-64 border-r transition-transform md:static md:w-60 md:translate-x-0',
                           open ? 'translate-x-0' : '-translate-x-full')}>
        {sidebar}
      </aside>
      {open && <button aria-label="Đóng menu" className="fixed inset-0 z-30 bg-black/30 md:hidden" onClick={() => setOpen(false)} />}
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b px-3 py-2 md:hidden">
          <Button variant="ghost" size="icon" aria-label="Mở menu" onClick={() => setOpen(true)}>
            <Menu />
          </Button>
          <Logo className="size-6" />
          <span className="font-semibold">Quản trị</span>
        </div>
        <main className="min-h-0 flex-1 overflow-y-auto bg-muted/20">
          <div className="mx-auto grid max-w-6xl gap-6 px-4 py-6 md:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

/** The title row of an admin page, with optional controls on the right. */
export function PageHeader({ title, description, children }: {
  title: string; description?: string; children?: React.ReactNode
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {children}
    </div>
  )
}

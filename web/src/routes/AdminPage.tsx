// "/admin": manage accounts and the tutor's system prompts. Admins only; others go to "/".
import { ArrowLeft, Loader2, MessageSquareText, Users } from 'lucide-react'
import { Link, Navigate, useSearchParams } from 'react-router'

import { PromptsPanel } from '@/components/admin/PromptsPanel'
import { UsersPanel } from '@/components/admin/UsersPanel'
import { Logo } from '@/components/Logo'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { APP_NAME } from '@/lib/brand'
import { useMe } from '@/lib/queries'

const TABS = ['users', 'prompts'] as const

export function AdminPage() {
  const me = useMe()
  const [params, setParams] = useSearchParams()
  const tab = TABS.find((t) => t === params.get('tab')) ?? 'users'

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

  return (
    <div className="min-h-svh bg-muted/20">
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          <Logo className="size-7" />
          <div className="min-w-0">
            <h1 className="leading-tight font-semibold">Quản trị {APP_NAME}</h1>
            <p className="text-xs text-muted-foreground">Đăng nhập với tên {user.name}</p>
          </div>
          <Button variant="outline" size="sm" className="ml-auto" asChild>
            <Link to="/"><ArrowLeft /> Về trang học</Link>
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Tabs value={tab} onValueChange={(value) => setParams({ tab: value }, { replace: true })}>
          <TabsList>
            <TabsTrigger value="users"><Users /> Người dùng</TabsTrigger>
            <TabsTrigger value="prompts"><MessageSquareText /> System prompt</TabsTrigger>
          </TabsList>
          <TabsContent value="users" className="pt-4">
            <UsersPanel meId={user.id} />
          </TabsContent>
          <TabsContent value="prompts" className="pt-4">
            <PromptsPanel />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}

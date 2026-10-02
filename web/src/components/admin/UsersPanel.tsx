// Admin → Người dùng: every account with its activity, and the actions on it.
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronRight, Loader2, Lock, Search, ShieldCheck } from 'lucide-react'
import { useDeferredValue, useState } from 'react'
import { Link } from 'react-router'

import { UserActions } from '@/components/admin/UserActions'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { api } from '@/lib/api'
import { ago, date } from '@/lib/format'
import { keys } from '@/lib/queries'
import { cn } from '@/lib/utils'

export function UsersPanel({ meId }: { meId: string }) {
  const client = useQueryClient()
  const [search, setSearch] = useState('')
  const q = useDeferredValue(search.trim())
  const users = useQuery({
    queryKey: keys.adminUsers(q), queryFn: () => api.admin.users(q), placeholderData: keepPreviousData,
  })
  const refresh = () => client.invalidateQueries({ queryKey: ['admin'] })

  const list = users.data?.users ?? []
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm theo tên…"
                 className="pl-8" aria-label="Tìm người dùng" />
        </div>
        {users.data && (
          <p className="text-sm text-muted-foreground">
            {list.length} tài khoản · hạn mức mặc định {users.data.default_limit} lượt AI/ngày
          </p>
        )}
      </div>

      {users.isPending ? (
        <Loader2 className="mx-auto my-10 animate-spin text-muted-foreground" />
      ) : users.isError ? (
        <p className="text-sm text-destructive">{users.error.message}</p>
      ) : list.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">Không có tài khoản nào khớp.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Người dùng</th>
                <th className="px-3 py-2 font-medium">Ngày tạo</th>
                <th className="px-3 py-2 font-medium">Hoạt động gần nhất</th>
                <th className="px-3 py-2 text-right font-medium">Cuộc trò chuyện</th>
                <th className="px-3 py-2 text-right font-medium">Lượt AI hôm nay</th>
                <th className="w-20" />
              </tr>
            </thead>
            <tbody>
              {list.map((user) => {
                const self = user.id === meId
                return (
                  <tr key={user.id} className={cn('border-t', user.disabled && 'text-muted-foreground')}>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Link to={`/admin/users/${user.id}`} className="font-medium hover:text-primary hover:underline">
                          {user.name}
                        </Link>
                        {self && <Badge variant="outline">Bạn</Badge>}
                        {user.role === 'admin' && <Badge><ShieldCheck /> Quản trị</Badge>}
                        {user.disabled && <Badge variant="destructive"><Lock /> Đã khóa</Badge>}
                      </div>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">{date(user.created_at)}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {ago(Math.max(user.last_active ?? 0, user.last_login ?? 0) || null)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">{user.conversations}</td>
                    <td className="px-3 py-2 text-right whitespace-nowrap tabular-nums">
                      {user.quota.used}/{user.quota.limit}
                      {user.quota.custom && <span className="ml-1 text-xs text-primary">(riêng)</span>}
                    </td>
                    <td className="px-1 py-1">
                      <div className="flex items-center justify-end">
                        <UserActions user={user} self={self} defaultLimit={users.data?.default_limit ?? 0}
                                     onChanged={refresh} onDeleted={refresh} />
                        <Link to={`/admin/users/${user.id}`} aria-label={`Xem chi tiết ${user.name}`}
                              className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground">
                          <ChevronRight className="size-4" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

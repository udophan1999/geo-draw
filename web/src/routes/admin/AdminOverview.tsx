// /admin: totals and daily activity over 7, 30 or 90 days.
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Loader2, MessagesSquare, Sparkles, UserCheck, Users } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { AreaChart, BarList, ChartCard, ColumnChart, shortDay, StatTile } from '@/components/admin/charts'
import { RangeSwitch, type Range } from '@/components/admin/RangeSwitch'
import { api } from '@/lib/api'
import { keys } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { PageHeader } from '@/routes/admin/AdminLayout'

const ACCOUNTS = { label: 'Tài khoản', color: 'var(--viz-1)' }
const GUESTS = { label: 'Khách', color: 'var(--viz-2)' }

export function AdminOverview() {
  const [days, setDays] = useState<Range>(30)
  const stats = useQuery({
    queryKey: keys.adminStats(days), queryFn: () => api.admin.stats(days), placeholderData: keepPreviousData,
  })

  const range = <RangeSwitch value={days} onChange={setDays} />

  if (stats.isPending) {
    return (
      <>
        <PageHeader title="Tổng quan" description="Hoạt động của người dùng và lượt dùng AI.">{range}</PageHeader>
        <Loader2 className="mx-auto my-16 animate-spin text-muted-foreground" />
      </>
    )
  }
  if (stats.isError) return <p className="text-sm text-destructive">{stats.error.message}</p>

  const { days: labels, series, totals, outcomes, top_users: top } = stats.data
  const period = `${days} ngày qua`
  const dayRows = (...columns: number[][]) => labels.map((d, i) => [shortDay(d), ...columns.map((c) => c[i])])

  return (
    <>
      <PageHeader title="Tổng quan" description="Hoạt động của người dùng và lượt dùng AI.">{range}</PageHeader>
      {/* Refetching keeps the previous frame, dimmed, instead of a layout jump. */}
      <div className={cn('grid gap-4 transition-opacity', stats.isPlaceholderData && 'opacity-60')}>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatTile icon={<Users className="size-4" />} label="Người dùng" value={totals.users}
                    detail={`+${totals.new_users} mới trong ${period} · ${totals.admins} quản trị`} />
          <StatTile icon={<UserCheck className="size-4" />} label="Đang hoạt động" value={totals.active_users}
                    detail={`đăng nhập hoặc dùng AI trong ${period}`} />
          <StatTile icon={<MessagesSquare className="size-4" />} label="Cuộc trò chuyện mới" value={totals.new_conversations}
                    detail={`tổng cộng ${totals.conversations} của các tài khoản`} />
          <StatTile icon={<Sparkles className="size-4" />} label="Lượt AI" value={totals.ai_turns}
                    detail={`${totals.ai_guest_turns} lượt của khách · ${period}`} />
        </div>

        <ChartCard title="Lượt dùng AI mỗi ngày" subtitle="Mỗi lượt trợ giảng trả lời và mỗi lần vẽ bằng AI tính 1 lượt."
                   legend={[ACCOUNTS, GUESTS]}
                   table={{ columns: ['Ngày', ACCOUNTS.label, GUESTS.label], rows: dayRows(series.ai_users, series.ai_guests) }}>
          <ColumnChart days={labels} series={[
            { key: 'users', ...ACCOUNTS, values: series.ai_users },
            { key: 'guests', ...GUESTS, values: series.ai_guests },
          ]} />
        </ChartCard>

        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard title="Cuộc trò chuyện mới mỗi ngày" subtitle="Của các tài khoản đã đăng ký."
                     table={{ columns: ['Ngày', 'Cuộc trò chuyện'], rows: dayRows(series.new_conversations) }}>
            <AreaChart days={labels} series={{ key: 'conversations', label: 'cuộc trò chuyện', color: 'var(--viz-1)', values: series.new_conversations }} />
          </ChartCard>
          <ChartCard title="Người dùng mới mỗi ngày" subtitle="Tài khoản đăng ký mới."
                     table={{ columns: ['Ngày', 'Người dùng mới'], rows: dayRows(series.new_users) }}>
            <ColumnChart days={labels} series={[{ key: 'new', label: 'người dùng mới', color: 'var(--viz-1)', values: series.new_users }]} />
          </ChartCard>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard title="Kết quả các cuộc trò chuyện" subtitle={`Bắt đầu trong ${period}, của các tài khoản.`}>
            <BarList color="var(--viz-1)" items={[
              { label: 'Tự giải xong (theo gợi ý)', value: outcomes.solved },
              { label: 'Đang làm theo gợi ý', value: outcomes.in_progress },
              { label: 'Đã xem lời giải chi tiết', value: outcomes.solution },
            ]} />
          </ChartCard>
          <ChartCard title="Người dùng tích cực nhất" subtitle={`Theo lượt AI trong ${period}.`}>
            {top.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Chưa có hoạt động.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-muted-foreground">
                  <tr>
                    <th className="pb-2 font-medium">Người dùng</th>
                    <th className="pb-2 text-right font-medium">Lượt AI</th>
                    <th className="pb-2 text-right font-medium">Cuộc trò chuyện</th>
                  </tr>
                </thead>
                <tbody>
                  {top.map((u) => (
                    <tr key={u.id} className="border-t">
                      <td className="py-2">{u.name}</td>
                      <td className="py-2 text-right tabular-nums">{u.ai_turns}</td>
                      <td className="py-2 text-right tabular-nums">{u.conversations}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <Link to="/admin/users" className="text-sm text-primary hover:underline">Xem tất cả người dùng →</Link>
          </ChartCard>
        </div>
      </div>
    </>
  )
}

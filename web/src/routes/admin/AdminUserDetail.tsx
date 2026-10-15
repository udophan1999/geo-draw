// /admin/users/:userId: one account — usage over time, questions asked, results, and its
// conversations (titles and counts only; what was said stays private).
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, CalendarCheck, ChevronDown, CircleCheck, ImageIcon, Loader2, Lock, MessageCircleQuestion,
  MessagesSquare, ShieldCheck, Sparkles,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { AreaChart, BarList, ChartCard, ColumnChart, shortDay, StatTile } from '@/components/admin/charts'
import { RangeSwitch, type Range } from '@/components/admin/RangeSwitch'
import { UserActions } from '@/components/admin/UserActions'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { api, ApiError, type AdminUserDetail } from '@/lib/api'
import { ago, date } from '@/lib/format'
import { HINT_LEVELS } from '@/lib/hintLevels'
import { keys, useMe } from '@/lib/queries'
import { cn } from '@/lib/utils'

export function AdminUserDetail() {
  const { userId = '' } = useParams()
  const me = useMe()
  const client = useQueryClient()
  const navigate = useNavigate()
  const [days, setDays] = useState<Range>(30)
  const detail = useQuery({
    queryKey: keys.adminUser(userId, days), queryFn: () => api.admin.user(userId, days),
    placeholderData: keepPreviousData,
  })

  const back = (
    <Link to="/admin/users" className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
      <ArrowLeft className="size-4" /> Người dùng
    </Link>
  )
  if (detail.isPending) return <>{back}<Loader2 className="mx-auto my-16 animate-spin text-muted-foreground" /></>
  if (detail.isError) {
    const gone = detail.error instanceof ApiError && detail.error.status === 404
    return <>{back}<p className="text-sm text-destructive">{gone ? 'Không tìm thấy tài khoản này (có thể đã bị xóa).' : detail.error.message}</p></>
  }

  const user = detail.data
  const self = user.id === me.data?.user?.id
  const period = `${days} ngày qua`
  const refresh = () => client.invalidateQueries({ queryKey: ['admin'] })

  return (
    <>
      {back}
      <header className="flex flex-wrap items-center gap-4 rounded-xl border bg-card p-4">
        <Avatar className="size-14">
          <AvatarFallback className="bg-primary text-xl text-primary-foreground">
            {user.name.slice(0, 1).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <div className="grid min-w-0 gap-1">
          <h1 className="flex flex-wrap items-center gap-2 text-xl font-semibold tracking-tight">
            {user.name}
            {self && <Badge variant="outline">Bạn</Badge>}
            {user.role === 'admin' && <Badge><ShieldCheck /> Quản trị</Badge>}
            {user.disabled && <Badge variant="destructive"><Lock /> Đã khóa</Badge>}
          </h1>
          <p className="text-sm text-muted-foreground">
            Tạo ngày {date(user.created_at)} · đăng nhập {ago(user.last_login).toLowerCase()} ·
            hoạt động {ago(user.last_active).toLowerCase()}
          </p>
          <p className="text-sm text-muted-foreground">
            Hôm nay đã dùng {user.quota.used}/{user.quota.limit} lượt AI
            {user.quota.custom ? ' (hạn mức riêng)' : ' (hạn mức mặc định)'}
          </p>
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <RangeSwitch value={days} onChange={setDays} />
          <UserActions user={user} self={self} defaultLimit={user.default_limit} onChanged={refresh}
                       onDeleted={() => { void refresh(); navigate('/admin/users') }}
                       trigger={<Button variant="outline">Thao tác <ChevronDown /></Button>} />
        </div>
      </header>

      <Body user={user} period={period} dim={detail.isPlaceholderData} />
    </>
  )
}

function Body({ user, period, dim }: { user: AdminUserDetail; period: string; dim: boolean }) {
  const { days, series, totals, outcomes } = user
  const dayRows = (values: number[]) => days.map((d, i) => [shortDay(d), values[i]])
  return (
    <div className={cn('grid gap-4 transition-opacity', dim && 'opacity-60')}>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <StatTile icon={<MessageCircleQuestion className="size-4" />} label="Câu hỏi đã gửi" value={totals.questions}
                  detail={`${totals.questions_range} trong ${period}`} />
        <StatTile icon={<Sparkles className="size-4" />} label="Lượt AI đã dùng" value={totals.ai_turns}
                  detail={`${totals.ai_turns_range} trong ${period}`} />
        <StatTile icon={<MessagesSquare className="size-4" />} label="Cuộc trò chuyện" value={totals.conversations}
                  detail={`${totals.conversations_range} mới trong ${period}`} />
        <StatTile icon={<CircleCheck className="size-4" />} label="Tự giải xong" value={outcomes.solved}
                  detail={`trên ${totals.conversations} cuộc trò chuyện`} />
        <StatTile icon={<CalendarCheck className="size-4" />} label="Ngày có dùng AI" value={totals.active_days}
                  detail={`trong ${period}`} />
        <StatTile icon={<ImageIcon className="size-4" />} label="Hình vẽ" value={totals.drawings}
                  detail="hình và đồ thị đã vẽ" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Lượt AI mỗi ngày" subtitle="Lượt trợ giảng trả lời và lượt vẽ bằng AI."
                   table={{ columns: ['Ngày', 'Lượt AI'], rows: dayRows(series.ai) }}>
          <ColumnChart days={days} series={[{ key: 'ai', label: 'lượt AI', color: 'var(--viz-1)', values: series.ai }]} />
        </ChartCard>
        <ChartCard title="Câu hỏi mỗi ngày" subtitle="Tin nhắn gửi cho trợ giảng, kể cả đề bài."
                   table={{ columns: ['Ngày', 'Câu hỏi'], rows: dayRows(series.questions) }}>
          <AreaChart days={days} series={{ key: 'questions', label: 'câu hỏi', color: 'var(--viz-1)', values: series.questions }} />
        </ChartCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Kết quả các cuộc trò chuyện" subtitle="Mọi cuộc trò chuyện của người này.">
          <BarList color="var(--viz-1)" items={[
            { label: 'Tự giải xong (theo gợi ý)', value: outcomes.solved },
            { label: 'Đang làm theo gợi ý', value: outcomes.in_progress },
            { label: 'Đã xem lời giải chi tiết', value: outcomes.solution },
          ]} />
        </ChartCard>
        <ChartCard title="Mức gợi ý đã cần" subtitle="Bậc gợi ý cao nhất mà mỗi cuộc trò chuyện đã tới.">
          <BarList color="var(--viz-1)" items={HINT_LEVELS.map((name, i) => ({
            label: `Bậc ${i + 1} · ${name}`, value: user.hint_levels[i] ?? 0,
          }))} />
        </ChartCard>
      </div>

      <section className="grid gap-3 rounded-xl border bg-card p-4">
        <div>
          <h3 className="font-medium">Cuộc trò chuyện</h3>
          <p className="text-xs text-muted-foreground">
            {user.recent_conversations.length < totals.conversations
              ? `${user.recent_conversations.length} cuộc gần nhất trên ${totals.conversations}. `
              : ''}
            Chỉ hiện tiêu đề và số liệu; nội dung trao đổi được giữ riêng tư.
          </p>
        </div>
        {user.recent_conversations.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">Chưa có cuộc trò chuyện nào.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="text-left text-xs text-muted-foreground">
                <tr>
                  <th className="pb-2 font-medium">Đề bài</th>
                  <th className="pb-2 font-medium">Bắt đầu</th>
                  <th className="pb-2 font-medium">Gần nhất</th>
                  <th className="pb-2 text-right font-medium">Câu hỏi</th>
                  <th className="pb-2 text-right font-medium">Hình vẽ</th>
                  <th className="pb-2 pl-4 font-medium">Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {user.recent_conversations.map((c) => (
                  <tr key={c.id} className="border-t">
                    <td className="max-w-72 truncate py-2 pr-3" title={c.title}>{c.title}</td>
                    <td className="py-2 pr-3 whitespace-nowrap">{date(c.created_at)}</td>
                    <td className="py-2 pr-3 whitespace-nowrap text-muted-foreground">{ago(c.updated_at)}</td>
                    <td className="py-2 text-right tabular-nums">{c.questions}</td>
                    <td className="py-2 text-right tabular-nums">{c.drawings}</td>
                    <td className="py-2 pl-4 whitespace-nowrap">
                      {c.solved ? <Badge variant="secondary"><CircleCheck /> Tự giải xong</Badge>
                        : c.mode === 'solution' ? <Badge variant="outline">Đã xem lời giải</Badge>
                        : <span className="text-muted-foreground">Đang làm · bậc {c.hint_level}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

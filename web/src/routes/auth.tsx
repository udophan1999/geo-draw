// /login and /register: one 380px card, switched by route.
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ApiError, api, type Me } from '@/lib/api'
import { setGuestMode } from '@/lib/guest'
import { keys, useMe } from '@/lib/queries'

const MIN_PASSWORD = 6

function AuthShell({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-muted/30 px-4 py-10">
      <div className="mb-8 text-center">
        <div className="text-5xl leading-none">📐</div>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">geo-draw</h1>
        <p className="mt-1 text-sm text-muted-foreground">Vẽ hình học THCS từ đề bài hoặc ảnh chụp</p>
      </div>
      <div className="w-full max-w-[380px] rounded-2xl border bg-card p-6 shadow-sm">{children}</div>
      <Button
        variant="link"
        className="mt-6 text-muted-foreground"
        onClick={() => {
          setGuestMode(true)
          navigate('/')
        }}
      >
        Dùng thử không cần tài khoản →
      </Button>
      <p className="text-xs text-muted-foreground">Hình vẽ khi dùng thử chỉ lưu trên trình duyệt này.</p>
    </div>
  )
}

function Field({ id, label, ...props }: { id: string; label: string } & React.ComponentProps<'input'>) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} name={id} className="h-10" {...props} />
    </div>
  )
}

function FormError({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
      {message}
    </p>
  )
}

function useSignedIn() {
  const client = useQueryClient()
  const navigate = useNavigate()
  return (me: Me) => {
    setGuestMode(false)
    client.setQueryData(keys.me, me)
    client.removeQueries({ queryKey: keys.conversations })
    client.removeQueries({ queryKey: ['conversation'] })
    client.invalidateQueries({ queryKey: keys.settings })
    navigate('/')
  }
}

export function LoginPage() {
  const me = useMe()
  const signedIn = useSignedIn()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const login = useMutation({
    mutationFn: () => api.login(username, password),
    onSuccess: signedIn,
    onError: () => setPassword(''),
  })
  if (me.data?.user) return <Navigate to="/" replace />

  return (
    <AuthShell>
      <h2 className="text-xl font-semibold">Đăng nhập</h2>
      <p className="mt-1 text-sm text-muted-foreground">Đăng nhập để xem lại lịch sử hình đã vẽ.</p>
      <form
        className="mt-5 grid gap-4"
        onSubmit={(event) => {
          event.preventDefault()
          login.mutate()
        }}
      >
        <Field id="username" label="Tên đăng nhập" autoComplete="username" autoFocus
               value={username} onChange={(e) => setUsername(e.target.value)} maxLength={40} />
        <Field id="password" label="Mật khẩu" type="password" autoComplete="current-password"
               value={password} onChange={(e) => setPassword(e.target.value)} maxLength={64} />
        <FormError message={login.error?.message ?? null} />
        <Button type="submit" size="lg" className="h-10" disabled={login.isPending}>
          {login.isPending && <Loader2 className="animate-spin" />}
          Đăng nhập
        </Button>
      </form>
      <p className="mt-5 text-center text-sm text-muted-foreground">
        Chưa có tài khoản?{' '}
        <Link to="/register" className="font-medium text-primary hover:underline">
          Đăng ký ngay
        </Link>
      </p>
    </AuthShell>
  )
}

export function RegisterPage() {
  const me = useMe()
  const signedIn = useSignedIn()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  const register = useMutation({ mutationFn: () => api.register(username, password), onSuccess: signedIn })
  if (me.data?.user) return <Navigate to="/" replace />

  const suggestions = register.error instanceof ApiError ? register.error.suggestions : []
  const error = localError ?? register.error?.message ?? null

  return (
    <AuthShell>
      <h2 className="text-xl font-semibold">Tạo tài khoản</h2>
      <p className="mt-1 text-sm text-muted-foreground">Tài khoản giúp lưu lại lịch sử hỏi đáp và hình đã vẽ.</p>
      <form
        className="mt-5 grid gap-4"
        onSubmit={(event) => {
          event.preventDefault()
          register.reset()
          if (!username.trim()) return setLocalError('Hãy nhập tên đăng nhập.')
          if (password.length < MIN_PASSWORD)
            return setLocalError(`Mật khẩu phải có ít nhất ${MIN_PASSWORD} ký tự.`)
          if (password !== confirm) return setLocalError('Hai lần nhập mật khẩu không khớp.')
          setLocalError(null)
          register.mutate()
        }}
      >
        <Field id="username" label="Tên đăng nhập" autoComplete="username" autoFocus
               placeholder="Ví dụ: an.nguyen.7a" value={username} maxLength={40}
               onChange={(e) => setUsername(e.target.value)} />
        <Field id="password" label="Mật khẩu" type="password" autoComplete="new-password"
               placeholder={`Ít nhất ${MIN_PASSWORD} ký tự`} value={password} maxLength={64}
               onChange={(e) => setPassword(e.target.value)} />
        <Field id="confirm" label="Nhập lại mật khẩu" type="password" autoComplete="new-password"
               value={confirm} maxLength={64} onChange={(e) => setConfirm(e.target.value)} />
        <FormError message={error} />
        {suggestions.length > 0 && (
          <div className="grid gap-2">
            <p className="text-xs text-muted-foreground">Gợi ý tên còn trống (bấm để dùng):</p>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((name) => (
                <Button key={name} type="button" variant="outline" size="sm"
                        onClick={() => {
                          setUsername(name)
                          register.reset()
                        }}>
                  {name}
                </Button>
              ))}
            </div>
          </div>
        )}
        <Button type="submit" size="lg" className="h-10" disabled={register.isPending}>
          {register.isPending && <Loader2 className="animate-spin" />}
          Đăng ký
        </Button>
      </form>
      <p className="mt-5 text-center text-sm text-muted-foreground">
        Đã có tài khoản?{' '}
        <Link to="/login" className="font-medium text-primary hover:underline">
          Đăng nhập
        </Link>
      </p>
    </AuthShell>
  )
}

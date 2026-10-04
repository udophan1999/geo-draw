// The actions on one account (password, AI limit, role, lock, delete) as a ⋯ menu with its
// dialogs. Used by the user list and by the user detail page.
import { useMutation } from '@tanstack/react-query'
import {
  Gauge, KeyRound, Loader2, Lock, LockOpen, MoreHorizontal, ShieldCheck, ShieldOff, Shuffle, Trash2,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { toast } from 'sonner'

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { api, type AdminUser, type AdminUserUpdate } from '@/lib/api'

type Open = 'password' | 'limit' | 'remove' | null

/** ``trigger`` replaces the default ⋯ icon button (e.g. a labelled button on the detail page). */
export function UserActions({ user, self, defaultLimit, onChanged, onDeleted, trigger }: {
  user: AdminUser; self: boolean; defaultLimit: number
  onChanged: () => void; onDeleted: () => void; trigger?: ReactNode
}) {
  const [open, setOpen] = useState<Open>(null)
  const update = useMutation({
    mutationFn: ({ change }: { change: AdminUserUpdate; done: string }) => api.admin.updateUser(user.id, change),
    onSuccess: (_, { done }) => {
      toast.success(done)
      onChanged()
    },
    onError: (error) => toast.error(error.message),
  })
  const close = () => setOpen(null)

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          {trigger ?? (
            <Button variant="ghost" size="icon-sm" aria-label={`Thao tác với ${user.name}`} disabled={update.isPending}>
              {update.isPending ? <Loader2 className="animate-spin" /> : <MoreHorizontal />}
            </Button>
          )}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={() => setOpen('password')}>
            <KeyRound /> Đặt lại mật khẩu…
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => setOpen('limit')}>
            <Gauge /> Đổi hạn mức AI…
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          {user.role === 'admin' ? (
            <DropdownMenuItem disabled={self} onSelect={() => update.mutate({
              change: { role: 'user' }, done: `Đã bỏ quyền quản trị của ${user.name}.`,
            })}>
              <ShieldOff /> Bỏ quyền quản trị
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem onSelect={() => update.mutate({
              change: { role: 'admin' }, done: `${user.name} đã là quản trị viên.`,
            })}>
              <ShieldCheck /> Cấp quyền quản trị
            </DropdownMenuItem>
          )}
          {user.disabled ? (
            <DropdownMenuItem onSelect={() => update.mutate({
              change: { disabled: false }, done: `Đã mở khóa ${user.name}.`,
            })}>
              <LockOpen /> Mở khóa
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem disabled={self} onSelect={() => update.mutate({
              change: { disabled: true }, done: `Đã khóa ${user.name} và đăng xuất khỏi mọi thiết bị.`,
            })}>
              <Lock /> Khóa tài khoản
            </DropdownMenuItem>
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive" disabled={self} onSelect={() => setOpen('remove')}>
            <Trash2 /> Xóa tài khoản…
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <PasswordDialog user={open === 'password' ? user : undefined} onClose={close} />
      <LimitDialog user={open === 'limit' ? user : undefined} defaultLimit={defaultLimit}
                   onClose={close} onSaved={onChanged} />
      <DeleteDialog user={open === 'remove' ? user : undefined} onClose={close} onDeleted={onDeleted} />
    </>
  )
}

function randomPassword(): string {
  const alphabet = 'abcdefghjkmnpqrstuvwxyz23456789'
  const bytes = crypto.getRandomValues(new Uint8Array(10))
  return Array.from(bytes, (b) => alphabet[b % alphabet.length]).join('')
}

function PasswordDialog({ user, onClose }: { user?: AdminUser; onClose: () => void }) {
  const [password, setPassword] = useState('')
  const reset = useMutation({
    mutationFn: () => api.admin.resetPassword(user!.id, password),
    onSuccess: () => {
      toast.success(`Đã đặt mật khẩu mới cho ${user!.name}. Hãy gửi mật khẩu này cho họ.`)
      close()
    },
  })
  const close = () => {
    setPassword('')
    reset.reset()
    onClose()
  }
  return (
    <Dialog open={Boolean(user)} onOpenChange={(open) => !open && close()}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={(e) => { e.preventDefault(); reset.mutate() }} className="grid gap-4">
          <DialogHeader>
            <DialogTitle>Đặt lại mật khẩu cho {user?.name}</DialogTitle>
            <DialogDescription>
              Người dùng sẽ bị đăng xuất khỏi mọi thiết bị và đăng nhập lại bằng mật khẩu mới.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="new-password">Mật khẩu mới (6–64 ký tự)</Label>
            <div className="flex gap-2">
              <Input id="new-password" value={password} onChange={(e) => setPassword(e.target.value)}
                     autoComplete="new-password" className="font-mono" autoFocus />
              <Button type="button" variant="outline" onClick={() => setPassword(randomPassword())}>
                <Shuffle /> Tạo ngẫu nhiên
              </Button>
            </div>
            {reset.isError && <p className="text-sm text-destructive">{reset.error.message}</p>}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={close}>Hủy</Button>
            <Button type="submit" disabled={password.length < 6 || reset.isPending}>
              {reset.isPending && <Loader2 className="animate-spin" />} Đặt mật khẩu
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function LimitDialog({ user, defaultLimit, onClose, onSaved }: {
  user?: AdminUser; defaultLimit: number; onClose: () => void; onSaved: () => void
}) {
  // Keyed on the user, so the form starts from that user's current limit.
  return (
    <Dialog open={Boolean(user)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        {user && <LimitForm key={user.id} user={user} defaultLimit={defaultLimit} onClose={onClose} onSaved={onSaved} />}
      </DialogContent>
    </Dialog>
  )
}

function LimitForm({ user, defaultLimit, onClose, onSaved }: {
  user: AdminUser; defaultLimit: number; onClose: () => void; onSaved: () => void
}) {
  const [custom, setCustom] = useState(user.quota.custom)
  const [value, setValue] = useState(String(user.quota.limit))
  const number = Number(value)
  const valid = !custom || (value.trim() !== '' && Number.isInteger(number) && number >= 0 && number <= 100_000)
  const save = useMutation({
    mutationFn: () => api.admin.updateUser(user.id, custom ? { daily_limit: number } : { reset_limit: true }),
    onSuccess: (saved) => {
      toast.success(`${user.name}: ${saved.quota.limit} lượt AI mỗi ngày.`)
      onSaved()
      onClose()
    },
  })
  return (
    <form onSubmit={(e) => { e.preventDefault(); save.mutate() }} className="grid gap-4">
      <DialogHeader>
        <DialogTitle>Hạn mức AI của {user.name}</DialogTitle>
        <DialogDescription>
          Mỗi lượt trợ giảng trả lời và mỗi lần vẽ bằng AI tính 1 lượt. Hôm nay đã dùng {user.quota.used} lượt.
        </DialogDescription>
      </DialogHeader>
      <RadioGroup value={custom ? 'custom' : 'default'} onValueChange={(v) => setCustom(v === 'custom')}>
        <label className="flex items-center gap-3 rounded-lg border p-3 has-[:checked]:border-primary has-[:checked]:bg-primary/5">
          <RadioGroupItem value="default" />
          <span className="text-sm">Theo mặc định của máy chủ ({defaultLimit} lượt/ngày)</span>
        </label>
        <label className="flex items-center gap-3 rounded-lg border p-3 has-[:checked]:border-primary has-[:checked]:bg-primary/5">
          <RadioGroupItem value="custom" />
          <span className="text-sm">Hạn mức riêng</span>
          <Input type="number" min={0} max={100000} value={value} disabled={!custom} aria-label="Số lượt mỗi ngày"
                 onChange={(e) => setValue(e.target.value)} className="ml-auto w-24" />
          <span className="text-sm text-muted-foreground">lượt/ngày</span>
        </label>
      </RadioGroup>
      {custom && number === 0 && valid && (
        <p className="text-sm text-muted-foreground">0 lượt: người dùng vẫn đăng nhập được nhưng không dùng được AI.</p>
      )}
      {save.isError && <p className="text-sm text-destructive">{save.error.message}</p>}
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>Hủy</Button>
        <Button type="submit" disabled={!valid || save.isPending}>
          {save.isPending && <Loader2 className="animate-spin" />} Lưu
        </Button>
      </DialogFooter>
    </form>
  )
}

function DeleteDialog({ user, onClose, onDeleted }: {
  user?: AdminUser; onClose: () => void; onDeleted: () => void
}) {
  const [typed, setTyped] = useState('')
  const remove = useMutation({
    mutationFn: () => api.admin.deleteUser(user!.id),
    onSuccess: () => {
      toast.success(`Đã xóa tài khoản ${user!.name}.`)
      onDeleted()
      close()
    },
    onError: (error) => toast.error(error.message),
  })
  const close = () => {
    setTyped('')
    onClose()
  }
  return (
    <AlertDialog open={Boolean(user)} onOpenChange={(open) => !open && close()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Xóa tài khoản {user?.name}?</AlertDialogTitle>
          <AlertDialogDescription>
            Tài khoản cùng {user?.conversations ?? 0} cuộc trò chuyện, hình vẽ và cài đặt của người này sẽ bị
            xóa vĩnh viễn, không khôi phục được. Muốn tạm ngừng thì dùng “Khóa tài khoản”.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="grid gap-2">
          <Label htmlFor="confirm-name">Gõ <b>{user?.name}</b> để xác nhận</Label>
          <Input id="confirm-name" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel>Hủy</AlertDialogCancel>
          <AlertDialogAction
            className="bg-destructive text-white hover:bg-destructive/90"
            disabled={typed.trim() !== user?.name || remove.isPending}
            onClick={(e) => { e.preventDefault(); remove.mutate() }}
          >
            {remove.isPending && <Loader2 className="animate-spin" />} Xóa vĩnh viễn
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'

import {
  AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import { setGuestMode } from '@/lib/guest'

/** Delete the signed-in account for good, after the password is typed again. */
export function DeleteAccountDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const client = useQueryClient()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const remove = useMutation({
    mutationFn: () => api.deleteAccount(password),
    onSuccess: () => {
      setGuestMode(false)
      client.clear()
      toast.success('Đã xóa tài khoản và toàn bộ dữ liệu.')
      navigate('/login')
    },
  })
  const close = (next: boolean) => {
    if (!next) {
      setPassword('')
      remove.reset()
    }
    onOpenChange(next)
  }

  return (
    <AlertDialog open={open} onOpenChange={close}>
      <AlertDialogContent>
        <form
          className="grid gap-4"
          onSubmit={(event) => {
            event.preventDefault()
            if (password) remove.mutate()
          }}
        >
          <AlertDialogHeader>
            <AlertDialogTitle>Xóa tài khoản?</AlertDialogTitle>
            <AlertDialogDescription>
              Mọi cuộc trò chuyện, hình vẽ và cài đặt của bạn sẽ bị xóa vĩnh viễn, không khôi phục được.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="delete-password">Nhập mật khẩu để xác nhận</Label>
            <Input
              id="delete-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              aria-invalid={remove.isError}
            />
            {remove.isError && <p role="alert" className="text-sm text-destructive">{remove.error.message}</p>}
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel type="button">Hủy</AlertDialogCancel>
            <Button type="submit" variant="destructive" disabled={!password || remove.isPending}>
              {remove.isPending && <Loader2 className="animate-spin" />}
              Xóa vĩnh viễn
            </Button>
          </AlertDialogFooter>
        </form>
      </AlertDialogContent>
    </AlertDialog>
  )
}

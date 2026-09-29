import { useMutation, useQueryClient } from '@tanstack/react-query'
import { LogIn, LogOut, MoreHorizontal, Pencil, Settings2, SquarePen, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { NavLink, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'

import { Logo } from '@/components/Logo'
import { SettingsDialog } from '@/components/SettingsDialog'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { api, type Conversation } from '@/lib/api'
import { setGuestMode } from '@/lib/guest'
import { keys, useConversations, useMe } from '@/lib/queries'
import { cn } from '@/lib/utils'

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const navigate = useNavigate()
  return (
    <aside className="flex h-full w-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex items-center gap-2 px-4 pt-4 pb-2">
        <Logo />
        <span className="text-base font-semibold tracking-tight">geo-draw</span>
      </div>
      <div className="px-3 pb-2">
        <Button
          variant="outline"
          className="h-9 w-full justify-start gap-2 bg-background"
          onClick={() => {
            navigate('/')
            onNavigate?.()
          }}
        >
          <SquarePen /> Cuộc trò chuyện mới
        </Button>
      </div>
      <ConversationList onNavigate={onNavigate} />
      <AccountBox />
    </aside>
  )
}

function ConversationList({ onNavigate }: { onNavigate?: () => void }) {
  const conversations = useConversations()
  const [renaming, setRenaming] = useState<Conversation | null>(null)
  const [deleting, setDeleting] = useState<Conversation | null>(null)

  return (
    <nav className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
      <p className="px-2 pt-3 pb-1.5 text-xs font-medium text-muted-foreground">Gần đây</p>
      {conversations.isPending &&
        Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="mx-2 my-2 h-5" />)}
      {conversations.data?.length === 0 && (
        <p className="px-2 py-1 text-sm text-muted-foreground">Chưa có cuộc trò chuyện nào.</p>
      )}
      <ul className="flex min-w-0 flex-col gap-0.5">
        {conversations.data?.map((conversation) => (
          <li key={conversation.id} className="group relative min-w-0">
            <NavLink
              to={`/c/${conversation.id}`}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  'block truncate rounded-lg py-2 pr-8 pl-2 text-sm transition-colors hover:bg-sidebar-accent',
                  isActive && 'bg-sidebar-accent font-medium',
                )
              }
              title={conversation.title}
            >
              {conversation.title}
            </NavLink>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-xs"
                  aria-label="Tùy chọn cuộc trò chuyện"
                  className="absolute top-1/2 right-1 -translate-y-1/2 opacity-0 group-hover:opacity-100 data-[state=open]:opacity-100"
                >
                  <MoreHorizontal />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuItem onSelect={() => setRenaming(conversation)}>
                  <Pencil /> Đổi tên
                </DropdownMenuItem>
                <DropdownMenuItem variant="destructive" onSelect={() => setDeleting(conversation)}>
                  <Trash2 /> Xóa
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </li>
        ))}
      </ul>
      <RenameDialog conversation={renaming} onClose={() => setRenaming(null)} />
      <DeleteDialog conversation={deleting} onClose={() => setDeleting(null)} />
    </nav>
  )
}

function RenameDialog({ conversation, onClose }: { conversation: Conversation | null; onClose: () => void }) {
  const client = useQueryClient()
  const [title, setTitle] = useState('')
  const rename = useMutation({
    mutationFn: () => api.renameConversation(conversation!.id, title.trim()),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: keys.conversations })
      onClose()
    },
    onError: (error) => toast.error(error.message),
  })
  return (
    <Dialog open={Boolean(conversation)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="sm:max-w-md"
        onOpenAutoFocus={() => setTitle(conversation?.title ?? '')}
      >
        <DialogHeader><DialogTitle>Đổi tên cuộc trò chuyện</DialogTitle></DialogHeader>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (title.trim()) rename.mutate()
          }}
        >
          <Input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} autoFocus />
          <DialogFooter className="mt-4">
            <Button type="button" variant="outline" onClick={onClose}>Hủy</Button>
            <Button type="submit" disabled={!title.trim() || rename.isPending}>Lưu</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function DeleteDialog({ conversation, onClose }: { conversation: Conversation | null; onClose: () => void }) {
  const client = useQueryClient()
  const navigate = useNavigate()
  const { conversationId } = useParams()
  const remove = useMutation({
    mutationFn: () => api.deleteConversation(conversation!.id),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: keys.conversations })
      if (conversation?.id === conversationId) navigate('/')
      onClose()
    },
    onError: (error) => toast.error(error.message),
  })
  return (
    <AlertDialog open={Boolean(conversation)} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Xóa cuộc trò chuyện?</AlertDialogTitle>
          <AlertDialogDescription>
            «{conversation?.title}» và các hình vẽ trong đó sẽ bị xóa vĩnh viễn.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Hủy</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={(event) => {
              event.preventDefault()
              remove.mutate()
            }}
          >
            Xóa
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

function AccountBox() {
  const me = useMe()
  const client = useQueryClient()
  const navigate = useNavigate()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const logout = useMutation({
    mutationFn: api.logout,
    onSuccess: () => {
      setGuestMode(false)
      client.clear()
      navigate('/login')
    },
  })
  const user = me.data?.user

  return (
    <div className="border-t p-3">
      {user ? (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-11 w-full justify-start gap-3 px-2">
              <Avatar className="size-7">
                <AvatarFallback className="bg-primary text-xs text-primary-foreground">
                  {user.name.slice(0, 1).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <span className="truncate font-medium">{user.name}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent side="top" align="start" className="w-56">
            <DropdownMenuItem onSelect={() => setSettingsOpen(true)}>
              <Settings2 /> Cài đặt
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => logout.mutate()}>
              <LogOut /> Đăng xuất
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ) : (
        <div className="grid gap-2 px-1">
          <p className="text-xs text-muted-foreground">Đăng nhập để lưu lại lịch sử hỏi đáp</p>
          <div className="flex gap-2">
            <Button className="flex-1" onClick={() => navigate('/login')}>
              <LogIn /> Đăng nhập
            </Button>
            <Button variant="outline" size="icon" aria-label="Cài đặt" onClick={() => setSettingsOpen(true)}>
              <Settings2 />
            </Button>
          </div>
        </div>
      )}
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </div>
  )
}

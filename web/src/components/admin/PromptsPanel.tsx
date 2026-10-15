// Admin → System prompt: rewrite the tutor's prompts; the fixed rules are shown read-only.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, Loader2, RotateCcw, Save, Undo2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Textarea } from '@/components/ui/textarea'
import { api, type PromptInfo, type PromptList } from '@/lib/api'
import { keys } from '@/lib/queries'
import { cn } from '@/lib/utils'

const MAX_LENGTH = 20_000

export function PromptsPanel() {
  const prompts = useQuery({ queryKey: keys.adminPrompts, queryFn: api.admin.prompts })
  if (prompts.isPending) return <Loader2 className="mx-auto my-10 animate-spin text-muted-foreground" />
  if (prompts.isError) return <p className="text-sm text-destructive">{prompts.error.message}</p>

  return (
    <div className="grid gap-6">
      <p className="text-sm text-muted-foreground">
        Thay đổi áp dụng ngay từ lượt trả lời tiếp theo, cho mọi người dùng. Đề bài, trạng thái hình vẽ và bậc
        gợi ý hiện tại được ứng dụng tự thêm vào sau prompt.
      </p>
      {prompts.data.prompts.map((prompt) => (
        // Keyed on the saved text, so the editor restarts from it after a save or a reset.
        <PromptEditor key={`${prompt.key}:${prompt.value}`} prompt={prompt} />
      ))}
      <FixedRules fixed={prompts.data.fixed} />
    </div>
  )
}

function PromptEditor({ prompt }: { prompt: PromptInfo }) {
  const client = useQueryClient()
  const [draft, setDraft] = useState(prompt.value)
  const [confirmReset, setConfirmReset] = useState(false)
  const changed = draft !== prompt.value
  const stored = (data: PromptList) => client.setQueryData(keys.adminPrompts, data)

  const save = useMutation({
    mutationFn: () => api.admin.savePrompt(prompt.key, draft),
    onSuccess: (data) => {
      stored(data)
      toast.success(`Đã lưu “${prompt.label}”.`)
    },
    onError: (error) => toast.error(error.message),
  })
  const reset = useMutation({
    mutationFn: () => api.admin.resetPrompt(prompt.key),
    onSuccess: (data) => {
      stored(data)
      toast.success(`“${prompt.label}” đã về bản mặc định.`)
    },
    onError: (error) => toast.error(error.message),
  })

  return (
    <section className="grid gap-3 rounded-xl border p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="flex items-center gap-2 font-medium">
            {prompt.label}
            {prompt.custom
              ? <Badge>Đã chỉnh</Badge>
              : <Badge variant="outline">Mặc định</Badge>}
            {changed && <Badge variant="secondary">Chưa lưu</Badge>}
          </h3>
          <p className="text-sm text-muted-foreground">{prompt.description}</p>
          {prompt.custom && prompt.updated_at && (
            <p className="text-xs text-muted-foreground">
              Sửa lần cuối {new Date(prompt.updated_at * 1000).toLocaleString('vi-VN')}
              {prompt.updated_by && ` bởi ${prompt.updated_by}`}
            </p>
          )}
        </div>
      </div>
      <Textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        maxLength={MAX_LENGTH}
        spellCheck={false}
        aria-label={prompt.label}
        className="field-sizing-fixed h-80 resize-y font-mono text-[13px] leading-relaxed"
      />
      <div className="flex flex-wrap items-center gap-2">
        <span className={cn('text-xs text-muted-foreground', draft.length > MAX_LENGTH * 0.9 && 'text-destructive')}>
          {draft.length.toLocaleString('vi-VN')}/{MAX_LENGTH.toLocaleString('vi-VN')} ký tự
        </span>
        <div className="ml-auto flex flex-wrap gap-2">
          {prompt.custom && (
            <Button variant="ghost" size="sm" onClick={() => setConfirmReset(true)} disabled={reset.isPending}>
              <RotateCcw /> Khôi phục mặc định
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => setDraft(prompt.value)} disabled={!changed}>
            <Undo2 /> Hoàn tác
          </Button>
          <Button size="sm" onClick={() => save.mutate()} disabled={!changed || !draft.trim() || save.isPending}>
            {save.isPending ? <Loader2 className="animate-spin" /> : <Save />} Lưu
          </Button>
        </div>
      </div>

      <AlertDialog open={confirmReset} onOpenChange={setConfirmReset}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Khôi phục “{prompt.label}” về mặc định?</AlertDialogTitle>
            <AlertDialogDescription>
              Bản đã chỉnh sẽ bị bỏ, và trợ giảng dùng lại prompt gốc của ứng dụng (kể cả khi bản gốc được cập nhật sau này).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Hủy</AlertDialogCancel>
            <AlertDialogAction onClick={() => reset.mutate()}>Khôi phục</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  )
}

function FixedRules({ fixed }: { fixed: PromptList['fixed'] }) {
  const [open, setOpen] = useState(false)
  return (
    <Collapsible open={open} onOpenChange={setOpen} className="rounded-xl border bg-muted/30">
      <CollapsibleTrigger className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left">
        <span>
          <span className="font-medium">Phần cố định</span>
          <span className="block text-sm text-muted-foreground">
            Luôn được thêm vào cuối prompt ở chế độ Gợi ý và không chỉnh được: giữ trợ giảng không đưa đáp án, và
            cho ứng dụng biết học sinh đã tiến tới bậc nào.
          </span>
        </span>
        <ChevronDown className={cn('size-4 shrink-0 transition-transform', open && 'rotate-180')} />
      </CollapsibleTrigger>
      <CollapsibleContent className="grid gap-3 px-4 pb-4">
        {fixed.map((rule) => (
          <div key={rule.label} className="grid gap-1">
            <p className="text-sm font-medium">{rule.label}</p>
            <pre className="overflow-x-auto rounded-lg border bg-background p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap">
              {rule.text}
            </pre>
          </div>
        ))}
      </CollapsibleContent>
    </Collapsible>
  )
}

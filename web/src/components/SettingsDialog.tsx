import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, Loader2 } from 'lucide-react'
import { useState } from 'react'
import Markdown from 'react-markdown'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { api, type Settings } from '@/lib/api'
import { keys, useHelp, useMe, useSettings } from '@/lib/queries'

const QUALITY_LABELS: Record<Settings['quality'], string> = {
  l: 'Thấp — nhanh nhất',
  m: 'Vừa',
  h: 'Cao — chậm hơn',
}

export function SettingsDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const client = useQueryClient()
  const me = useMe()
  const saved = useSettings()
  const help = useHelp()
  // Unsaved edits; null means "show what is saved". Cleared whenever the dialog closes.
  const [edits, setEdits] = useState<Settings | null>(null)
  const aiAvailable = me.data?.ai_available ?? true
  // Without a server key, AI mode cannot run: preselect the parser instead.
  const stored = saved.data && !aiAvailable ? { ...saved.data, mode: 'parser' as const } : saved.data
  const draft = edits ?? stored ?? null
  const close = (next: boolean) => {
    if (!next) setEdits(null)
    onOpenChange(next)
  }

  const save = useMutation({
    mutationFn: api.saveSettings,
    onSuccess: (settings) => {
      client.setQueryData(keys.settings, settings)
      toast.success('Đã lưu cài đặt.')
      close(false)
    },
    onError: (error) => toast.error(error.message),
  })

  const quota = me.data?.quota
  const set = (patch: Partial<Settings>) => draft && setEdits({ ...draft, ...patch })

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Cài đặt</DialogTitle>
          <DialogDescription>Áp dụng cho các lượt vẽ tiếp theo.</DialogDescription>
        </DialogHeader>
        {!draft ? (
          <div className="flex justify-center py-8"><Loader2 className="animate-spin text-muted-foreground" /></div>
        ) : (
          <div className="grid gap-5">
            <div className="grid gap-2">
              <Label>Cách dựng hình</Label>
              <RadioGroup value={draft.mode} onValueChange={(mode) => set({ mode: mode as Settings['mode'] })}>
                <label className="flex items-start gap-3 rounded-lg border p-3 has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                  <RadioGroupItem value="ai" disabled={!aiAvailable} className="mt-0.5" />
                  <span className="grid gap-0.5">
                    <span className="text-sm font-medium">DeepSeek AI</span>
                    <span className="text-xs text-muted-foreground">
                      {aiAvailable
                        ? `Hiểu đề phức tạp và đọc được đề từ ảnh.${quota ? ` Hôm nay đã dùng ${quota.used}/${quota.limit} lượt.` : ''}`
                        : 'Máy chủ chưa cấu hình DeepSeek API key.'}
                    </span>
                  </span>
                </label>
                <label className="flex items-start gap-3 rounded-lg border p-3 has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                  <RadioGroupItem value="parser" className="mt-0.5" />
                  <span className="grid gap-0.5">
                    <span className="text-sm font-medium">Parser nhanh</span>
                    <span className="text-xs text-muted-foreground">
                      Chạy trên máy chủ, không tốn lượt AI; chỉ hiểu các mẫu cơ bản.
                    </span>
                  </span>
                </label>
              </RadioGroup>
            </div>

            {draft.mode === 'ai' && (
              <div className="grid gap-2">
                <Label>Mô hình DeepSeek</Label>
                <Select value={draft.model} onValueChange={(model) => set({ model: model as Settings['model'] })}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="deepseek-v4-flash">deepseek-v4-flash — nhanh, hợp đa số đề</SelectItem>
                    <SelectItem value="deepseek-v4-pro">deepseek-v4-pro — ưu tiên chất lượng</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label>Chất lượng hình</Label>
                <Select value={draft.quality} onValueChange={(quality) => set({ quality: quality as Settings['quality'] })}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {(Object.keys(QUALITY_LABELS) as Settings['quality'][]).map((value) => (
                      <SelectItem key={value} value={value}>{QUALITY_LABELS[value]}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="animate">Video hoạt hình</Label>
                <div className="flex h-8 items-center gap-2">
                  <Switch id="animate" checked={draft.animate} onCheckedChange={(animate) => set({ animate })} />
                  <span className="text-xs text-muted-foreground">Chậm hơn ảnh tĩnh</span>
                </div>
              </div>
            </div>

            <Collapsible>
              <CollapsibleTrigger className="group flex w-full items-center justify-between rounded-lg border px-3 py-2 text-sm font-medium">
                Quy ước hình học THCS
                <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
              </CollapsibleTrigger>
              <CollapsibleContent className="prose-sm mt-2 max-h-56 overflow-y-auto rounded-lg bg-muted/50 px-4 py-3 text-sm [&_li]:ml-4 [&_li]:list-disc [&_li]:py-0.5">
                <Markdown>{help.data?.markdown ?? ''}</Markdown>
              </CollapsibleContent>
            </Collapsible>
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => close(false)}>Hủy</Button>
          <Button disabled={!draft || save.isPending} onClick={() => draft && save.mutate(draft)}>
            {save.isPending && <Loader2 className="animate-spin" />}
            Lưu
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

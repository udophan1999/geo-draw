import { BookOpenCheck, Lightbulb, PenTool, Sparkles } from 'lucide-react'
import { useState } from 'react'

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { Conversation, TutorAction } from '@/lib/api'
import { cn } from '@/lib/utils'

// Same order as geo_draw/tutor_prompts.py HINT_LEVELS.
const HINT_LEVELS = ['Hiểu đề', 'Nhớ kiến thức', 'Chiến lược', 'Bước đầu tiên', 'Sâu hơn nữa']

type Props = {
  conversation: Conversation
  busy: boolean
  onAction: (action: TutorAction) => void
  /** Shown when the conversation has no figure yet. */
  onDrawFigure?: () => void
  drawing: boolean
}

export function TutorBar({ conversation, busy, onAction, onDrawFigure, drawing }: Props) {
  const [confirmSolution, setConfirmSolution] = useState(false)
  const solution = conversation.mode === 'solution'
  const level = Math.min(Math.max(conversation.hint_level, 1), HINT_LEVELS.length)

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-wrap items-center gap-2 px-4 pb-2">
      <div className="flex rounded-lg border bg-muted/50 p-0.5" role="group" aria-label="Cách trợ giảng">
        <button
          type="button"
          disabled={busy}
          onClick={() => solution && onAction('hint')}
          className={cn('flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition',
                        !solution ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground')}
        >
          <Lightbulb className="size-3.5" /> Gợi ý
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => !solution && setConfirmSolution(true)}
          className={cn('flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition',
                        solution ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground')}
        >
          <BookOpenCheck className="size-3.5" /> Lời giải chi tiết
        </button>
      </div>

      {!solution && (
        <>
          <Badge variant="outline" className="font-normal" title="Bậc gợi ý hiện tại">
            Bậc {level}/{HINT_LEVELS.length} · {HINT_LEVELS[level - 1]}
          </Badge>
          <Button variant="outline" size="xs" disabled={busy || level >= HINT_LEVELS.length} onClick={() => onAction('deeper')}>
            <Sparkles /> Gợi ý sâu hơn
          </Button>
        </>
      )}

      {onDrawFigure && (
        <Button variant="ghost" size="xs" className="ml-auto" disabled={drawing} onClick={onDrawFigure}>
          <PenTool /> {drawing ? 'Đang vẽ…' : 'Vẽ hình'}
        </Button>
      )}

      <AlertDialog open={confirmSolution} onOpenChange={setConfirmSolution}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xem lời giải chi tiết?</AlertDialogTitle>
            <AlertDialogDescription>
              Tự nghĩ ra lời giải sẽ giúp nhớ lâu hơn. Nếu đã thử mà vẫn bí, hoặc muốn đối chiếu bài làm, hãy xem lời
              giải đầy đủ. Bạn có thể quay lại chế độ gợi ý bất cứ lúc nào.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Tiếp tục tự làm</AlertDialogCancel>
            <AlertDialogAction onClick={() => onAction('solution')}>Xem lời giải</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

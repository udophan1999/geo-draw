import { BookOpenCheck, CircleCheck, Lightbulb, Sparkles } from 'lucide-react'
import { useState } from 'react'

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import type { Conversation, TutorAction } from '@/lib/api'
import { HINT_LEVELS } from '@/lib/hintLevels'
import { cn } from '@/lib/utils'


type Props = {
  conversation: Conversation
  busy: boolean
  onAction: (action: TutorAction) => void
}

/** The strip on top of the message box: hint/solution switch, hint level, "Gợi ý sâu hơn". */
export function TutorBar({ conversation, busy, onAction }: Props) {
  const [confirmSolution, setConfirmSolution] = useState(false)
  const solution = conversation.mode === 'solution'
  const level = Math.min(Math.max(conversation.hint_level, 1), HINT_LEVELS.length)
  // The tutor moves the level as the student progresses, and reports when the answer is found.
  const solved = conversation.solved
  const modeButton = (active: boolean) =>
    cn('flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium transition disabled:opacity-60',
       active ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground')

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 border-b bg-muted/40 px-2.5 py-1.5">
      <div className="flex rounded-lg bg-muted p-0.5" role="group" aria-label="Cách trợ giảng">
        <button type="button" disabled={busy} className={modeButton(!solution)}
                onClick={() => solution && onAction('hint')}>
          <Lightbulb className="size-3.5" /> Gợi ý
        </button>
        <button type="button" disabled={busy} className={modeButton(solution)}
                onClick={() => !solution && setConfirmSolution(true)}>
          <BookOpenCheck className="size-3.5" /> Lời giải chi tiết
        </button>
      </div>

      {solution ? (
        <span className="ml-auto text-xs text-muted-foreground">Đang xem lời giải đầy đủ</span>
      ) : solved ? (
        <span className="ml-auto flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
          <span className="flex gap-0.5" aria-hidden="true">
            {HINT_LEVELS.map((name) => <span key={name} className="h-1.5 w-3 rounded-full bg-emerald-500" />)}
          </span>
          <CircleCheck className="size-3.5" /> Đã giải xong
        </span>
      ) : (
        <div className="ml-auto flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground"
               title={`Bậc gợi ý ${level}/${HINT_LEVELS.length}`} aria-label={`Bậc ${level}/${HINT_LEVELS.length}: ${HINT_LEVELS[level - 1]}`}>
            <span className="flex gap-0.5" aria-hidden="true">
              {HINT_LEVELS.map((name, i) => (
                <span key={name} className={cn('h-1.5 w-3 rounded-full', i < level ? 'bg-primary' : 'bg-muted-foreground/20')} />
              ))}
            </span>
            {HINT_LEVELS[level - 1]}
          </div>
          <Button variant="ghost" size="xs" className="text-primary hover:text-primary"
                  disabled={busy || level >= HINT_LEVELS.length} onClick={() => onAction('deeper')}>
            <Sparkles /> Gợi ý sâu hơn
          </Button>
        </div>
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

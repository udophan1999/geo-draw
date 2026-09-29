// Markdown with math: $…$ inline and $$…$$ display formulas, rendered by KaTeX.
import 'katex/dist/katex.min.css'
import Markdown from 'react-markdown'
import rehypeKatex from 'rehype-katex'
import remarkMath from 'remark-math'

import { cn } from '@/lib/utils'

export function MathMarkdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn('prose-chat', className)}>
      <Markdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
      >
        {children}
      </Markdown>
    </div>
  )
}

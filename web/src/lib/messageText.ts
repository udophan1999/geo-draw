// The composer edits a ProseMirror document (text, line breaks and inline formulas). Messages
// are plain text with $LaTeX$ formulas, which MathMarkdown renders everywhere else.
import type { Node } from '@tiptap/pm/model'

export function toMessageText(doc: Node): string {
  const lines: string[] = []
  doc.forEach((block) => {
    let line = ''
    block.forEach((child) => {
      if (child.type.name === 'inlineMath') line += `$${child.attrs.latex}$`
      else if (child.type.name === 'hardBreak') line += '\n'
      else line += child.text ?? ''
    })
    lines.push(line)
  })
  return lines.join('\n')
}

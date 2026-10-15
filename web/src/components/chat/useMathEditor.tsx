// The message editor shared by the composer and by "Sửa" on a sent message: text with inline
// formulas rendered by KaTeX (Notion-style). `$x^2$` typed or pasted becomes a formula, a
// click on one opens the formula dialog, and the text out is the message format ($latex$).
import 'katex/dist/katex.min.css'
import { InputRule, PasteRule, type JSONContent } from '@tiptap/core'
import Document from '@tiptap/extension-document'
import HardBreak from '@tiptap/extension-hard-break'
import { InlineMath } from '@tiptap/extension-mathematics'
import Paragraph from '@tiptap/extension-paragraph'
import Text from '@tiptap/extension-text'
import { Placeholder, UndoRedo } from '@tiptap/extensions'
import { Fragment, type Node } from '@tiptap/pm/model'
import { TextSelection } from '@tiptap/pm/state'
import { useEditor } from '@tiptap/react'
import { useLayoutEffect, useRef, useState } from 'react'

import { FormulaDialog } from '@/components/chat/MathInput'
import { acceptImage } from '@/lib/images'
import { latexToPlain } from '@/lib/plainMath'

// The extension itself turns `$$x^2$$` into a formula. A `$` right after a letter, digit or
// `\` is left alone ("5$"), and so is `$ … $` with a space inside the opening sign.
const TYPED_FORMULA = /(^|[^$\\\w])\$([^$\s][^$\n]*?)\$$/
const PASTED_FORMULA = /(^|[^$\\\w])\$([^$\s][^$\n]*?)\$(?!\$)/g
const MESSAGE_FORMULA = /\$\$([^$]+?)\$\$|\$([^$\n]+?)\$/g

/** Placeholder text per editor: the extension is configured once, the text follows the page. */
const placeholders = new WeakMap<object, string>()

/** A formula opened in the dialog; ``pos`` is null for a new one. */
type Editing = { latex: string; pos: number | null }

/** A message (text with $latex$) as editor content, formulas as chips. */
export function fromMessageText(text: string): JSONContent {
  const content: JSONContent[] = []
  text.split('\n').forEach((line, index) => {
    if (index > 0) content.push({ type: 'hardBreak' })
    let last = 0
    for (const match of line.matchAll(MESSAGE_FORMULA)) {
      if (match.index > last) content.push({ type: 'text', text: line.slice(last, match.index) })
      content.push({ type: 'inlineMath', attrs: { latex: (match[1] ?? match[2]).trim() } })
      last = match.index + match[0].length
    }
    if (last < line.length) content.push({ type: 'text', text: line.slice(last) })
  })
  return { type: 'doc', content: [{ type: 'paragraph', content }] }
}

type Options = {
  label: string
  placeholder: string
  className: string
  /** A message to start from (editing a sent message). */
  initialText?: string
  onSubmit: () => void
  onImage?: (file: File | null) => void
  onEscape?: () => void
}

export function useMathEditor({ label, placeholder, className, initialText, onSubmit, onImage, onEscape }: Options) {
  const [empty, setEmpty] = useState(!initialText?.trim())
  const [editing, setEditing] = useState<Editing | null>(null)
  // The editor is built once; its handlers read the current callbacks from here.
  const latest = useRef({ onSubmit, onImage, onEscape })
  useLayoutEffect(() => {
    latest.current = { onSubmit, onImage, onEscape }
  })

  const editor = useEditor({
    content: initialText ? fromMessageText(initialText) : undefined,
    extensions: [
      Document, Paragraph, Text, HardBreak, UndoRedo,
      Placeholder.configure({ placeholder: ({ editor }) => placeholders.get(editor) ?? '' }),
      InlineMath.extend({
        addInputRules() {
          return [new InputRule({
            find: TYPED_FORMULA,
            handler: ({ state, range, match }) => {
              const start = range.from + match[1].length
              state.tr.replaceWith(start, range.to, this.type.create({ latex: match[2] }))
            },
          }), ...(this.parent?.() ?? [])]
        },
        addPasteRules() {
          return [new PasteRule({
            find: PASTED_FORMULA,
            handler: ({ state, range, match }) => {
              const start = range.from + (match[1] ?? '').length
              state.tr.replaceWith(start, range.to, this.type.create({ latex: match[2] }))
            },
          })]
        },
      }).configure({
        katexOptions: { throwOnError: false, strict: false },
        onClick: (node: Node, pos: number) => setEditing({ latex: node.attrs.latex, pos }),
      }),
    ],
    editorProps: {
      attributes: { role: 'textbox', 'aria-label': label, 'aria-multiline': 'true', class: `composer-editor ${className}` },
      handleDOMEvents: {
        // Enter sends, Shift+Enter breaks the line. Handled before ProseMirror's own keydown:
        // on iOS it turns every Enter (Shift too) into a plain one, and on Android it let the
        // browser add a second line break. Vietnamese IMEs compose with Enter too: leave those.
        keydown: (view, event) => {
          if (event.key === 'Escape' && latest.current.onEscape) {
            latest.current.onEscape()
            return true
          }
          if (event.key !== 'Enter' || event.isComposing || view.composing) return false
          event.preventDefault()
          if (event.shiftKey) {
            view.dispatch(view.state.tr.replaceSelectionWith(view.state.schema.nodes.hardBreak.create()).scrollIntoView())
          } else latest.current.onSubmit()
          return true
        },
      },
      // Soft keyboards that report Enter only through the text they change (keyCode 229)
      // reach here instead, as a plain Enter.
      handleKeyDown: (view, event) => {
        if (event.key !== 'Enter' || event.shiftKey || event.isComposing || view.composing) return false
        latest.current.onSubmit()
        return true
      },
      handlePaste: (_view, event) => {
        const file = Array.from(event.clipboardData?.files ?? []).find((f) => f.type.startsWith('image/'))
        if (!file || !latest.current.onImage) return false
        latest.current.onImage(acceptImage(file))
        return true
      },
      // A dropped image goes to the drop zone of the chat page, not into the text.
      handleDrop: (_view, event) => Boolean(event.dataTransfer?.files.length),
    },
    onUpdate: ({ editor }) => setEmpty(editor.isEmpty),
  })

  // The placeholder changes with the page (first message vs. reply): redraw it.
  useLayoutEffect(() => {
    if (!editor || editor.isDestroyed) return
    placeholders.set(editor, placeholder)
    editor.view.dispatch(editor.state.tr)
  }, [editor, placeholder])

  /** Put ``snippet`` at the caret (replacing any selection) and keep typing after it. */
  const insertText = (snippet: string) => {
    editor?.chain().focus().command(({ tr }) => {
      tr.insertText(snippet)
      return true
    }).run()
  }

  /** A formula from the dialog: plain Unicode when it can be, else a formula chip. */
  const insertFormula = (latex: string) => {
    if (!editor) return
    if (editing?.pos != null) {
      editor.chain().focus().updateInlineMath({ latex, pos: editing.pos }).run()
      return
    }
    const plain = latexToPlain(latex)
    editor.chain().focus().command(({ tr, state }) => {
      const { from, to } = tr.selection
      // A formula is a word of its own: keep it apart from the text around it.
      const $from = state.doc.resolve(from)
      const $to = state.doc.resolve(to)
      const before = $from.parent.textBetween(Math.max($from.parentOffset - 1, 0), $from.parentOffset, '\n', 'x')
      const after = $to.parent.textBetween($to.parentOffset, Math.min($to.parentOffset + 1, $to.parent.content.size), '\n', 'x')
      const nodes = [
        ...(before && !/\s/.test(before) ? [state.schema.text(' ')] : []),
        plain === null ? state.schema.nodes.inlineMath.create({ latex }) : state.schema.text(plain),
        ...(/^\s/.test(after) ? [] : [state.schema.text(' ')]),
      ]
      const fragment = Fragment.from(nodes)
      tr.replaceWith(from, to, fragment)
      tr.setSelection(TextSelection.create(tr.doc, from + fragment.size))
      return true
    }).run()
  }

  const formulaDialog = (
    <FormulaDialog
      open={editing !== null}
      initialLatex={editing?.latex ?? ''}
      editingExisting={editing?.pos != null}
      onOpenChange={(open) => !open && setEditing(null)}
      onInsert={insertFormula}
    />
  )

  return { editor, empty, insertText, openFormula: () => setEditing({ latex: '', pos: null }), formulaDialog }
}

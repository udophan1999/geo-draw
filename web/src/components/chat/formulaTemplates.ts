// Templates for the formula editor, in the spirit of Word's equation gallery.
// In `latex`, `#?` is an empty slot to fill in and `#@` takes the current selection (or the
// term just before the caret), as MathLive's insert() understands them.

import groups from '@shared/formula_templates.json'

export type FormulaTemplate = { label: string; latex: string }
export type FormulaGroup = { id: string; name: string; wide?: boolean; items: FormulaTemplate[] }

// The templates themselves live in shared/formula_templates.json, which the iOS app reads too.
export const FORMULA_GROUPS: FormulaGroup[] = groups

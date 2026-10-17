// The math text helpers against shared/fixtures/math_cases.json, the cases the iOS app's
// ports (MathNormalizer, LatexToPlain, MessageTextCodec) must pass too. No browser needed.
import { expect, test } from '@playwright/test'
import type { Node } from '@tiptap/pm/model'

import cases from '../../shared/fixtures/math_cases.json' with { type: 'json' }
import { normalizeMath } from '../src/lib/math'
import { toMessageText } from '../src/lib/messageText'
import { latexToPlain } from '../src/lib/plainMath'

type Piece = { text?: string; math?: string; break?: boolean }

// Just enough of a ProseMirror document for toMessageText: paragraphs of text, inline
// formulas and line breaks.
function doc(blocks: Piece[][]): Node {
  const child = (piece: Piece) =>
    piece.math !== undefined ? { type: { name: 'inlineMath' }, attrs: { latex: piece.math } }
      : piece.break ? { type: { name: 'hardBreak' } }
        : { type: { name: 'text' }, text: piece.text }
  const block = (pieces: Piece[]) => ({ forEach: (f: (n: unknown) => void) => pieces.map(child).forEach(f) })
  return { forEach: (f: (n: unknown) => void) => blocks.map(block).forEach(f) } as unknown as Node
}

// Pure functions: one project is enough.
test.beforeEach(() => test.skip(test.info().project.name !== 'desktop', 'chạy một lần là đủ'))

test('normalizeMath theo shared fixtures', () => {
  for (const { input, expected } of cases.normalizeMath) expect(normalizeMath(input), input).toBe(expected)
})

test('latexToPlain theo shared fixtures', () => {
  for (const { input, expected } of cases.latexToPlain) expect(latexToPlain(input), input).toBe(expected)
})

test('toMessageText theo shared fixtures', () => {
  for (const { blocks, expected } of cases.toMessageText) {
    expect(toMessageText(doc(blocks as Piece[][])), JSON.stringify(blocks)).toBe(expected)
  }
})

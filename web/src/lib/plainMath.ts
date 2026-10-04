// Turn simple LaTeX from the formula editor into plain Unicode ("BC^2=AB^2+AC^2" ->
// "BC²=AB²+AC²"), so the message box shows readable text instead of $…$ source. Anything
// Unicode cannot write cleanly (fractions, roots of long expressions…) returns null and is
// kept as $LaTeX$ (the composer then shows a rendered preview).

const SUPERSCRIPT: Record<string, string> = {
  '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
  '+': '⁺', '-': '⁻', '(': '⁽', ')': '⁾', n: 'ⁿ', x: 'ˣ',
}
const SUBSCRIPT: Record<string, string> = {
  '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
  '+': '₊', '-': '₋', n: 'ₙ',
}
const COMMANDS: Record<string, string> = {
  cdot: '·', times: '×', div: '÷', le: '≤', leq: '≤', ge: '≥', geq: '≥', ne: '≠', neq: '≠',
  pm: '±', approx: '≈', pi: 'π', angle: '∠', widehat: '∠', triangle: '△', perp: '⊥', parallel: '∥',
  alpha: 'α', beta: 'β', gamma: 'γ', Delta: 'Δ', delta: 'δ', infty: '∞', Rightarrow: '⇒',
  Leftrightarrow: '⇔', in: '∈', notin: '∉', subset: '⊂', cup: '∪', cap: '∩', emptyset: '∅',
  varnothing: '∅', sim: '∽', circ: '°', degree: '°', left: '', right: '',
}

function script(body: string, table: Record<string, string>): string | null {
  const chars = [...body]
  return chars.every((c) => table[c]) ? chars.map((c) => table[c]).join('') : null
}

export function latexToPlain(latex: string): string | null {
  let text = latex
    .replace(/\\(?:,|;|:|!|\s)/g, ' ') // spacing commands
    .replace(/\^\{?\\circ\}?/g, '°')
    .replace(/\\(?:text|mathrm)\{([^{}]*)\}/g, '$1')
  // \sqrt{x} with a short plain body: √x (√(…) for longer ones would read ambiguously).
  text = text.replace(/\\sqrt\{([A-Za-z0-9]{1,3})\}/g, '√$1')
  text = text.replace(/\\widehat\{([A-Za-z]{1,3})\}/g, '∠$1') // "góc A"
  // A space after a command only ends its name in LaTeX ("\perp BC"): drop it.
  text = text.replace(/\\([A-Za-z]+) ?/g, (whole, name: string) =>
    name in COMMANDS ? COMMANDS[name] : whole)
  let failed = false
  text = text.replace(/([\^_])(?:\{([^{}]*)\}|(.))/g, (_, mark: string, group?: string, single?: string) => {
    const converted = script(group ?? single ?? '', mark === '^' ? SUPERSCRIPT : SUBSCRIPT)
    if (converted === null) failed = true
    return converted ?? ''
  })
  if (failed || /[\\{}^_]/.test(text)) return null
  return text.replace(/\s+/g, ' ').trim()
}

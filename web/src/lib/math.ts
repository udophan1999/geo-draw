// Make model-written math safe for remark-math + KaTeX. DeepSeek often writes:
// - $$…$$ in the middle of a sentence: remark-math then renders it inline, where
//   \tag and other display-only commands fail (red source text);
// - \[…\] and \(…\), which remark-math does not recognise at all.
// Code spans and fenced code blocks are left untouched.

const CODE = /(```[\s\S]*?```|`[^`\n]*`)/g

function fixMath(text: string): string {
  return text
    .replace(/\\\[([\s\S]+?)\\\]/g, (_, body: string) => `\n\n$$\n${body.trim()}\n$$\n\n`)
    .replace(/\\\(([\s\S]+?)\\\)/g, (_, body: string) => `$${body.trim()}$`)
    .replace(/\$\$([\s\S]+?)\$\$/g, (_, body: string) => `\n\n$$\n${body.trim()}\n$$\n\n`)
    .replace(/\\tag\*?\{([^}]*)\}/g, (_, label: string) => `\\qquad (${label})`)
    .replace(/\n{3,}/g, '\n\n')
}

export function normalizeMath(text: string): string {
  return text
    .split(CODE)
    .map((part, i) => (i % 2 === 1 ? part : fixMath(part)))
    .join('')
    .trim()
}

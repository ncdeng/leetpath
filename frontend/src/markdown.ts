import DOMPurify from 'dompurify'
import { marked } from 'marked'
import markedKatex from 'marked-katex-extension'

marked.use(
  markedKatex({
    throwOnError: false,
    output: 'htmlAndMathml',
  }),
)

// 题面 / 题解 / AI 回复都走这里；外链必须带 noopener，避免 tabnabbing。
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName !== 'A' || !node.hasAttribute('href')) return
  node.setAttribute('rel', 'noopener noreferrer')
})

export function filterSolutionMarkdown(markdown: string, lang: 'python3' | 'cpp'): string {
  if (!markdown) return ''
  
  const hasPy = /###\s*Python/i.test(markdown)
  const hasCpp = /###\s*C\+\+/i.test(markdown)
  
  if (!hasPy || !hasCpp) return markdown

  // 提取公共部分（思路与复杂度）
  const parts = markdown.split(/###\s*(Python|C\+\+)/i)
  const basePart = parts[0] || ''

  // 提取 Python 代码段
  const pyMatch = markdown.match(/(###\s*Python[\s\S]*?)(?=(?:###\s*C\+\+)|$)/i)
  // 提取 C++ 代码段
  const cppMatch = markdown.match(/(###\s*C\+\+[\s\S]*?)(?=(?:###\s*Python)|$)/i)

  if (lang === 'python3' && pyMatch) {
    return `${basePart.trim()}\n\n${pyMatch[1].trim()}`
  } else if (lang === 'cpp' && cppMatch) {
    return `${basePart.trim()}\n\n${cppMatch[1].trim()}`
  }

  return markdown
}

export function renderMarkdown(source: string): string {
  if (!source) return ''
  const rawHtml = marked.parse(source, { async: false }) as string
  return DOMPurify.sanitize(rawHtml, {
    ADD_TAGS: [
      'math',
      'semantics',
      'mrow',
      'mi',
      'mo',
      'mn',
      'msup',
      'msub',
      'msubsup',
      'mfrac',
      'mover',
      'munder',
      'munderover',
      'mtable',
      'mtr',
      'mtd',
      'annotation',
      'span',
      'svg',
      'path',
      'line',
    ],
    ADD_ATTR: [
      'xmlns',
      'display',
      'aria-hidden',
      'viewBox',
      'd',
      'fill',
      'stroke',
      'class',
      'style',
      'target',
      'rel',
    ],
  })
}

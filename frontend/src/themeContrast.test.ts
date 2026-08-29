import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { describe, it } from 'node:test'

import { THEME_LIST } from './theme.ts'

const css = readFileSync(new URL('./styles/base.css', import.meta.url), 'utf8')

function themeBlock(theme: string): string {
  const selector = theme === 'paper'
    ? ':root,\\s*:root\\[data-theme="paper"\\]'
    : `:root\\[data-theme="${theme}"\\]`
  const match = css.match(new RegExp(`${selector}\\s*\\{([\\s\\S]*?)\\}`))
  assert.ok(match, `missing CSS variable block for theme ${theme}`)
  return match[1]
}

function token(block: string, name: string): string {
  const match = block.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})\\s*;`))
  assert.ok(match, `missing six-digit hex token --${name}`)
  return match[1]
}

function relativeLuminance(hex: string): number {
  const channels = [1, 3, 5].map((index) => Number.parseInt(hex.slice(index, index + 2), 16) / 255)
  const linear = channels.map((channel) => (
    channel <= 0.04045
      ? channel / 12.92
      : ((channel + 0.055) / 1.055) ** 2.4
  ))
  return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722
}

function contrastRatio(foreground: string, background: string): number {
  const a = relativeLuminance(foreground)
  const b = relativeLuminance(background)
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)
}

describe('accent foreground theme tokens', () => {
  it('keep normal and hover text at WCAG AA contrast in every theme', () => {
    for (const { id } of THEME_LIST) {
      const block = themeBlock(id)
      const normal = contrastRatio(token(block, 'on-accent'), token(block, 'accent'))
      const hover = contrastRatio(token(block, 'on-accent-hover'), token(block, 'accent-hover'))

      assert.ok(normal >= 4.5, `${id} normal contrast ${normal.toFixed(2)} is below 4.5`)
      assert.ok(hover >= 4.5, `${id} hover contrast ${hover.toFixed(2)} is below 4.5`)
    }
  })
})

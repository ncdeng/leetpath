import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { addDays, diffDays, formatLocalDate, todayLocalDate } from './dates.ts'

describe('local calendar date semantics', () => {
  it('keeps an early-morning local time on the same calendar day', () => {
    assert.equal(formatLocalDate(new Date(2026, 7, 29, 1, 0)), '2026-08-29')
  })

  it('zero-pads single-digit months and days', () => {
    assert.equal(formatLocalDate(new Date(2026, 0, 5, 12, 0)), '2026-01-05')
  })

  it('returns today in the YYYY-MM-DD format', () => {
    assert.match(todayLocalDate(), /^\d{4}-\d{2}-\d{2}$/)
  })

  it('handles cross-month addition and signed differences', () => {
    assert.equal(addDays('2026-08-31', 1), '2026-09-01')
    assert.equal(addDays('2026-09-01', -1), '2026-08-31')
    assert.equal(diffDays('2026-08-31', '2026-09-02'), 2)
    assert.equal(diffDays('2026-09-02', '2026-08-31'), -2)
  })
})

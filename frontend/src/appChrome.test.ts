import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { shouldAutoShowPopupOnce, tabsFadeState } from './appChrome.ts'

describe('shouldAutoShowPopupOnce', () => {
  it('allows the first popup for a local calendar day', () => {
    assert.equal(shouldAutoShowPopupOnce(null, '2026-08-29'), true)
  })

  it('blocks a repeated popup on the same local calendar day', () => {
    assert.equal(shouldAutoShowPopupOnce('2026-08-29', '2026-08-29'), false)
  })

  it('allows the popup after the local calendar day changes', () => {
    assert.equal(shouldAutoShowPopupOnce('2026-08-28', '2026-08-29'), true)
  })
})

describe('tabsFadeState', () => {
  it('covers no-overflow, left-edge, middle, and right-edge states', () => {
    assert.deepEqual(tabsFadeState({ scrollLeft: 0, clientWidth: 320, scrollWidth: 320 }), {
      left: false,
      right: false,
    })
    assert.deepEqual(tabsFadeState({ scrollLeft: 0, clientWidth: 320, scrollWidth: 560 }), {
      left: false,
      right: true,
    })
    assert.deepEqual(tabsFadeState({ scrollLeft: 80, clientWidth: 320, scrollWidth: 560 }), {
      left: true,
      right: true,
    })
    assert.deepEqual(tabsFadeState({ scrollLeft: 240, clientWidth: 320, scrollWidth: 560 }), {
      left: true,
      right: false,
    })
  })
})

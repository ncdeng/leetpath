import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import {
  AI_LAUNCHER_GAP_PX,
  AI_LAUNCHER_POS_KEY,
  BOTTOM_NAV_BAR_PX,
  CAPSULE_FALLBACK_SIZE,
  createDragSession,
  defaultCapsulePoint,
  dragSessionMove,
  exceededDragThreshold,
  isMobileWidth,
  loadLauncherChrome,
  parseCssPx,
  parseLauncherChrome,
  saveLauncherChrome,
  bottomClearancePx,
  clampPoint,
} from './aiLauncherChrome.ts'

const IPHONE = { width: 390, height: 844 }
const DESKTOP = { width: 1440, height: 900 }

describe('bottomClearancePx', () => {
  it('parks above the 56px tab bar + iOS safe area + gap on iPhone widths', () => {
    const safe = 34
    const clearance = bottomClearancePx({ viewportWidth: IPHONE.width, safeAreaBottom: safe })
    assert.equal(clearance, BOTTOM_NAV_BAR_PX + safe + AI_LAUNCHER_GAP_PX)
  })

  it('uses a desktop inset when the bottom nav is hidden', () => {
    assert.equal(bottomClearancePx({ viewportWidth: DESKTOP.width, safeAreaBottom: 34 }), 28)
  })

  it('prefers measured --bottom-nav-h when provided', () => {
    assert.equal(
      bottomClearancePx({ viewportWidth: 390, safeAreaBottom: 0, navHeight: 90 }),
      90 + AI_LAUNCHER_GAP_PX,
    )
  })
})

describe('isMobileWidth', () => {
  it('matches the <768px iPhone breakpoint', () => {
    assert.equal(isMobileWidth(390), true)
    assert.equal(isMobileWidth(767), true)
    assert.equal(isMobileWidth(768), false)
  })
})

describe('defaultCapsulePoint', () => {
  it('sits above the bottom nav on <768px so 背题/手册 stay tappable', () => {
    const pos = defaultCapsulePoint(IPHONE, CAPSULE_FALLBACK_SIZE, { safeAreaBottom: 34 })
    const pillBottom = pos.y + CAPSULE_FALLBACK_SIZE.height
    const navTop = IPHONE.height - (BOTTOM_NAV_BAR_PX + 34)
    assert.ok(pillBottom <= navTop - AI_LAUNCHER_GAP_PX + 0.01, `pillBottom=${pillBottom} navTop=${navTop}`)
  })

  it('does not cover a problem card that ends at body+container padding', () => {
    // styles.css @ 1023px: body padding-bottom 62+safe, .container padding-bottom 54
    const safe = 34
    const cardBottom = IPHONE.height - (62 + safe + 54)
    const pos = defaultCapsulePoint(IPHONE, CAPSULE_FALLBACK_SIZE, { safeAreaBottom: safe })
    assert.ok(
      pos.y + 0.5 >= cardBottom,
      `pill top ${pos.y} would overlap card bottom ${cardBottom}`,
    )
  })

  it('stays bottom-right on desktop without a huge bottom reserve', () => {
    const pos = defaultCapsulePoint(DESKTOP, CAPSULE_FALLBACK_SIZE, { safeAreaBottom: 0 })
    assert.ok(pos.x > DESKTOP.width / 2)
    assert.ok(pos.y > DESKTOP.height / 2)
    assert.equal(DESKTOP.height - (pos.y + CAPSULE_FALLBACK_SIZE.height), 28)
  })
})

describe('clampPoint', () => {
  it('keeps a dragged pill above the mobile tab bar', () => {
    const reserve = bottomClearancePx({ viewportWidth: IPHONE.width, safeAreaBottom: 34 })
    const clamped = clampPoint(
      { x: 300, y: 820 },
      IPHONE,
      CAPSULE_FALLBACK_SIZE,
      { bottomReserve: reserve },
    )
    const pillBottom = clamped.y + CAPSULE_FALLBACK_SIZE.height
    const navTop = IPHONE.height - (BOTTOM_NAV_BAR_PX + 34)
    assert.ok(pillBottom <= navTop - AI_LAUNCHER_GAP_PX + 0.01)
    assert.ok(clamped.x >= 8)
  })
})

describe('drag vs tap', () => {
  it('does not treat a finger jitter under 8px as a drag', () => {
    const session = createDragSession(100, 200, { x: 10, y: 20 })
    dragSessionMove(session, 104, 203)
    assert.equal(session.moved, false)
    assert.equal(exceededDragThreshold(4, 3), false)
  })

  it('marks a real drag so the following click must be ignored', () => {
    const session = createDragSession(100, 200, { x: 10, y: 20 })
    const next = dragSessionMove(session, 100, 220)
    assert.equal(session.moved, true)
    assert.equal(next.y, 40)
  })
})

describe('localStorage chrome only', () => {
  it('round-trips capsule/window points and ignores unrelated keys', () => {
    const parsed = parseLauncherChrome(
      JSON.stringify({
        capsule: { x: 12, y: 40 },
        window: { x: 80, y: 60 },
        draft: 'SHOULD_NOT_PERSIST',
        progress: { remembered: true },
      }),
    )
    assert.deepEqual(parsed, {
      capsule: { x: 12, y: 40 },
      window: { x: 80, y: 60 },
    })
  })

  it('writes only chrome keys under leetpath_ai_launcher_pos', () => {
    const store = new Map<string, string>()
    const storage = {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => {
        store.set(k, v)
      },
    }
    saveLauncherChrome(storage, { capsule: { x: 1, y: 2 } })
    saveLauncherChrome(storage, { window: { x: 3, y: 4 } })
    assert.equal(store.size, 1)
    assert.ok(store.has(AI_LAUNCHER_POS_KEY))
    const loaded = loadLauncherChrome(storage)
    assert.deepEqual(loaded, { capsule: { x: 1, y: 2 }, window: { x: 3, y: 4 } })
    assert.equal(JSON.parse(store.get(AI_LAUNCHER_POS_KEY)!).draft, undefined)
  })

  it('tolerates corrupt JSON', () => {
    assert.deepEqual(parseLauncherChrome('{nope'), {})
    assert.deepEqual(loadLauncherChrome(null), {})
  })
})

describe('parseCssPx', () => {
  it('reads computed pixel strings', () => {
    assert.equal(parseCssPx('90px'), 90)
    assert.equal(parseCssPx(' 12.5px '), 12.5)
    assert.equal(parseCssPx(''), 0)
  })
})

/** Chrome-only helpers for the floating AI launcher (position, drag, localStorage). */

export const AI_LAUNCHER_POS_KEY = 'leetpath_ai_launcher_pos'

/** iPhone / small-phone breakpoint from the task (<768px). */
export const MOBILE_MAX_WIDTH = 767

/** Bottom tabs become `display: flex` at this max-width (see styles.css). */
export const BOTTOM_NAV_MAX_WIDTH = 1023

/** Open AI panel becomes a bottom sheet at this max-width. */
export const FLOATING_SHEET_MAX_WIDTH = 768

/** Matches `.bottom-tabs { height: calc(56px + env(safe-area-inset-bottom)) }`. */
export const BOTTOM_NAV_BAR_PX = 56

export const AI_LAUNCHER_GAP_PX = 12
export const DESKTOP_INSET_PX = 28
export const MOBILE_SIDE_INSET_PX = 12
export const DRAG_THRESHOLD_PX = 8
export const EDGE_MIN_PX = 8

export const CAPSULE_FALLBACK_SIZE = { width: 148, height: 44 }
export const WINDOW_FALLBACK_SIZE = { width: 580, height: 740 }

export type Point = { x: number; y: number }
export type Size = { width: number; height: number }
export type Viewport = { width: number; height: number }

export interface LauncherChromeState {
  capsule?: Point
  window?: Point
}

export interface DragSession {
  moved: boolean
  startX: number
  startY: number
  initX: number
  initY: number
}

export function shouldHideCapsule(
  routeMeta: Readonly<{ hasInlineAi?: boolean }>,
  isCompactViewport: boolean,
): boolean {
  return isCompactViewport && routeMeta.hasInlineAi === true
}

export function isMobileWidth(width: number): boolean {
  return width <= MOBILE_MAX_WIDTH
}

export function isBottomNavVisible(width: number): boolean {
  return width <= BOTTOM_NAV_MAX_WIDTH
}

export function isFloatingSheet(width: number): boolean {
  return width <= FLOATING_SHEET_MAX_WIDTH
}

/**
 * Space to keep above the physical bottom of the viewport.
 * On phones this is the tab bar + iOS home indicator + a small gap so 背题/手册 stay tappable.
 */
export function bottomClearancePx(opts: {
  viewportWidth: number
  safeAreaBottom?: number
  navHeight?: number
}): number {
  const safe = Math.max(0, opts.safeAreaBottom ?? 0)
  if (!isBottomNavVisible(opts.viewportWidth)) {
    return DESKTOP_INSET_PX
  }
  const nav = opts.navHeight != null && opts.navHeight > 0
    ? opts.navHeight
    : BOTTOM_NAV_BAR_PX + safe
  return nav + AI_LAUNCHER_GAP_PX
}

/** Default park: bottom-right; on <768px (and whenever the tab bar shows) sit above the nav. */
export function defaultCapsulePoint(
  viewport: Viewport,
  size: Size,
  opts: { safeAreaBottom?: number; navHeight?: number } = {},
): Point {
  const clearance = bottomClearancePx({
    viewportWidth: viewport.width,
    safeAreaBottom: opts.safeAreaBottom,
    navHeight: opts.navHeight,
  })
  const side = isBottomNavVisible(viewport.width) ? MOBILE_SIDE_INSET_PX : DESKTOP_INSET_PX
  return {
    x: Math.max(EDGE_MIN_PX, viewport.width - size.width - side),
    y: Math.max(EDGE_MIN_PX, viewport.height - size.height - clearance),
  }
}

export function clampPoint(
  point: Point,
  viewport: Viewport,
  size: Size,
  opts: { minTop?: number; minLeft?: number; bottomReserve?: number; rightReserve?: number } = {},
): Point {
  const minLeft = opts.minLeft ?? EDGE_MIN_PX
  const minTop = opts.minTop ?? EDGE_MIN_PX
  const bottomReserve = opts.bottomReserve ?? EDGE_MIN_PX
  const rightReserve = opts.rightReserve ?? EDGE_MIN_PX
  const maxX = Math.max(minLeft, viewport.width - size.width - rightReserve)
  const maxY = Math.max(minTop, viewport.height - size.height - bottomReserve)
  return {
    x: Math.min(maxX, Math.max(minLeft, point.x)),
    y: Math.min(maxY, Math.max(minTop, point.y)),
  }
}

export function exceededDragThreshold(
  dx: number,
  dy: number,
  threshold: number = DRAG_THRESHOLD_PX,
): boolean {
  return Math.abs(dx) >= threshold || Math.abs(dy) >= threshold
}

export function createDragSession(clientX: number, clientY: number, origin: Point): DragSession {
  return { moved: false, startX: clientX, startY: clientY, initX: origin.x, initY: origin.y }
}

export function dragSessionMove(
  session: DragSession,
  clientX: number,
  clientY: number,
  threshold: number = DRAG_THRESHOLD_PX,
): Point {
  const dx = clientX - session.startX
  const dy = clientY - session.startY
  if (!session.moved && exceededDragThreshold(dx, dy, threshold)) {
    session.moved = true
  }
  return { x: session.initX + dx, y: session.initY + dy }
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function isPoint(value: unknown): value is Point {
  if (!value || typeof value !== 'object') return false
  const p = value as { x?: unknown; y?: unknown }
  return isFiniteNumber(p.x) && isFiniteNumber(p.y)
}

export function parseCssPx(value: string): number {
  const n = Number.parseFloat(value.trim())
  return Number.isFinite(n) ? n : 0
}

export function parseLauncherChrome(raw: string | null): LauncherChromeState {
  if (!raw) return {}
  try {
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return {}
    const rec = parsed as Record<string, unknown>
    const out: LauncherChromeState = {}
    if (isPoint(rec.capsule)) out.capsule = { x: rec.capsule.x, y: rec.capsule.y }
    if (isPoint(rec.window)) out.window = { x: rec.window.x, y: rec.window.y }
    return out
  } catch {
    return {}
  }
}

export function loadLauncherChrome(storage: Pick<Storage, 'getItem'> | null | undefined): LauncherChromeState {
  if (!storage) return {}
  try {
    return parseLauncherChrome(storage.getItem(AI_LAUNCHER_POS_KEY))
  } catch {
    return {}
  }
}

export function saveLauncherChrome(
  storage: Pick<Storage, 'getItem' | 'setItem'> | null | undefined,
  patch: LauncherChromeState,
): LauncherChromeState {
  const next: LauncherChromeState = { ...loadLauncherChrome(storage), ...patch }
  if (!storage) return next
  try {
    storage.setItem(AI_LAUNCHER_POS_KEY, JSON.stringify(next))
  } catch {
    // Safari private mode / quota: chrome position is optional.
  }
  return next
}

export function rectSize(rect: { width: number; height: number } | null | undefined, fallback: Size): Size {
  if (!rect || rect.width < 8 || rect.height < 8) return fallback
  return { width: rect.width, height: rect.height }
}

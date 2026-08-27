import type { IoMode, Language } from './types'

export interface DraftContext {
  readonly slug: string
  readonly language: Language
  readonly ioMode: IoMode
}

export interface DraftSnapshot extends DraftContext {
  readonly code: string
}

export interface DraftSaveRequest {
  readonly path: string
  readonly body: {
    readonly language: Language
    readonly io_mode: IoMode
    readonly code: string
  }
}

export function createDraftContext(
  slug: string,
  language: Language,
  ioMode: IoMode,
): Readonly<DraftContext> {
  return Object.freeze({ slug, language, ioMode })
}

export function createDraftSnapshot(
  context: DraftContext,
  code: string,
): Readonly<DraftSnapshot> {
  return Object.freeze({ ...context, code })
}

export function sameDraftContext(
  left: DraftContext | null | undefined,
  right: DraftContext | null | undefined,
): boolean {
  return Boolean(
    left
      && right
      && left.slug === right.slug
      && left.language === right.language
      && left.ioMode === right.ioMode,
  )
}

export function draftLoadPath(context: DraftContext): string {
  return `/api/drafts/${encodeURIComponent(context.slug)}?language=${encodeURIComponent(context.language)}&io_mode=${encodeURIComponent(context.ioMode)}`
}

export function draftSaveRequest(snapshot: DraftSnapshot): DraftSaveRequest {
  return Object.freeze({
    path: `/api/drafts/${encodeURIComponent(snapshot.slug)}`,
    body: Object.freeze({
      language: snapshot.language,
      io_mode: snapshot.ioMode,
      code: snapshot.code,
    }),
  })
}

import { sameDraftContext, type DraftContext } from './problemDraft.ts'

export function canCommitProblemLoad(
  requestGeneration: number,
  currentGeneration: number,
  routeSlug: string,
  requestSlug: string,
): boolean {
  return requestGeneration === currentGeneration && routeSlug === requestSlug
}

export function canCommitProblemDraft(
  requestGeneration: number,
  currentGeneration: number,
  routeSlug: string,
  requestSlug: string,
  loaded: DraftContext,
  desired: DraftContext | null,
): boolean {
  return canCommitProblemLoad(
    requestGeneration,
    currentGeneration,
    routeSlug,
    requestSlug,
  ) && sameDraftContext(loaded, desired)
}

export function canCommitDraftTransition(
  requestGeneration: number,
  currentGeneration: number,
  routeSlug: string,
  target: DraftContext,
  desired: DraftContext | null,
): boolean {
  return requestGeneration === currentGeneration
    && routeSlug === target.slug
    && sameDraftContext(target, desired)
}

export function canAcceptSubmissionPoll(
  requestEpoch: number,
  currentEpoch: number,
  activeSlug: string | null | undefined,
  submissionSlug: string,
): boolean {
  return requestEpoch === currentEpoch && activeSlug === submissionSlug
}

export function isDraftRevisionCurrent(
  savedContext: DraftContext,
  activeContext: DraftContext | null | undefined,
  savedRevision: number,
  currentRevision: number,
): boolean {
  return sameDraftContext(savedContext, activeContext) && savedRevision === currentRevision
}

export async function flushUntilStable(
  saveOnce: () => Promise<boolean>,
  isStable: () => boolean,
): Promise<boolean> {
  for (;;) {
    if (!(await saveOnce())) return false
    if (isStable()) return true
  }
}

import type { SubmissionStatus } from './types'

const STATUS_CLASSES: Record<SubmissionStatus, string> = {
  pending: 'st-pending',
  judging: 'st-judging',
  AC: 'st-ac',
  WA: 'st-wa',
  TLE: 'st-tle',
  MLE: 'st-mle',
  CE: 'st-ce',
  RE: 'st-re',
  IE: 'st-ie',
}

export function submissionStatusClass(status: SubmissionStatus): string {
  return STATUS_CLASSES[status]
}

export function isPendingSubmissionStatus(status: SubmissionStatus): boolean {
  return status === 'pending' || status === 'judging'
}

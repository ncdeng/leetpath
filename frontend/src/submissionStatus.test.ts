import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { isPendingSubmissionStatus, submissionStatusClass } from './submissionStatus.ts'
import type { SubmissionStatus } from './types'

describe('submission status presentation', () => {
  it('maps every API status to the lowercase CSS class', () => {
    const expected: Record<SubmissionStatus, string> = {
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

    for (const [status, className] of Object.entries(expected)) {
      assert.equal(submissionStatusClass(status as SubmissionStatus), className)
    }
  })

  it('shows the spinner only for pending states', () => {
    assert.equal(isPendingSubmissionStatus('pending'), true)
    assert.equal(isPendingSubmissionStatus('judging'), true)
    assert.equal(isPendingSubmissionStatus('AC'), false)
    assert.equal(isPendingSubmissionStatus('IE'), false)
  })
})

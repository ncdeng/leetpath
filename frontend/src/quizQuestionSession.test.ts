import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { createGenerationGate } from './problemDraftSession.ts'
import {
  buildQuizQuestionParams,
  isCurrentQuestionRequest,
  quizEnterHint,
} from './quizQuestionSession.ts'

describe('quiz question request gates', () => {
  it('rejects a stale generation even when the question id is unchanged', () => {
    const gate = createGenerationGate()
    const stale = { generation: gate.next(), questionId: 7 }
    gate.next()

    assert.equal(isCurrentQuestionRequest(gate, stale, 7), false)
  })

  it('requires both the current generation and current question id', () => {
    const gate = createGenerationGate()
    const current = { generation: gate.next(), questionId: 7 }

    assert.equal(isCurrentQuestionRequest(gate, current, 8), false)
    assert.equal(isCurrentQuestionRequest(gate, current, 7), true)
  })
})

describe('quiz question query parameters', () => {
  it('excludes open and skipped questions from an exam', () => {
    const params = buildQuizQuestionParams({
      tab: 'exam',
      selectedBank: '',
      onlyUnanswered: false,
      randomOrder: false,
    })

    assert.equal(
      params.toString(),
      'limit=20&random_order=true&exclude_open=true&exclude_skipped=true',
    )
  })
})

describe('quiz Enter hint', () => {
  it('shows only reveal before an open answer is revealed', () => {
    assert.equal(quizEnterHint(true, false), '查看答案')
  })

  it('shows next after an open answer is revealed', () => {
    assert.equal(quizEnterHint(true, true), '下一题')
  })

  it('keeps the objective-question submit/next hint', () => {
    assert.equal(quizEnterHint(false, false), '提交/下一题')
  })
})

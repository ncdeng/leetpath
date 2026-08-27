import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import {
  canAcceptSubmissionPoll,
  canCommitDraftTransition,
  canCommitProblemDraft,
  canCommitProblemLoad,
  flushUntilStable,
  isDraftRevisionCurrent,
} from './problemConcurrency.ts'
import { createDraftContext } from './problemDraft.ts'

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

describe('problem page async commit guards', () => {
  it('ignores the late B response after C becomes the current page load', async () => {
    let currentGeneration = 0
    let routeSlug = 'b'
    let title = ''
    const b = deferred<string>()
    const bGeneration = ++currentGeneration
    const bCommit = b.promise.then((value) => {
      if (canCommitProblemLoad(bGeneration, currentGeneration, routeSlug, 'b')) title = value
    })

    routeSlug = 'c'
    const c = deferred<string>()
    const cGeneration = ++currentGeneration
    const cCommit = c.promise.then((value) => {
      if (canCommitProblemLoad(cGeneration, currentGeneration, routeSlug, 'c')) title = value
    })

    c.resolve('problem C')
    await cCommit
    b.resolve('stale problem B')
    await bCommit

    assert.equal(title, 'problem C')
  })

  it('only commits the final combined language and IO preference', async () => {
    const pythonLeetCode = createDraftContext('two-sum', 'python3', 'leetcode')
    const cppLeetCode = createDraftContext('two-sum', 'cpp', 'leetcode')
    let desired = pythonLeetCode
    let currentGeneration = 0
    let applied = ''

    const first = deferred<string>()
    const firstGeneration = ++currentGeneration
    const firstCommit = first.promise.then((value) => {
      if (
        canCommitDraftTransition(
          firstGeneration,
          currentGeneration,
          'two-sum',
          pythonLeetCode,
          desired,
        )
      ) applied = value
    })

    desired = cppLeetCode
    const second = deferred<string>()
    const secondGeneration = ++currentGeneration
    const secondCommit = second.promise.then((value) => {
      if (
        canCommitDraftTransition(
          secondGeneration,
          currentGeneration,
          'two-sum',
          cppLeetCode,
          desired,
        )
      ) applied = value
    })

    second.resolve('cpp/leetcode')
    await secondCommit
    first.resolve('python/leetcode')
    await firstCommit

    assert.equal(applied, 'cpp/leetcode')
  })

  it('rejects a page draft when the preference changes while sibling requests finish', () => {
    const loaded = createDraftContext('two-sum', 'python3', 'acm')
    const desired = createDraftContext('two-sum', 'cpp', 'acm')

    assert.equal(
      canCommitProblemDraft(4, 4, 'two-sum', 'two-sum', loaded, desired),
      false,
    )
    assert.equal(
      canCommitProblemDraft(4, 4, 'two-sum', 'two-sum', desired, desired),
      true,
    )
  })

  it('detects an edit made while a draft PUT is pending', async () => {
    const context = createDraftContext('two-sum', 'python3', 'acm')
    let currentRevision = 1
    const put = deferred<void>()
    const completion = put.promise.then(() => (
      isDraftRevisionCurrent(context, context, 1, currentRevision)
    ))

    currentRevision = 2
    put.resolve()

    assert.equal(await completion, false)
  })

  it('flushes the revision created while the first PUT is pending', async () => {
    const firstPut = deferred<void>()
    const secondPut = deferred<void>()
    const puts = [firstPut, secondPut]
    let dirty = true
    let putCount = 0

    const flushing = flushUntilStable(
      async () => {
        if (!dirty) return true
        const pending = puts[putCount]
        putCount += 1
        dirty = false
        await pending.promise
        return true
      },
      () => !dirty,
    )

    await Promise.resolve()
    assert.equal(putCount, 1)
    dirty = true
    firstPut.resolve()
    await Promise.resolve()
    await Promise.resolve()
    assert.equal(putCount, 2)
    secondPut.resolve()

    assert.equal(await flushing, true)
    assert.equal(dirty, false)
  })

  it('rejects a poll response after the active problem or poll epoch changes', () => {
    assert.equal(canAcceptSubmissionPoll(3, 3, 'two-sum', 'two-sum'), true)
    assert.equal(canAcceptSubmissionPoll(2, 3, 'two-sum', 'two-sum'), false)
    assert.equal(canAcceptSubmissionPoll(3, 3, 'three-sum', 'two-sum'), false)
    assert.equal(canAcceptSubmissionPoll(3, 3, null, 'two-sum'), false)
  })
})

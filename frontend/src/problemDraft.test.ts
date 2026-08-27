import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import {
  createDraftContext,
  createDraftSnapshot,
  draftLoadPath,
  draftSaveRequest,
  sameDraftContext,
} from './problemDraft.ts'
import type { IoMode, Language } from './types'

describe('draft context snapshots', () => {
  it('keeps the old slug/language/io mode when the editor moves to a new context', () => {
    let slug = 'two-sum'
    let language: Language = 'python3'
    let ioMode: IoMode = 'acm'
    const oldContext = createDraftContext(slug, language, ioMode)
    const oldDraft = createDraftSnapshot(oldContext, 'print("old code")')

    slug = 'three-sum'
    language = 'cpp'
    ioMode = 'leetcode'

    assert.deepEqual(draftSaveRequest(oldDraft), {
      path: '/api/drafts/two-sum',
      body: {
        language: 'python3',
        io_mode: 'acm',
        code: 'print("old code")',
      },
    })
    assert.equal(Object.isFrozen(oldContext), true)
    assert.equal(Object.isFrozen(oldDraft), true)
  })

  it('builds encoded load/save URLs from the supplied immutable context', () => {
    const context = createDraftContext('contains/slash', 'cpp', 'leetcode')
    const snapshot = createDraftSnapshot(context, 'class Solution {};')

    assert.equal(
      draftLoadPath(context),
      '/api/drafts/contains%2Fslash?language=cpp&io_mode=leetcode',
    )
    assert.equal(draftSaveRequest(snapshot).path, '/api/drafts/contains%2Fslash')
  })

  it('compares all context dimensions', () => {
    const base = createDraftContext('two-sum', 'python3', 'acm')
    assert.equal(sameDraftContext(base, createDraftContext('two-sum', 'python3', 'acm')), true)
    assert.equal(sameDraftContext(base, createDraftContext('three-sum', 'python3', 'acm')), false)
    assert.equal(sameDraftContext(base, createDraftContext('two-sum', 'cpp', 'acm')), false)
    assert.equal(sameDraftContext(base, createDraftContext('two-sum', 'python3', 'leetcode')), false)
  })
})

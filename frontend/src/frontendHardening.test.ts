import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { hasAvailableAiKey, resolveAiPayloadBaseUrl } from './aiRequest.ts'
import { compareFeaturedCompanies } from './jobBoardSort.ts'
import { loginRedirectUrl } from './loginRedirect.ts'
import { copyToClipboard } from './clipboard.ts'

describe('resolveAiPayloadBaseUrl', () => {
  it('delegates the base URL to the backend when the personal key is blank', () => {
    assert.equal(resolveAiPayloadBaseUrl('https://old-relay.example/v1', '   '), '')
    assert.equal(hasAvailableAiKey('   ', true), true)
    assert.equal(hasAvailableAiKey('   ', false), false)
  })

  it('keeps the selected base URL when a personal key is present', () => {
    assert.equal(
      resolveAiPayloadBaseUrl('  https://user-relay.example/v1/  ', ' personal-key '),
      'https://user-relay.example/v1/',
    )
  })
})

describe('compareFeaturedCompanies', () => {
  it('keeps dated opportunities ahead of long-running recruitment within a tier', () => {
    const companies = [
      { name: '长期多岗', tier: 'big' as const, deadlineDays: null, jobCount: 100 },
      { name: '二十天截止', tier: 'big' as const, deadlineDays: 20, jobCount: 8 },
      { name: '一天急投', tier: 'big' as const, deadlineDays: 1, jobCount: 1 },
    ]

    companies.sort(compareFeaturedCompanies)

    assert.deepEqual(companies.map((company) => company.name), ['一天急投', '二十天截止', '长期多岗'])
  })
})

describe('loginRedirectUrl', () => {
  it('preserves the path, query, and hash in the redirect target', () => {
    assert.equal(
      loginRedirectUrl({ pathname: '/handbook', search: '?q=1', hash: '#section' }),
      `/login?redirect=${encodeURIComponent('/handbook?q=1#section')}`,
    )
  })
})

function clipboardFallback(select: () => void, copy: () => boolean = () => false) {
  let removed = false
  const textarea = {
    value: '',
    style: { position: '', opacity: '' },
    select,
    remove: () => { removed = true },
  }

  return {
    environment: {
      navigator: {},
      document: {
        body: { appendChild: () => undefined },
        createElement: () => textarea,
        execCommand: copy,
      },
    },
    wasRemoved: () => removed,
  }
}

describe('copyToClipboard', () => {
  it('removes the fallback textarea when copying returns false', async () => {
    const fallback = clipboardFallback(() => undefined)

    assert.equal(await copyToClipboard('content', fallback.environment), false)
    assert.equal(fallback.wasRemoved(), true)
  })

  it('removes the fallback textarea when copying throws', async () => {
    const fallback = clipboardFallback(
      () => undefined,
      () => { throw new Error('copy failed') },
    )

    assert.equal(await copyToClipboard('content', fallback.environment), false)
    assert.equal(fallback.wasRemoved(), true)
  })
})

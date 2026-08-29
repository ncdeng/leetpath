export function resolveAiPayloadBaseUrl(baseUrl: string, apiKey: string): string {
  return apiKey.trim() ? baseUrl.trim() : ''
}

export function hasAvailableAiKey(apiKey: string, hasSystemKey: boolean): boolean {
  return Boolean(apiKey.trim()) || hasSystemKey
}

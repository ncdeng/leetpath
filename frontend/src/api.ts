// API 层：与 docs/spec/backend-api.md 契约对齐

import { loginRedirectUrl } from './loginRedirect'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isForm = typeof FormData !== 'undefined' && options.body instanceof FormData
  const res = await fetch(path, {
    credentials: 'include',
    ...options,
    headers: options.body && !isForm
      ? { 'Content-Type': 'application/json', ...options.headers }
      : options.headers,
  })
  if (!res.ok) {
    let message = `请求失败 (${res.status})`
    try {
      const data = await res.json()
      if (data?.detail) {
        message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
      }
    } catch {
      /* ignore */
    }
    if (res.status === 401 && !['/login', '/register'].includes(location.pathname)) {
      location.assign(loginRedirectUrl(location))
    }
    throw new ApiError(res.status, message)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  upload: <T>(path: string, body: FormData) => request<T>(path, { method: 'POST', body }),
}

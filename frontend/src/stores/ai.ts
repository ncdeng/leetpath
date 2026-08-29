import { computed, ref } from 'vue'
import { hasAvailableAiKey, resolveAiPayloadBaseUrl } from '../aiRequest'

export type AiContentPart =
  | { type: 'text'; text: string }
  | { type: 'image_url'; image_url: { url: string } }

export interface AiMessage {
  role: 'system' | 'user' | 'assistant'
  content: string | AiContentPart[]
}

export function messagePlainText(content: AiMessage['content']): string {
  if (typeof content === 'string') return content
  return content
    .filter((part): part is { type: 'text'; text: string } => part.type === 'text')
    .map((part) => part.text)
    .join('\n')
}

export interface AiPreset {
  name: string
  url: string
  defaultModel?: string
  placeholder?: string
}

export const AI_PRESETS: AiPreset[] = [
  {
    name: 'Antithor 专属中转站 (默认)',
    url: 'https://api.antithor.asia/v1',
  },
]

const STORAGE_KEY = 'leetpath_ai_config'
const CACHE_STORAGE_KEY = 'leetpath_ai_response_cache_v1'

export type ReasoningEffort = 'off' | 'low' | 'medium' | 'high' | 'xhigh'

interface AiConfig {
  baseUrl: string
  apiKey: string
  model: string
  modelsList: string[]
  temperature: number
  reasoningEffort: ReasoningEffort
  maxContextTurns: number
  maxContextTokens: number
  maxResponseTokens: number
  enableLocalCache: boolean
}

export const REASONING_EFFORT_OPTIONS: { value: ReasoningEffort; label: string; hint: string }[] = [
  { value: 'off', label: '关闭', hint: '不传该字段，适合不支持推理参数的型号' },
  { value: 'low', label: '低', hint: '快，适合简单问答和工具调用' },
  { value: 'medium', label: '中', hint: '更稳，适合长上下文分析' },
  { value: 'high', label: '高', hint: '默认深度思考，适合难题与代码' },
  { value: 'xhigh', label: '极高', hint: '最深，延迟更高（grok-4.6+）' },
]

function defaultReasoningEffort(model: string): ReasoningEffort {
  const name = model.toLowerCase()
  if (!name) return 'off'
  if (name.includes('non-reasoning') || name.includes('nonreasoning')) return 'off'
  if (name.includes('grok') || name.includes('gpt-5') || /(^|[-_/])o[1-9]/.test(name) || name.includes('reason')) {
    return 'high'
  }
  return 'off'
}

function parseEffort(value: unknown): ReasoningEffort | undefined {
  if (value === 'off' || value === 'low' || value === 'medium' || value === 'high' || value === 'xhigh') {
    return value
  }
  return undefined
}

interface CacheItem {
  content: string
  model: string
  timestamp: number
}

// 快速估算文本 Token 数（中文约 1.5 token/字，英文代码约 0.5~1 token/词）
export function estimateTokens(text: string): number {
  if (!text) return 0
  const cjkMatches = text.match(/[\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]/g) || []
  const cjkCount = cjkMatches.length
  const nonCjkCount = text.length - cjkCount
  return Math.ceil(cjkCount * 1.5 + nonCjkCount * 0.45)
}

// 读取持久化配置
const savedConfig: Partial<AiConfig> = (() => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
})()

const baseUrl = ref<string>(savedConfig.baseUrl || 'https://api.antithor.asia/v1')
const apiKey = ref<string>(savedConfig.apiKey || '')
const selectedModel = ref<string>(savedConfig.model || 'grok-4.6-xhigh')
const modelsList = ref<string[]>(savedConfig.modelsList || [])
const temperature = ref<number>(savedConfig.temperature ?? 0.7)
const reasoningEffort = ref<ReasoningEffort>(
  parseEffort(savedConfig.reasoningEffort)
    ?? defaultReasoningEffort(savedConfig.model || 'grok-4.6-xhigh'),
)
const maxContextTurns = ref<number>(savedConfig.maxContextTurns ?? 5)
const maxContextTokens = ref<number>(savedConfig.maxContextTokens ?? 131072)
const maxResponseTokens = ref<number>(savedConfig.maxResponseTokens ?? 4096)
const enableLocalCache = ref<boolean>(savedConfig.enableLocalCache ?? true)
const hasSystemKey = ref<boolean>(false)

// 异步探测服务端内置 Key 状态
async function checkSystemStatus() {
  try {
    const res = await fetch('/api/ai/status')
    if (res.ok) {
      const data = await res.json()
      hasSystemKey.value = Boolean(data.has_system_key)
      if (!selectedModel.value && data.default_model) {
        selectedModel.value = data.default_model
      }
    }
  } catch {
    // ignore
  }
}
checkSystemStatus()

// 读取本地问答响应缓存
function getCacheMap(): Record<string, CacheItem> {
  try {
    const raw = localStorage.getItem(CACHE_STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveCacheMap(map: Record<string, CacheItem>) {
  try {
    localStorage.setItem(CACHE_STORAGE_KEY, JSON.stringify(map))
  } catch {
    // 若超限清空旧缓存
    const keys = Object.keys(map)
    if (keys.length > 50) {
      const trimmed: Record<string, CacheItem> = {}
      keys.slice(-30).forEach((k) => {
        const item = map[k]
        if (item) trimmed[k] = item
      })
      localStorage.setItem(CACHE_STORAGE_KEY, JSON.stringify(trimmed))
    }
  }
}

const isConfigured = computed(() => {
  const hasKey = apiKey.value.trim().length > 0 || hasSystemKey.value
  const hasModel = selectedModel.value.trim().length > 0 || hasSystemKey.value
  return baseUrl.value.trim().length > 0 && hasKey && hasModel
})

function saveConfig() {
  const cfg: AiConfig = {
    baseUrl: baseUrl.value.trim(),
    apiKey: apiKey.value.trim(),
    model: selectedModel.value.trim(),
    modelsList: modelsList.value,
    temperature: temperature.value,
    reasoningEffort: reasoningEffort.value,
    maxContextTurns: maxContextTurns.value,
    maxContextTokens: maxContextTokens.value,
    maxResponseTokens: maxResponseTokens.value,
    enableLocalCache: enableLocalCache.value,
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg))
}

function extractModelNames(data: any): string[] {
  const models = new Set<string>()

  function tryAdd(val: any) {
    if (!val) return
    if (typeof val === 'string') {
      const s = val.trim()
      if (s && s.length < 120) models.add(s)
    } else if (typeof val === 'object') {
      const name = val.id || val.name || val.model || val.model_name || val.slug || val.value
      if (typeof name === 'string' && name.trim()) {
        models.add(name.trim())
      }
    }
  }

  if (Array.isArray(data)) {
    data.forEach(tryAdd)
  } else if (data && typeof data === 'object') {
    if (Array.isArray(data.data)) {
      data.data.forEach(tryAdd)
    } else if (Array.isArray(data.models)) {
      data.models.forEach(tryAdd)
    } else if (Array.isArray(data.result)) {
      data.result.forEach(tryAdd)
    } else if (Array.isArray(data.items)) {
      data.items.forEach(tryAdd)
    } else if (Array.isArray(data.model_list)) {
      data.model_list.forEach(tryAdd)
    } else if (data.data && typeof data.data === 'object') {
      Object.keys(data.data).forEach(tryAdd)
    } else if (data.models && typeof data.models === 'object') {
      Object.keys(data.models).forEach(tryAdd)
    }
  }

  return Array.from(models)
}

export function useAiStore() {
  /**
   * 一键拉取中转站 / 官方 API 提供的全部可用模型列表 (通过后端安全代理，完美解决浏览器跨域与预检拦截)
   */
  async function fetchModels(): Promise<string[]> {
    if (apiKey.value.trim() && !baseUrl.value.trim()) {
      throw new Error('请先填写 Base URL')
    }
    if (!hasAvailableAiKey(apiKey.value, hasSystemKey.value)) {
      throw new Error('请先填写 API Key')
    }

    const res = await fetch('/api/ai/models', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        base_url: resolveAiPayloadBaseUrl(baseUrl.value, apiKey.value),
        api_key: apiKey.value.trim(),
      }),
    })

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      throw new Error(errJson.detail || `获取模型列表失败 (${res.status})`)
    }

    const data = await res.json()
    const list = extractModelNames(data)

    if (list.length === 0) {
      throw new Error('中转站未返回模型列表，请检查 Key 权限或直接在下方输入框中手动填写模型名称')
    }

    list.sort((a, b) => a.localeCompare(b))
    modelsList.value = list
    if (!list.includes(selectedModel.value)) {
      selectedModel.value = list[0] || ''
    }
    saveConfig()
    return list
  }

  /**
   * 本地响应缓存查询：根据 contextKey + prompt + model
   */
  function getCachedAnswer(contextKey: string, prompt: string, model?: string): string | null {
    if (!enableLocalCache.value) return null
    const map = getCacheMap()
    const targetModel = model || selectedModel.value
    const key = `${contextKey}:::${prompt.trim()}:::${targetModel}:::${reasoningEffort.value}`
    const item = map[key]
    return item ? item.content : null
  }

  /**
   * 写入本地响应缓存
   */
  function setCachedAnswer(contextKey: string, prompt: string, content: string, model?: string) {
    if (!enableLocalCache.value || !content.trim()) return
    const map = getCacheMap()
    const targetModel = model || selectedModel.value
    const key = `${contextKey}:::${prompt.trim()}:::${targetModel}:::${reasoningEffort.value}`
    map[key] = {
      content,
      model: targetModel,
      timestamp: Date.now(),
    }
    saveCacheMap(map)
  }

  /**
   * 清空所有本地 AI 响应缓存
   */
  function clearAllCache() {
    localStorage.removeItem(CACHE_STORAGE_KEY)
  }

  /**
   * 获取当前已缓存条目数
   */
  function getCacheCount(): number {
    const map = getCacheMap()
    return Object.keys(map).length
  }

  /**
   * 发起流式对话（包含严格 Token 预算裁剪 + 轮数约束 + 前缀保护）
   */
  async function streamChat(
    messages: AiMessage[],
    onChunk: (chunk: string) => void,
    signal?: AbortSignal,
  ): Promise<string> {
    if (!isConfigured.value) {
      throw new Error('请先在顶部「🤖 AI 设置」中配置 API Key 与模型')
    }

    // 1. 分离系统核心提示词（锚定保护，永不截断）与历史会话
    const systemMsg = messages.find((m) => m.role === 'system')
    const historyMsgs = messages.filter((m) => m.role !== 'system')

    // 2. 第一重防线：最大轮数裁剪（保留最近 maxContextTurns 轮对话）
    const maxHistoryCount = Math.max(1, maxContextTurns.value * 2)
    const recentHistory = historyMsgs.slice(-maxHistoryCount)

    // 3. 第二重防线：Token 预算滑动裁剪（从旧到新丢弃，直至总 Token <= maxContextTokens）
    const budget = maxContextTokens.value
    let sysTokens = systemMsg ? estimateTokens(messagePlainText(systemMsg.content)) : 0
    let remainingBudget = budget - sysTokens

    const selectedHistory: AiMessage[] = []
    // 从最新的消息往旧遍历反向装载
    for (let i = recentHistory.length - 1; i >= 0; i--) {
      const msg = recentHistory[i]
      if (!msg) continue
      const msgTokens = estimateTokens(messagePlainText(msg.content))
      if (remainingBudget >= msgTokens || selectedHistory.length === 0) {
        selectedHistory.unshift(msg)
        remainingBudget -= msgTokens
      } else {
        // 超过 Token 预算，丢弃更早的历史
        break
      }
    }

    const finalMessages: AiMessage[] = []
    if (systemMsg) finalMessages.push(systemMsg)
    finalMessages.push(...selectedHistory)

    const res = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        base_url: resolveAiPayloadBaseUrl(baseUrl.value, apiKey.value),
        api_key: apiKey.value.trim(),
        model: selectedModel.value.trim(),
        messages: finalMessages,
        temperature: temperature.value,
        max_tokens: Math.min(Math.max(16, maxResponseTokens.value || 4096), 8192),
        reasoning_effort: reasoningEffort.value === 'off' ? null : reasoningEffort.value,
      }),
      signal,
    })

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      throw new Error(errJson.detail || `AI 请求失败 [${res.status}]`)
    }

    if (!res.body) {
      throw new Error('返回数据流为空')
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let fullText = ''
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || trimmed.startsWith(':')) continue
          if (trimmed === 'data: [DONE]') continue

          if (trimmed.startsWith('data:')) {
            const jsonStr = trimmed.slice(5).trim()
            try {
              const parsed = JSON.parse(jsonStr)
              if (parsed.error) {
                throw new Error(parsed.error)
              }
              const choice = parsed.choices?.[0]
              const delta = choice?.delta
              const content =
                delta?.content ||
                delta?.reasoning_content ||
                delta?.text ||
                choice?.text ||
                choice?.message?.content ||
                parsed.response ||
                parsed.message?.content ||
                ''
              if (content) {
                fullText += content
                onChunk(content)
              }
            } catch (err: any) {
              if (err.message && !err.message.includes('JSON')) {
                throw err
              }
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }

    return fullText
  }

  return {
    baseUrl,
    apiKey,
    selectedModel,
    modelsList,
    temperature,
    reasoningEffort,
    maxContextTurns,
    maxContextTokens,
    maxResponseTokens,
    enableLocalCache,
    isConfigured,
    saveConfig,
    fetchModels,
    getCachedAnswer,
    setCachedAnswer,
    clearAllCache,
    getCacheCount,
    streamChat,
  }
}

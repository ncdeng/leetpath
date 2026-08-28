<template>
  <div v-if="visible" class="drawer-backdrop" @click.self="$emit('close')">
    <div class="drawer">
      <!-- 头部 -->
      <div class="drawer-head">
        <div class="drawer-title-group">
          <div class="drawer-kicker">AI Tutor & In-Context Assistant</div>
          <h3 class="drawer-title">
            <AppIcon name="robot" :size="17" class="drawer-title-icon" />
            <span class="drawer-title-text">{{ title || 'AI 导师智能答疑' }}</span>
          </h3>
        </div>
        <div class="drawer-actions">
          <button class="btn btn-xs" :title="`当前模型: ${ai.selectedModel.value}`" @click="showSettings = true">
            <AppIcon name="sparkle" :size="12" />
            <span class="mono drawer-model-name">{{ ai.selectedModel.value || '未选模型' }}</span>
          </button>
          <button class="btn btn-xs btn-ghost drawer-close-btn" title="关闭" @click="$emit('close')">
            <AppIcon name="x" :size="14" />
          </button>
        </div>
      </div>

      <!-- 未配置提示 -->
      <div v-if="!ai.isConfigured.value" class="drawer-warning-card">
        <p><strong>尚未配置 AI API Key</strong></p>
        <p class="muted drawer-warning-sub">
          支持接入 DeepSeek、硅基流动、Claude、OpenRouter 或自定义中转站。
        </p>
        <button class="btn btn-sm btn-primary" @click="showSettings = true">
          <AppIcon name="gear" :size="14" /> 立即前往配置 Base URL 与 Key
        </button>
      </div>

      <!-- 快捷预设提问 Chips -->
      <div class="quick-prompts-bar" v-if="presetPrompts && presetPrompts.length > 0">
        <span class="quick-lbl">快捷追问：</span>
        <div class="quick-chips">
          <button
            v-for="p in presetPrompts"
            :key="p.label"
            class="chip-btn"
            :disabled="generating"
            @click="onPromptClick(p.prompt)"
          >
            {{ p.label }}
          </button>
        </div>
      </div>

      <!-- 对话消息记录区 -->
      <div class="drawer-messages" ref="msgContainer">
        <div v-for="(msg, idx) in messages" :key="idx" class="chat-bubble" :class="`bubble-${msg.role}`">
          <div class="bubble-avatar">
            <AppIcon v-if="msg.role === 'assistant'" name="robot" :size="16" />
            <span v-else>我</span>
          </div>
          <div class="bubble-body">
            <div class="bubble-header">
              <span class="bubble-name">{{ msg.role === 'assistant' ? `AI 导师 (${ai.selectedModel.value})` : '我' }}</span>
              <div class="bubble-header-actions" v-if="msg.role === 'assistant'">
                <span v-if="msg.isCached" class="cached-badge" title="从本地浏览器直接秒级载入，未调用网络 API">
                  <AppIcon name="sparkle" :size="10" /> 命中本地缓存 (0 Token)
                </span>
                <button
                  v-if="msg.isCached && msg.originalPrompt"
                  class="btn btn-xs btn-ghost bubble-regen"
                  :disabled="generating"
                  @click="reGenerate(msg.originalPrompt)"
                >
                  <AppIcon name="refresh" :size="11" /> 重新生成
                </button>
                <button
                  v-if="msg.content"
                  class="btn btn-xs btn-ghost bubble-copy"
                  @click="copyText(typeof msg.content === 'string' ? msg.content : '')"
                >
                  <AppIcon name="copy" :size="11" /> 复制
                </button>
              </div>
            </div>
            <div v-if="msg.images?.length" class="msg-images">
              <img v-for="(src, imgIdx) in msg.images" :key="imgIdx" :src="src" alt="粘贴的截图" />
            </div>
            <div class="statement bubble-markdown markdown-body" v-html="renderMd(typeof msg.content === 'string' ? msg.content : '')"></div>
          </div>
        </div>

        <!-- 正在生成的流式消息 -->
        <div v-if="generating" class="chat-bubble bubble-assistant">
          <div class="bubble-avatar"><AppIcon name="robot" :size="16" /></div>
          <div class="bubble-body">
            <div class="bubble-header">
              <span class="bubble-name">AI 导师思考中...</span>
            </div>
            <div class="statement bubble-markdown markdown-body" v-html="renderMd(streamBuffer || '...')"></div>
            <div class="stream-cursor"></div>
          </div>
        </div>
      </div>

      <!-- 底部输入框 -->
      <div class="drawer-input-bar" @paste="onComposerPaste">
        <div v-if="pendingImages.length" class="composer-previews">
          <div v-for="(src, idx) in pendingImages" :key="idx" class="composer-preview">
            <img :src="src" alt="待发送截图" />
            <button type="button" class="preview-remove" title="去掉这张图" @click="pendingImages.splice(idx, 1)">
              <AppIcon name="x" :size="10" />
            </button>
          </div>
        </div>
        <textarea
          ref="composerEl"
          v-model="inputQuestion"
          class="input drawer-textarea"
          placeholder="可粘贴文字或截图... (Enter 发送，Shift+Enter 换行)"
          rows="2"
          :disabled="generating"
          @keydown.enter.exact.prevent="onEnterSend"
          @paste="onComposerPaste"
        ></textarea>
        <div class="input-bottom-row">
          <span class="drawer-hint">已开启上下文约束 (保留近 {{ ai.maxContextTurns.value }} 轮) 与本地缓存</span>
          <div class="drawer-send-row">
            <input
              ref="fileEl"
              type="file"
              accept="image/*"
              multiple
              hidden
              @change="onPickFiles"
            />
            <button
              type="button"
              class="btn btn-sm btn-ghost"
              title="添加截图"
              :disabled="generating"
              @click="fileEl?.click()"
            ><AppIcon name="plus" :size="14" /> 截图</button>
            <button v-if="generating" class="btn btn-sm btn-outline" @click="abort">
              <AppIcon name="x" :size="13" /> 停止生成
            </button>
            <button
              v-else
              class="btn btn-sm btn-primary"
              :disabled="(!inputQuestion.trim() && !pendingImages.length) || !ai.isConfigured.value"
              @click="onPromptClick(inputQuestion)"
            >
              <AppIcon name="send" :size="13" /> 发送 (Enter)
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- AI 设置弹窗 -->
    <AiSettingsModal v-if="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import AiSettingsModal from './AiSettingsModal.vue'
import AppIcon from './AppIcon.vue'
import { renderMarkdown } from '../markdown'
import { copyToClipboard } from '../clipboard'
import { useAiStore, type AiMessage } from '../stores/ai'
import { useToast } from '../stores/toast'
import { compressPickedFiles, insertAtCursor, readClipboard, toApiContent } from '../aiPaste'

export interface PromptPreset {
  label: string
  prompt: string
}

interface DrawerMessage extends AiMessage {
  isCached?: boolean
  originalPrompt?: string
  images?: string[]
}

const props = defineProps<{
  visible: boolean
  title?: string
  contextKey?: string // 用于本地缓存键，如 `quiz:12` 或 `problem:two-sum`
  contextText?: string
  presetPrompts?: PromptPreset[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const toast = useToast()
const ai = useAiStore()

const showSettings = ref(false)
const generating = ref(false)
const inputQuestion = ref('')
const pendingImages = ref<string[]>([])
const streamBuffer = ref('')
const messages = ref<DrawerMessage[]>([])
const msgContainer = ref<HTMLElement | null>(null)
const composerEl = ref<HTMLTextAreaElement | null>(null)
const fileEl = ref<HTMLInputElement | null>(null)
let abortController: AbortController | null = null

function renderMd(text: string) {
  if (!text) return ''
  return renderMarkdown(text)
}

async function copyText(text: string) {
  const ok = await copyToClipboard(text)
  if (ok) toast.success('已复制到剪贴板')
  else toast.error('复制失败，请手动选择复制')
}

function scrollToBottom() {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}

function onEnterSend() {
  if (generating.value) return
  if (!inputQuestion.value.trim() && !pendingImages.value.length) return
  onPromptClick(inputQuestion.value)
}

function applyInsertedText(text: string) {
  const { next, caret } = insertAtCursor(composerEl.value, inputQuestion.value, text)
  inputQuestion.value = next
  nextTick(() => {
    const el = composerEl.value
    if (!el) return
    el.focus()
    el.selectionStart = el.selectionEnd = caret
  })
}

function addPendingImages(urls: string[]) {
  if (!urls.length) return
  const room = Math.max(0, 4 - pendingImages.value.length)
  pendingImages.value.push(...urls.slice(0, room))
  if (urls.length > room) toast.info('一次最多 4 张图')
}

async function handlePasteData(dt: DataTransfer | null) {
  const { text, images } = await readClipboard(dt)
  if (images.length) addPendingImages(images)
  if (text) applyInsertedText(text)
  return Boolean(text || images.length)
}

async function onComposerPaste(e: ClipboardEvent) {
  e.preventDefault()
  e.stopPropagation()
  const ok = await handlePasteData(e.clipboardData)
  if (!ok) toast.info('剪贴板里没有文字或图片')
}

async function onPickFiles(e: Event) {
  const input = e.target as HTMLInputElement
  try {
    const urls = await compressPickedFiles(input.files)
    addPendingImages(urls)
  } finally {
    input.value = ''
  }
}

function abort() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
  generating.value = false
}

// 检查本地缓存或发起请求
async function onPromptClick(userPrompt: string, forceRefresh = false) {
  const attached = pendingImages.value.slice()
  if (!userPrompt.trim() && !attached.length) return
  if (!ai.isConfigured.value) {
    showSettings.value = true
    return
  }

  const promptText = userPrompt.trim() || (attached.length ? '（见附图）' : '')
  inputQuestion.value = ''
  pendingImages.value = []

  const cKey = props.contextKey || props.title || 'default'

  // 1. 如果不强制刷新，先检查本地响应缓存！
  if (!forceRefresh && ai.enableLocalCache.value) {
    const cached = ai.getCachedAnswer(cKey, promptText)
    if (cached) {
      messages.value.push({
        role: 'user',
        content: promptText,
        images: attached,
      })
      messages.value.push({
        role: 'assistant',
        content: cached,
        isCached: true,
        originalPrompt: promptText,
      })
      scrollToBottom()
      toast.info('⚡ 已从本地秒级载入缓存回答 (0 Token 消耗)')
      return
    }
  }

  // 2. 没有缓存，发起真实流式请求
  messages.value.push({
    role: 'user',
    content: promptText,
    images: attached,
  })
  scrollToBottom()

  generating.value = true
  streamBuffer.value = ''
  abortController = new AbortController()

  // 构造标准静态系统前缀（利于服务商端 Prefix/Prompt Caching）
  const sysContent = `你是一位资深的技术面试官与计算机/大模型教学导师。
请针对用户目前正在学习或练习的题目进行清晰、深度、易懂的答疑。
回答风格要求：
1. 深入浅出，善于用直观比喻或实际工业场景说明原理；
2. 如涉及代码，请给出清晰注释；如涉及数学公式，请使用标准 LaTeX 格式（例如 $O(n)$ 或 $$...$$）；
3. 重点突出，条理分明。

【当前学习上下文】：
${props.contextText || '无指定上下文'}`

  const apiMessages: AiMessage[] = [
    { role: 'system', content: sysContent },
    ...messages.value.map((m) => ({
      role: m.role,
      content: m.images?.length ? toApiContent(typeof m.content === 'string' ? m.content : '', m.images) : m.content,
    })),
  ]

  try {
    const full = await ai.streamChat(
      apiMessages,
      (chunk) => {
        streamBuffer.value += chunk
        scrollToBottom()
      },
      abortController.signal,
    )
    const resultText = full || streamBuffer.value
    messages.value.push({
      role: 'assistant',
      content: resultText,
      isCached: false,
      originalPrompt: promptText,
    })

    // 写入本地持久缓存
    if (ai.enableLocalCache.value && resultText.trim()) {
      ai.setCachedAnswer(cKey, promptText, resultText)
    }
    streamBuffer.value = ''
  } catch (err: any) {
    if (err.name !== 'AbortError') {
      toast.error(err.message || 'AI 答疑生成失败')
      messages.value.push({
        role: 'assistant',
        content: `✕ 生成失败：${err.message || '网络连接中断'}`,
      })
    }
  } finally {
    generating.value = false
    abortController = null
    scrollToBottom()
  }
}

function reGenerate(promptText: string) {
  onPromptClick(promptText, true)
}

// 监听打开时初始化欢迎语
watch(
  () => props.visible,
  (val) => {
    if (val && messages.value.length === 0) {
      messages.value = [
        {
          role: 'assistant',
          content: '👋 你好！我是你的 AI 导师。你可以点击上方的**快捷追问**按钮，或在下方输入你想深入了解的疑问，我将结合这道题为你深度剖析！',
        },
      ]
    }
  },
  { immediate: true },
)
</script>

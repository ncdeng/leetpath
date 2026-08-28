<template>
  <div>
    <!-- 1. 全局悬浮按钮（52px 圆形 accent 渐变，可拖拽） -->
    <div
      v-if="!assistant.isVisible.value && auth.me"
      class="floating-capsule"
      :class="{ 'has-context': isContextual, 'is-dragging': isDraggingCapsule }"
      :style="capsuleStyle"
      @pointerdown="onCapsulePointerDown"
      @touchstart="onCapsuleTouchStart"
      @click.capture="onCapsuleClickCapture"
      @click="onCapsuleClick"
      title="按住拖拽位置 · 点击唤起 AI 导师"
    >
      <AppIcon name="sparkle" :size="24" :stroke-width="2" />
      <span class="capsule-dot" :class="{ ready: ai.isConfigured.value }"></span>
    </div>

    <!-- 2. 悬浮智能交互窗口（macOS 磨砂面板，可拖拽/缩放/最大化） -->
    <div
      v-if="assistant.isVisible.value"
      class="floating-window-backdrop"
      :class="{ maximized: assistant.isMaximized.value }"
      @click.self="onBackdropClick"
    >
      <div
        class="floating-window"
        :class="{ 'is-max': assistant.isMaximized.value, 'is-dragging': isDraggingWindow }"
        :style="windowStyle"
        @paste="onWindowPaste"
      >
        <!-- 窗口顶栏（macOS 标题栏：左关闭圆点 · 标题居中 · 右操作组；按住可拖动） -->
        <div
          class="f-window-head"
          @pointerdown="onWindowPointerDown"
          @touchstart="onWindowTouchStart"
          title="按住顶部可自由拖动位置"
        >
          <!-- macOS 交通灯：只保留关闭红点（阻止冒泡，避免误触发拖拽） -->
          <div class="f-traffic" @mousedown.stop @pointerdown.stop @touchstart.stop>
            <button class="traffic-dot traffic-close" title="最小化收起" @click="assistant.close()">
              <AppIcon name="x" :size="9" :stroke-width="2.6" />
            </button>
          </div>

          <div class="f-head-info">
            <div class="f-head-badge">
              <AppIcon name="sparkle" :size="10" class="badge-sparkle" />
              <span class="badge-source-label">{{ contextTypeLabel }}</span>
              <span class="badge-model-tag mono">{{ ai.selectedModel.value || '未选模型' }}</span>
            </div>
            <h3 class="f-title" :title="assistant.currentContext.value.title">
              {{ assistant.currentContext.value.title }}
            </h3>
          </div>

          <div class="f-head-actions" @mousedown.stop @pointerdown.stop @touchstart.stop>
            <!-- 新建会话 / 清空记忆 -->
            <button class="win-btn" title="新建会话 / 清空历史记忆 (0 Token 重置)" @click="onNewChat">
              <AppIcon name="plus" :size="15" />
            </button>
            <!-- 智能压缩上下文 -->
            <button
              v-if="messages.length > 2"
              class="win-btn"
              title="智能压缩上下文（提炼关键要点，释放 Token）"
              :disabled="generating"
              @click="onCompressContext"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="4 14 10 14 10 20" />
                <polyline points="20 10 14 10 14 4" />
                <line x1="14" y1="10" x2="21" y2="3" />
                <line x1="3" y1="21" x2="10" y2="14" />
              </svg>
            </button>
            <!-- 设置按钮 -->
            <button class="win-btn" title="AI 设置与模型配置" @click="showSettings = true">
              <AppIcon name="gear" :size="15" />
            </button>
            <!-- 居中复位 -->
            <button
              v-if="!assistant.isMaximized.value"
              class="win-btn"
              title="复位窗口位置"
              @click="resetWindowPos"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="22" y1="12" x2="18" y2="12" />
                <line x1="6" y1="12" x2="2" y2="12" />
                <line x1="12" y1="6" x2="12" y2="2" />
                <line x1="12" y1="22" x2="12" y2="18" />
              </svg>
            </button>
            <!-- 最大化/还原 -->
            <button
              class="win-btn"
              :title="assistant.isMaximized.value ? '还原' : '最大化'"
              @click="assistant.toggleMaximize()"
            >
              <svg v-if="!assistant.isMaximized.value" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              </svg>
              <svg v-else viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="6" y="9" width="14" height="12" rx="1.5" />
                <path d="M4 15V5a1 1 0 0 1 1-1h10" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 未配置 API Key 引导 -->
        <div v-if="!ai.isConfigured.value" class="f-config-guide">
          <div class="guide-icon"><AppIcon name="sparkle" :size="18" /></div>
          <div class="guide-text">
            <h4>尚未配置大模型 API Key</h4>
            <p>
              已默认接入 Antithor 专属中转站，可
              <a href="https://api.antithor.asia" target="_blank" rel="noopener noreferrer" class="guide-link">点击登录 antithor 获取 key ↗</a>
            </p>
          </div>
          <button class="btn btn-xs btn-primary guide-btn" @click="showSettings = true">
            一键配置
          </button>
        </div>

        <!-- 场景化快捷追问 Chips -->
        <div
          v-if="assistant.currentContext.value.presetPrompts?.length"
          class="f-chips-wrapper"
        >
          <div class="f-chips-track">
            <button
              v-for="p in assistant.currentContext.value.presetPrompts"
              :key="p.label"
              class="chip-pill"
              :disabled="generating"
              @click="onSendPrompt(p.prompt)"
            >
              {{ p.label }}
            </button>
          </div>
        </div>

        <!-- 对话流消息区域 -->
        <div class="f-messages-container" ref="msgContainer">
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="msg-bubble-group"
            :class="`role-${msg.role}`"
          >
            <!-- 头像标识 -->
            <div class="msg-avatar">
              <div v-if="msg.role === 'assistant'" class="assistant-avatar-badge">
                <AppIcon name="sparkle" :size="13" />
              </div>
              <div v-else class="user-avatar-badge">
                {{ (auth.me?.username || 'U').slice(0, 1).toUpperCase() }}
              </div>
            </div>

            <!-- 消息主体 -->
            <div class="msg-card">
              <div class="msg-header">
                <span class="msg-sender">
                  {{ msg.role === 'assistant' ? (ai.selectedModel.value ? `AI 导师 · ${ai.selectedModel.value}` : 'AI 导师') : '我' }}
                </span>
                <div class="msg-actions" v-if="msg.role === 'assistant'">
                  <span v-if="msg.isCached" class="tag-cache" title="已从本地浏览器 0 Token 秒级读取">
                    <AppIcon name="sparkle" :size="9" /> 0 Token 缓存
                  </span>
                  <button
                    v-if="msg.isCached && msg.originalPrompt"
                    class="btn-text-action"
                    :disabled="generating"
                    @click="onSendPrompt(msg.originalPrompt, true)"
                  >
                    <AppIcon name="refresh" :size="11" /> 重新生成
                  </button>
                  <button
                    v-if="msg.content"
                    class="btn-text-action"
                    @click="copyText(typeof msg.content === 'string' ? msg.content : '')"
                  >
                    复制
                  </button>
                </div>
              </div>

              <div v-if="msg.images?.length" class="msg-images">
                <img v-for="(src, imgIdx) in msg.images" :key="imgIdx" :src="src" alt="粘贴的截图" />
              </div>
              <div class="msg-markdown statement" v-html="renderMd(typeof msg.content === 'string' ? msg.content : '')"></div>
            </div>
          </div>

          <!-- 正在流式生成状态 -->
          <div v-if="generating" class="msg-bubble-group role-assistant">
            <div class="msg-avatar">
              <div class="assistant-avatar-badge pulsing">
                <AppIcon name="sparkle" :size="13" />
              </div>
            </div>
            <div class="msg-card">
              <div class="msg-header">
                <span class="msg-sender">AI 导师正在深度思考生成中...</span>
              </div>
              <div class="msg-markdown statement" v-html="renderMd(streamBuffer || '...')"></div>
              <span class="typing-cursor"></span>
            </div>
          </div>
        </div>

        <!-- 底部输入框区域 -->
        <div class="f-bottom-composer">
          <div class="composer-box" @mousedown.stop @paste="onComposerPaste">
            <div v-if="pendingImages.length" class="composer-previews">
              <div v-for="(src, idx) in pendingImages" :key="idx" class="composer-preview">
                <img :src="src" alt="待发送截图" />
                <button type="button" class="preview-remove" title="去掉这张图" @click="pendingImages.splice(idx, 1)"><AppIcon name="x" :size="10" :stroke-width="2.5" /></button>
              </div>
            </div>
            <textarea
              ref="composerEl"
              v-model="inputQuestion"
              class="composer-textarea"
              placeholder="输入疑问，可粘贴文字或截图... (Enter 发送)"
              rows="2"
              :disabled="generating"
              @keydown.enter.exact.prevent="onEnterSend"
              @paste="onComposerPaste"
            ></textarea>
            
            <div class="composer-toolbar">
              <div class="composer-status">
                <span class="status-shield" :class="tokenLevelClass" :title="`当前会话预估已占用 ${currentTotalTokens} Tokens，总预算上限 ${ai.maxContextTokens.value} Tokens`">
                  <AppIcon name="sparkle" :size="11" /> 记忆占用: {{ formatTokens(currentTotalTokens) }} / {{ formatTokens(ai.maxContextTokens.value) }} ({{ tokenPercent }}%)
                </span>
              </div>
              
              <div class="composer-actions">
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
                  class="btn-attach"
                  title="添加截图"
                  :disabled="generating"
                  @click="fileEl?.click()"
                >
                  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <circle cx="8.5" cy="8.5" r="1.5" />
                    <polyline points="21 15 16 10 5 21" />
                  </svg>
                </button>
                <button
                  v-if="generating"
                  class="btn-stop"
                  @click="abort"
                >
                  <span class="stop-icon"></span> 停止
                </button>
                <button
                  v-else
                  class="btn-send"
                  :disabled="(!inputQuestion.trim() && !pendingImages.length) || !ai.isConfigured.value"
                  @click="onSendPrompt(inputQuestion)"
                  title="发送提问 (Enter)"
                >
                  <AppIcon name="send" :size="14" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 右下角拉伸角标 -->
        <div class="f-resize-corner" title="拖动右下角拉伸窗口">
          <svg viewBox="0 0 10 10" width="10" height="10" fill="none" stroke="currentColor">
            <line x1="8" y1="2" x2="2" y2="8" stroke-width="1.5" />
            <line x1="8" y1="5" x2="5" y2="8" stroke-width="1.5" />
            <line x1="8" y1="8" x2="8" y2="8" stroke-width="1.5" />
          </svg>
        </div>
      </div>
    </div>

    <!-- AI 设置弹窗 -->
    <AiSettingsModal v-if="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AiSettingsModal from './AiSettingsModal.vue'
import AppIcon from './AppIcon.vue'
import {
  CAPSULE_FALLBACK_SIZE,
  WINDOW_FALLBACK_SIZE,
  bottomClearancePx,
  clampPoint,
  createDragSession,
  dragSessionMove,
  isFloatingSheet,
  loadLauncherChrome,
  parseCssPx,
  rectSize,
  saveLauncherChrome,
  type DragSession,
  type Point,
  type Size,
} from '../aiLauncherChrome'
import { renderMarkdown } from '../markdown'
import { copyToClipboard } from '../clipboard'
import { estimateTokens, messagePlainText, useAiStore, type AiMessage } from '../stores/ai'
import { useAiAssistant } from '../stores/aiAssistant'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../stores/toast'
import { compressPickedFiles, insertAtCursor, readClipboard, toApiContent } from '../aiPaste'

interface ChatMessage extends AiMessage {
  isCached?: boolean
  originalPrompt?: string
  images?: string[]
}

const auth = useAuthStore()
const ai = useAiStore()
const assistant = useAiAssistant()
const toast = useToast()

const showSettings = ref(false)
const generating = ref(false)
const inputQuestion = ref('')
const pendingImages = ref<string[]>([])
const streamBuffer = ref('')
const messages = ref<ChatMessage[]>([])
const msgContainer = ref<HTMLElement | null>(null)
const composerEl = ref<HTMLTextAreaElement | null>(null)
const fileEl = ref<HTMLInputElement | null>(null)
let abortController: AbortController | null = null

// --- 窗口自由拖拽与尺寸管理 ---
const isDraggingWindow = ref(false)
const isDraggingCapsule = ref(false)
let hasMovedCapsule = false
let suppressCapsuleClick = false
let ignoreCapsuleClickUntil = 0
let capsuleDragKind: 'pointer' | 'touch' | null = null
let windowDragKind: 'pointer' | 'touch' | null = null
let capsuleDrag: DragSession | null = null
let windowDrag: DragSession | null = null
let capsuleDragSize: Size = CAPSULE_FALLBACK_SIZE
let windowDragSize: Size = WINDOW_FALLBACK_SIZE
let stopActiveDrag: (() => void) | null = null

function browserStorage(): Storage | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

const savedChrome = typeof window !== 'undefined' ? loadLauncherChrome(browserStorage()) : {}

// 悬浮窗口坐标与初始宽高（大幅加大默认尺寸：宽 580px，高 740px）
const windowPos = ref<Point>(
  savedChrome.window
    ?? {
      x: typeof window !== 'undefined' ? Math.max(20, window.innerWidth - 620) : 100,
      y: typeof window !== 'undefined' ? Math.max(20, window.innerHeight - 780) : 40,
    },
)

// 悬浮球坐标；null 时走 CSS 默认（移动端停在底栏上方，不盖题面）
const capsulePos = ref<{ x: number | null; y: number | null }>(
  savedChrome.capsule ? savedChrome.capsule : { x: null, y: null },
)

const isContextual = computed(() => assistant.currentContext.value.source !== 'general')

const contextTypeLabel = computed(() => {
  const src = assistant.currentContext.value.source
  if (src === 'problem') return '力扣手撕'
  if (src === 'review') return '背题模式'
  if (src === 'quiz') return '八股自测'
  return '技术导师'
})

const contextBadgeText = computed(() => {
  const src = assistant.currentContext.value.source
  if (src === 'problem') return '当前题目'
  if (src === 'review') return '背题助手'
  if (src === 'quiz') return '八股考点'
  return ai.selectedModel.value ? ai.selectedModel.value.slice(0, 10) : '未配置'
})

// 窗口动态样式
const windowStyle = computed(() => {
  if (assistant.isMaximized.value) return {}
  return {
    left: `${windowPos.value.x}px`,
    top: `${windowPos.value.y}px`,
  }
})

// 胶囊动态样式
const capsuleStyle = computed(() => {
  if (capsulePos.value.x === null || capsulePos.value.y === null) return {}
  return {
    left: `${capsulePos.value.x}px`,
    top: `${capsulePos.value.y}px`,
    right: 'auto',
    bottom: 'auto',
  }
})

function viewportSize() {
  return { width: window.innerWidth, height: window.innerHeight }
}

function readBottomNavHeight(): number {
  return parseCssPx(getComputedStyle(document.documentElement).getPropertyValue('--bottom-nav-h'))
}

function capsuleBottomReserve(): number {
  return bottomClearancePx({
    viewportWidth: window.innerWidth,
    navHeight: readBottomNavHeight(),
  })
}

function clampCapsule(point: Point, size: Size = CAPSULE_FALLBACK_SIZE): Point {
  return clampPoint(point, viewportSize(), size, {
    bottomReserve: capsuleBottomReserve(),
    rightReserve: 8,
  })
}

function clampWindow(point: Point, size: Size = WINDOW_FALLBACK_SIZE): Point {
  return clampPoint(point, viewportSize(), size, {
    minLeft: 0,
    minTop: 0,
    bottomReserve: 24,
    rightReserve: 24,
  })
}

function persistCapsule() {
  if (capsulePos.value.x === null || capsulePos.value.y === null) return
  saveLauncherChrome(browserStorage(), { capsule: { x: capsulePos.value.x, y: capsulePos.value.y } })
}

function persistWindow() {
  saveLauncherChrome(browserStorage(), { window: { ...windowPos.value } })
}

function resetWindowPos() {
  windowPos.value = {
    x: Math.max(20, window.innerWidth - 620),
    y: Math.max(20, window.innerHeight - 780),
  }
  persistWindow()
  toast.info('已复位悬浮窗位置')
}

function preventTouchScroll(e: TouchEvent) {
  if (e.cancelable) e.preventDefault()
}

function bindDragListeners(kind: 'pointer' | 'touch', onMove: (e: Event) => void, onUp: () => void) {
  stopActiveDrag?.()
  if (kind === 'pointer') {
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)
    window.addEventListener('pointercancel', onUp)
  } else {
    window.addEventListener('touchmove', onMove, { passive: false })
    window.addEventListener('touchend', onUp)
    window.addEventListener('touchcancel', onUp)
  }
  window.addEventListener('touchmove', preventTouchScroll, { passive: false })
  stopActiveDrag = () => {
    unbindDragListeners(kind, onMove, onUp)
    stopActiveDrag = null
  }
}

function unbindDragListeners(kind: 'pointer' | 'touch', onMove: (e: Event) => void, onUp: () => void) {
  if (kind === 'pointer') {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    window.removeEventListener('pointercancel', onUp)
  } else {
    window.removeEventListener('touchmove', onMove)
    window.removeEventListener('touchend', onUp)
    window.removeEventListener('touchcancel', onUp)
  }
  window.removeEventListener('touchmove', preventTouchScroll)
}

function clientPoint(e: Event, pointerId?: number): Point | null {
  if ('clientX' in e && typeof (e as PointerEvent).clientX === 'number' && !('touches' in e)) {
    return { x: (e as PointerEvent).clientX, y: (e as PointerEvent).clientY }
  }
  const te = e as TouchEvent
  const list = te.touches?.length ? te.touches : te.changedTouches
  if (!list?.length) return null
  if (pointerId != null) {
    for (let i = 0; i < list.length; i++) {
      if (list[i].identifier === pointerId) return { x: list[i].clientX, y: list[i].clientY }
    }
  }
  return { x: list[0].clientX, y: list[0].clientY }
}

function beginCapsuleDrag(clientX: number, clientY: number, el: HTMLElement, kind: 'pointer' | 'touch') {
  capsuleDragKind = kind
  hasMovedCapsule = false
  isDraggingCapsule.value = false
  const rect = el.getBoundingClientRect()
  capsuleDragSize = rectSize(rect, CAPSULE_FALLBACK_SIZE)
  capsuleDrag = createDragSession(clientX, clientY, { x: rect.left, y: rect.top })

  const onMove = (ev: Event) => {
    if (!capsuleDrag) return
    if (kind === 'touch' && ev.cancelable) (ev as TouchEvent).preventDefault()
    const pt = clientPoint(ev)
    if (!pt) return
    const next = dragSessionMove(capsuleDrag, pt.x, pt.y)
    if (!capsuleDrag.moved) return
    hasMovedCapsule = true
    suppressCapsuleClick = true
    isDraggingCapsule.value = true
    capsulePos.value = clampCapsule(next, capsuleDragSize)
  }

  const onUp = () => {
    stopActiveDrag?.()
    const moved = capsuleDrag?.moved
    capsuleDrag = null
    capsuleDragKind = null
    isDraggingCapsule.value = false
    if (moved) {
      suppressCapsuleClick = true
      ignoreCapsuleClickUntil = Date.now() + 500
      persistCapsule()
    }
  }

  bindDragListeners(kind, onMove, onUp)
}

function onCapsulePointerDown(e: PointerEvent) {
  if (e.pointerType === 'mouse' && e.button !== 0) return
  if (capsuleDragKind) return
  if (e.pointerType === 'touch') {
    // iOS also sends touch events; handle those so we can preventDefault on touchmove.
    return
  }
  const el = e.currentTarget as HTMLElement
  try {
    el.setPointerCapture(e.pointerId)
  } catch {
    /* capture is optional */
  }
  beginCapsuleDrag(e.clientX, e.clientY, el, 'pointer')
}

function onCapsuleTouchStart(e: TouchEvent) {
  if (capsuleDragKind) return
  if (e.touches.length !== 1) return
  const t = e.touches[0]
  beginCapsuleDrag(t.clientX, t.clientY, e.currentTarget as HTMLElement, 'touch')
}

function shouldIgnoreCapsuleClick() {
  return hasMovedCapsule || suppressCapsuleClick || Date.now() < ignoreCapsuleClickUntil
}

function onCapsuleClickCapture(e: MouseEvent) {
  if (shouldIgnoreCapsuleClick()) {
    e.preventDefault()
    e.stopImmediatePropagation()
  }
}

function onCapsuleClick() {
  if (shouldIgnoreCapsuleClick()) return
  assistant.toggle()
}

function eventElement(target: EventTarget | null): Element | null {
  if (!target) return null
  if (target instanceof Element) return target
  return (target as Node).parentElement
}

function canDragFloatingWindow(target: EventTarget | null): boolean {
  if (assistant.isMaximized.value) return false
  if (isFloatingSheet(window.innerWidth)) return false
  if (eventElement(target)?.closest('.f-head-actions')) return false
  return true
}

function beginWindowDrag(clientX: number, clientY: number, el: HTMLElement, kind: 'pointer' | 'touch') {
  windowDragKind = kind
  isDraggingWindow.value = false
  const rect = el.closest('.floating-window')?.getBoundingClientRect()
  windowDragSize = rectSize(rect, WINDOW_FALLBACK_SIZE)
  windowDrag = createDragSession(clientX, clientY, { ...windowPos.value })

  const onMove = (ev: Event) => {
    if (!windowDrag) return
    if (kind === 'touch' && ev.cancelable) (ev as TouchEvent).preventDefault()
    const pt = clientPoint(ev)
    if (!pt) return
    const next = dragSessionMove(windowDrag, pt.x, pt.y)
    if (!windowDrag.moved) return
    isDraggingWindow.value = true
    windowPos.value = clampWindow(next, windowDragSize)
  }

  const onUp = () => {
    stopActiveDrag?.()
    const moved = windowDrag?.moved
    windowDrag = null
    windowDragKind = null
    isDraggingWindow.value = false
    if (moved) persistWindow()
  }

  bindDragListeners(kind, onMove, onUp)
}

function onWindowPointerDown(e: PointerEvent) {
  if (e.pointerType === 'mouse' && e.button !== 0) return
  if (windowDragKind) return
  if (e.pointerType === 'touch') return
  if (!canDragFloatingWindow(e.target)) return
  const el = e.currentTarget as HTMLElement
  try {
    el.setPointerCapture(e.pointerId)
  } catch {
    /* capture is optional */
  }
  beginWindowDrag(e.clientX, e.clientY, el, 'pointer')
}

function onWindowTouchStart(e: TouchEvent) {
  if (windowDragKind) return
  if (e.touches.length !== 1) return
  if (!canDragFloatingWindow(e.target)) return
  const t = e.touches[0]
  beginWindowDrag(t.clientX, t.clientY, e.currentTarget as HTMLElement, 'touch')
}

function onViewportChange() {
  const size = viewportSize()
  if (capsulePos.value.x !== null && capsulePos.value.y !== null) {
    capsulePos.value = clampCapsule({ x: capsulePos.value.x, y: capsulePos.value.y })
  }
  if (!isFloatingSheet(size.width) && !assistant.isMaximized.value) {
    windowPos.value = clampWindow(windowPos.value)
  }
}

function onBackdropClick() {
  if (assistant.isMaximized.value) {
    assistant.close()
  }
}

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
  onSendPrompt(inputQuestion.value)
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

async function onWindowPaste(e: ClipboardEvent) {
  const target = e.target as HTMLElement | null
  if (target && (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT' || target.isContentEditable)) {
    return
  }
  e.preventDefault()
  const ok = await handlePasteData(e.clipboardData)
  if (ok) composerEl.value?.focus()
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

async function onSendPrompt(userPrompt: string, forceRefresh = false) {
  const attached = pendingImages.value.slice()
  if (!userPrompt.trim() && !attached.length) return
  if (!ai.isConfigured.value) {
    showSettings.value = true
    return
  }

  const promptText = userPrompt.trim() || (attached.length ? '（见附图）' : '')
  inputQuestion.value = ''
  pendingImages.value = []

  const ctx = assistant.currentContext.value
  const cKey = ctx.contextKey || 'general'

  // 1. 检查本地响应缓存（0 Token 秒级读取）
  if (!forceRefresh && ai.enableLocalCache.value) {
    const cached = ai.getCachedAnswer(cKey, promptText)
    if (cached) {
      messages.value.push({ role: 'user', content: promptText, images: attached })
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

  // 2. 发起真实流式请求
  messages.value.push({ role: 'user', content: promptText, images: attached })
  scrollToBottom()

  generating.value = true
  streamBuffer.value = ''
  abortController = new AbortController()

  const sysContent = `你是一位资深的技术面试官与计算机/大模型教学导师。
请针对用户目前正在练习或背诵的题目提供深入浅出、极具洞察力的解答。
回答要求：
1. 若询问【更多解法】，请按思维演进清晰罗列（如：暴力法 ➔ 空间换时间哈希法 ➔ 双指针/单调栈最优解），并逐一分析时空复杂度与优缺点；
2. 若询问【记忆口诀/核心代码模板】，请提炼极简、易背、不易写错的骨架；
3. 如涉及代码，请给出清晰注释；如涉及数学公式，使用标准 LaTeX 格式。

【当前题目/学习上下文】：
${ctx.contextText || '无特定上下文'}`

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

function formatTokens(n: number): string {
  if (n >= 1048576) return `${(n / 1048576).toFixed(1)}M`
  if (n >= 1024) return `${(n / 1024).toFixed(0)}K`
  return `${n}`
}

const currentTotalTokens = computed(() => {
  const ctx = assistant.currentContext.value
  let total = estimateTokens(ctx.contextText || '') + 200
  for (const m of messages.value) {
    total += estimateTokens(messagePlainText(m.content))
  }
  if (streamBuffer.value) {
    total += estimateTokens(streamBuffer.value)
  }
  return total
})

const tokenPercent = computed(() => {
  const budget = ai.maxContextTokens.value || 131072
  return Math.min(100, Math.round((currentTotalTokens.value / budget) * 100))
})

const tokenLevelClass = computed(() => {
  if (tokenPercent.value > 85) return 'token-danger'
  if (tokenPercent.value > 60) return 'token-warning'
  return 'token-normal'
})

function onNewChat() {
  if (generating.value) abort()
  messages.value = [
    {
      role: 'assistant',
      content: `✨ 已为你开启全新会话！\n\n已清空上一轮历史对话，Token 计数已重置归零。当前锚定 **${assistant.currentContext.value.title}**，你可以随时输入新疑问或点击上方快捷芯片！`,
    },
  ]
  toast.success('已新建会话，历史记忆已清空重置')
}

async function onCompressContext() {
  if (generating.value || messages.value.length <= 1) return

  const promptText = '请将我们上方全部讨论过的核心解法、代码要点与关键结论，精炼压缩为 3-4 条极简核心知识备忘（保留关键思路，删除多余废话）。'
  toast.info('正在智能压缩历史上下文要点...')

  await onSendPrompt(promptText, true)

  // 压缩完毕后，把历史多轮消息归约成一条精简摘要
  const lastReply = messages.value[messages.value.length - 1]
  if (lastReply && lastReply.role === 'assistant') {
    messages.value = [
      {
        role: 'assistant',
        content: `🗜️ **[已压缩历史上下文备忘]**：\n\n${lastReply.content}\n\n*(历史长对话已智能精简压缩，释放了大量 Token 空间，你可以顺着以上要点继续提问)*`,
      },
    ]
    toast.success('上下文压缩完毕！已释放大部分 Token 空间')
  }
}

// 监听上下文切换时重置会话并提示
watch(
  () => assistant.currentContext.value.contextKey,
  (newKey, oldKey) => {
    if (newKey !== oldKey) {
      messages.value = [
        {
          role: 'assistant',
          content: `👋 你好！已为你锁定当前 **${assistant.currentContext.value.title}**。\n\n你可以点击下方的**快捷追问**（例如查看*更多解法*、*时空优化*、*记忆口诀*），或直接输入你的疑问！`,
        },
      ]
    }
  },
  { immediate: true },
)

// 监听待发送的 pendingPrompt
watch(
  () => assistant.pendingPrompt.value,
  (prompt) => {
    if (prompt) {
      assistant.pendingPrompt.value = null
      onSendPrompt(prompt)
    }
  },
)

onMounted(() => {
  if (typeof window === 'undefined') return
  const saved = loadLauncherChrome(browserStorage())
  if (saved.capsule) {
    capsulePos.value = clampCapsule(saved.capsule)
  }
  if (saved.window) {
    windowPos.value = clampWindow(saved.window)
  } else {
    windowPos.value = {
      x: Math.max(20, window.innerWidth - 620),
      y: Math.max(20, window.innerHeight - 780),
    }
  }
  window.addEventListener('resize', onViewportChange)
  window.visualViewport?.addEventListener('resize', onViewportChange)
})

onBeforeUnmount(() => {
  stopActiveDrag?.()
  window.removeEventListener('resize', onViewportChange)
  window.visualViewport?.removeEventListener('resize', onViewportChange)
})
</script>

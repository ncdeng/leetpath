<template>
  <div class="container" :class="{ 'zen-container': isZen }">
    <div v-if="loading" class="card" style="padding:24px;margin-top:20px">
      <Skeleton :count="1" height="32px" width="40%" radius="6px" gap="14px" />
      <Skeleton :count="3" height="18px" width="85%" radius="6px" gap="10px" />
      <div style="margin-top:30px">
        <Skeleton :count="6" height="24px" width="100%" radius="6px" gap="12px" />
      </div>
    </div>
    <div v-else-if="!problem" class="empty">题目不存在或未发布</div>
    <template v-else>
      <!-- 移动端 Tabs -->
      <div class="mobile-tabs">
        <button :class="{ active: tab === 'statement' }" @click="tab = 'statement'">题面</button>
        <button :class="{ active: tab === 'solution' }" @click="tab = 'solution'">
          题解<span v-if="problem.has_solution"> ·</span>
        </button>
        <button :class="{ active: tab === 'code' }" @click="tab = 'code'">代码</button>
        <button :class="{ active: tab === 'result' }" @click="tab = 'result'">
          结果<span v-if="submission && !isFinal(submission.status)"> ·</span>
        </button>
      </div>

      <!-- 顶部辅助工具栏（全屏/禅模式、计时器） -->
      <div class="workspace-bar">
        <div class="workspace-left">
          <RouterLink to="/problems" class="btn btn-sm back-link"><AppIcon name="arrow-left" :size="14" /> 返回题库</RouterLink>
          <span class="problem-title-inline">{{ problemHeading(problem) }}</span>
          <span class="badge" :class="`badge-${problem.difficulty}`">{{ difficultyText }}</span>
        </div>

        <div class="workspace-right">
          <!-- 计时器 -->
          <div class="stopwatch-badge" :class="{ running: timerRunning, urgent: timerMode === 'countdown' && timerSeconds <= 300 }">
            <span class="timer-icon"><AppIcon name="clock" :size="13" /></span>
            <span class="timer-text mono">{{ formattedTimer }}</span>
            <button class="timer-btn" :title="timerRunning ? '暂停' : '开始'" @click="toggleTimer">
              <span v-if="timerRunning" class="pause-glyph"></span>
              <AppIcon v-else name="play" :size="12" />
            </button>
            <button class="timer-btn" title="重置计时器" @click="resetTimer"><AppIcon name="refresh" :size="12" /></button>
            <button class="timer-btn mode-btn" :title="timerMode === 'stopwatch' ? '切换为30分钟面试倒计时' : '切换为正向计时'" @click="toggleTimerMode">
              {{ timerMode === 'stopwatch' ? '倒计时' : '正计时' }}
            </button>
          </div>

          <!-- 禅模式切换 -->
          <button class="btn btn-sm zen-btn" :class="{ active: isZen }" :title="isZen ? '退出禅模式 (Esc)' : '开启沉浸禅模式'" @click="isZen = !isZen">
            <template v-if="isZen"><AppIcon name="x" :size="13" /> 退出全屏</template>
            <template v-else><AppIcon name="sparkle" :size="13" /> 禅模式</template>
          </button>
        </div>
      </div>

      <div
        class="problem-layout"
        :class="{ 'is-dragging': isDragging }"
        :style="isDesktop ? { gridTemplateColumns: `${splitRatio}% 6px calc(${100 - splitRatio}% - 6px)` } : {}"
      >
        <!-- 左侧面板：题面 / 题解 -->
        <section ref="statementPaneRef" class="pane pane-statement card statement" v-show="isDesktop || tab === 'statement' || tab === 'solution'">
          <!-- 桌面端左面板 Tab（题面 / 题解思路） -->
          <div class="pane-tab-bar" v-if="isDesktop">
            <button class="pane-tab" :class="{ active: leftPaneTab === 'statement' }" @click="leftPaneTab = 'statement'">
              题目描述
            </button>
            <button class="pane-tab" :class="{ active: leftPaneTab === 'solution' }" @click="leftPaneTab = 'solution'">
              题解
            </button>
          </div>

          <!-- 题面内容 -->
          <div v-show="!isDesktop ? tab === 'statement' : leftPaneTab === 'statement'">
            <h1 class="statement-title">{{ problemHeading(problem) }}</h1>
            <div class="problem-meta">
              <span class="badge" :class="`badge-${problem.difficulty}`">{{ difficultyText }}</span>
              <span v-for="label in sourceBadgeTexts(problem)" :key="label" class="badge badge-source">{{ label }}</span>
              <span v-for="t in problem.tags" :key="t" class="badge badge-tag">{{ t }}</span>
            </div>
            <div class="problem-limits">时间限制 {{ problem.time_limit_ms / 1000 }}s · 内存限制 {{ problem.memory_limit_mb }}MB</div>

            <div class="markdown-body" v-html="statementHtml"></div>

            <!-- 历史提交记录 -->
            <div class="sub-history" v-if="history.length > 0">
              <h3>我的提交 ({{ history.length }})</h3>
              <div v-for="s in history" :key="s.id" class="sub-item">
                <div class="sub-line" @click="toggleHistory(s.id)">
                  <StatusBadge :status="s.status" />
                  <span class="mono sub-lang">{{ s.language === 'cpp' ? 'C++' : 'Python3' }}</span>
                  <span class="mono sub-io">{{ s.io_mode === 'leetcode' ? '力扣' : 'ACM' }}</span>
                  <span v-if="s.runtime_ms !== null" class="sub-runtime">{{ s.runtime_ms }}ms</span>
                  <span class="sub-time">{{ formatTime(s.created_at) }}</span>
                </div>
                <div v-if="expandedHistory.has(s.id)" class="history-code-box">
                  <div class="history-code-actions">
                    <button class="btn btn-xs" @click.stop="loadCodeIntoEditor(historyCode[s.id], s.language, s.io_mode || 'acm')">
                      载入编辑器
                    </button>
                    <button class="btn btn-xs" @click.stop="copyCode(historyCode[s.id])">
                      复制代码
                    </button>
                  </div>
                  <pre class="history-pre">{{ historyCode[s.id] }}</pre>
                </div>
              </div>
            </div>
          </div>

          <!-- 题解内容 -->
          <div v-show="!isDesktop ? tab === 'solution' : leftPaneTab === 'solution'" class="solution-pane-wrap">
            <h2 class="solution-title">
              <span>{{ problemHeading(problem) }} · 题解（多种解法）</span>
            </h2>
            <div v-if="solutionLoading" class="empty" style="padding:24px 0">题解加载中…</div>
            <div v-else-if="solutionHtml" class="markdown-body rc-solution" v-html="solutionHtml"></div>
            <div v-else class="empty" style="padding:24px 0">该题目题解正在整理中…</div>
          </div>
        </section>

        <!-- 桌面端分栏拖拽手柄 -->
        <div
          v-if="isDesktop"
          class="split-resizer"
          :class="{ active: isDragging }"
          title="拖动调整左右分栏宽度"
          @mousedown="onMouseDownResizer"
        >
          <div class="resizer-line"></div>
        </div>

        <!-- 右侧面板：代码编辑器 + 评测结果 -->
        <section class="pane pane-right" v-show="isDesktop || tab === 'code' || tab === 'result'">
          <div class="card" v-show="isDesktop || tab === 'code'">
            <div class="editor-toolbar">
              <!-- 语言由顶栏全局偏好统一控制，此处只读展示 -->
              <span class="editor-lang-label mono" title="在页面右上角切换全局语言">{{ language === 'cpp' ? 'C++ (C++20)' : 'Python3' }}</span>
              <div class="segmented mode-switch" role="group" aria-label="评测模式">
                <button
                  type="button"
                  :class="{ active: ioMode === 'acm' }"
                  title="ACM 模式：自己读 stdin、写 stdout"
                  @click="setMode('acm')"
                >ACM</button>
                <button
                  type="button"
                  :class="{ active: ioMode === 'leetcode' }"
                  :disabled="!problem.leetcode_available"
                  :title="problem.leetcode_available ? '力扣模式：只写 class Solution / 设计类，签名与力扣一致' : '本题暂不支持力扣函数模式'"
                  @click="setMode('leetcode')"
                >力扣</button>
              </div>

              <button class="btn btn-primary btn-sm" :disabled="submitting" @click="submit" title="快捷键: Ctrl + Enter">
                {{ submitting ? '评测中…' : '提交评测' }}
              </button>

              <button
                class="btn btn-sm btn-outline ai-btn"
                @click="openAiDrawer"
                title="让 AI 助教帮我找茬、分析复杂度或提供递进思路"
              >
                <AppIcon name="robot" :size="14" /> AI 助教
              </button>

              <button class="btn btn-sm btn-ghost" @click="confirmResetCode" title="重置为初始模板代码">
                重置
              </button>

              <span class="save-hint" :title="saveHint">{{ saveHint }}</span>
              <span class="shortcut-tip" v-if="isDesktop">Ctrl+Enter 提交 · Ctrl+S 保存</span>
            </div>
            <div class="acm-hint">
              <p class="acm-hint-full">{{ acmHintFull }}</p>
              <details class="acm-hint-mobile">
                <summary>{{ acmHintShort }}</summary>
                <p class="acm-hint-expanded">{{ acmHintFull }}</p>
              </details>
              <RouterLink to="/handbook" class="acm-hint-link">写法对比 · 极速 I/O 模板 →</RouterLink>
            </div>
            <Editor v-model="code" :language="language" />
          </div>

          <!-- 评测结果面板 -->
          <div class="card result-panel" v-show="isDesktop || tab === 'result'">
            <div class="result-body">
              <div v-if="!submission" class="empty" style="padding:24px 0">
                <p>提交后在这里查看实时评测结果</p>
                <span class="result-empty-note">支持 Python 3 / C++，可切换 ACM 标准输入输出或力扣函数模式</span>
              </div>
              <template v-else>
                <div class="result-head">
                  <StatusBadge :status="submission.status" />
                  <span v-if="submission.runtime_ms !== null" class="runtime">总耗时 {{ submission.runtime_ms }}ms</span>
                </div>
                <div v-if="submission.compile_output" class="io-block">
                  <div class="io-label">编译 / 系统诊断输出</div>
                  <pre class="mono compile-pre">{{ submission.compile_output }}</pre>
                </div>
                <div v-for="tc in submission.detail ?? []" :key="tc.ordinal">
                  <div class="tc-row" :style="tc.is_sample ? 'cursor:pointer' : ''" @click="tc.is_sample && toggleTc(tc.ordinal)">
                    <span class="tc-ord">#{{ tc.ordinal }}</span>
                    <span v-if="tc.is_sample" class="tc-sample">样例</span>
                    <span class="status-pill tc-status" :class="'st-' + tc.status.toLowerCase()">{{ tc.status }}</span>
                    <span class="tc-time">{{ tc.runtime_ms ?? '-' }}ms</span>
                  </div>
                  <div v-if="tc.is_sample && expandedTc.has(tc.ordinal)" class="tc-detail">
                    <div class="io-block">
                      <div class="io-label">输入</div>
                      <pre>{{ tc.input }}</pre>
                    </div>
                    <div class="io-block">
                      <div class="io-label">期望输出</div>
                      <pre>{{ tc.expected }}</pre>
                    </div>
                    <div class="io-block">
                      <div class="io-label">你的输出</div>
                      <pre>{{ tc.output ?? '(无)' }}</pre>
                    </div>
                  </div>
                  <div v-if="tc.stderr" class="tc-detail">
                    <div class="io-block">
                      <div class="io-label">错误输出</div>
                      <pre>{{ tc.stderr }}</pre>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </section>
      </div>
    </template>

  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import {
  DraftSaveQueue,
  createGenerationGate,
  type DraftKey,
  type DraftSnapshot,
  type FlushResult,
} from '../problemDraftSession'
import AppIcon from '../components/AppIcon.vue'
import Editor from '../components/Editor.vue'
import Skeleton from '../components/Skeleton.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useToast } from '../stores/toast'
import { useIoModePref, useLangPref } from '../stores/pref'
import { useStudyPlan } from '../stores/plan'
import { renderMarkdown, filterSolutionMarkdown } from '../markdown'
import { copyToClipboard } from '../clipboard'
import {
  isFinal,
  problemHeading,
  sourceBadgeTexts,
  type Draft,
  type IoMode,
  type Language,
  type ProblemDetail,
  type Submission,
} from '../types'

const route = useRoute()
const slug = computed(() => route.params.slug as string)
const toast = useToast()
const { langPref, setLang } = useLangPref()
const { ioModePref, setIoMode } = useIoModePref()

const loading = ref(true)
const problem = ref<ProblemDetail | null>(null)
const language = ref<Language>(langPref.value)
const ioMode = ref<IoMode>(ioModePref.value)
const code = ref('')
const submission = ref<Submission | null>(null)
const submitting = ref(false)
const saveHint = ref('')
const history = ref<Submission[]>([])
const tab = ref<'statement' | 'solution' | 'code' | 'result'>('statement')
const leftPaneTab = ref<'statement' | 'solution'>('statement')
const statementPaneRef = ref<HTMLElement | null>(null)
const isDesktop = ref(window.innerWidth >= 1024)
const isZen = ref(false)

import { useAiAssistant } from '../stores/aiAssistant'

const assistant = useAiAssistant()

function openAiDrawer() {
  updateAiContext()
  assistant.openWithContext(assistant.currentContext.value)
}

function updateAiContext() {
  const p = problem.value
  if (!p) return
  const sub = submission.value
  let subInfo = '当前尚未提交或评测。'
  if (sub) {
    subInfo = `最后一次评测状态：[${sub.status}]（耗时: ${sub.runtime_ms ?? '-'}ms）`
    if (sub.compile_output) {
      subInfo += `\n编译/错误输出：\n${sub.compile_output}`
    }
  }

  const prompts = []
  if (sub && sub.status !== 'AC') {
    prompts.push({
      label: `🐞 帮我找当前 [${sub.status}] 的 Bug`,
      prompt: `我的代码提交评测结果为 [${sub.status}]。请检查我的代码中可能遗漏的极端边界条件、越界、死循环或逻辑错误。请给出思考方向和引导，不要直接给我完整代码。`,
    })
  }
  prompts.push(
    {
      label: '💡 还有更多解法吗？（多种流派对比）',
      prompt: `对于这道《${problemHeading(p)}》，除了我当前的写法外，还有哪些其他经典、进阶或不同流派的解法？（例如动态规划、单调栈、双指针、哈希等，请对比各解法的时空复杂度与优劣）`,
    },
    {
      label: '🚀 怎么优化到最优时空复杂度？',
      prompt: `请分析当前这道题的理论最优时空复杂度是多少？有哪些技巧可以将当前写法进一步降阶优化？`,
    },
    {
      label: '💡 递进式解题思路提示 (Hint)',
      prompt: '请像技术面试官一样，给我一个层层递进的思路提示（Hint 1 ➔ Hint 2 ➔ 伪代码核心思想），不要直接剧透完整实现。',
    },
    {
      label: '⏱️ 时空复杂度分析与瓶颈诊断',
      prompt: '请分析我当前代码的时间复杂度和空间复杂度分别是多少？是否存在性能瓶颈或可以优化的空间？',
    },
  )

  assistant.setContext({
    source: 'problem',
    title: `力扣 · ${problemHeading(p)}`,
    contextKey: `problem:${p.slug}`,
    contextText: `【题目】：${problemHeading(p)} (${p.difficulty} · ${p.tags.join(', ')})
【语言】：${language.value === 'cpp' ? 'C++ (C++20)' : 'Python 3'}（${ioMode.value === 'leetcode' ? '力扣函数模式，只写 Solution / 设计类' : 'ACM 模式，自己处理 stdin/stdout'}）
【评测状态】：${subInfo}

【用户当前代码】：
\`\`\`${language.value === 'cpp' ? 'cpp' : 'python'}
${code.value}
\`\`\`

【题目描述】：
${p.statement_md}`,
    presetPrompts: prompts,
  })
}

watch([problem, code, language, ioMode, submission], () => {
  updateAiContext()
})

// 分栏拖拽
const splitRatio = ref(50)
const isDragging = ref(false)

// 计时器状态
const timerSeconds = ref(0)
const timerRunning = ref(false)
const timerMode = ref<'stopwatch' | 'countdown'>('stopwatch')
let timerInterval: ReturnType<typeof setInterval> | null = null

// 题解数据
const solutionMd = ref('')
const solutionLoading = ref(false)

const expandedTc = ref(new Set<number>())
const expandedHistory = ref(new Set<number>())
const historyCode = ref<Record<number, string>>({})

let saveTimer: ReturnType<typeof setTimeout> | null = null
let pollTimer: ReturnType<typeof setTimeout> | null = null
let activeDraftKey: DraftKey | null = null
let suppressCodeTracking = false
let activePageGeneration = 0

const draftQueue = new DraftSaveQueue()
const navigationGeneration = createGenerationGate()
const pageGeneration = createGenerationGate()
const draftGeneration = createGenerationGate()
const pollGeneration = createGenerationGate()

const DRAFT_FLUSH_OPTIONS = { maxAttempts: 2, timeoutMs: 1500 } as const

// ACM 极速模板
const DEFAULT_TEMPLATES: Record<Language, string> = {
  python3: `import sys

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    # 在此编写解题代码

if __name__ == "__main__":
    solve()
`,
  cpp: `#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // 在此编写解题代码
    return 0;
}
`,
}

const cleanStatementMd = computed(() => {
  if (!problem.value) return ''
  let md = problem.value.statement_md
  md = md.replace(/^##\s*题目描述\s*\n+/i, '')
  return md
})

const statementHtml = computed(() =>
  cleanStatementMd.value ? renderMarkdown(cleanStatementMd.value) : '',
)

const solutionHtml = computed(() =>
  solutionMd.value ? renderMarkdown(filterSolutionMarkdown(solutionMd.value, language.value)) : '',
)

const difficultyText = computed(() => {
  const d = problem.value?.difficulty
  return d === 'easy' ? '简单' : d === 'medium' ? '中等' : '困难'
})

const acmHintShort = computed(() =>
  ioMode.value === 'leetcode' ? '力扣模式：只写函数 / 设计类' : 'ACM 模式：读 stdin、打印 stdout',
)
const acmHintFull = computed(() =>
  ioMode.value === 'leetcode'
    ? '力扣模式：只实现下方函数 / 设计类，签名与力扣一致。评测仍用本题用例，不必自己处理输入输出。'
    : 'ACM 模式：提交完整程序，自己读 stdin / 打印 stdout，格式以题面「输入 / 输出格式」为准',
)

const formattedTimer = computed(() => {
  const total = Math.max(0, timerSeconds.value)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

function formatTime(iso: string) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function toggleTimer() {
  if (timerRunning.value) {
    timerRunning.value = false
    if (timerInterval) clearInterval(timerInterval)
  } else {
    timerRunning.value = true
    timerInterval = setInterval(() => {
      if (timerMode.value === 'stopwatch') {
        timerSeconds.value++
      } else {
        if (timerSeconds.value > 0) {
          timerSeconds.value--
        } else {
          timerRunning.value = false
          if (timerInterval) clearInterval(timerInterval)
          toast.info('⏱️ 30 分钟模拟面试时间到！')
        }
      }
    }, 1000)
  }
}

function resetTimer() {
  timerRunning.value = false
  if (timerInterval) clearInterval(timerInterval)
  timerSeconds.value = timerMode.value === 'stopwatch' ? 0 : 30 * 60
}

function toggleTimerMode() {
  timerMode.value = timerMode.value === 'stopwatch' ? 'countdown' : 'stopwatch'
  resetTimer()
}

// 左右分栏拖拽
function onMouseDownResizer(e: MouseEvent) {
  e.preventDefault()
  isDragging.value = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'

  const onMouseMove = (moveEvent: MouseEvent) => {
    if (!isDragging.value) return
    const containerWidth = window.innerWidth
    const newRatio = (moveEvent.clientX / containerWidth) * 100
    if (newRatio >= 25 && newRatio <= 75) {
      splitRatio.value = Math.round(newRatio)
    }
  }

  const onMouseUp = () => {
    isDragging.value = false
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    localStorage.setItem('leetpath_split_ratio', String(splitRatio.value))
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
  }

  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

function toggleTc(ordinal: number) {
  const s = new Set(expandedTc.value)
  if (s.has(ordinal)) s.delete(ordinal)
  else s.add(ordinal)
  expandedTc.value = s
}

async function toggleHistory(id: number) {
  const requestedSlug = slug.value
  const generation = activePageGeneration
  const s = new Set(expandedHistory.value)
  if (s.has(id)) {
    s.delete(id)
  } else {
    s.add(id)
    if (!historyCode.value[id]) {
      const full = await api.get<Submission>(`/api/submissions/${id}`)
      if (!pageGeneration.isCurrent(generation) || slug.value !== requestedSlug) return
      historyCode.value = { ...historyCode.value, [id]: full.code ?? '' }
    }
  }
  if (!pageGeneration.isCurrent(generation) || slug.value !== requestedSlug) return
  expandedHistory.value = s
}

async function loadCodeIntoEditor(historySnippet: string, lang: Language, mode: IoMode = 'acm') {
  if (!historySnippet) return
  if (confirm('确认将此历史提交代码载入到编辑器中吗？当前未保存的修改将被覆盖。')) {
    const generation = draftGeneration.next()
    if (saveTimer) clearTimeout(saveTimer)
    if (activeDraftKey) void flushDraftKey(activeDraftKey)
    if (!draftGeneration.isCurrent(generation)) return
    language.value = lang
    ioMode.value = mode
    setLang(lang)
    setIoMode(mode)
    const key = makeDraftKey(slug.value, lang, mode)
    activeDraftKey = key
    draftQueue.edit(key, historySnippet)
    suppressCodeTracking = true
    code.value = historySnippet
    suppressCodeTracking = false
    await saveDraftNow()
    toast.success('已载入历史提交代码')
  }
}

async function copyCode(content: string) {
  if (!content) return
  if (await copyToClipboard(content)) toast.success('代码已复制到剪贴板')
  else toast.error('复制失败，请手动复制')
}

function defaultCodeFor(lang: Language, mode: IoMode): string {
  if (mode === 'leetcode') {
    return problem.value?.leetcode_starters?.[lang] || ''
  }
  return DEFAULT_TEMPLATES[lang] || ''
}

function confirmResetCode() {
  if (confirm('确定要重置当前代码吗？将恢复为初始默认模板。')) {
    code.value = defaultCodeFor(language.value, ioMode.value)
    void saveDraftNow()
    toast.info(ioMode.value === 'leetcode' ? '已重置为力扣函数模板' : '代码已重置为初始模板')
  }
}

function makeDraftKey(
  slugValue: string,
  lang: Language = language.value,
  mode: IoMode = ioMode.value,
): DraftKey {
  return { slug: slugValue, language: lang, ioMode: mode }
}

function isActiveDraftKey(key: DraftKey): boolean {
  return Boolean(
    activeDraftKey
      && activeDraftKey.slug === key.slug
      && activeDraftKey.language === key.language
      && activeDraftKey.ioMode === key.ioMode,
  )
}

async function persistDraftSnapshot(snapshot: DraftSnapshot): Promise<void> {
  await api.put(`/api/drafts/${snapshot.slug}`, {
    language: snapshot.language,
    io_mode: snapshot.ioMode,
    code: snapshot.code,
  })
}

function updateSaveHint(key: DraftKey, result: FlushResult): void {
  if (!isActiveDraftKey(key)) return
  if (result.status === 'failed' || result.status === 'timeout') {
    saveHint.value = '保存失败，本地修改待重试'
    return
  }
  if (result.status === 'saved' && draftQueue.isDirty(key)) {
    saveHint.value = '有未保存修改'
    return
  }
  if (result.status === 'saved') {
    const d = new Date()
    saveHint.value = `已保存 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }
}

async function flushDraftKey(key: DraftKey, showHint = true): Promise<FlushResult> {
  if (showHint && isActiveDraftKey(key) && draftQueue.isDirty(key)) {
    saveHint.value = '保存中…'
  }
  const result = await draftQueue.flush(key, persistDraftSnapshot, DRAFT_FLUSH_OPTIONS)
  if (showHint) updateSaveHint(key, result)
  return result
}

async function saveDraftNow(): Promise<FlushResult> {
  if (!problem.value || !activeDraftKey) return { status: 'clean' }
  return flushDraftKey(activeDraftKey)
}

watch(code, () => {
  if (suppressCodeTracking || !activeDraftKey) return
  draftQueue.edit(activeDraftKey, code.value)
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => void saveDraftNow(), 1000)
}, { flush: 'sync' })

async function loadDraftFor(key: DraftKey, generation: number): Promise<void> {
  const draft = await api.get<Draft>(
    `/api/drafts/${key.slug}?language=${key.language}&io_mode=${key.ioMode}`,
  )
  if (!draftGeneration.isCurrent(generation)) return
  const serverCode = draft.code && draft.code.trim().length > 0
    ? draft.code
    : defaultCodeFor(key.language, key.ioMode)
  const restored = draftQueue.recordLoaded(key, serverCode)
  if (!draftGeneration.isCurrent(generation)) return
  activeDraftKey = key
  suppressCodeTracking = true
  code.value = restored.code
  suppressCodeTracking = false
  saveHint.value = restored.dirty
    ? '已恢复本地未保存修改'
    : draft.is_default ? '' : '草稿已恢复'
}

async function setMode(mode: IoMode) {
  if (ioMode.value === mode && activeDraftKey?.ioMode === mode) return
  if (mode === 'leetcode' && !problem.value?.leetcode_available) {
    toast.info('本题暂不支持力扣函数模式')
    return
  }
  const generation = draftGeneration.next()
  if (saveTimer) clearTimeout(saveTimer)
  if (activeDraftKey) void flushDraftKey(activeDraftKey)
  if (!draftGeneration.isCurrent(generation)) return
  ioMode.value = mode
  setIoMode(mode)
  try {
    await loadDraftFor(makeDraftKey(slug.value, language.value, mode), generation)
  } catch {
    if (draftGeneration.isCurrent(generation)) saveHint.value = '草稿加载失败'
  }
}

// 全局语言偏好变化时，编辑器语言与草稿同步切换
watch(langPref, async (lang) => {
  if (language.value === lang && activeDraftKey?.language === lang) return
  const generation = draftGeneration.next()
  if (saveTimer) clearTimeout(saveTimer)
  if (activeDraftKey) void flushDraftKey(activeDraftKey)
  if (!draftGeneration.isCurrent(generation)) return
  language.value = lang
  if (!problem.value) return
  try {
    await loadDraftFor(makeDraftKey(slug.value, lang, ioMode.value), generation)
  } catch {
    if (draftGeneration.isCurrent(generation)) saveHint.value = '草稿加载失败'
  }
})

async function submit() {
  if (!problem.value || submitting.value) return
  if (saveTimer) clearTimeout(saveTimer)
  await saveDraftNow()
  submitting.value = true
  tab.value = 'result'
  try {
    const res = await api.post<{ id: number; status: string }>('/api/submissions', {
      problem_slug: slug.value,
      language: language.value,
      io_mode: ioMode.value,
      code: code.value,
    })
    submission.value = null
    const generation = pollGeneration.next()
    void poll(res.id, generation, slug.value, Date.now() + 90_000)
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '提交评测失败')
    submitting.value = false
  }
}

const { recordSolvedProblem, activePlan } = useStudyPlan()

function stopPolling(): void {
  pollGeneration.invalidate()
  if (pollTimer) clearTimeout(pollTimer)
  pollTimer = null
  submitting.value = false
}

async function poll(id: number, generation: number, submittedSlug: string, deadline: number) {
  try {
    const s = await api.get<Submission>(`/api/submissions/${id}`)
    if (!pollGeneration.isCurrent(generation) || slug.value !== submittedSlug) return
    submission.value = s
    if (isFinal(s.status)) {
      submitting.value = false
      if (s.status === 'AC') {
        toast.success('恭喜！代码全部通过 (Accepted)')
        if (activePlan.value) {
          recordSolvedProblem(submittedSlug)
        }
      } else {
        toast.info(`评测完成：状态为 ${s.status}`)
      }
      void loadHistoryFor(submittedSlug, () => (
        pollGeneration.isCurrent(generation) && slug.value === submittedSlug
      ))
      return
    }
  } catch {
    /* 忽略网络抖动 */
  }
  if (!pollGeneration.isCurrent(generation) || slug.value !== submittedSlug) return
  if (Date.now() > deadline) {
    submitting.value = false
    toast.error('评测响应超时，请刷新重试')
    return
  }
  pollTimer = setTimeout(() => void poll(id, generation, submittedSlug, deadline), 800)
}

async function loadHistoryFor(requestedSlug: string, isCurrent: () => boolean): Promise<void> {
  const loadedHistory = await api.get<Submission[]>(
    `/api/submissions?problem_slug=${requestedSlug}&limit=20`,
  )
  if (isCurrent()) history.value = loadedHistory
}

async function loadSolutionFor(requestedSlug: string, generation: number): Promise<void> {
  solutionLoading.value = true
  try {
    const res = await api.get<{ slug: string; solution_md: string }>(
      `/api/problems/${requestedSlug}/solution`,
    )
    if (pageGeneration.isCurrent(generation) && slug.value === requestedSlug) {
      solutionMd.value = res.solution_md
    }
  } catch {
    if (pageGeneration.isCurrent(generation) && slug.value === requestedSlug) {
      solutionMd.value = ''
    }
  } finally {
    if (pageGeneration.isCurrent(generation) && slug.value === requestedSlug) {
      solutionLoading.value = false
    }
  }
}

async function loadAll(requestedSlug: string) {
  const generation = pageGeneration.next()
  activePageGeneration = generation
  loading.value = true
  submission.value = null
  solutionMd.value = ''
  expandedHistory.value = new Set()
  historyCode.value = {}
  tab.value = window.innerWidth >= 1024 ? 'code' : 'statement'
  try {
    const loadedProblem = await api.get<ProblemDetail>(`/api/problems/${requestedSlug}`)
    if (!pageGeneration.isCurrent(generation) || slug.value !== requestedSlug) return
    problem.value = loadedProblem
    language.value = langPref.value
    const preferred: IoMode =
      loadedProblem.leetcode_available && ioModePref.value === 'leetcode' ? 'leetcode' : 'acm'
    ioMode.value = preferred
    const draftLoadGeneration = draftGeneration.next()
    await Promise.all([
      loadDraftFor(makeDraftKey(requestedSlug, language.value, preferred), draftLoadGeneration),
      loadHistoryFor(requestedSlug, () => (
        pageGeneration.isCurrent(generation) && slug.value === requestedSlug
      )),
      loadSolutionFor(requestedSlug, generation),
    ])
  } catch {
    if (pageGeneration.isCurrent(generation) && slug.value === requestedSlug) {
      problem.value = null
    }
  } finally {
    if (pageGeneration.isCurrent(generation) && slug.value === requestedSlug) {
      loading.value = false
      nextTick(() => {
        if (statementPaneRef.value) statementPaneRef.value.scrollTop = 0
        window.scrollTo(0, 0)
      })
    }
  }
}

async function onGlobalKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault()
    submit()
  } else if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
    e.preventDefault()
    const result = await saveDraftNow()
    if (result.status === 'saved' || result.status === 'clean') {
      toast.success('草稿已立即保存')
    } else {
      toast.error('草稿保存失败，本地修改仍会保留')
    }
  } else if (e.key === 'Escape') {
    if (isZen.value) isZen.value = false
  }
}

function onResize() {
  isDesktop.value = window.innerWidth >= 1024
}

watch(slug, async (n, o) => {
  if (n !== o && o) {
    const generation = navigationGeneration.next()
    pageGeneration.invalidate()
    draftGeneration.invalidate()
    stopPolling()
    if (saveTimer) clearTimeout(saveTimer)
    const previousKey = activeDraftKey
    if (previousKey) void flushDraftKey(previousKey)
    if (!navigationGeneration.isCurrent(generation) || slug.value !== n) return
    await loadAll(n)
  }
})

onMounted(() => {
  const savedRatio = localStorage.getItem('leetpath_split_ratio')
  if (savedRatio) {
    const r = parseInt(savedRatio, 10)
    if (!isNaN(r) && r >= 25 && r <= 75) splitRatio.value = r
  }
  window.addEventListener('resize', onResize)
  window.addEventListener('keydown', onGlobalKeydown)
  navigationGeneration.next()
  void loadAll(slug.value)
})

onBeforeUnmount(() => {
  navigationGeneration.invalidate()
  pageGeneration.invalidate()
  draftGeneration.invalidate()
  stopPolling()
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onGlobalKeydown)
  if (saveTimer) clearTimeout(saveTimer)
  if (timerInterval) clearInterval(timerInterval)
  void draftQueue.flushAll(persistDraftSnapshot, DRAFT_FLUSH_OPTIONS)
})
</script>

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
          <RouterLink to="/problems" class="btn btn-sm back-link">← 返回题库</RouterLink>
          <span class="problem-title-inline">{{ problemHeading(problem) }}</span>
          <span class="badge" :class="`badge-${problem.difficulty}`">{{ difficultyText }}</span>
        </div>

        <div class="workspace-right">
          <!-- 计时器 -->
          <div class="stopwatch-badge" :class="{ running: timerRunning, urgent: timerMode === 'countdown' && timerSeconds <= 300 }">
            <span class="timer-icon">◷</span>
            <span class="timer-text mono">{{ formattedTimer }}</span>
            <button class="timer-btn" :title="timerRunning ? '暂停' : '开始'" @click="toggleTimer">
              {{ timerRunning ? '⏸' : '▶' }}
            </button>
            <button class="timer-btn" title="重置计时器" @click="resetTimer">↺</button>
            <button class="timer-btn mode-btn" :title="timerMode === 'stopwatch' ? '切换为30分钟面试倒计时' : '切换为正向计时'" @click="toggleTimerMode">
              {{ timerMode === 'stopwatch' ? '倒计时' : '正计时' }}
            </button>
          </div>

          <!-- 禅模式切换 -->
          <button class="btn btn-sm zen-btn" :class="{ active: isZen }" :title="isZen ? '退出禅模式 (Esc)' : '开启沉浸禅模式'" @click="isZen = !isZen">
            {{ isZen ? '✕ 退出全屏' : '禅模式' }}
          </button>
        </div>
      </div>

      <div
        class="problem-layout"
        :class="{ 'is-dragging': isDragging }"
        :style="isDesktop ? { gridTemplateColumns: `${splitRatio}% 6px calc(${100 - splitRatio}% - 6px)` } : {}"
      >
        <!-- 左侧面板：题面 / 题解 -->
        <section class="pane pane-statement card statement" v-show="isDesktop || tab === 'statement' || tab === 'solution'">
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
            <h1 style="font-size:20px;margin-top:4px">{{ problemHeading(problem) }}</h1>
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
                  <span class="mono" style="font-size:12px">{{ s.language === 'cpp' ? 'C++' : 'Python3' }}</span>
                  <span class="mono" style="font-size:11px;color:var(--text-faint)">{{ s.io_mode === 'leetcode' ? '力扣' : 'ACM' }}</span>
                  <span v-if="s.runtime_ms !== null" style="color:var(--text-faint);font-size:12px">{{ s.runtime_ms }}ms</span>
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
            <h2 style="font-size:18px;margin-top:6px;display:flex;align-items:center;gap:8px">
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
              <div class="mode-switch" role="group" aria-label="评测模式">
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
                class="btn btn-sm btn-outline"
                style="border-color:var(--accent);color:var(--accent)"
                @click="openAiDrawer"
                title="让 AI 助教帮我找茬、分析复杂度或提供递进思路"
              >
                🤖 AI 助教
              </button>

              <button class="btn btn-sm btn-ghost" @click="confirmResetCode" title="重置为初始模板代码">
                重置
              </button>

              <span class="save-hint" :title="saveHint">{{ saveHint }}</span>
              <span class="shortcut-tip" v-if="isDesktop">Ctrl+Enter 提交 · Ctrl+S 保存</span>
            </div>
            <div class="acm-hint">
              <span v-if="ioMode === 'leetcode'">力扣模式：只实现下方函数 / 设计类，签名与力扣一致。评测仍用本题用例，不必自己处理输入输出。</span>
              <span v-else>ACM 模式：提交完整程序，自己读 stdin / 打印 stdout，格式以题面「输入 / 输出格式」为准</span>
              <RouterLink to="/handbook" class="acm-hint-link">写法对比 · 极速 I/O 模板 →</RouterLink>
            </div>
            <Editor v-model="code" :language="language" />
          </div>

          <!-- 评测结果面板 -->
          <div class="card result-panel" v-show="isDesktop || tab === 'result'">
            <div class="result-body">
              <div v-if="!submission" class="empty" style="padding:24px 0">
                <p>提交后在这里查看实时评测结果</p>
                <span style="font-size:12px;color:var(--text-faint)">支持 Python 3 / C++，可切换 ACM 标准输入输出或力扣函数模式</span>
              </div>
              <template v-else>
                <div class="result-head">
                  <StatusBadge :status="submission.status" />
                  <span v-if="submission.runtime_ms !== null" class="runtime">总耗时 {{ submission.runtime_ms }}ms</span>
                </div>
                <div v-if="submission.compile_output" class="io-block">
                  <div class="io-label">编译 / 系统诊断输出</div>
                  <pre class="mono" style="background:var(--surface-2);border:1px solid var(--border);border-radius:7px;padding:8px 10px;font-size:12.5px;white-space:pre-wrap;word-break:break-all">{{ submission.compile_output }}</pre>
                </div>
                <div v-for="tc in submission.detail ?? []" :key="tc.ordinal">
                  <div class="tc-row" :style="tc.is_sample ? 'cursor:pointer' : ''" @click="tc.is_sample && toggleTc(tc.ordinal)">
                    <span class="tc-ord">#{{ tc.ordinal }}</span>
                    <span v-if="tc.is_sample" class="tc-sample">样例</span>
                    <span class="status-badge" :class="submissionStatusClass(tc.status)" style="padding:1px 10px;font-size:12px">{{ tc.status }}</span>
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteUpdate, useRoute } from 'vue-router'
import { api } from '../api'
import Editor from '../components/Editor.vue'
import Skeleton from '../components/Skeleton.vue'
import StatusBadge from '../components/StatusBadge.vue'
import {
  canAcceptSubmissionPoll,
  canCommitDraftTransition,
  canCommitProblemDraft,
  canCommitProblemLoad,
  flushUntilStable,
  isDraftRevisionCurrent,
} from '../problemConcurrency'
import {
  createDraftContext,
  createDraftSnapshot,
  draftLoadPath,
  draftSaveRequest,
  sameDraftContext,
  type DraftContext,
} from '../problemDraft'
import { submissionStatusClass } from '../submissionStatus'
import { useToast } from '../stores/toast'
import { useIoModePref, useLangPref } from '../stores/pref'
import { useStudyPlan } from '../stores/plan'
import { renderMarkdown, filterSolutionMarkdown } from '../markdown'
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

interface SaveInFlight {
  readonly context: Readonly<DraftContext>
  readonly revision: number
  readonly promise: Promise<boolean>
}

type DraftTransitionResult = 'applied' | 'superseded' | 'failed'

let saveTimer: ReturnType<typeof setTimeout> | null = null
let saveInFlight: SaveInFlight | null = null
let pollTimer: ReturnType<typeof setTimeout> | null = null
let pollEpoch = 0
let problemLoadGeneration = 0
let draftTransitionGeneration = 0
let editorRevision = 0
let dirty = false
let applyingEditorCode = false
let activeDraftContext: Readonly<DraftContext> | null = null
let desiredLanguage: Language = langPref.value
let desiredIoMode: IoMode = ioMode.value

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

const statementHtml = computed(() =>
  problem.value ? renderMarkdown(problem.value.statement_md) : '',
)

const solutionHtml = computed(() =>
  solutionMd.value ? renderMarkdown(filterSolutionMarkdown(solutionMd.value, language.value)) : '',
)

const difficultyText = computed(() => {
  const d = problem.value?.difficulty
  return d === 'easy' ? '简单' : d === 'medium' ? '中等' : '困难'
})

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
  const problemSlug = slug.value
  const generation = problemLoadGeneration
  const s = new Set(expandedHistory.value)
  if (s.has(id)) {
    s.delete(id)
  } else {
    s.add(id)
    if (!historyCode.value[id]) {
      const full = await api.get<Submission>(`/api/submissions/${id}`)
      if (!isCurrentProblemLoad(generation, problemSlug)) return
      historyCode.value = { ...historyCode.value, [id]: full.code ?? '' }
    }
  }
  if (!isCurrentProblemLoad(generation, problemSlug)) return
  expandedHistory.value = s
}

async function loadCodeIntoEditor(historySnippet: string, lang: Language, mode: IoMode = 'acm') {
  if (!historySnippet) return
  if (confirm('确认将此历史提交代码载入到编辑器中吗？当前未保存的修改将被覆盖。')) {
    const sourceContext = activeDraftContext
    const transitionGeneration = ++draftTransitionGeneration
    if (!(await flushDraftBeforeTransition())) {
      toast.error('当前草稿保存失败，请重试后再载入历史代码')
      return
    }
    if (
      transitionGeneration !== draftTransitionGeneration
      || !sourceContext
      || !sameDraftContext(sourceContext, activeDraftContext)
      || sourceContext.slug !== slug.value
    ) return

    const targetContext = createDraftContext(
      sourceContext.slug,
      lang,
      mode,
    )
    desiredLanguage = lang
    desiredIoMode = mode
    applyEditorCode(targetContext, historySnippet, true)
    setLang(lang)
    setIoMode(mode)

    if (await saveDraftOnce()) {
      toast.success('已载入并保存历史提交代码')
    } else {
      toast.error('历史代码已载入，草稿保存失败，可按 Ctrl+S 重试')
    }
  }
}

function copyCode(content: string) {
  if (!content) return
  navigator.clipboard.writeText(content)
  toast.success('代码已复制到剪贴板')
}

function defaultCodeFor(
  problemDetail: ProblemDetail | null,
  lang: Language,
  mode: IoMode,
): string {
  if (mode === 'leetcode') {
    return problemDetail?.leetcode_starters?.[lang] || ''
  }
  return DEFAULT_TEMPLATES[lang] || ''
}

function confirmResetCode() {
  if (confirm('确定要重置当前代码吗？将恢复为初始默认模板。')) {
    code.value = defaultCodeFor(problem.value, language.value, ioMode.value)
    void saveDraftOnce()
    toast.info(ioMode.value === 'leetcode' ? '已重置为力扣函数模板' : '代码已重置为初始模板')
  }
}

function isCurrentProblemLoad(generation: number, problemSlug: string): boolean {
  return canCommitProblemLoad(
    generation,
    problemLoadGeneration,
    slug.value,
    problemSlug,
  )
}

async function fetchSolution(problemSlug: string): Promise<string> {
  try {
    const res = await api.get<{ slug: string; solution_md: string }>(
      `/api/problems/${problemSlug}/solution`,
    )
    return res.solution_md
  } catch {
    return ''
  }
}

function fetchDraft(context: DraftContext): Promise<Draft> {
  return api.get<Draft>(draftLoadPath(context))
}

function fetchHistory(problemSlug: string): Promise<Submission[]> {
  return api.get<Submission[]>(`/api/submissions?problem_slug=${problemSlug}&limit=20`)
}

async function fetchDesiredPageDraft(
  problemSlug: string,
  problemGeneration: number,
): Promise<{ context: Readonly<DraftContext>; draft: Draft } | null> {
  while (isCurrentProblemLoad(problemGeneration, problemSlug)) {
    const context = desiredDraftContextForSlug(problemSlug)
    try {
      const draft = await fetchDraft(context)
      if (!isCurrentProblemLoad(problemGeneration, problemSlug)) return null
      if (sameDraftContext(context, desiredDraftContextForSlug(problemSlug))) {
        return { context, draft }
      }
    } catch (error) {
      if (!isCurrentProblemLoad(problemGeneration, problemSlug)) return null
      if (sameDraftContext(context, desiredDraftContextForSlug(problemSlug))) throw error
    }
  }
  return null
}

function clearSaveTimer() {
  if (!saveTimer) return
  clearTimeout(saveTimer)
  saveTimer = null
}

function applyEditorCode(context: DraftContext, nextCode: string, shouldBeDirty: boolean) {
  clearSaveTimer()
  activeDraftContext = createDraftContext(context.slug, context.language, context.ioMode)
  language.value = context.language
  ioMode.value = context.ioMode
  applyingEditorCode = true
  code.value = nextCode
  applyingEditorCode = false
  editorRevision += 1
  dirty = shouldBeDirty
}

async function saveDraftOnce(): Promise<boolean> {
  while (saveInFlight) {
    const pendingSave = saveInFlight
    const succeeded = await pendingSave.promise
    if (saveInFlight === pendingSave) saveInFlight = null
    if (!succeeded) return false
  }

  if (!activeDraftContext || !dirty) return true

  const context = activeDraftContext
  const revision = editorRevision
  const snapshot = createDraftSnapshot(context, code.value)
  const request = draftSaveRequest(snapshot)
  dirty = false
  saveHint.value = '保存中…'

  const promise = (async () => {
    try {
      await api.put(request.path, request.body)
      if (sameDraftContext(activeDraftContext, context)) {
        if (!isDraftRevisionCurrent(context, activeDraftContext, revision, editorRevision)) {
          dirty = true
        }
        const d = new Date()
        saveHint.value = dirty
          ? '有未保存修改'
          : `已保存 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
      }
      return true
    } catch {
      if (sameDraftContext(activeDraftContext, context)) {
        dirty = true
        saveHint.value = '保存失败，可重试'
      }
      return false
    }
  })()

  const pendingSave: SaveInFlight = { context, revision, promise }
  saveInFlight = pendingSave
  const succeeded = await promise
  if (saveInFlight === pendingSave) saveInFlight = null
  return succeeded
}

async function flushDraftBeforeTransition(): Promise<boolean> {
  return flushUntilStable(
    async () => {
      clearSaveTimer()
      return saveDraftOnce()
    },
    () => !activeDraftContext || (!saveInFlight && !dirty),
  )
}

watch(code, () => {
  if (applyingEditorCode) return
  editorRevision += 1
  dirty = true
  clearSaveTimer()
  saveTimer = setTimeout(() => {
    saveTimer = null
    void saveDraftOnce()
  }, 1000)
}, { flush: 'sync' })

function applyLoadedDraft(
  context: DraftContext,
  draft: Draft,
  problemDetail: ProblemDetail,
) {
  const nextCode = draft.code && draft.code.trim().length > 0
    ? draft.code
    : defaultCodeFor(problemDetail, context.language, context.ioMode)
  applyEditorCode(context, nextCode, false)
  saveHint.value = draft.is_default ? '' : '草稿已恢复'
}

function desiredDraftContextForSlug(problemSlug: string): Readonly<DraftContext> {
  return createDraftContext(problemSlug, desiredLanguage, desiredIoMode)
}

function currentDesiredDraftContext(): Readonly<DraftContext> | null {
  if (!activeDraftContext) return null
  return desiredDraftContextForSlug(activeDraftContext.slug)
}

async function requestDraftContext(
  targetContext: Readonly<DraftContext>,
): Promise<DraftTransitionResult> {
  const transitionGeneration = ++draftTransitionGeneration
  if (sameDraftContext(activeDraftContext, targetContext)) return 'applied'
  if (!(await flushDraftBeforeTransition())) {
    return transitionGeneration === draftTransitionGeneration ? 'failed' : 'superseded'
  }
  if (!canCommitDraftTransition(
    transitionGeneration,
    draftTransitionGeneration,
    slug.value,
    targetContext,
    currentDesiredDraftContext(),
  )) return 'superseded'

  let draft: Draft
  try {
    draft = await fetchDraft(targetContext)
  } catch {
    if (transitionGeneration !== draftTransitionGeneration) return 'superseded'
    saveHint.value = '草稿加载失败'
    return 'failed'
  }

  if (!canCommitDraftTransition(
    transitionGeneration,
    draftTransitionGeneration,
    slug.value,
    targetContext,
    currentDesiredDraftContext(),
  )) return 'superseded'

  // 用户可能在 GET 目标草稿期间继续编辑旧代码；提交目标状态前再保存一次。
  if (!(await flushDraftBeforeTransition())) {
    return transitionGeneration === draftTransitionGeneration ? 'failed' : 'superseded'
  }
  if (!canCommitDraftTransition(
    transitionGeneration,
    draftTransitionGeneration,
    slug.value,
    targetContext,
    currentDesiredDraftContext(),
  )) return 'superseded'

  const currentProblem = problem.value
  if (!currentProblem || currentProblem.slug !== targetContext.slug) return 'superseded'
  applyLoadedDraft(targetContext, draft, currentProblem)
  return 'applied'
}

function revertDesiredContext(targetContext: DraftContext) {
  const currentContext = activeDraftContext
  if (!currentContext) return
  desiredLanguage = currentContext.language
  desiredIoMode = currentContext.ioMode
  if (langPref.value === targetContext.language && langPref.value !== currentContext.language) {
    setLang(currentContext.language)
  }
  if (ioModePref.value === targetContext.ioMode && ioModePref.value !== currentContext.ioMode) {
    setIoMode(currentContext.ioMode)
  }
}

async function reconcileDesiredDraftContext(errorMessage: string) {
  const targetContext = currentDesiredDraftContext()
  if (!targetContext) return
  const result = await requestDraftContext(targetContext)
  if (result === 'failed') {
    revertDesiredContext(targetContext)
    toast.error(errorMessage)
  }
}

async function setMode(mode: IoMode) {
  if (desiredIoMode === mode && ioMode.value === mode) return
  if (mode === 'leetcode' && !problem.value?.leetcode_available) {
    toast.info('本题暂不支持力扣函数模式')
    return
  }
  desiredIoMode = mode
  setIoMode(mode)
  await reconcileDesiredDraftContext('当前草稿保存或目标草稿加载失败，评测模式未切换')
}

// 全局语言偏好变化时，编辑器语言与草稿同步切换
watch(langPref, (nextLanguage) => {
  desiredLanguage = nextLanguage
  void reconcileDesiredDraftContext('当前草稿保存或目标草稿加载失败，语言未切换')
})

async function submit() {
  if (!problem.value || !activeDraftContext || submitting.value) return
  cancelPoll()
  const submissionPollEpoch = pollEpoch
  submitting.value = true
  submission.value = null
  tab.value = 'result'
  const submissionSnapshot = createDraftSnapshot(activeDraftContext, code.value)
  await saveDraftOnce()
  if (!canAcceptSubmissionPoll(
    submissionPollEpoch,
    pollEpoch,
    activeDraftContext?.slug,
    submissionSnapshot.slug,
  )) return
  try {
    const res = await api.post<{ id: number; status: string }>('/api/submissions', {
      problem_slug: submissionSnapshot.slug,
      language: submissionSnapshot.language,
      io_mode: submissionSnapshot.ioMode,
      code: submissionSnapshot.code,
    })
    if (!canAcceptSubmissionPoll(
      submissionPollEpoch,
      pollEpoch,
      activeDraftContext?.slug,
      submissionSnapshot.slug,
    )) return
    submission.value = null
    void poll(
      res.id,
      submissionSnapshot.slug,
      submissionPollEpoch,
      Date.now() + 90_000,
    )
  } catch (e) {
    if (canAcceptSubmissionPoll(
      submissionPollEpoch,
      pollEpoch,
      activeDraftContext?.slug,
      submissionSnapshot.slug,
    )) {
      toast.error(e instanceof Error ? e.message : '提交评测失败')
      submitting.value = false
    }
  }
}

const { recordSolvedProblem, activePlan } = useStudyPlan()

function cancelPoll() {
  pollEpoch += 1
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
  submitting.value = false
}

function isCurrentPoll(epoch: number, problemSlug: string): boolean {
  return canAcceptSubmissionPoll(
    epoch,
    pollEpoch,
    activeDraftContext?.slug,
    problemSlug,
  )
}

async function poll(
  id: number,
  problemSlug: string,
  epoch: number,
  deadline: number,
) {
  if (!isCurrentPoll(epoch, problemSlug)) return
  try {
    const s = await api.get<Submission>(`/api/submissions/${id}`)
    if (!isCurrentPoll(epoch, problemSlug)) return
    submission.value = s
    if (isFinal(s.status)) {
      submitting.value = false
      if (s.status === 'AC') {
        toast.success('恭喜！代码全部通过 (Accepted)')
        if (activePlan.value) {
          recordSolvedProblem(problemSlug)
        }
      } else {
        toast.info(`评测完成：状态为 ${s.status}`)
      }
      void refreshHistory(problemSlug)
      return
    }
  } catch {
    /* 忽略网络抖动 */
  }
  if (!isCurrentPoll(epoch, problemSlug)) return
  if (Date.now() > deadline) {
    submitting.value = false
    toast.error('评测响应超时，请刷新重试')
    return
  }
  pollTimer = setTimeout(() => {
    pollTimer = null
    void poll(id, problemSlug, epoch, deadline)
  }, 800)
}

async function refreshHistory(problemSlug: string) {
  const generation = problemLoadGeneration
  try {
    const nextHistory = await fetchHistory(problemSlug)
    if (
      !isCurrentProblemLoad(generation, problemSlug)
      || activeDraftContext?.slug !== problemSlug
    ) return
    history.value = nextHistory
  } catch {
    // 提交终态已经展示，历史刷新失败不覆盖现有记录。
  }
}

async function loadAll(problemSlug: string = slug.value) {
  const generation = ++problemLoadGeneration
  draftTransitionGeneration += 1
  cancelPoll()
  clearSaveTimer()
  activeDraftContext = null
  dirty = false
  desiredLanguage = langPref.value
  loading.value = true
  problem.value = null
  submission.value = null
  solutionMd.value = ''
  solutionLoading.value = true
  history.value = []
  expandedTc.value = new Set()
  expandedHistory.value = new Set()
  historyCode.value = {}
  tab.value = window.innerWidth >= 1024 ? 'code' : 'statement'
  try {
    const nextProblem = await api.get<ProblemDetail>(`/api/problems/${problemSlug}`)
    if (!isCurrentProblemLoad(generation, problemSlug)) return
    problem.value = nextProblem
    desiredIoMode =
      nextProblem.leetcode_available && ioModePref.value === 'leetcode' ? 'leetcode' : 'acm'
    desiredLanguage = langPref.value

    let [loadedDraft, nextHistory, nextSolution] = await Promise.all([
      fetchDesiredPageDraft(problemSlug, generation),
      fetchHistory(problemSlug),
      fetchSolution(problemSlug),
    ])
    if (!loadedDraft || !isCurrentProblemLoad(generation, problemSlug)) return

    const desiredContext = desiredDraftContextForSlug(problemSlug)
    if (!canCommitProblemDraft(
      generation,
      problemLoadGeneration,
      slug.value,
      problemSlug,
      loadedDraft.context,
      desiredContext,
    )) {
      loadedDraft = await fetchDesiredPageDraft(problemSlug, generation)
    }
    if (
      !loadedDraft
      || !canCommitProblemDraft(
        generation,
        problemLoadGeneration,
        slug.value,
        problemSlug,
        loadedDraft.context,
        desiredDraftContextForSlug(problemSlug),
      )
    ) return

    applyLoadedDraft(loadedDraft.context, loadedDraft.draft, nextProblem)
    history.value = nextHistory
    solutionMd.value = nextSolution
  } catch {
    if (isCurrentProblemLoad(generation, problemSlug)) problem.value = null
  } finally {
    if (isCurrentProblemLoad(generation, problemSlug)) {
      loading.value = false
      solutionLoading.value = false
    }
  }
}

function onGlobalKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault()
    void submit()
  } else if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
    e.preventDefault()
    void flushDraftBeforeTransition().then((succeeded) => {
      if (succeeded) toast.success('草稿已立即保存')
      else toast.error('草稿保存失败，可再次按 Ctrl+S 重试')
    })
  } else if (e.key === 'Escape') {
    if (isZen.value) isZen.value = false
  }
}

function onResize() {
  isDesktop.value = window.innerWidth >= 1024
}

onBeforeRouteUpdate(async (to, from) => {
  if (to.params.slug === from.params.slug) return true
  if (await flushDraftBeforeTransition()) return true
  toast.error('当前草稿保存失败，请重试后再切换题目')
  return false
})

watch(slug, (n, o) => {
  if (n !== o && o) {
    void loadAll(n)
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
  void loadAll()
})

onBeforeUnmount(() => {
  problemLoadGeneration += 1
  draftTransitionGeneration += 1
  cancelPoll()
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onGlobalKeydown)
  clearSaveTimer()
  if (timerInterval) clearInterval(timerInterval)
  void saveDraftOnce()
})
</script>

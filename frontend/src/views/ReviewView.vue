<template>
  <div class="container">
    <div class="page-head review-page-head">
      <div>
        <div class="kicker">Review Deck</div>
        <h1 class="display">背题模式</h1>
      </div>

      <!-- 语言切换器：移至顶栏与标题/统计项水平对齐 -->
      <div class="review-head-control" v-if="!loading && deck.length > 0">
        <span class="review-lang-hint">当前背题语言</span>
        <div class="segmented">
          <button
            :class="{ active: langPref === 'python3' }"
            @click="setLang('python3')"
          >
            Python 3
          </button>
          <button
            :class="{ active: langPref === 'cpp' }"
            @click="setLang('cpp')"
          >
            C++ 20
          </button>
        </div>
      </div>

      <div class="head-stats">
        <div class="stat">
          <span class="num" :class="{ accent: rememberedCount > 0 }">{{ rememberedCount }}</span>
          <span class="lbl">已记住</span>
        </div>
        <div class="stat">
          <span class="num">{{ deck.length - rememberedCount }}</span>
          <span class="lbl">待背</span>
        </div>
        <div class="stat">
          <span class="num">{{ deck.length }}</span>
          <span class="lbl">题解总数</span>
        </div>
      </div>
    </div>

    <!-- 顶部进度条 -->
    <div v-if="!loading && deck.length" class="progress-track review-progress">
      <div class="seg" :style="{ width: `${(rememberedCount / deck.length) * 100}%`, background: 'var(--accent)' }"></div>
    </div>

    <!-- 骨架屏加载 -->
    <div v-if="loading" class="card review-skeleton">
      <Skeleton :count="1" height="32px" width="50%" radius="6px" gap="16px" />
      <Skeleton :count="4" height="20px" width="100%" radius="6px" gap="12px" />
    </div>
    <div v-else-if="deck.length === 0" class="empty">题解还在生成中，稍后再来</div>

    <!-- 背题卡片主体：正面只亮题名，翻开后是「题目 | 题解」对照画布 -->
    <template v-else-if="current">
      <div class="review-stage" :class="{ open: flipped }">
        <transition name="review-flip" mode="out-in">
          <div
            v-if="!flipped"
            key="front"
            class="card review-card"
            @click="flipped = true"
          >
            <div class="review-meta review-meta-center">
              <span class="badge" :class="`badge-${current.difficulty}`">{{ difficultyText(current.difficulty) }}</span>
              <span v-for="label in sourceBadgeTexts(current)" :key="label" class="badge badge-source">{{ label }}</span>
              <span v-if="current.memory === 'remembered'" class="badge badge-remembered">
                <AppIcon name="check" :size="11" :stroke-width="2.6" /> 已记住
              </span>
            </div>
            <div class="rc-title">{{ problemHeading(current) }}</div>
            <div class="rc-slug mono">{{ current.slug }}</div>
            <div class="rc-tags">{{ current.tags.join(' · ') }}</div>
            <div class="rc-hint">
              点击翻开题目与【{{ langPref === 'cpp' ? 'C++' : 'Python3' }}】题解（Space / Enter）
            </div>
          </div>

          <div v-else key="back" class="review-board">
            <div class="review-canvas-bar">
              <div class="review-canvas-bar-main">
                <div class="review-meta">
                  <span class="badge" :class="`badge-${current.difficulty}`">{{ difficultyText(current.difficulty) }}</span>
                  <span v-for="label in sourceBadgeTexts(current)" :key="label" class="badge badge-source">{{ label }}</span>
                  <span v-if="current.memory === 'remembered'" class="badge badge-remembered">
                    <AppIcon name="check" :size="11" :stroke-width="2.6" /> 已记住
                  </span>
                </div>
                <div class="review-canvas-title">{{ problemHeading(current) }}</div>
                <div class="rc-slug mono review-canvas-sub">{{ current.slug }} · {{ current.tags.join(' · ') }}</div>
              </div>
              <div class="review-canvas-bar-actions">
                <button class="btn btn-sm review-ai-btn" type="button" @click="openAiTutor">
                  <AppIcon name="robot" :size="14" /> 问 AI 更多解法 / 口诀
                </button>
                <button class="btn btn-sm btn-ghost" type="button" @click="flipped = false">
                  <AppIcon name="refresh" :size="13" /> 翻回正面
                </button>
                <RouterLink class="review-canvas-link" :to="`/problems/${current.slug}`">
                  去刷这道题 <AppIcon name="arrow-right" :size="13" />
                </RouterLink>
              </div>
            </div>

            <div class="review-spread">
              <section class="review-sheet">
                <div class="review-sheet-label">
                  <AppIcon name="book" :size="12" /> 题目
                </div>
                <div v-if="payloadLoading && !statementHtml" class="empty review-sheet-loading">题面加载中…</div>
                <div v-else class="markdown-body" v-html="statementHtml"></div>
              </section>
              <section class="review-sheet review-sheet-solution">
                <div class="review-sheet-label">
                  <AppIcon name="sparkle" :size="12" /> 题解 · {{ langPref === 'cpp' ? 'C++' : 'Python3' }}
                </div>
                <div v-if="payloadLoading && !solutionHtml" class="empty review-sheet-loading">题解加载中…</div>
                <div v-else class="markdown-body rc-solution" v-html="solutionHtml"></div>
              </section>
            </div>
          </div>
        </transition>

        <div class="review-actions">
          <button class="btn" :disabled="index === 0" @click="go(index - 1)">
            <AppIcon name="chevron-left" :size="15" /> 上一张
          </button>
          <button class="btn" :disabled="marking" @click="mark(false)">
            <AppIcon name="x" :size="14" /> 没记住
          </button>
          <button class="btn btn-primary" :disabled="marking" @click="mark(true)">
            <AppIcon name="check" :size="15" :stroke-width="2.4" /> 记住了
          </button>
          <button class="btn" :disabled="index >= deck.length - 1" @click="go(index + 1)">
            下一张 <AppIcon name="chevron-right" :size="15" />
          </button>
        </div>
        <div class="review-pos num">{{ index + 1 }} / {{ deck.length }}</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { renderMarkdown, filterSolutionMarkdown } from '../markdown'
import Skeleton from '../components/Skeleton.vue'
import AppIcon from '../components/AppIcon.vue'
import { useLangPref } from '../stores/pref'
import { useAiAssistant } from '../stores/aiAssistant'
import {
  problemHeading,
  sourceBadgeTexts,
  type Difficulty,
  type ProblemDetail,
  type ProblemListItem,
} from '../types'

const { langPref, setLang } = useLangPref()
const assistant = useAiAssistant()

interface ReviewPayload {
  statement_md: string
  solution_md: string
}

const loading = ref(true)
const deck = ref<ProblemListItem[]>([])
const index = ref(0)
const flipped = ref(false)
const marking = ref(false)
const payloadLoading = ref(false)
const payloadCache = new Map<string, ReviewPayload>()
const statementMd = ref('')
const solutionMd = ref('')

const rememberedCount = computed(
  () => deck.value.filter((p) => p.memory === 'remembered').length,
)
const current = computed(() => deck.value[index.value])

const statementHtml = computed(() =>
  statementMd.value ? renderMarkdown(statementMd.value) : '',
)

// 根据用户选择的语言过滤题解内容，只呈现选定语言
const solutionHtml = computed(() => {
  if (!solutionMd.value) return ''
  const filtered = filterSolutionMarkdown(solutionMd.value, langPref.value)
  return renderMarkdown(filtered)
})

function difficultyText(d: Difficulty) {
  return d === 'easy' ? '简单' : d === 'medium' ? '中等' : '困难'
}

function updateAiContext() {
  const p = current.value
  if (!p) return
  assistant.setContext({
    source: 'review',
    title: `背题 · ${problemHeading(p)}`,
    contextKey: `review:${p.slug}`,
    contextText: `【当前背题】：${problemHeading(p)} (${difficultyText(p.difficulty)} · 标签: ${p.tags.join(', ')})
【语言】：${langPref.value === 'cpp' ? 'C++' : 'Python 3'}
【题面描述】：
${statementMd.value}

【参考题解】：
${solutionMd.value}`,
    presetPrompts: [
      {
        label: '💡 这道题还有更多解法吗？（对比时空复杂度）',
        prompt: `对于这道《${problemHeading(p)}》，除了当前给出的解法外，还有哪些其他经典或进阶解法？（请按思维演进从基础到最优解清晰分析，并对比各自的时空复杂度与适用场景）`,
      },
      {
        label: '🧠 提炼极简记忆口诀与代码模板骨架',
        prompt: `请用 1-2 句极简口诀和最精炼的核心代码骨架，帮我在面试前能快速回忆起本题的关键思路。`,
      },
      {
        label: '🔍 面试官通常会顺着这个解法怎么追问？',
        prompt: `在技术面试中，如果我写出了当前这种解法，面试官通常会提出哪些 follow-up 进阶深挖问题？（例如大数据量、并发场景、内存受限等）`,
      },
      {
        label: '⚡ 核心易错点与边界条件清单',
        prompt: `这道题在手撕写代码时最容易踩的 3 个边界 Bug 或隐蔽陷阱是什么？`,
      },
    ],
  })
}

function openAiTutor() {
  updateAiContext()
  assistant.openWithContext(assistant.currentContext.value)
}

watch([current, statementMd, solutionMd], () => {
  updateAiContext()
})

async function fetchPayload(slug: string): Promise<ReviewPayload> {
  const hit = payloadCache.get(slug)
  if (hit) return hit
  const [detail, sol] = await Promise.all([
    api.get<ProblemDetail>(`/api/problems/${slug}`),
    api.get<{ slug: string; solution_md: string }>(`/api/problems/${slug}/solution`),
  ])
  const payload: ReviewPayload = {
    statement_md: detail.statement_md,
    solution_md: sol.solution_md,
  }
  payloadCache.set(slug, payload)
  return payload
}

function applyPayload(slug: string, payload: ReviewPayload) {
  if (current.value?.slug !== slug) return
  statementMd.value = payload.statement_md
  solutionMd.value = payload.solution_md
}

async function loadPayload() {
  const c = current.value
  if (!c) return
  const cached = payloadCache.get(c.slug)
  if (cached) {
    applyPayload(c.slug, cached)
    payloadLoading.value = false
    prefetchNeighbor(index.value + 1)
    return
  }
  statementMd.value = ''
  solutionMd.value = ''
  payloadLoading.value = true
  try {
    const payload = await fetchPayload(c.slug)
    applyPayload(c.slug, payload)
  } catch {
    if (current.value?.slug === c.slug) {
      statementMd.value = '题目加载失败'
      solutionMd.value = '题解加载失败'
    }
  } finally {
    if (current.value?.slug === c.slug) payloadLoading.value = false
  }
  prefetchNeighbor(index.value + 1)
}

function prefetchNeighbor(i: number) {
  const n = deck.value[i]
  if (!n || payloadCache.has(n.slug)) return
  void fetchPayload(n.slug).catch(() => undefined)
}

function go(i: number) {
  index.value = i
  flipped.value = false
  loadPayload()
}

async function mark(remembered: boolean) {
  const c = current.value
  if (!c || marking.value) return
  marking.value = true
  try {
    await api.post(`/api/problems/${c.slug}/memory`, { remembered })
    c.memory = remembered ? 'remembered' : 'unremembered'
    if (remembered && index.value < deck.value.length - 1) {
      go(index.value + 1)
    }
  } finally {
    marking.value = false
  }
}

function onKey(e: KeyboardEvent) {
  const tag = (e.target as HTMLElement)?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'BUTTON' || tag === 'A' || tag === 'SELECT') return
  if (e.key === ' ' || e.key === 'Enter') {
    e.preventDefault()
    flipped.value = !flipped.value
  } else if (e.key === 'ArrowLeft' && index.value > 0) go(index.value - 1)
  else if (e.key === 'ArrowRight' && index.value < deck.value.length - 1) go(index.value + 1)
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  try {
    const all = await api.get<ProblemListItem[]>('/api/problems')
    const withSol = all.filter((p) => p.has_solution)
    deck.value = withSol.sort((a, b) => {
      const ra = a.memory === 'remembered' ? 1 : 0
      const rb = b.memory === 'remembered' ? 1 : 0
      return ra - rb || a.id - b.id
    })
    await loadPayload()
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="container">
    <div v-if="error" class="error-banner">
      <span>{{ error }}</span>
      <button type="button" class="btn btn-sm" @click="loadHome">重试</button>
    </div>
    <div class="hero">
      <div class="kicker">Daily Practice & Career Board</div>
      <h1 class="display">
        专为校招求职打造的<br />
        <span class="grad">极客刷题与算法<span class="kw">手撕</span>平台</span>
      </h1>
      <p class="lede">
        力扣热题 100 + 面经高频<span class="kw">手撕</span>题库 · Python3 / C++ 在线沙箱评测 · 52周打卡热力图 · 秋招公司级聚合看板
      </p>

      <div class="hero-stats">
        <div class="hstat">
          <span class="num grad-num">{{ problemCount }}</span>
          <span class="lbl">精选精校题目</span>
        </div>
        <div class="hstat">
          <span class="num">{{ solvedCount }}</span>
          <span class="lbl">已解决题目</span>
        </div>
        <div class="hstat">
          <span class="num">{{ rememberedCount }}</span>
          <span class="lbl">已牢记题解</span>
        </div>
        <div class="hstat">
          <span class="num">{{ openJobCount }}</span>
          <span class="lbl">秋招在招岗位</span>
        </div>
      </div>

      <div class="hero-actions">
        <RouterLink class="btn btn-primary" to="/problems">
          代码题库
          <AppIcon name="arrow-right" :size="15" />
        </RouterLink>
        <RouterLink class="btn" to="/quiz">
          <AppIcon name="pencil" :size="15" />
          八股自测{{ quizTotal ? ` (${quizTotal}题)` : '' }}
        </RouterLink>
        <button class="btn" @click="pickRandomProblem">
          <AppIcon name="dice" :size="15" />
          随机刷算法
        </button>
        <RouterLink class="btn" to="/review">
          <AppIcon name="cards" :size="15" />
          背题模式
        </RouterLink>
        <RouterLink class="btn" to="/handbook">
          <AppIcon name="book" :size="15" />
          新手手册
        </RouterLink>
      </div>
    </div>

    <!-- 刷题打卡计划看板组件 -->
    <PlanCard
      :problems="problems"
      @open-modal="showPlanModal = true"
    />

    <!-- 年度打卡热力图卡片 -->
    <div class="card heatmap-card">
      <div class="heatmap-head">
        <div>
          <h3>刷题活跃度与打卡记录</h3>
          <span class="heatmap-sub">今天 {{ formatZhDate(todayStr) }} · 过去 52 周</span>
        </div>
        <div class="heatmap-streak">
          <span class="streak-tag">{{ streakLabel }}</span>
        </div>
      </div>

      <div class="heatmap-scroll-wrap">
        <div class="heatmap-chart">
          <div class="heatmap-wdays" aria-hidden="true">
            <span v-for="(w, i) in WEEKDAY_LABELS" :key="i">{{ w }}</span>
          </div>
          <div class="heatmap-right">
            <div class="heatmap-months">
              <span
                v-for="(label, i) in heatmapMonths"
                :key="i"
                class="heatmap-month"
              >{{ label }}</span>
            </div>
            <div class="heatmap-grid">
              <div
                v-for="(day, idx) in heatmapDays"
                :key="idx"
                class="heatmap-cell"
                :class="[
                  `level-${day.level}`,
                  { 'is-today': day.isToday, 'is-pad': day.pad },
                ]"
                :title="day.pad ? '' : `${formatZhDate(day.date)}：${day.count} 次提交`"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <div class="heatmap-legend">
        <span>Less</span>
        <span class="heatmap-cell level-0"></span>
        <span class="heatmap-cell level-1"></span>
        <span class="heatmap-cell level-2"></span>
        <span class="heatmap-cell level-3"></span>
        <span class="heatmap-cell level-4"></span>
        <span>More</span>
      </div>
    </div>

    <!-- 算法核心专题掌握度 -->
    <div class="card category-card" v-if="categoryStats.length > 0">
      <div class="section-title">
        <h3>经典算法专题掌握度</h3>
        <RouterLink to="/problems">
          查看全部专题
          <AppIcon name="chevron-right" :size="13" />
        </RouterLink>
      </div>

      <div class="category-grid">
        <div v-for="cat in categoryStats" :key="cat.name" class="cat-item">
          <div class="cat-top">
            <span class="cat-name">{{ cat.name }}</span>
            <span class="cat-ratio mono">{{ cat.solved }} / {{ cat.total }}</span>
          </div>
          <div class="cat-track">
            <div class="cat-bar" :style="{ width: `${cat.percent}%` }"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 秋招看板精选 -->
    <div class="section-title">
      <h2>秋招高频在招看板</h2>
      <RouterLink to="/jobs">
        查看全部公司与岗位
        <AppIcon name="chevron-right" :size="13" />
      </RouterLink>
    </div>
    <JobBoard :limit="4" />

    <!-- 计划制定弹窗 -->
    <PlanModal
      v-if="showPlanModal"
      :problems="problems"
      @close="showPlanModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import AppIcon from '../components/AppIcon.vue'
import JobBoard from '../components/JobBoard.vue'
import PlanCard from '../components/PlanCard.vue'
import PlanModal from '../components/PlanModal.vue'
import { addDays, formatZhDate, todayLocalDate } from '../dates'
import type { Job, ProblemListItem, QuizStats, Submission } from '../types'

const router = useRouter()

const error = ref('')
const problemCount = ref(0)
const solvedCount = ref(0)
const rememberedCount = ref(0)
const openJobCount = ref(0)
const quizTotal = ref(0)
const problems = ref<ProblemListItem[]>([])
const showPlanModal = ref(false)

interface HeatmapDay {
  date: string
  count: number
  level: number
  isToday: boolean
  pad: boolean
}
const WEEKDAY_LABELS = ['一', '', '三', '', '五', '', '日']
const heatmapDays = ref<HeatmapDay[]>([])
const heatmapMonths = ref<string[]>([])
const todayStr = todayLocalDate()
const streakDays = ref(0)

const streakLabel = computed(() => {
  if (streakDays.value <= 0) return '今天还没提交'
  return `连续打卡 ${streakDays.value} 天`
})

// 随机一题
function pickRandomProblem() {
  if (problems.value.length === 0) return
  const unsolved = problems.value.filter((p) => p.my_status !== 'solved')
  const pool = unsolved.length > 0 ? unsolved : problems.value
  const target = pool[Math.floor(Math.random() * pool.length)]
  if (target) {
    router.push(`/problems/${target.slug}`)
  }
}

// 统计核心算法专题
const CORE_CATEGORIES = ['数组', '双指针', '二叉树', '动态规划', '哈希表', '滑动窗口', '回溯', '图论', '链表', '栈']

const categoryStats = computed(() => {
  if (problems.value.length === 0) return []
  return CORE_CATEGORIES.map((cat) => {
    const list = problems.value.filter((p) => (p.tags || []).includes(cat))
    const solved = list.filter((p) => p.my_status === 'solved').length
    const total = list.length || 1
    return {
      name: cat,
      solved,
      total: list.length,
      percent: Math.round((solved / total) * 100),
    }
  }).filter((c) => c.total > 0)
})

function countLevel(count: number): number {
  if (count >= 5) return 4
  if (count >= 3) return 3
  if (count >= 2) return 2
  if (count >= 1) return 1
  return 0
}

function generateHeatmap(submissions: Submission[]) {
  const countMap = new Map<string, number>()
  for (const s of submissions) {
    const key = s.created_at.split('T')[0]
    if (key) countMap.set(key, (countMap.get(key) || 0) + 1)
  }

  const today = todayLocalDate()
  const todayDate = new Date()
  const mondayOffset = (todayDate.getDay() + 6) % 7
  const start = addDays(today, -(52 * 7 - 1 + mondayOffset))

  const days: HeatmapDay[] = []
  for (let cursor = start; cursor <= today; cursor = addDays(cursor, 1)) {
    const count = countMap.get(cursor) || 0
    days.push({
      date: cursor,
      count,
      level: countLevel(count),
      isToday: cursor === today,
      pad: false,
    })
  }
  while (days.length % 7 !== 0) {
    days.push({ date: '', count: 0, level: 0, isToday: false, pad: true })
  }

  const weekCount = days.length / 7
  const months: string[] = Array.from({ length: weekCount }, () => '')
  let lastMonth = ''
  for (let w = 0; w < weekCount; w++) {
    const cell = days[w * 7]
    if (!cell || cell.pad) continue
    const month = cell.date.slice(0, 7)
    if (month !== lastMonth) {
      months[w] = `${Number(cell.date.slice(5, 7))}月`
      lastMonth = month
    }
  }

  heatmapDays.value = days
  heatmapMonths.value = months

  let streak = 0
  let cursor = today
  if ((countMap.get(today) || 0) === 0) {
    cursor = addDays(today, -1)
  }
  while ((countMap.get(cursor) || 0) > 0) {
    streak += 1
    cursor = addDays(cursor, -1)
  }
  streakDays.value = streak
}

async function loadHome() {
  try {
    const [pList, jobs, subs, quiz] = await Promise.all([
      api.get<ProblemListItem[]>('/api/problems'),
      api.get<Job[]>('/api/jobs'),
      api.get<Submission[]>('/api/submissions?limit=100').catch(() => [] as Submission[]),
      api.get<QuizStats>('/api/quiz/stats').catch(() => null),
    ])
    problems.value = pList
    problemCount.value = pList.length
    solvedCount.value = pList.filter((p) => p.my_status === 'solved').length
    rememberedCount.value = pList.filter((p) => p.memory === 'remembered').length
    openJobCount.value = jobs.filter((j) => j.status !== 'closed' && (j.days_left === null || j.days_left >= 0)).length
    quizTotal.value = quiz?.total_questions ?? 0

    generateHeatmap(subs)
    error.value = ''
  } catch {
    error.value = '加载失败，请检查网络后重试'
  }
}

onMounted(() => loadHome())
</script>

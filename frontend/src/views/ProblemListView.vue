<template>
  <div class="container">
    <div class="page-head">
      <div>
        <div class="kicker">Problems</div>
        <h1 class="display">题库</h1>
      </div>
      <div class="head-stats">
        <div class="stat">
          <span class="num" :class="{ accent: stats.solved > 0 }">{{ stats.solved }}</span>
          <span class="lbl">已通过</span>
        </div>
        <div class="stat">
          <span class="num">{{ stats.attempted }}</span>
          <span class="lbl">尝试过</span>
        </div>
        <div class="stat">
          <span class="num">{{ problems.length }}</span>
          <span class="lbl">总题数</span>
        </div>
      </div>
    </div>

    <div v-if="!loading && problems.length" class="progress-track" title="按难度统计已通过">
      <div class="seg easy" :style="{ width: pct(stats.easySolved) }" title="简单通过"></div>
      <div class="seg medium" :style="{ width: pct(stats.mediumSolved) }" title="中等通过"></div>
      <div class="seg hard" :style="{ width: pct(stats.hardSolved) }" title="困难通过"></div>
    </div>

    <div class="filters">
      <input v-model="searchInput" class="input" placeholder="搜索题目标题 / slug (支持实时检索)" />
      <select v-model="difficulty" class="select">
        <option value="">全部难度</option>
        <option value="easy">简单</option>
        <option value="medium">中等</option>
        <option value="hard">困难</option>
      </select>
      <select v-model="source" class="select">
        <option value="">全部来源</option>
        <option value="hot100">热题 100</option>
        <option value="mianjing">面经手撕</option>
      </select>
      <select v-model="tag" class="select">
        <option value="">全部标签</option>
        <option v-for="t in allTags" :key="t" :value="t">{{ t }}</option>
      </select>
      <span class="problem-limits" style="margin-left:auto">{{ filtered.length }} / {{ problems.length }} 题</span>
    </div>

    <div class="card list-card">
      <div v-if="loading" style="padding:20px">
        <Skeleton :count="8" height="42px" width="100%" radius="8px" gap="10px" />
      </div>
      <div v-else-if="filtered.length === 0" class="empty">没有匹配的题目</div>
      <template v-else>
        <div class="list-head">
          <span class="sortable-th" @click="toggleSort('id')"># <AppIcon v-if="sortField === 'id'" name="chevron-down" :size="11" class="sort-caret" :class="{ asc: sortAsc }" /></span>
          <span class="sortable-th" @click="toggleSort('status')">状态 <AppIcon v-if="sortField === 'status'" name="chevron-down" :size="11" class="sort-caret" :class="{ asc: sortAsc }" /></span>
          <span class="sortable-th" @click="toggleSort('title')">题目 <AppIcon v-if="sortField === 'title'" name="chevron-down" :size="11" class="sort-caret" :class="{ asc: sortAsc }" /></span>
          <span class="sortable-th" @click="toggleSort('difficulty')">难度 <AppIcon v-if="sortField === 'difficulty'" name="chevron-down" :size="11" class="sort-caret" :class="{ asc: sortAsc }" /></span>
          <span class="sortable-th" @click="toggleSort('source')">来源 <AppIcon v-if="sortField === 'source'" name="chevron-down" :size="11" class="sort-caret" :class="{ asc: sortAsc }" /></span>
          <span>标签</span>
          <span></span>
        </div>
        <RouterLink
          v-for="(p, i) in filtered"
          :key="p.id"
          class="p-row"
          :to="`/problems/${p.slug}`"
        >
          <span class="p-idx">{{ p.leetcode_id ?? String(i + 1).padStart(2, '0') }}</span>
          <span class="p-check">
            <span v-if="p.my_status === 'solved'" class="solved" title="已通过"><AppIcon name="check" :size="14" :stroke-width="2.6" /></span>
            <span v-else-if="p.my_status === 'attempted'" class="attempted-dot" title="尝试过"></span>
            <span v-else class="todo">·</span>
          </span>
          <span class="p-main">
            <span class="p-title">{{ problemHeading(p) }}</span>
            <span class="p-slug">{{ p.slug }}</span>
          </span>
          <span class="badge" :class="`badge-${p.difficulty}`">{{ difficultyText(p.difficulty) }}</span>
          <span class="p-src">{{ sourceBadgeTexts(p, true).join(' · ') }}</span>
          <span class="p-tags">{{ p.tags.slice(0, 3).join(' · ') }}</span>
          <span class="p-arrow"><AppIcon name="chevron-right" :size="15" /></span>
        </RouterLink>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import AppIcon from '../components/AppIcon.vue'
import Skeleton from '../components/Skeleton.vue'
import { belongsToSource, problemHeading, sourceBadgeTexts, type Difficulty, type ProblemListItem } from '../types'

const problems = ref<ProblemListItem[]>([])
const loading = ref(true)
const searchInput = ref('')
const q = ref('')
const difficulty = ref('')
const source = ref('')
const tag = ref('')

const sortField = ref<'id' | 'title' | 'difficulty' | 'status' | 'source'>('id')
const sortAsc = ref(true)

let searchTimer: ReturnType<typeof setTimeout> | null = null

watch(searchInput, (val) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    q.value = val
  }, 200)
})

function toggleSort(field: 'id' | 'title' | 'difficulty' | 'status' | 'source') {
  if (sortField.value === field) {
    sortAsc.value = !sortAsc.value
  } else {
    sortField.value = field
    sortAsc.value = true
  }
}

const allTags = computed(() => {
  const s = new Set<string>()
  problems.value.forEach((p) => (p.tags || []).forEach((t) => s.add(t)))
  return [...s].sort()
})

const stats = computed(() => {
  let solved = 0, attempted = 0, easySolved = 0, mediumSolved = 0, hardSolved = 0
  for (const p of problems.value) {
    if (p.my_status === 'solved') {
      solved++
      if (p.difficulty === 'easy') easySolved++
      else if (p.difficulty === 'medium') mediumSolved++
      else hardSolved++
    } else if (p.my_status === 'attempted') attempted++
  }
  return { solved, attempted, easySolved, mediumSolved, hardSolved }
})

function pct(n: number) {
  return problems.value.length ? `${(n / problems.value.length) * 100}%` : '0%'
}

const difficultyWeight: Record<Difficulty, number> = {
  easy: 1,
  medium: 2,
  hard: 3,
}

const statusWeight: Record<string, number> = {
  solved: 2,
  attempted: 1,
}

const filtered = computed(() => {
  const kw = q.value.trim().toLowerCase()
  const list = problems.value.filter((p) => {
    if (difficulty.value && p.difficulty !== difficulty.value) return false
    if (source.value && !belongsToSource(p, source.value)) return false
    if (tag.value && !p.tags.includes(tag.value)) return false
    if (
      kw &&
      !p.title.toLowerCase().includes(kw) &&
      !p.slug.includes(kw) &&
      String(p.leetcode_id ?? '') !== kw
    )
      return false
    return true
  })

  return list.sort((a, b) => {
    let cmp = 0
    if (sortField.value === 'id') {
      const av = a.leetcode_id ?? a.id
      const bv = b.leetcode_id ?? b.id
      cmp = av - bv
    }
    else if (sortField.value === 'title') cmp = a.title.localeCompare(b.title, 'zh-CN')
    else if (sortField.value === 'difficulty') cmp = difficultyWeight[a.difficulty] - difficultyWeight[b.difficulty]
    else if (sortField.value === 'status') cmp = (statusWeight[a.my_status || ''] || 0) - (statusWeight[b.my_status || ''] || 0)
    else if (sortField.value === 'source') cmp = a.source.localeCompare(b.source)

    return sortAsc.value ? cmp : -cmp
  })
})

function difficultyText(d: Difficulty) {
  return d === 'easy' ? '简单' : d === 'medium' ? '中等' : '困难'
}

onMounted(async () => {
  try {
    problems.value = await api.get<ProblemListItem[]>('/api/problems')
  } finally {
    loading.value = false
  }
})
</script>

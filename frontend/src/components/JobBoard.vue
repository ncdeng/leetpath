<template>
  <div class="job-board-wrap">
    <!-- 顶部状态提示与统计 -->
    <div class="job-stats-bar" v-if="!loading && jobs.length > 0">
      <div class="stat-pill">
        <span class="pill-dot"></span>
        <span>秋招火热进行中 · 共 <strong>{{ companyList.length }}</strong> 家公司 <strong>{{ jobs.length }}</strong> 个岗位</span>
      </div>
      <div class="tracked-count" v-if="trackedJobIds.size > 0">
        已标记跟进 <strong>{{ trackedJobIds.size }}</strong> 个岗位
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <div v-if="!limit" class="filters job-filters">
      <!-- 搜索关键词 -->
      <input v-model="q" class="input search-job-input" placeholder="搜索公司或岗位关键词，如 字节 / 腾讯 / 算法 / 后端" />

      <!-- 秋招批次选择 -->
      <select v-model="batchFilter" class="select">
        <option value="">全部秋招批次</option>
        <option value="urgent">7 天内急投</option>
        <option value="early">秋招提前批</option>
        <option value="regular">秋招正式批</option>
      </select>

      <!-- 公司规模与梯队 -->
      <select v-model="tierFilter" class="select">
        <option value="">全部公司梯队</option>
        <option value="big">头部大厂</option>
        <option value="mid">中厂 / 独角兽</option>
        <option value="small">精选中小型 / 初创</option>
      </select>

      <!-- 快速标签开关 -->
      <label class="job-checkbox-label">
        <input type="checkbox" v-model="openOnly" /> 只看在招
      </label>
      <label class="job-checkbox-label" v-if="trackedJobIds.size > 0">
        <input type="checkbox" v-model="trackedOnly" /> 仅看我跟进的
      </label>

      <span class="problem-limits">
        显示 {{ filteredCompanies.length }} 家公司 / {{ filteredJobsCount }} 岗
      </span>
    </div>

    <!-- 骨架屏加载 -->
    <div v-if="loading" class="job-skeleton-grid">
      <div v-for="i in 6" :key="i" class="card job-skeleton-card">
        <Skeleton :count="1" height="28px" width="50%" radius="6px" gap="10px" />
        <Skeleton :count="2" height="16px" width="80%" radius="4px" gap="8px" />
      </div>
    </div>

    <div v-else-if="filteredCompanies.length === 0" class="empty">
      没有匹配的秋招公司或岗位
    </div>

    <!-- 公司聚合卡片列表 (Company-Centric Accordion) -->
    <div v-else class="company-grid">
      <div
        v-for="c in filteredCompanies"
        :key="c.name"
        class="card company-card"
        :class="{ 'is-expanded': expandedCompanies.has(c.name) }"
      >
        <!-- 公司卡片头部 -->
        <div class="company-head" @click="toggleCompany(c.name)">
          <span class="company-logo" :style="tileStyle(c.name)">{{ c.name.slice(0, 1) }}</span>

          <div class="company-info">
            <div class="company-title-line">
              <span class="company-name">{{ c.name }}</span>
              <span class="badge" :class="`badge-${c.tier}`">{{ tierName(c.tier) }}</span>
              <span class="pos-count-tag">{{ c.jobs.length }} 个在招岗位</span>
            </div>
            <div class="company-meta-line">
              <span class="dday-pill" :class="c.earliestDDay.cls">{{ c.earliestDDay.text }}</span>
              <span class="roles-preview" v-if="c.roles.length > 0">
                涵盖: {{ c.roles.slice(0, 4).join(' · ') }}
              </span>
            </div>
          </div>

          <div class="company-actions" @click.stop>
            <a
              v-if="c.homepageUrl"
              :href="c.homepageUrl"
              target="_blank"
              rel="noopener"
              class="btn btn-sm btn-ghost"
              title="前往校招官网投递主页"
            >
              校招官网 <AppIcon name="arrow-right" :size="12" class="icon-open" />
            </a>
            <button
              class="btn btn-sm expand-btn"
              @click.stop="toggleCompany(c.name)"
            >
              {{ expandedCompanies.has(c.name) ? '收起' : `查看岗位 (${c.jobs.length})` }}
              <AppIcon name="chevron-down" :size="13" class="expand-chevron" />
            </button>
          </div>
        </div>

        <!-- 展开的岗位细分抽屉 (Positions Drawer) -->
        <transition name="drawer">
          <div v-if="expandedCompanies.has(c.name)" class="positions-drawer">
            <!-- 岗位角色快捷筛选（仅当岗位较多时展示） -->
            <div class="role-filter-chips" v-if="c.roles.length > 3">
              <button
                class="chip-btn"
                :class="{ active: !selectedRole[c.name] }"
                @click="selectedRole[c.name] = ''"
              >
                全部方向 ({{ c.jobs.length }})
              </button>
              <button
                v-for="r in c.roles"
                :key="r"
                class="chip-btn"
                :class="{ active: selectedRole[c.name] === r }"
                @click="selectedRole[c.name] = r"
              >
                {{ r }}
              </button>
            </div>

            <div class="positions-list">
              <div
                v-for="job in getFilteredJobs(c)"
                :key="job.id"
                class="pos-card job-card"
                :class="{ 'is-closed': isClosed(job), 'is-tracked': getTrackedStatus(job.id) !== 'none' }"
              >
                <div class="pos-top-line">
                  <div class="pos-title-wrap">
                    <span class="pos-title">{{ job.position }}</span>
                    <span v-if="job.batch" class="badge badge-source">{{ job.batch }}</span>
                    <span class="dday-mini" :class="ddayClass(job)">{{ ddayText(job) }}</span>
                  </div>

                  <div class="pos-actions">
                    <a
                      v-if="job.apply_url"
                      :href="job.apply_url"
                      target="_blank"
                      rel="noopener"
                      class="btn btn-sm btn-primary"
                    >
                      直达投递 <AppIcon name="arrow-right" :size="12" class="icon-open" />
                    </a>
                    <slot name="actions" :job="job"></slot>
                  </div>
                </div>

                <div class="pos-time-line">
                  <span v-if="job.open_at">开投: {{ job.open_at }}</span>
                  <span v-if="job.deadline_at">截止: {{ job.deadline_at }}</span>
                  <span v-if="job.jd_text">
                    <button type="button" class="jd-toggle" :class="{ open: expandedJd.has(job.id) }" @click="toggleJd(job.id)">
                      {{ expandedJd.has(job.id) ? '收起 JD' : '查看 JD 要求' }}
                      <AppIcon name="chevron-down" :size="12" class="jd-chevron" />
                    </button>
                  </span>
                </div>

                <!-- 展开的 JD 详情 -->
                <div v-if="expandedJd.has(job.id) && job.jd_text" class="pos-jd-content">
                  <pre>{{ job.jd_text }}</pre>
                </div>

                <!-- 个人求职投递状态流转器 -->
                <div class="tracker-status-bar">
                  <span class="tracker-lbl">求职进度:</span>
                  <div class="tracker-steps">
                    <button
                      v-for="st in STATUS_STEPS"
                      :key="st.key"
                      class="step-chip"
                      :class="{ active: getTrackedStatus(job.id) === st.key }"
                      @click="setTrackedStatus(job.id, st.key)"
                    >
                      {{ st.label }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import Skeleton from './Skeleton.vue'
import AppIcon from './AppIcon.vue'
import { useToast } from '../stores/toast'
import type { Job } from '../types'
import { compareFeaturedCompanies } from '../jobBoardSort'

const props = defineProps<{ limit?: number }>()
const toast = useToast()

const jobs = ref<Job[]>([])
const loading = ref(true)
const q = ref('')
const batchFilter = ref('')
const tierFilter = ref('')
const openOnly = ref(true)
const trackedOnly = ref(false)

const expandedCompanies = ref(new Set<string>())
const expandedJd = ref(new Set<number>())
const selectedRole = reactive<Record<string, string>>({})

// 个人投递进度（入库，多端同步）
const trackerData = ref<Record<number, string>>({})

const STATUS_STEPS = [
  { key: 'none', label: '未标记' },
  { key: 'applied', label: '已投简历' },
  { key: 'test', label: '笔试中' },
  { key: 'interview', label: '面试中' },
  { key: 'offer', label: '已获 Offer' },
  { key: 'rejected', label: '流程结束' },
]

function getTrackedStatus(jobId: number) {
  return trackerData.value[jobId] || 'none'
}

async function setTrackedStatus(jobId: number, status: string) {
  try {
    await api.put(`/api/jobs/${jobId}/track`, { status })
  } catch {
    toast.error('标记失败，请稍后重试')
    return
  }
  if (status === 'none') {
    delete trackerData.value[jobId]
  } else {
    trackerData.value[jobId] = status
    const label = STATUS_STEPS.find((s) => s.key === status)?.label || ''
    toast.success(`已标记为: ${label}`)
  }
}

const trackedJobIds = computed(() => {
  const s = new Set<number>()
  for (const [id, st] of Object.entries(trackerData.value)) {
    if (st && st !== 'none') s.add(Number(id))
  }
  return s
})

interface CompanyGroup {
  name: string
  tier: 'big' | 'mid' | 'small'
  jobs: Job[]
  roles: string[]
  homepageUrl?: string
  earliestDDay: { text: string; cls: string; days: number | null }
}

function extractRole(pos: string): string {
  const p = pos.toLowerCase()
  if (p.includes('算法') || p.includes('ai') || p.includes('大模型') || p.includes('视觉') || p.includes('nlp') || p.includes('搜索'))
    return 'AI/算法'
  if (p.includes('后端') || p.includes('研发') || p.includes('后台') || p.includes('开发') || p.includes('java') || p.includes('c++') || p.includes('go'))
    return '后端/研发'
  if (p.includes('前端') || p.includes('web')) return '前端开发'
  if (p.includes('客户端') || p.includes('android') || p.includes('ios')) return '客户端'
  if (p.includes('测试') || p.includes('测开') || p.includes('qa')) return '测试/质量'
  if (p.includes('产品') || p.includes('运营')) return '产品/运营'
  return '技术综合'
}

const companyList = computed<CompanyGroup[]>(() => {
  const map = new Map<string, Job[]>()
  for (const j of jobs.value) {
    if (!map.has(j.company)) map.set(j.company, [])
    map.get(j.company)!.push(j)
  }

  const result: CompanyGroup[] = []
  for (const [name, cJobs] of map.entries()) {
    const tier = cJobs[0]?.tier || 'small'
    const roles = [...new Set(cJobs.map((j) => extractRole(j.position)))]
    const homepage = cJobs.find((j) => j.apply_url)?.apply_url || undefined

    // 计算最早截止天数
    let minDays: number | null = null
    for (const j of cJobs) {
      if (j.days_left !== null && j.status !== 'closed' && j.days_left >= 0) {
        if (minDays === null || j.days_left < minDays) minDays = j.days_left
      }
    }

    let ddayText = '长期招募'
    let ddayCls = 'ok'
    if (minDays !== null) {
      if (minDays === 0) {
        ddayText = '今天截止'
        ddayCls = 'urgent'
      } else if (minDays <= 7) {
        ddayText = `最早 D-${minDays} 截止`
        ddayCls = 'urgent'
      } else if (minDays <= 14) {
        // 两周内截止： amber 提示档，避免 D-8 与 D-93 同灰无从分辨缓急
        ddayText = `最早 D-${minDays} 截止`
        ddayCls = 'soon'
      } else {
        ddayText = `最早 D-${minDays} 截止`
        ddayCls = 'normal'
      }
    }

    result.push({
      name,
      tier,
      jobs: cJobs,
      roles,
      homepageUrl: homepage,
      earliestDDay: { text: ddayText, cls: ddayCls, days: minDays },
    })
  }

  return result.sort((a, b) => compareFeaturedCompanies(
    { tier: a.tier, deadlineDays: a.earliestDDay.days, jobCount: a.jobs.length },
    { tier: b.tier, deadlineDays: b.earliestDDay.days, jobCount: b.jobs.length },
  ))
})

const filteredCompanies = computed(() => {
  const kw = q.value.trim().toLowerCase()

  const list = companyList.value
    .map((c) => {
      // 过滤公司下的岗位
      const matchedJobs = c.jobs.filter((j) => {
        if (tierFilter.value && (j.tier ?? 'small') !== tierFilter.value) return false
        if (openOnly.value && isClosed(j)) return false
        if (trackedOnly.value && !trackedJobIds.value.has(j.id)) return false

        // 批次筛选
        if (batchFilter.value === 'urgent') {
          if (j.days_left === null || j.days_left < 0 || j.days_left > 7) return false
        } else if (batchFilter.value === 'early') {
          if (!((j.batch ?? '').includes('提前') || (j.position ?? '').includes('提前'))) return false
        } else if (batchFilter.value === 'regular') {
          if ((j.batch ?? '').includes('提前')) return false
        }

        // 关键词搜索（匹配公司、岗位、JD、方向）
        if (kw) {
          const matchCompany = c.name.toLowerCase().includes(kw)
          const matchPos = j.position.toLowerCase().includes(kw)
          const matchJd = (j.jd_text ?? '').toLowerCase().includes(kw)
          const matchBatch = (j.batch ?? '').toLowerCase().includes(kw)
          if (!matchCompany && !matchPos && !matchJd && !matchBatch) return false
        }
        return true
      })

      if (matchedJobs.length === 0) return null
      return {
        ...c,
        jobs: matchedJobs,
      }
    })
    .filter((c): c is CompanyGroup => c !== null)

  return props.limit ? list.slice(0, props.limit) : list
})

const filteredJobsCount = computed(() =>
  filteredCompanies.value.reduce((sum, c) => sum + c.jobs.length, 0),
)

function getFilteredJobs(c: CompanyGroup): Job[] {
  const role = selectedRole[c.name]
  if (!role) return c.jobs
  return c.jobs.filter((j) => extractRole(j.position) === role)
}

function tierName(tier: string) {
  if (tier === 'big') return '头部大厂'
  if (tier === 'mid') return '中厂/独角兽'
  return '精选小厂'
}

function isClosed(job: Job) {
  return job.status === 'closed' || (job.days_left !== null && job.days_left < 0)
}

function ddayText(job: Job) {
  if (job.status === 'closed') return '已关闭'
  if (job.days_left === null) return '长期'
  if (job.days_left < 0) return '已截止'
  if (job.days_left === 0) return '今天截止'
  return `D-${job.days_left}`
}

function ddayClass(job: Job) {
  if (isClosed(job)) return 'closed'
  if (job.days_left !== null && job.days_left <= 7) return 'urgent'
  if (job.days_left !== null && job.days_left <= 14) return 'soon'
  return 'ok'
}

function tileStyle(company: string) {
  let h = 0
  for (const ch of company) h = (h * 31 + ch.codePointAt(0)!) % 360
  return {
    background: `hsl(${h} 65% 55% / 0.14)`,
    color: `hsl(${h} 70% 62%)`,
    border: `1px solid hsl(${h} 65% 55% / 0.25)`,
  }
}

function toggleCompany(name: string) {
  const s = new Set(expandedCompanies.value)
  if (s.has(name)) s.delete(name)
  else s.add(name)
  expandedCompanies.value = s
}

function toggleJd(id: number) {
  const s = new Set(expandedJd.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  expandedJd.value = s
}

async function load() {
  loading.value = true
  try {
    jobs.value = await api.get<Job[]>('/api/jobs')
    // 不再默认展开公司：头部大厂单家就有几百个岗位，自动展开会一次性渲染
    // 数千个 DOM 节点，每次进入看板都触发一次渲染尖峰（低端 GPU 直接卡死）
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const saved = await api.get<Record<string, string>>('/api/jobs/track')
    const parsed: Record<number, string> = {}
    for (const [id, st] of Object.entries(saved)) parsed[Number(id)] = st
    trackerData.value = parsed
  } catch {}
  load()
})

defineExpose({ reload: load })
</script>

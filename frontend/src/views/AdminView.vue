<template>
  <div class="container">
    <div v-if="error" class="error-banner">
      <span>{{ error }}</span>
      <button type="button" class="btn btn-sm" @click="loadAll">重试</button>
    </div>
    <div class="page-head">
      <div>
        <div class="kicker">Admin</div>
        <h1 class="display">管理后台</h1>
      </div>
    </div>

    <div class="segmented admin-tabs">
      <button type="button" :class="{ active: tab === 'problems' }" @click="tab = 'problems'">题目管理</button>
      <button type="button" :class="{ active: tab === 'jobs' }" @click="tab = 'jobs'">看板管理</button>
      <button type="button" :class="{ active: tab === 'invites' }" @click="tab = 'invites'">邀请码</button>
      <button type="button" :class="{ active: tab === 'ai' }" @click="tab = 'ai'"><AppIcon name="robot" :size="14" /> AI 内测配置</button>
    </div>

    <!-- 题目管理 -->
    <div v-show="tab === 'problems'" class="card">
      <div class="admin-card-toolbar">
        <button class="btn btn-sm btn-primary" :disabled="seeding" @click="reloadSeed">
          {{ seeding ? '导入中…' : '重新导入题库与八股' }}
        </button>
        <span v-if="seedMsg" class="admin-note">{{ seedMsg }}</span>
      </div>
      <div v-if="problems.length === 0" class="empty">暂无题目，点上方按钮导入种子</div>
      <div v-for="p in problems" :key="p.id" class="admin-row">
        <span class="badge" :class="`badge-${p.difficulty}`">{{ p.difficulty }}</span>
        <span class="grow">{{ problemHeading(p) }} <span class="admin-dim">{{ p.slug }}</span></span>
        <label class="admin-check">
          <input type="checkbox" :checked="p.is_published" @change="togglePublish(p)" /> 上架
        </label>
      </div>
    </div>

    <!-- 看板管理 -->
    <div v-show="tab === 'jobs'">
      <div class="card admin-card">
        <h3>{{ editingJob ? '编辑岗位' : '新增岗位' }}</h3>
        <div v-if="jobError" class="form-err">{{ jobError }}</div>
        <form @submit.prevent="saveJob">
          <div class="admin-form-grid">
            <div class="field"><label>公司 *</label><input v-model="jobForm.company" class="input" required /></div>
            <div class="field"><label>岗位 *</label><input v-model="jobForm.position" class="input" required /></div>
            <div class="field"><label>批次</label><input v-model="jobForm.batch" class="input" placeholder="如 2027秋招" /></div>
            <div class="field"><label>开投日期</label><input v-model="jobForm.open_at" class="input" type="date" /></div>
            <div class="field"><label>截止日期</label><input v-model="jobForm.deadline_at" class="input" type="date" /></div>
            <div class="field"><label>投递链接</label><input v-model="jobForm.apply_url" class="input" type="url" placeholder="https://" /></div>
            <div class="field">
              <label>规模</label>
              <select v-model="jobForm.tier" class="select">
                <option value="big">大厂</option>
                <option value="mid">中厂</option>
                <option value="small">小厂</option>
              </select>
            </div>
            <div class="field">
              <label>状态</label>
              <select v-model="jobForm.status" class="select">
                <option value="open">进行中</option>
                <option value="closed">已关闭</option>
              </select>
            </div>
          </div>
          <div class="field"><label>JD 摘要</label><textarea v-model="jobForm.jd_text" class="textarea" rows="3"></textarea></div>
          <div class="admin-actions">
            <button class="btn btn-primary btn-sm" type="submit">{{ editingJob ? '保存修改' : '添加岗位' }}</button>
            <button v-if="editingJob" class="btn btn-sm" type="button" @click="resetForm">取消编辑</button>
          </div>
        </form>
      </div>

      <div class="card">
        <div v-if="jobs.length === 0" class="empty">暂无岗位</div>
        <div v-for="j in jobs" :key="j.id" class="admin-row">
          <span class="grow"><b>{{ j.company }}</b> · {{ j.position }}
            <span class="admin-dim">{{ j.deadline_at ? ` 截止 ${j.deadline_at}` : '' }}</span>
          </span>
          <button class="btn btn-sm" @click="editJob(j)">编辑</button>
          <button class="btn btn-sm btn-danger-text" @click="deleteJob(j)">删除</button>
        </div>
      </div>
    </div>

    <div v-show="tab === 'invites'">
      <div class="card admin-card">
        <h3>创建一次性邀请码</h3>
        <div class="admin-inline-form">
          <div class="field">
            <label>有效期</label>
            <select v-model="inviteDays" class="select">
              <option :value="1">1 天</option>
              <option :value="3">3 天</option>
              <option :value="7">7 天</option>
              <option :value="30">30 天</option>
            </select>
          </div>
          <button class="btn btn-primary btn-sm" :disabled="creatingInvite" @click="createInvite">
            {{ creatingInvite ? '生成中…' : '生成邀请码' }}
          </button>
        </div>
        <div v-if="newInviteCode" class="invite-result">
          <code>{{ newInviteCode }}</code>
          <button class="btn btn-sm" @click="copyInvite">复制</button>
        </div>
        <div v-if="inviteMessage" class="admin-note admin-note-block">
          {{ inviteMessage }}
        </div>
      </div>

      <div class="card">
        <div v-if="invites.length === 0" class="empty">还没有邀请码</div>
        <div v-for="invite in invites" :key="invite.id" class="admin-row">
          <span class="grow">
            <b>#{{ invite.id }}</b>
            <span class="admin-dim"> 有效至 {{ formatInviteTime(invite.expires_at) }}</span>
          </span>
          <span class="badge" :class="inviteState(invite).className">{{ inviteState(invite).text }}</span>
          <button
            v-if="!invite.used_at && !invite.revoked_at"
            class="btn btn-sm btn-danger-text"
            @click="revokeInvite(invite.id)"
          >撤销</button>
        </div>
      </div>
    </div>

    <!-- AI 内测配置 -->
    <div v-show="tab === 'ai'">
      <div class="card admin-card">
        <div class="admin-head-row">
          <div>
            <h3><AppIcon name="robot" :size="17" class="admin-h3-icon" />系统内置共享 AI 助教配置（内测免 Key 模式）</h3>
            <p class="muted admin-note-block">
              在此配置由你（管理员）统一提供的 API Key。配置后，<strong>所有内测用户登录后无需输入任何 Key 即可直接与 Grok 提问对话</strong>。
            </p>
          </div>
          <span
            class="badge admin-key-badge"
            :class="aiConfig.has_key ? 'badge-easy' : 'badge-hard'"
          >
            <AppIcon :name="aiConfig.has_key ? 'check' : 'x'" :size="12" />
            {{ aiConfig.has_key ? `已启用内置 Key (${aiConfig.masked_key})` : '尚未配置内置 Key' }}
          </span>
        </div>

        <div v-if="aiMsg" :class="aiMsgType === 'error' ? 'form-err' : 'form-success'">
          {{ aiMsg }}
        </div>

        <form @submit.prevent="saveAiConfig">
          <div class="admin-form-grid admin-form-grid-wide">
            <div class="field">
              <label>Antithor / OpenAI 接口地址 (Base URL) *</label>
              <input
                v-model="aiForm.base_url"
                class="input mono"
                required
                placeholder="https://api.antithor.asia/v1"
              />
            </div>
            <div class="field">
              <label>默认 AI 模型 (Model) *</label>
              <input
                v-model="aiForm.model"
                class="input mono"
                required
                placeholder="grok-4.6-xhigh"
              />
            </div>
            <div class="field admin-field-full">
              <label>系统内置 API Key (支持 Antithor 密钥) *</label>
              <input
                v-model="aiForm.api_key"
                type="password"
                class="input mono"
                :placeholder="aiConfig.has_key ? `留空保持当前密钥 (${aiConfig.masked_key})，输入新密钥覆盖` : 'sk-xxxxxxxxxxxxxxxxxxxxxxxx'"
              />
              <small class="admin-field-hint">
                安全承诺：此 Key 仅保存在服务器数据库 WAL 中，绝不下发给普通用户的前端 JS 或网络抓包，普通用户只能通过服务器代理进行安全问答。
              </small>
            </div>
          </div>

          <div class="admin-actions">
            <button class="btn btn-primary" :disabled="savingAi" type="submit">
              {{ savingAi ? '保存中…' : '保存并应用全局内置 Key' }}
            </button>
            <button class="btn btn-outline" :disabled="testingAi" type="button" @click="testAiConnection">
              <AppIcon name="refresh" :size="14" /> {{ testingAi ? '测试中…' : '测试中转站连接与拉取模型' }}
            </button>
            <span v-if="aiTestResult" class="admin-ok">{{ aiTestResult }}</span>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import AppIcon from '../components/AppIcon.vue'
import { problemHeading, type InviteCreated, type InviteSummary, type Job, type ProblemListItem } from '../types'
import { copyToClipboard } from '../clipboard'

interface AdminProblem extends ProblemListItem {
  is_published: boolean
}

interface SystemAiConfig {
  has_key: boolean
  masked_key: string
  base_url: string
  model: string
  updated_at: string | null
}

const tab = ref<'problems' | 'jobs' | 'invites' | 'ai'>('problems')
const error = ref('')

// 题目管理
const problems = ref<AdminProblem[]>([])
const seeding = ref(false)
const seedMsg = ref('')

async function loadProblems() {
  problems.value = await api.get<AdminProblem[]>('/api/admin/problems')
}

async function togglePublish(p: AdminProblem) {
  await api.put(`/api/admin/problems/${p.id}`, { is_published: !p.is_published })
  p.is_published = !p.is_published
}

async function reloadSeed() {
  seeding.value = true
  seedMsg.value = ''
  try {
    const res = await api.post<{ imported: number; quiz_imported?: number }>('/api/admin/seed/reload')
    seedMsg.value = `已导入 ${res.imported} 道算法题、${res.quiz_imported ?? 0} 道八股`
    await loadProblems()
  } catch (e) {
    seedMsg.value = e instanceof Error ? e.message : '导入失败'
  } finally {
    seeding.value = false
  }
}

// 看板管理
const jobs = ref<Job[]>([])
const editingJob = ref<Job | null>(null)
const jobError = ref('')
const jobForm = reactive({
  company: '',
  position: '',
  tier: 'small',
  batch: '',
  open_at: '',
  deadline_at: '',
  apply_url: '',
  jd_text: '',
  status: 'open',
})

async function loadJobs() {
  jobs.value = await api.get<Job[]>('/api/jobs')
}

function resetForm() {
  editingJob.value = null
  jobError.value = ''
  Object.assign(jobForm, {
    company: '', position: '', tier: 'small', batch: '', open_at: '', deadline_at: '',
    apply_url: '', jd_text: '', status: 'open',
  })
}

function editJob(j: Job) {
  editingJob.value = j
  Object.assign(jobForm, {
    company: j.company,
    position: j.position,
    tier: j.tier ?? 'small',
    batch: j.batch ?? '',
    open_at: j.open_at ?? '',
    deadline_at: j.deadline_at ?? '',
    apply_url: j.apply_url ?? '',
    jd_text: j.jd_text ?? '',
    status: j.status,
  })
}

async function saveJob() {
  jobError.value = ''
  const body = {
    company: jobForm.company,
    position: jobForm.position,
    tier: jobForm.tier,
    batch: jobForm.batch || null,
    open_at: jobForm.open_at || null,
    deadline_at: jobForm.deadline_at || null,
    apply_url: jobForm.apply_url || null,
    jd_text: jobForm.jd_text || null,
    status: jobForm.status,
  }
  try {
    if (editingJob.value) {
      await api.put(`/api/jobs/${editingJob.value.id}`, body)
    } else {
      await api.post('/api/jobs', body)
    }
    resetForm()
    await loadJobs()
  } catch (e) {
    jobError.value = e instanceof Error ? e.message : '保存失败'
  }
}

async function deleteJob(j: Job) {
  if (!confirm(`确认删除「${j.company} · ${j.position}」？`)) return
  await api.del(`/api/jobs/${j.id}`)
  await loadJobs()
}

const invites = ref<InviteSummary[]>([])
const inviteDays = ref(7)
const creatingInvite = ref(false)
const newInviteCode = ref('')
const inviteMessage = ref('')

async function loadInvites() {
  invites.value = await api.get<InviteSummary[]>('/api/admin/invites')
}

async function createInvite() {
  creatingInvite.value = true
  inviteMessage.value = ''
  newInviteCode.value = ''
  try {
    const invite = await api.post<InviteCreated>('/api/admin/invites', {
      expires_in_days: inviteDays.value,
    })
    newInviteCode.value = invite.code
    inviteMessage.value = '邀请码只在这里显示一次，请立即发给需要注册的朋友。'
    await loadInvites()
  } catch (e) {
    inviteMessage.value = e instanceof Error ? e.message : '邀请码生成失败'
  } finally {
    creatingInvite.value = false
  }
}

async function copyInvite() {
  if (!newInviteCode.value) return
  inviteMessage.value = await copyToClipboard(newInviteCode.value)
    ? '邀请码已复制'
    : '复制失败，请手动复制'
}

async function revokeInvite(id: number) {
  await api.del(`/api/admin/invites/${id}`)
  await loadInvites()
}

function formatInviteTime(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}

function inviteState(invite: InviteSummary) {
  if (invite.revoked_at) return { text: '已撤销', className: 'badge-hard' }
  if (invite.used_at) return { text: '已使用', className: 'badge-easy' }
  if (new Date(invite.expires_at).getTime() <= Date.now()) {
    return { text: '已过期', className: 'badge-medium' }
  }
  return { text: '可使用', className: 'badge-source' }
}

// AI 内测配置管理
const aiConfig = ref<SystemAiConfig>({
  has_key: false,
  masked_key: '',
  base_url: 'https://api.antithor.asia/v1',
  model: 'grok-4.6-xhigh',
  updated_at: null,
})
const aiForm = reactive({
  base_url: 'https://api.antithor.asia/v1',
  model: 'grok-4.6-xhigh',
  api_key: '',
})
const savingAi = ref(false)
const testingAi = ref(false)
const aiMsg = ref('')
const aiMsgType = ref<'success' | 'error'>('success')
const aiTestResult = ref('')

async function loadAiConfig() {
  try {
    const res = await api.get<SystemAiConfig>('/api/admin/ai-config')
    aiConfig.value = res
    aiForm.base_url = res.base_url || 'https://api.antithor.asia/v1'
    aiForm.model = res.model || 'grok-4.6-xhigh'
  } catch {
    // ignore
  }
}

async function saveAiConfig() {
  savingAi.value = true
  aiMsg.value = ''
  try {
    const res = await api.put<SystemAiConfig>('/api/admin/ai-config', {
      base_url: aiForm.base_url,
      model: aiForm.model,
      api_key: aiForm.api_key,
    })
    aiConfig.value = res
    aiForm.api_key = ''
    aiMsg.value = '✓ 系统内置 AI 配置保存成功！全体内测用户已无感生效。'
    aiMsgType.value = 'success'
  } catch (e) {
    aiMsg.value = e instanceof Error ? e.message : '保存失败'
    aiMsgType.value = 'error'
  } finally {
    savingAi.value = false
  }
}

async function testAiConnection() {
  testingAi.value = true
  aiTestResult.value = ''
  aiMsg.value = ''
  try {
    const res = await api.post<any>('/api/ai/models', {
      base_url: aiForm.base_url,
      api_key: aiForm.api_key,
    })
    const count = res?.data?.length || 0
    aiTestResult.value = `✓ 连接成功！从中转站成功识别到 ${count} 个可用模型`
  } catch (e) {
    aiMsg.value = `测试失败: ${e instanceof Error ? e.message : '无法连接中转站'}`
    aiMsgType.value = 'error'
  } finally {
    testingAi.value = false
  }
}

async function loadAll() {
  try {
    await Promise.all([loadProblems(), loadJobs(), loadInvites(), loadAiConfig()])
    error.value = ''
  } catch {
    error.value = '加载失败，请检查网络后重试'
  }
}

onMounted(() => loadAll())
</script>

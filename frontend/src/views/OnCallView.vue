<template>
  <div class="container oncall-page">
    <div class="page-head">
      <div>
        <div class="kicker">Project Deep Dive & Interview Prep</div>
        <h1 class="display">OnCall 智能值班项目作战室</h1>
      </div>
      <div class="head-stats">
        <div class="stat">
          <span class="num accent">63</span>
          <span class="lbl">核心面试真题</span>
        </div>
        <div class="stat">
          <span class="num">5</span>
          <span class="lbl">技术模块深度拆解</span>
        </div>
        <div class="stat">
          <span class="num">0 ➔ 1</span>
          <span class="lbl">实战架构复盘</span>
        </div>
      </div>
    </div>

    <!-- 导航选项卡 -->
    <div class="oncall-tabs-wrap">
      <div class="segmented oncall-tabs">
        <button :class="{ active: currentTab === 'notes' }" @click="currentTab = 'notes'">
          📋 架构笔记与 60s 话术
        </button>
        <button :class="{ active: currentTab === 'questions' }" @click="currentTab = 'questions'">
          🎯 63 道面试真题专栏
        </button>
        <button :class="{ active: currentTab === 'mock' }" @click="currentTab = 'mock'">
          🤖 AI 面试官模拟实战
        </button>
      </div>
    </div>

    <!-- ==================== 模块 1: 架构笔记与 60s 话术 ==================== -->
    <section v-if="currentTab === 'notes'" class="blueprint-grid">
      <!-- 60s 满分话术 -->
      <div class="card bp-card">
        <h2><AppIcon name="sparkles" :size="20" /> 60 秒口头项目介绍模板（面试必背）</h2>
        <div class="bp-pitch-box">
          <div class="bp-pitch-title">🎯 标准 60s 口述版本：</div>
          “我在业余时间<strong>从 0 到 1 独立设计并落地了一套 OnCall 智能值班与故障排查 Agent 系统</strong>。痛点在于此前上游业务与开发同事经常遇到同一类报错重复来问，翻文档成本高，耗费大量时间打杂。因此我利用 <strong>FastAPI + Eino / Spring-AI-Alibaba 工作流</strong> 构建了智能值班助手：接入腾讯云日志检索、动态错误码匹配与基于向量数据库的 RAG 知识库检索，自动给出故障诊断报告与修复脚本。<br/><br/>
          核心难点主要攻克了三点：<strong>第一是日志防爆上下文</strong>，通过滑动窗口 + 错误行特征摘要将 Token 开销降低了 60% 以上；<strong>第二是意图识别分发与 Multi-Agent 编排</strong>，支持根据报错类型路由到排障 Agent 或文档检索 Agent；<strong>第三是针对 Agent Tool 调用的容错与降级兜底机制</strong>，即使模型产生幻觉也能保证服务稳定可用。”
        </div>
      </div>

      <!-- 系统架构与技术选型 -->
      <div class="card bp-card">
        <h2><AppIcon name="book" :size="20" /> 系统架构全景与技术选型对比</h2>
        <div class="bp-grid-2col">
          <div class="bp-subcard">
            <h3>⚡ 核心技术选型</h3>
            <ul>
              <li><strong>Agent 框架</strong>：选用轻量高性能工作流（Eino / Spring-AI-Alibaba），摒弃冗余臃肿的 LangChain，调用链更可控、调试更直观。</li>
              <li><strong>知识库检索 (RAG)</strong>：向量库（Milvus）+ 密集向量检索，Top-K 精准召回排障 Sop 文档。</li>
              <li><strong>实时推送</strong>：采用 <strong>SSE (Server-Sent Events)</strong> 单向流式推送排障进度与思考链，对比 WebSocket 协议更轻、天然契合 HTTP 鉴权与重连。</li>
              <li><strong>数据存储</strong>：SQLite WAL 模式存储工单与对话快照，读写并发高效且部署零运维负担。</li>
            </ul>
          </div>

          <div class="bp-subcard">
            <h3>🔥 核心技术难点与避坑点</h3>
            <ul>
              <li><strong>日志上下文防爆</strong>：长日志严禁直接丢进 Prompt。先通过正则提取堆栈关节点，再由轻量模型做行级摘要压缩。</li>
              <li><strong>Prompt 注意力衰减治理</strong>：遵循 <code>System Prompt ➔ 历史对话摘要 ➔ 最近两轮上下文</code> 的物理顺序，防止因中间上下文迷失（Lost in the Middle）导致意图识别失真。</li>
              <li><strong>Tool Function Call 兜底校验</strong>：对 Agent 解析出的参数加 Pydantic Schema 强校验，不合法立即反射报错促使模型 Re-Plan，防止死循环。</li>
              <li><strong>指标真实答法 (TPM)</strong>：如实回答单机并发与 LLM 供应商速率限制，不编造夸大假指标，突出高稳定与低延迟。</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== 模块 2: 63 道真题卡片流 ==================== -->
    <section v-else-if="currentTab === 'questions'" class="qdeck-section">
      <div class="qdeck-toolbar">
        <div class="qdeck-filters">
          <button
            class="filter-btn"
            :class="{ active: filterCategory === 'all' }"
            @click="filterCategory = 'all'"
          >
            全部真题 ({{ questions.length }})
          </button>
          <button
            class="filter-btn"
            :class="{ active: filterCategory === 'arch' }"
            @click="filterCategory = 'arch'"
          >
            01. 项目背景与选型 ({{ archCount }})
          </button>
          <button
            class="filter-btn"
            :class="{ active: filterCategory === 'agent' }"
            @click="filterCategory = 'agent'"
          >
            02. Agent 与 RAG 架构 ({{ agentCount }})
          </button>
          <button
            class="filter-btn"
            :class="{ active: filterCategory === 'hard' }"
            @click="filterCategory = 'hard'"
          >
            03. 核心难点与防爆 ({{ hardCount }})
          </button>
          <button
            class="filter-btn"
            :class="{ active: filterCategory === 'pressure' }"
            @click="filterCategory = 'pressure'"
          >
            04. 压力面与指标 ({{ pressureCount }})
          </button>
        </div>

        <input
          v-model="searchQuery"
          type="search"
          class="qdeck-search"
          placeholder="搜索真题关键词（如：SSE、日志、Eino、Prompt…）"
        />
      </div>

      <div v-if="filteredQuestions.length === 0" class="empty">未找到匹配的题目</div>

      <div v-else class="qdeck-list">
        <div
          v-for="q in filteredQuestions"
          :key="q.id"
          class="qdeck-card"
        >
          <div class="qdeck-header" @click="toggleCard(q.id)">
            <div class="qdeck-title-row">
              <span class="qdeck-num">{{ formatOrdinal(q.ordinal) }}</span>
              <span class="qdeck-stem">{{ q.stem }}</span>
            </div>
            <div class="qdeck-meta">
              <span class="badge badge-source">{{ q.category || 'OnCall项目' }}</span>
              <span class="qdeck-toggle" :class="{ open: expandedIds.has(q.id) }">
                <AppIcon name="chevron-down" :size="16" />
              </span>
            </div>
          </div>

          <div v-if="expandedIds.has(q.id)" class="qdeck-body">
            <div class="qdeck-analysis-box" v-if="q.analysis">
              <div class="qdeck-analysis-title">
                <AppIcon name="book" :size="14" /> 💡 标准答案与面试作答要点：
              </div>
              <div class="markdown-body" v-html="renderMd(q.analysis)"></div>
            </div>

            <div class="qdeck-actions">
              <button class="btn btn-xs btn-primary" @click="openAiTutor(q)">
                <AppIcon name="robot" :size="13" /> 追问 AI 面试官
              </button>
              <RouterLink
                class="btn btn-xs btn-ghost"
                :to="`/quiz?bank=${encodeURIComponent('OnCall 智能值班项目')}`"
              >
                <AppIcon name="pencil" :size="13" /> 在八股刷题中答题
              </RouterLink>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== 模块 3: AI 模拟面试作战室 ==================== -->
    <section v-else-if="currentTab === 'mock'" class="mock-grid">
      <div class="mock-card">
        <div>
          <h3><AppIcon name="robot" :size="18" /> 字节一面：0 到 1 架构与技术选型深挖</h3>
          <p>“请你从 0 到 1 介绍你的 OnCall 智能值班助手项目，为什么选 Eino / Spring-AI 而不是 LangChain？你们的意图识别和工具调用是怎么编排的？”</p>
        </div>
        <button class="btn btn-primary" @click="startMock('byte_arch')">
          开始对练 <AppIcon name="arrow-right" :size="14" />
        </button>
      </div>

      <div class="mock-card">
        <div>
          <h3><AppIcon name="shield" :size="18" /> 美团高频：日志防爆上下文与长对话管理</h3>
          <p>“真实业务场景下日志量非常大，动辄几十兆，你是怎么保证调用 LLM 时上下文不被撑爆的？Prompt 结构中 System/History/Current 顺序如何安排？”</p>
        </div>
        <button class="btn btn-primary" @click="startMock('meituan_log')">
          开始对练 <AppIcon name="arrow-right" :size="14" />
        </button>
      </div>

      <div class="mock-card">
        <div>
          <h3><AppIcon name="sparkles" :size="18" /> 阿里一面：Agentic RAG 与幻觉抑制</h3>
          <p>“如果排障 Sop 知识库召回的答案不准确，或者大模型产生了幻觉给出了错误的运维命令，你的系统有哪些拦截与自愈机制？”</p>
        </div>
        <button class="btn btn-primary" @click="startMock('ali_rag')">
          开始对练 <AppIcon name="arrow-right" :size="14" />
        </button>
      </div>

      <div class="mock-card">
        <div>
          <h3><AppIcon name="fire" :size="18" /> 压力面：项目指标 TPM 与技术深度挑刺</h3>
          <p>“你们这个项目的并发 TPM 是多少？看起来方案都是业界现成的，有没有真正比较深入的技术突破点？为什么没做多租户与 Redis 缓存？”</p>
        </div>
        <button class="btn btn-primary" @click="startMock('stress_test')">
          开始对练 <AppIcon name="arrow-right" :size="14" />
        </button>
      </div>
    </section>

    <!-- AI 导师抽屉 -->
    <AiTutorDrawer
      :visible="aiDrawerVisible"
      :title="drawerTitle"
      :context-key="drawerContextKey"
      :context-text="drawerContextText"
      :preset-prompts="drawerPresets"
      @close="aiDrawerVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import AiTutorDrawer, { type PromptPreset } from '../components/AiTutorDrawer.vue'
import AppIcon from '../components/AppIcon.vue'
import { renderMarkdown } from '../markdown'
import type { QuizQuestionItem } from '../types'

const currentTab = ref<'notes' | 'questions' | 'mock'>('notes')
const questions = ref<QuizQuestionItem[]>([])
const expandedIds = ref<Set<number>>(new Set())
const filterCategory = ref<'all' | 'arch' | 'agent' | 'hard' | 'pressure'>('all')
const searchQuery = ref('')

// AI Drawer 状态
const aiDrawerVisible = ref(false)
const drawerTitle = ref('AI 面试官 · OnCall 项目深度对练')
const drawerContextKey = ref('oncall:general')
const drawerContextText = ref('')
const drawerPresets = ref<PromptPreset[]>([])

function renderMd(content: string) {
  return renderMarkdown(content)
}

function formatOrdinal(ord?: number) {
  if (ord === undefined || ord === null) return '#'
  return String(ord).padStart(2, '0')
}

function toggleCard(id: number) {
  if (expandedIds.value.has(id)) {
    expandedIds.value.delete(id)
  } else {
    expandedIds.value.add(id)
  }
}

async function loadQuestions() {
  try {
    const res = await api.get<{ total: number; items: QuizQuestionItem[] }>(
      `/api/quiz/questions?bank=${encodeURIComponent('OnCall 智能值班项目')}&limit=100`,
    )
    questions.value = res.items
    // 默认展开前 2 个
    if (res.items.length > 0) {
      expandedIds.value.add(res.items[0].id)
      if (res.items.length > 1) expandedIds.value.add(res.items[1].id)
    }
  } catch {
    // ignore
  }
}

const archCount = computed(() =>
  questions.value.filter((q) => (q.ordinal || 0) <= 15).length,
)
const agentCount = computed(() =>
  questions.value.filter((q) => (q.ordinal || 0) > 15 && (q.ordinal || 0) <= 35).length,
)
const hardCount = computed(() =>
  questions.value.filter((q) => (q.ordinal || 0) > 35 && (q.ordinal || 0) <= 50).length,
)
const pressureCount = computed(() =>
  questions.value.filter((q) => (q.ordinal || 0) > 50).length,
)

const filteredQuestions = computed(() => {
  let list = questions.value
  if (filterCategory.value === 'arch') {
    list = list.filter((q) => (q.ordinal || 0) <= 15)
  } else if (filterCategory.value === 'agent') {
    list = list.filter((q) => (q.ordinal || 0) > 15 && (q.ordinal || 0) <= 35)
  } else if (filterCategory.value === 'hard') {
    list = list.filter((q) => (q.ordinal || 0) > 35 && (q.ordinal || 0) <= 50)
  } else if (filterCategory.value === 'pressure') {
    list = list.filter((q) => (q.ordinal || 0) > 50)
  }

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(
      (item) =>
        item.stem.toLowerCase().includes(q) ||
        (item.analysis && item.analysis.toLowerCase().includes(q)),
    )
  }
  return list
})

function openAiTutor(q: QuizQuestionItem) {
  drawerTitle.value = `AI 导师 · 第 ${q.ordinal || '#'} 题深度答疑`
  drawerContextKey.value = `oncall:q:${q.id}`
  drawerContextText.value = `【题目】：${q.stem}

【参考答题草稿与考点】：
${q.analysis || '无'}`
  drawerPresets.value = [
    {
      label: '按面试官深入追问这题',
      prompt: '请扮演字节/阿里资深面试官，针对这道题的回答草稿提出 2-3 个连环深挖追问，并指出可以提升的亮点。',
    },
    {
      label: '帮我提炼 60 秒口头作答版本',
      prompt: '请把这份草稿提炼成 60 秒的口述版本：先说结论与痛点，再说方案核心机制，最后留一个技术细节。',
    },
    {
      label: '草稿里有哪些容易被抓住的漏洞',
      prompt: '请指出这份草稿里可能不够严谨、或容易被面试官顺藤摸瓜抓住盘问的表述，并给出更稳妥的回答建议。',
    },
  ]
  aiDrawerVisible.value = true
}

function startMock(scene: string) {
  if (scene === 'byte_arch') {
    drawerTitle.value = 'AI 面试官 · 字节一面架构深挖'
    drawerContextKey.value = 'oncall:mock:byte_arch'
    drawerContextText.value = '场景：字节跳动一面，面试官针对候选人的 OnCall 智能值班项目进行从 0 到 1 的架构与技术选型深挖。'
    drawerPresets.value = [
      {
        label: '开始 0 到 1 架构面试',
        prompt: '你好，我是候选人。我在工作之余从 0 到 1 落地了 OnCall 智能值班助手项目。请针对我的项目背景与 Eino/Spring-AI 选型开始提问。',
      },
      {
        label: '针对 Multi-Agent 编排提问',
        prompt: '请针对我系统中排障 Agent 与 RAG 检索 Agent 的编排与意图识别机制进行深入追问。',
      },
    ]
  } else if (scene === 'meituan_log') {
    drawerTitle.value = 'AI 面试官 · 美团长日志防爆与高并发'
    drawerContextKey.value = 'oncall:mock:meituan_log'
    drawerContextText.value = '场景：美团技术二面，面试官聚焦长日志上下文防爆、滑动窗口、Prompt 物理顺序与注意力衰减等高并发工程难点。'
    drawerPresets.value = [
      {
        label: '考察长日志防爆机制',
        prompt: '请作为面试官提问：你们线上日志几十兆，调用大模型时是如何做到上下文不爆且准确抓住报错关键行的？',
      },
      {
        label: '考察 Prompt 顺序对注意力的影响',
        prompt: '请作为面试官提问：Prompt 中的 System Prompt、历史对话摘要和当前轮次的物理顺序如何设计？为什么会有 Lost in the Middle 现象？',
      },
    ]
  } else if (scene === 'ali_rag') {
    drawerTitle.value = 'AI 面试官 · 阿里 Agentic RAG 与幻觉治理'
    drawerContextKey.value = 'oncall:mock:ali_rag'
    drawerContextText.value = '场景：阿里巴巴一面，面试官考察向量检索召回不准时的兜底、Agentic RAG 重思机制与幻觉抑制。'
    drawerPresets.value = [
      {
        label: '考察 RAG 召回不准时的应对',
        prompt: '请作为面试官提问：如果知识库中检索出的 Sop 并不完全匹配当前报错，Agent 会怎么处理？如何防止大模型胡乱执行危险运维指令？',
      },
    ]
  } else {
    drawerTitle.value = 'AI 面试官 · 极限压力面与指标挑刺'
    drawerContextKey.value = 'oncall:mock:stress_test'
    drawerContextText.value = '场景：大厂技术总监压力面，重点挑刺项目并发 TPM 指标、为什么没做多租户与 Redis、方案是否过于常规。'
    drawerPresets.value = [
      {
        label: '开始压力面挑刺',
        prompt: '请作为苛刻的技术面试官开始挑刺：“你这个项目看起来就是调用一下大模型 API，技术深度在哪里？TPM 是多少？为什么没用 Redis？”',
      },
    ]
  }
  aiDrawerVisible.value = true
}

onMounted(() => {
  loadQuestions()
})
</script>

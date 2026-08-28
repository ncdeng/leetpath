<template>
  <div class="container quiz-container">
    <!-- 顶部标题与统计概览 -->
    <div class="page-head">
      <div>
        <div class="kicker">Interactive Quiz & Theory Bank</div>
        <h1 class="display">八股刷题与自测</h1>
      </div>
      <div class="head-stats" v-if="stats">
        <div class="stat">
          <span class="num accent">{{ stats.answered_count }}</span>
          <span class="lbl">已刷题数</span>
        </div>
        <div class="stat">
          <span class="num" :style="{ color: stats.accuracy_rate >= 80 ? 'var(--green)' : 'var(--text)' }">
            {{ stats.accuracy_rate }}%
          </span>
          <span class="lbl">正确率</span>
        </div>
        <div class="stat">
          <span class="num" style="color:var(--red)">{{ stats.wrong_count }}</span>
          <span class="lbl">待消灭错题</span>
        </div>
        <div class="stat">
          <span class="num" style="color:var(--green)">{{ stats.slashed_count }}</span>
          <span class="lbl">已斩题</span>
        </div>
        <div class="stat">
          <span class="num">{{ stats.total_questions }}</span>
          <span class="lbl">题库总量</span>
        </div>
      </div>
    </div>

    <!-- 顶部主进度条 -->
    <div v-if="stats && stats.total_questions > 0" class="progress-track">
      <div
        class="seg"
        :style="{
          width: `${(stats.answered_count / stats.total_questions) * 100}%`,
          background: 'var(--accent)',
        }"
      ></div>
    </div>

    <!-- 模式导航选项卡（iOS 分段器，五项可横向滚动） -->
    <div class="quiz-tabs-scroll">
      <div class="segmented quiz-nav-tabs">
        <button :class="{ active: currentTab === 'practice' }" @click="switchTab('practice')">
          <AppIcon name="pencil" :size="14" /> 刷题练习
        </button>
        <button :class="{ active: currentTab === 'wrongbook' }" @click="switchTab('wrongbook')">
          <AppIcon name="flame" :size="14" /> 错题斩题 ({{ stats?.wrong_count || 0 }})
        </button>
        <button :class="{ active: currentTab === 'banks' }" @click="switchTab('banks')">
          <AppIcon name="cards" :size="14" /> {{ bankCount }} 个专题库
        </button>
        <button :class="{ active: currentTab === 'favorites' }" @click="switchTab('favorites')">
          <AppIcon name="sparkle" :size="14" /> 收藏夹 ({{ stats?.favorite_count || 0 }})
        </button>
        <button :class="{ active: currentTab === 'exam' }" @click="switchTab('exam')">
          <AppIcon name="clock" :size="14" /> 模拟小测 (20题)
        </button>
      </div>
    </div>

    <!-- ==================== 视图 1: 刷题练习 / 错题本 / 收藏夹 / 模拟小测 ==================== -->
    <div v-if="currentTab === 'practice' || currentTab === 'wrongbook' || currentTab === 'favorites' || currentTab === 'exam'">
      <!-- 刷题工具栏 -->
      <div class="quiz-toolbar card">
        <div class="quiz-filter-group">
          <!-- 专题选择器（练习模式下有效） -->
          <div class="quiz-filter-item" v-if="currentTab === 'practice'">
            <label>专题分类：</label>
            <select class="select" v-model="selectedBank" @change="fetchQuestions">
              <option value="">全部 {{ bankCount }} 个专题 ({{ stats?.total_questions }}题)</option>
              <optgroup v-for="(bList, cat) in groupedBanks" :key="cat" :label="cat">
                <option v-for="b in bList" :key="b.bank" :value="b.bank">
                  {{ b.bank === HARNESS_BANK ? '新 · ' : '' }}{{ b.bank }} ({{ b.total }}题 · {{ b.answered }}/{{ b.total }})
                </option>
              </optgroup>
            </select>
          </div>
          <div class="quiz-featured" v-if="currentTab === 'practice'">
            <button
              type="button"
              class="quiz-feat-chip"
              :class="{ active: selectedBank === HARNESS_BANK }"
              @click="startBankPractice(HARNESS_BANK)"
            >
              新 · Agent Harness
            </button>
            <button
              type="button"
              class="quiz-feat-chip"
              :class="{ active: selectedBank === '' }"
              @click="startBankPractice('')"
            >
              全部专题
            </button>
          </div>

          <!-- 错题本提示 -->
          <div class="wrongbook-hint" v-if="currentTab === 'wrongbook'">
            <AppIcon name="flame" :size="15" class="hint-icon hint-icon-red" />
            <span><strong>错题斩题模式</strong>：做对或点击「斩题」可从错题本消除，直到清空所有错题！</span>
          </div>

          <!-- 收藏夹提示 -->
          <div class="wrongbook-hint" v-if="currentTab === 'favorites'">
            <AppIcon name="sparkle" :size="15" class="hint-icon hint-icon-amber" />
            <span><strong>我的收藏夹</strong>：复习标记过的重点和难题。</span>
          </div>

          <!-- 模拟考试提示 -->
          <div class="wrongbook-hint" v-if="currentTab === 'exam'">
            <AppIcon name="clock" :size="15" class="hint-icon" />
            <span><strong>模拟测验</strong>：随机抽取 20 道客观题进行自测（不含问答题）。</span>
            <button class="btn btn-xs btn-primary" @click="startNewExam">重新抽题</button>
          </div>
        </div>

        <div class="quiz-tool-actions">
          <label class="quiz-switch" v-if="currentTab === 'practice'">
            <span class="switch">
              <input type="checkbox" v-model="onlyUnanswered" @change="fetchQuestions" />
              <span class="track"></span>
            </span>
            <span class="quiz-switch-text">仅刷未作答题</span>
          </label>
          <label class="quiz-switch">
            <span class="switch">
              <input type="checkbox" v-model="randomOrder" @change="fetchQuestions" />
              <span class="track"></span>
            </span>
            <span class="quiz-switch-text">随机乱序</span>
          </label>
        </div>
      </div>

      <!-- 加载中骨架 -->
      <div v-if="loading" class="card quiz-card">
        <Skeleton :count="1" height="28px" width="40%" radius="6px" gap="16px" />
        <Skeleton :count="2" height="20px" width="90%" radius="6px" gap="12px" />
        <div style="margin-top:24px">
          <Skeleton :count="4" height="48px" width="100%" radius="8px" gap="12px" />
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="questions.length === 0" class="card empty-card">
        <div class="empty-icon">
          <AppIcon :name="currentTab === 'wrongbook' ? 'trophy' : 'pencil'" :size="36" />
        </div>
        <h3>{{ emptyTitle }}</h3>
        <p class="muted">{{ emptyDesc }}</p>
        <button
          v-if="currentTab === 'wrongbook' || currentTab === 'favorites'"
          class="btn btn-primary"
          @click="switchTab('practice')"
        >
          前往刷题练习 <AppIcon name="arrow-right" :size="15" />
        </button>
      </div>

      <!-- 核心答题卡片主体 -->
      <div v-else-if="currentQ" class="quiz-stage">
        <div class="card quiz-card">
          <!-- 题目顶部元信息 -->
          <div class="quiz-card-head">
            <div class="quiz-badges">
              <span class="badge badge-source">{{ currentQ.bank }}</span>
              <span class="badge" :class="typeBadgeClass(currentQ.type)">{{ typeText(currentQ.type) }}</span>
              <span class="mono quiz-num-tag">#{{ currentQ.ordinal }}</span>
              <span v-if="isOpenQuestion && currentQ.is_answered" class="badge badge-source">已对照草稿</span>
              <span v-else-if="currentQ.is_answered" class="badge" :class="currentQ.is_correct ? 'badge-easy' : 'badge-hard'">
                <AppIcon :name="currentQ.is_correct ? 'check' : 'x'" :size="11" />
                {{ currentQ.is_correct ? '上次做对' : '上次做错' }}
              </span>
              <span v-if="currentQ.wrong_count > 1" class="badge badge-hard">
                累积做错 {{ currentQ.wrong_count }} 次
              </span>
            </div>

            <div class="quiz-head-actions">
              <!-- 问 AI 按钮 -->
              <button
                class="btn btn-xs btn-outline quiz-ai-btn"
                title="针对当前题目向 AI 导师提问与考点深挖"
                @click="openAiDrawer"
              >
                <AppIcon name="robot" :size="13" /> 问 AI
              </button>
              <!-- 斩题按钮 -->
              <button
                class="btn btn-xs"
                :class="currentQ.is_slashed ? 'btn-ghost' : 'btn-outline'"
                :title="currentQ.is_slashed ? '已从错题本消除' : '斩掉此题（移出错题本）'"
                @click="toggleSlash(currentQ)"
              >
                <AppIcon name="flame" :size="13" /> {{ currentQ.is_slashed ? '已斩题' : '斩题' }}
              </button>
              <!-- 收藏按钮 -->
              <button
                class="btn btn-xs"
                :class="currentQ.is_favorite ? 'btn-favorite active' : 'btn-ghost'"
                :title="currentQ.is_favorite ? '取消收藏' : '收藏此题'"
                @click="toggleFavorite(currentQ)"
              >
                <AppIcon name="sparkle" :size="13" /> {{ currentQ.is_favorite ? '已收藏' : '收藏' }}
              </button>
            </div>
          </div>

          <!-- 题干 -->
          <div class="quiz-stem">
            <span class="quiz-q-idx mono">{{ currentIndex + 1 }}.</span>
            <div class="quiz-stem-text markdown-body" v-html="renderMd(currentQ.stem)"></div>
          </div>

          <!-- 问答题：题干 → 查看答案 → 草稿 -->
          <div v-if="isOpenQuestion" class="quiz-open-panel">
            <button
              v-if="!openRevealed"
              class="btn btn-primary"
              :disabled="submitting"
              @click="revealOpenAnswer"
            >
              查看答案
            </button>
            <p v-if="!openRevealed" class="muted open-hint">先自己口述一遍，点一下再对照草稿（非正式标准答案）。</p>
            <div v-else class="quiz-analysis-box">
              <div class="analysis-header">
                <span class="analysis-title"><AppIcon name="book" :size="15" /> 参考答案 <span class="badge badge-source">草稿</span></span>
                <button class="btn btn-xs btn-primary" @click="openAiDrawer">
                  <AppIcon name="robot" :size="13" /> 和 AI 助教聊聊这题
                </button>
              </div>
              <div class="statement analysis-content markdown-body" v-html="renderMd(currentQ.analysis || '')"></div>
            </div>
          </div>

          <!-- 选项列表 -->
          <div class="quiz-options-grid" v-else>
            <!-- 单选 / 多选 / 判断 选项按钮 -->
            <button
              v-for="(text, key) in currentQ.options"
              :key="key"
              class="quiz-option-btn"
              :class="getOptionClass(key)"
              :disabled="submitting || Boolean(currentResult || currentQ.is_answered)"
              @click="onOptionClick(key)"
            >
              <div class="opt-prefix mono">{{ key }}</div>
              <div class="opt-content">{{ text }}</div>
              <div class="opt-indicator">
                <span v-if="isOptionCorrect(key)" class="indicator-tag correct"><AppIcon name="check" :size="16" /></span>
                <span v-else-if="isOptionUserWrong(key)" class="indicator-tag wrong"><AppIcon name="x" :size="16" /></span>
                <span v-else-if="currentQ.type === 'multiple' && multiSelected.includes(key)" class="indicator-tag selected"><AppIcon name="check" :size="16" /></span>
              </div>
            </button>
          </div>

          <!-- 多选题提交按钮 -->
          <div v-if="currentQ.type === 'multiple' && !currentResult && !currentQ.is_answered" class="multi-submit-bar">
            <button
              class="btn btn-primary"
              :disabled="multiSelected.length === 0 || submitting"
              @click="submitMultiAnswer"
            >
              提交答案 ({{ multiSelected.sort().join('') || '请勾选' }})
            </button>
            <span class="multi-hint">多选题可勾选多个选项后提交</span>
          </div>

          <!-- 答题结果横幅 -->
          <transition name="fade">
            <div v-if="!isOpenQuestion && (currentResult || (currentQ.is_answered && currentQ.answer))" class="quiz-result-banner" :class="isCurrentCorrect ? 'res-correct' : 'res-wrong'">
              <div class="res-icon"><AppIcon :name="isCurrentCorrect ? 'check' : 'x'" :size="20" /></div>
              <div class="res-msg">
                <div class="res-title">
                  {{ isCurrentCorrect ? '回答正确！' : '回答错误！' }}
                  <span class="res-ans">标准答案：<strong>{{ currentResult?.correct_answer || currentQ.answer }}</strong></span>
                </div>
                <div class="res-sub">
                  你的选择：{{ currentResult?.user_answer || currentQ.user_answer || '未记录' }}
                  <span v-if="currentResult?.wrong_count" class="res-wrong-count">
                    (累积做错 {{ currentResult.wrong_count }} 次)
                  </span>
                </div>
              </div>
              <div class="res-actions">
                <button class="btn btn-xs btn-primary" @click="openAiDrawer"><AppIcon name="robot" :size="13" /> 追问 AI 导师</button>
                <button class="btn btn-xs btn-ghost" @click="retryCurrentQuestion"><AppIcon name="refresh" :size="12" /> 重新作答</button>
              </div>
            </div>
          </transition>

          <!-- 详细解析展示区 -->
          <transition name="fade">
            <div v-if="!isOpenQuestion && (currentResult?.analysis || (currentQ.is_answered && currentQ.analysis))" class="quiz-analysis-box">
              <div class="analysis-header">
                <span class="analysis-title"><AppIcon name="book" :size="15" /> 考点与详细解析</span>
                <button class="btn btn-xs btn-ghost" @click="openAiDrawer">
                  <AppIcon name="robot" :size="13" /> 追问 AI / 举工业落地例子 <AppIcon name="arrow-right" :size="12" />
                </button>
              </div>
              <div class="statement analysis-content markdown-body" v-html="renderMd(currentResult?.analysis || currentQ.analysis || '')"></div>
            </div>
          </transition>

          <!-- 底部答题卡切换栏与快捷键提示 -->
          <div class="quiz-card-footer">
            <div class="quiz-nav-btns">
              <button class="btn btn-sm" :disabled="currentIndex === 0" @click="navigateQuestion(currentIndex - 1)">
                <AppIcon name="chevron-left" :size="14" /> 上一题
              </button>
              <button
                class="btn btn-sm btn-primary"
                :disabled="currentIndex >= questions.length - 1"
                @click="navigateQuestion(currentIndex + 1)"
              >
                下一题 <AppIcon name="chevron-right" :size="14" />
              </button>
            </div>

            <div class="quiz-progress-text mono">
              {{ currentIndex + 1 }} / {{ questions.length }}
            </div>

            <!-- 快捷键提示条（触屏端隐藏） -->
            <div class="quiz-keyboard-tips">
              <span class="kbd-tip" v-if="!isOpenQuestion"><kbd>1-4</kbd> / <kbd>A-D</kbd> 选择</span>
              <span class="kbd-tip" v-else><kbd>Enter</kbd> 查看答案</span>
              <span class="kbd-tip"><kbd>Enter</kbd> 提交/下一题</span>
              <span class="kbd-tip"><kbd>←</kbd> <kbd>→</kbd> 切题</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== 视图 2: 专题库大纲 (Banks) ==================== -->
    <div v-else-if="currentTab === 'banks'" class="banks-view">
      <div class="banks-header card">
        <div class="banks-header-info">
          <h2>{{ bankCount }} 个大模型与算法核心专题库</h2>
          <p class="muted">涵盖 OnCall 项目问答、面经项目知识点、八股，以及 Agent Harness、MCP/Skills、Transformer、RAG，点击专题直接刷。</p>
        </div>
      </div>

      <div v-for="(bList, cat) in groupedBanks" :key="cat" class="category-block">
        <h3 class="category-title">
          <span class="cat-pill">{{ cat }}</span>
          <span class="cat-count">共 {{ bList.reduce((acc, b) => acc + b.total, 0) }} 题</span>
        </h3>

        <div class="curated-grid banks-grid">
          <div
            v-for="b in bList"
            :key="b.bank"
            class="card curated-card bank-card"
            @click="startBankPractice(b.bank)"
          >
            <div class="curated-top">
              <span class="curated-badge">{{ cat }}</span>
              <span class="curated-star mono">{{ b.answered }}/{{ b.total }} 题</span>
            </div>
            <h3 class="curated-title">{{ b.bank }}</h3>

            <div class="bank-progress-bar">
              <div
                class="bank-progress-fill"
                :style="{
                  width: `${(b.answered / b.total) * 100}%`,
                  background: b.wrong > 0 ? 'var(--accent)' : 'var(--green)'
                }"
              ></div>
            </div>

            <div class="curated-footer">
              <div class="bank-stats-text mono">
                <span class="bank-stat-ok"><AppIcon name="check" :size="13" /> {{ b.correct }}</span>
                <span v-if="b.wrong > 0" class="bank-stat-bad"><AppIcon name="x" :size="13" /> {{ b.wrong }}</span>
              </div>
              <span class="curated-link">开始刷此专题 <AppIcon name="arrow-right" :size="13" /></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI 导师抽屉 -->
    <AiTutorDrawer
      :visible="aiDrawerVisible"
      :title="`AI 导师 · 第 ${currentQ?.ordinal || currentIndex + 1} 题深度答疑`"
      :context-key="`quiz:${currentQ?.id}`"
      :context-text="aiContext"
      :preset-prompts="quizPresetPrompts"
      @close="aiDrawerVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import AiTutorDrawer, { type PromptPreset } from '../components/AiTutorDrawer.vue'
import AppIcon from '../components/AppIcon.vue'
import Skeleton from '../components/Skeleton.vue'
import { renderMarkdown } from '../markdown'
import { useToast } from '../stores/toast'
import type {
  QuizAnswerResult,
  QuizBank,
  QuizQuestionItem,
  QuizQuestionType,
  QuizStats,
} from '../types'

const toast = useToast()

const currentTab = ref<'practice' | 'wrongbook' | 'banks' | 'favorites' | 'exam'>('practice')
const loading = ref(true)
const submitting = ref(false)
const stats = ref<QuizStats | null>(null)
const banks = ref<QuizBank[]>([])
const HARNESS_BANK = 'Agent Harness 与编码智能体'
const selectedBank = ref<string>(HARNESS_BANK)
const onlyUnanswered = ref(false)
const randomOrder = ref(false)
const aiDrawerVisible = ref(false)

const questions = ref<QuizQuestionItem[]>([])
const currentIndex = ref(0)
const multiSelected = ref<string[]>([])
const currentResult = ref<QuizAnswerResult | null>(null)

const currentQ = computed(() => questions.value[currentIndex.value])
const isOpenQuestion = computed(() => currentQ.value?.type === 'open')
const openRevealed = computed(() => {
  const q = currentQ.value
  if (!q || q.type !== 'open') return false
  return Boolean(q.analysis) || q.is_answered
})

async function openAiDrawer() {
  if (isOpenQuestion.value && currentQ.value && !openRevealed.value) {
    await revealOpenAnswer()
  }
  aiDrawerVisible.value = true
}

const aiContext = computed(() => {
  const q = currentQ.value
  if (!q) return ''
  if (q.type === 'open') {
    const draft = q.analysis || '（尚未揭晓草稿）'
    return `【所属专题】：${q.bank} (${q.category || ''})
【题型】：问答题（答案为草稿，非正式标准答案）
【题干】：
${q.stem}

【草稿答案】：
${draft}

请按面试深挖来讨论，指出草稿里可以补强或纠正的点。如需写代码，只用 Python3 或 C++。`
  }
  const optStr = Object.entries(q.options || {})
    .map(([k, v]) => `${k}. ${v}`)
    .join('\n')
  return `【所属专题】：${q.bank} (${q.category || ''})
【题型】：${typeText(q.type)} (第 ${q.ordinal} 题)
【题干】：
${q.stem}

【选项】：
${optStr}

【标准答案】：${currentResult.value?.correct_answer || q.answer || '未知'}
【我的选择】：${currentResult.value?.user_answer || q.user_answer || '未作答'}
【官方解析】：
${currentResult.value?.analysis || q.analysis || '暂无官方解析'}`
})

const quizPresetPrompts = computed<PromptPreset[]>(() => {
  const q = currentQ.value
  if (q?.type === 'open') {
    return [
      {
        label: '按面试官追问这题',
        prompt: '请扮演面试官，基于题干和这份草稿答案追问 2-3 个深挖问题，并给出简要作答要点。草稿不是标准答案，请标出可以补强的地方。',
      },
      {
        label: '帮我把草稿讲圆',
        prompt: '请把这份草稿整理成 60 秒口头版本：先讲痛点与目标，再讲方案与结果，最后补一个可追问的技术细节。',
      },
      {
        label: '草稿里有哪些坑',
        prompt: '请指出这份草稿里不严谨、过时或容易被面试官抓住的表述，并给出更稳妥的说法。不要编造项目经历。',
      },
    ]
  }
  const userAns = currentResult.value?.user_answer || q?.user_answer
  const isWrong = userAns && !isCurrentCorrect.value
  const list: PromptPreset[] = []
  if (isWrong) {
    list.push({
      label: `❌ 深入分析我为什么选错 [${userAns}]`,
      prompt: `我在这道题中选择了 [${userAns}]，而标准答案是 [${currentResult.value?.correct_answer || q?.answer}]。请详细帮我剖析我选择的这个选项错在哪里？它的迷惑性是什么？`,
    })
  }
  list.push(
    {
      label: '💡 举一个实际工业落地例子',
      prompt: '请结合实际大模型系统/工业落地场景（如 Agent 规划、RAG 检索、分布式训练或 Transformer 架构），举一个具体的场景例子来说明本题考察的核心原理。',
    },
    {
      label: '🔍 面试官可能怎么顺着往下深挖？',
      prompt: '如果我在校招/社招面试中回答了这道题，面试官通常会顺着这个考点提出哪些进阶深挖问题？请列出 2-3 个深挖方向及简要答题要点。',
    },
    {
      label: '⚡ 极简口诀/记忆卡片',
      prompt: '请用一句话极简口诀或思维导图结构，帮我提炼本题的核心考点，方便快速记忆且以后绝不再错。',
    },
  )
  return list
})

const bankCount = computed(() => banks.value.length)

const groupedBanks = computed(() => {
  const map: Record<string, QuizBank[]> = {}
  for (const b of banks.value) {
    if (!map[b.category]) map[b.category] = []
    map[b.category].push(b)
  }
  for (const list of Object.values(map)) {
    list.sort((a, b) => {
      if (a.bank === HARNESS_BANK) return -1
      if (b.bank === HARNESS_BANK) return 1
      return a.bank.localeCompare(b.bank, 'zh')
    })
  }
  const ordered: Record<string, QuizBank[]> = {}
  const preferred = ['OnCall项目', '面经项目知识点', '八股', 'AI Agent 与智能体']
  for (const cat of preferred) {
    if (map[cat]) ordered[cat] = map[cat]
  }
  for (const [cat, list] of Object.entries(map)) {
    if (!ordered[cat]) ordered[cat] = list
  }
  return ordered
})

const isCurrentCorrect = computed(() => {
  if (currentResult.value) return currentResult.value.is_correct
  if (currentQ.value?.is_answered) return currentQ.value.is_correct === true
  return false
})

const emptyTitle = computed(() => {
  if (currentTab.value === 'wrongbook') return '太棒了！错题本空空如也'
  if (currentTab.value === 'favorites') return '暂无收藏题目'
  return '未找到符合条件的题目'
})

const emptyDesc = computed(() => {
  if (currentTab.value === 'wrongbook') return '所有做错过的题目都已被攻克斩除，继续保持！'
  if (currentTab.value === 'favorites') return '做题时点击题目右上角的「☆ 收藏」按钮即可加入收藏夹。'
  return '请尝试调整筛选条件或切换其他专题。'
})

function renderMd(md: string) {
  if (!md) return ''
  return renderMarkdown(md)
}

function typeText(t: QuizQuestionType) {
  if (t === 'single') return '单选题'
  if (t === 'multiple') return '多选题'
  if (t === 'judge') return '判断题'
  if (t === 'open') return '问答题'
  return '客观题'
}

function typeBadgeClass(t: QuizQuestionType) {
  if (t === 'open') return 'badge-source'
  if (t === 'single') return 'badge-easy'
  if (t === 'multiple') return 'badge-medium'
  return 'badge-hard'
}

function switchTab(tab: 'practice' | 'wrongbook' | 'banks' | 'favorites' | 'exam') {
  currentTab.value = tab
  currentIndex.value = 0
  currentResult.value = null
  multiSelected.value = []
  if (tab !== 'banks') {
    fetchQuestions()
  }
}

function startBankPractice(bankName: string) {
  selectedBank.value = bankName
  currentTab.value = 'practice'
  fetchQuestions()
}

function startNewExam() {
  currentTab.value = 'exam'
  fetchQuestions()
}

async function loadStatsAndBanks() {
  try {
    const [s, b] = await Promise.all([
      api.get<QuizStats>(`/api/quiz/stats?tz_offset=${-new Date().getTimezoneOffset()}`),
      api.get<QuizBank[]>('/api/quiz/banks'),
    ])
    stats.value = s
    banks.value = b
  } catch {
    // ignore
  }
}

async function fetchQuestions() {
  loading.value = true
  currentResult.value = null
  multiSelected.value = []
  try {
    const params = new URLSearchParams()
    if (currentTab.value === 'wrongbook') {
      params.set('status', 'wrong')
    } else if (currentTab.value === 'favorites') {
      params.set('status', 'favorited')
    } else if (currentTab.value === 'exam') {
      params.set('limit', '20')
      params.set('random_order', 'true')
      params.set('exclude_open', 'true')
    } else {
      if (selectedBank.value) params.set('bank', selectedBank.value)
      if (onlyUnanswered.value) params.set('status', 'unanswered')
      if (randomOrder.value) params.set('random_order', 'true')
    }

    const qs = params.toString()
    const res = await api.get<{ total: number; items: QuizQuestionItem[] }>(
      qs ? `/api/quiz/questions?${qs}` : '/api/quiz/questions',
    )
    questions.value = res.items
    if (
      currentTab.value === 'practice' &&
      selectedBank.value === HARNESS_BANK &&
      res.items.length === 0
    ) {
      selectedBank.value = ''
      const retry = await api.get<{ total: number; items: QuizQuestionItem[] }>(
        '/api/quiz/questions',
      )
      questions.value = retry.items
    }
    currentIndex.value = 0
    await loadStatsAndBanks()
  } catch {
    toast.error('加载题目失败，请重试')
  } finally {
    loading.value = false
  }
}

function navigateQuestion(idx: number) {
  if (idx < 0 || idx >= questions.value.length) return
  currentIndex.value = idx
  currentResult.value = null
  multiSelected.value = []
}

async function revealOpenAnswer() {
  const q = currentQ.value
  if (!q || q.type !== 'open' || submitting.value) return
  if (q.analysis) {
    q.is_answered = true
    return
  }
  submitting.value = true
  try {
    const res = await api.post<{
      id: number
      analysis: string
      answer_status: string
      is_answered: boolean
    }>(`/api/quiz/questions/${q.id}/reveal`)
    q.analysis = res.analysis
    q.is_answered = true
    q.answer_status = res.answer_status || 'draft'
    await loadStatsAndBanks()
  } catch {
    toast.error('揭晓答案失败，请重试')
  } finally {
    submitting.value = false
  }
}

// 选项样式判定
function getOptionClass(key: string) {
  const q = currentQ.value
  if (!q) return {}

  const answered = currentResult.value !== null || q.is_answered
  const correctAns = currentResult.value?.correct_answer || q.answer || ''
  const userAns = currentResult.value?.user_answer || q.user_answer || ''

  if (answered && correctAns) {
    const isCorrectKey = optionMatchesAnswer(q, key, correctAns)
    const isUserKey = optionMatchesAnswer(q, key, userAns)

    if (isCorrectKey) {
      return { 'opt-correct': true }
    }
    if (isUserKey && !isCorrectKey) {
      return { 'opt-wrong': true }
    }
  }

  if (q.type === 'multiple' && multiSelected.value.includes(key)) {
    return { 'opt-selected': true }
  }

  return {}
}

function optionMatchesAnswer(q: QuizQuestionItem, key: string, ans: string): boolean {
  if (!ans) return false
  const text = q.options?.[key] ?? ''
  if (q.type === 'judge') {
    return ans === key || ans === text
  }
  return ans.includes(key)
}

function isOptionCorrect(key: string) {
  const q = currentQ.value
  if (!q) return false
  const answered = currentResult.value !== null || q.is_answered
  const correctAns = currentResult.value?.correct_answer || q.answer || ''
  return answered && optionMatchesAnswer(q, key, correctAns)
}

function isOptionUserWrong(key: string) {
  const q = currentQ.value
  if (!q) return false
  const answered = currentResult.value !== null || q.is_answered
  const correctAns = currentResult.value?.correct_answer || q.answer || ''
  const userAns = currentResult.value?.user_answer || q.user_answer || ''
  return (
    answered &&
    optionMatchesAnswer(q, key, userAns) &&
    !optionMatchesAnswer(q, key, correctAns)
  )
}

// 点击选项
async function onOptionClick(key: string) {
  const q = currentQ.value
  if (!q || submitting.value || q.type === 'open') return

  // 严格防作弊锁定：如果本题已作答过，坚决不允许再次点击修改答案
  if (currentResult.value !== null || q.is_answered) {
    toast.info('本题已完成作答，答案与解析已揭晓，不可重复提交刷分')
    return
  }

  // 多选题点击是勾选/反勾选
  if (q.type === 'multiple') {
    if (multiSelected.value.includes(key)) {
      multiSelected.value = multiSelected.value.filter((k) => k !== key)
    } else {
      multiSelected.value.push(key)
    }
    return
  }

  // 单选 / 判断：直接提交作答
  await submitAnswer(key)
}

async function submitMultiAnswer() {
  if (multiSelected.value.length === 0) return
  const sorted = multiSelected.value.slice().sort().join('')
  await submitAnswer(sorted)
}

async function submitAnswer(ans: string) {
  const q = currentQ.value
  if (!q || submitting.value) return
  submitting.value = true
  try {
    const res = await api.post<QuizAnswerResult>(`/api/quiz/questions/${q.id}/answer`, {
      user_answer: ans,
    })
    currentResult.value = res
    q.is_answered = true
    q.is_correct = res.is_correct
    q.user_answer = res.user_answer
    q.answer = res.correct_answer
    q.analysis = res.analysis
    q.wrong_count = res.wrong_count
    q.attempts_count = res.attempts_count

    if (res.is_correct) {
      toast.success('回答正确！🎉')
    } else {
      toast.error(`回答错误！正确答案为：${res.correct_answer}`)
    }
    await loadStatsAndBanks()
  } catch {
    toast.error('提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

function retryCurrentQuestion() {
  const q = currentQ.value
  if (!q) return
  currentResult.value = null
  q.is_answered = false
  q.user_answer = null
  q.answer = null
  q.analysis = null
  multiSelected.value = []
  toast.info('已重置作答状态，请独立思考后重新作答')
}

// 斩题
async function toggleSlash(q: QuizQuestionItem) {
  try {
    const target = !q.is_slashed
    const res = await api.post<{ id: number; is_slashed: boolean }>(`/api/quiz/questions/${q.id}/slash`, {
      slashed: target,
    })
    q.is_slashed = res.is_slashed
    if (res.is_slashed) {
      toast.success('已斩题！成功移出错题本 🗡️')
      if (currentTab.value === 'wrongbook') {
        // 如果在错题本中斩题，平滑切到下一题
        if (currentIndex.value < questions.value.length - 1) {
          navigateQuestion(currentIndex.value + 1)
        }
      }
    } else {
      toast.info('已恢复至错题本')
    }
    await loadStatsAndBanks()
  } catch {
    toast.error('操作失败')
  }
}

// 收藏
async function toggleFavorite(q: QuizQuestionItem) {
  try {
    const res = await api.post<{ id: number; is_favorite: boolean }>(`/api/quiz/questions/${q.id}/favorite`)
    q.is_favorite = res.is_favorite
    if (res.is_favorite) {
      toast.success('已加入收藏夹 ⭐')
    } else {
      toast.info('已取消收藏')
    }
    await loadStatsAndBanks()
  } catch {
    toast.error('操作失败')
  }
}

// 全局快捷键监听
function onKey(e: KeyboardEvent) {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName)) return
  if (!currentQ.value) return

  const key = e.key.toUpperCase()

  // 1/2/3/4 或 A/B/C/D 选选项
  const keyMap: Record<string, string> = {
    '1': 'A',
    '2': 'B',
    '3': 'C',
    '4': 'D',
    'A': 'A',
    'B': 'B',
    'C': 'C',
    'D': 'D',
  }

  if (keyMap[key] && currentQ.value.type !== 'open' && currentQ.value.options?.[keyMap[key]]) {
    e.preventDefault()
    onOptionClick(keyMap[key])
    return
  }

  // Enter / Space：提交多选或切下一题
  if (e.key === 'Enter') {
    e.preventDefault()
    if (currentQ.value.type === 'open' && !openRevealed.value) {
      revealOpenAnswer()
    } else if (currentQ.value.type === 'multiple' && !currentResult.value && !currentQ.value.is_answered) {
      submitMultiAnswer()
    } else if (currentIndex.value < questions.value.length - 1) {
      navigateQuestion(currentIndex.value + 1)
    }
    return
  }

  // 方向键切题
  if (e.key === 'ArrowLeft' && currentIndex.value > 0) {
    e.preventDefault()
    navigateQuestion(currentIndex.value - 1)
  } else if (e.key === 'ArrowRight' && currentIndex.value < questions.value.length - 1) {
    e.preventDefault()
    navigateQuestion(currentIndex.value + 1)
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  await loadStatsAndBanks()
  await fetchQuestions()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
})
</script>

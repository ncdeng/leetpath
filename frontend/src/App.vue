<template>
  <div>
    <!-- 登录后：信号工具壳（品牌行 + 发丝栏目条 + 内容栏） -->
    <div class="app-shell" v-if="auth.me">
      <header class="masthead">
        <div class="masthead-inner">
          <div class="masthead-top">
            <div class="masthead-brand">
              <RouterLink class="brand" to="/">leet<span class="path">path</span></RouterLink>
              <span class="brand-version" :title="`当前部署版本 v${appVersion}`">v{{ appVersion }}</span>
            </div>
            <span class="masthead-edition">Campus Edition · 2026</span>

            <div class="masthead-controls">
              <!-- AI 设置 -->
              <button
                class="topbar-btn"
                :title="aiStore.isConfigured.value ? `当前 AI: ${aiStore.selectedModel.value}（点击设置）` : '点击配置自定义 AI 密钥与模型'"
                @click="showAiSettings = true"
              >
                <AppIcon name="robot" :size="17" />
              </button>
              <!-- 全局语言偏好切换 -->
              <button
                class="topbar-btn desktop-only"
                :title="langPref === 'python3' ? '当前全局语言: Python 3（点击切换到 C++）' : '当前全局语言: C++（点击切换到 Python 3）'"
                @click="toggleLang"
              >
                <span class="mono">{{ langPref === 'python3' ? 'Py' : 'C++' }}</span>
              </button>
              <!-- 全站字号自由调节 -->
              <button class="topbar-btn desktop-only" :title="fontSizeTooltip" @click="cycleFontSize">
                <span style="font-weight: 700">aA</span>
                <span style="font-size: 10px; opacity: 0.7">{{ fontSizeLabel }}</span>
              </button>
              <!-- 主题选择：六套主题全家桶 -->
              <div class="theme-picker">
                <button
                  class="topbar-btn"
                  :title="`当前主题：${currentThemeName}（点击更换）`"
                  @click.stop="showThemeMenu = !showThemeMenu"
                >
                  <AppIcon name="palette" :size="17" />
                </button>
                <div v-if="showThemeMenu" class="theme-menu-backdrop" @click="showThemeMenu = false"></div>
                <div v-if="showThemeMenu" class="theme-menu">
                  <button
                    v-for="t in themeList"
                    :key="t.id"
                    :class="{ active: t.id === currentTheme }"
                    @click="pickTheme(t.id)"
                  >
                    <span class="theme-dot" :style="{ background: themeDots[t.id] }"></span>
                    {{ t.name }}
                    <span v-if="t.id === currentTheme" class="check"><AppIcon name="check" :size="13" /></span>
                  </button>
                </div>
              </div>

              <div class="masthead-user">
                <RouterLink class="user-chip" to="/settings" title="账号设置：改密与头像">
                  <UserAvatar :username="auth.me.username" :avatar-url="auth.me.avatar_url" />
                  <span class="username">{{ auth.me.username }}</span>
                </RouterLink>
                <button class="btn btn-sm desktop-only" @click="onLogout">退出</button>
              </div>
            </div>
          </div>

          <nav class="masthead-nav">
            <RouterLink to="/" exact-active-class="active">
              <span class="tab-icon"><AppIcon name="home" :size="15" /></span>首页
            </RouterLink>
            <RouterLink to="/leaderboard" :class="{ active: route.path === '/leaderboard' }">
              <span class="tab-icon"><AppIcon name="trophy" :size="15" /></span>排行榜
            </RouterLink>
            <RouterLink to="/problems" :class="{ active: route.path.startsWith('/problems') }">
              <span class="tab-icon"><AppIcon name="list" :size="15" /></span>题库
            </RouterLink>
            <RouterLink to="/quiz" :class="{ active: route.path.startsWith('/quiz') }">
              <span class="tab-icon"><AppIcon name="pencil" :size="15" /></span>八股刷题
            </RouterLink>
            <RouterLink to="/review" :class="{ active: route.path === '/review' }">
              <span class="tab-icon"><AppIcon name="cards" :size="15" /></span>背题
            </RouterLink>
            <RouterLink to="/handbook" :class="{ active: route.path === '/handbook' }">
              <span class="tab-icon"><AppIcon name="book" :size="15" /></span>新手速查
            </RouterLink>
            <RouterLink to="/jobs" :class="{ active: route.path === '/jobs' }">
              <span class="tab-icon"><AppIcon name="briefcase" :size="15" /></span>秋招看板
            </RouterLink>
            <RouterLink to="/links" :class="{ active: route.path === '/links' }">
              <span class="tab-icon"><AppIcon name="link" :size="15" /></span>八股笔记
            </RouterLink>
            <RouterLink v-if="auth.me.is_admin" to="/admin" :class="{ active: route.path === '/admin' }">
              <span class="tab-icon"><AppIcon name="gear" :size="15" /></span>管理
            </RouterLink>
          </nav>
        </div>
      </header>

      <div class="main-pane">
        <RouterView />
      </div>
    </div>

    <!-- 未登录（登录/注册页）：裸渲染 -->
    <RouterView v-else />

    <Toast />
    <FloatingAiAssistant />
    <AiSettingsModal v-if="showAiSettings" @close="showAiSettings = false" />
    <LeaderboardPopup v-if="showLeaderboardPopup" @close="showLeaderboardPopup = false" />

    <nav class="bottom-tabs" v-if="auth.me">
      <RouterLink to="/" exact-active-class="active">
        <span class="tab-icon"><AppIcon name="home" :size="21" /></span>首页
      </RouterLink>
      <RouterLink to="/leaderboard" :class="{ active: route.path === '/leaderboard' }">
        <span class="tab-icon"><AppIcon name="trophy" :size="21" /></span>榜单
      </RouterLink>
      <RouterLink to="/problems" :class="{ active: route.path.startsWith('/problems') }">
        <span class="tab-icon"><AppIcon name="list" :size="21" /></span>题库
      </RouterLink>
      <RouterLink to="/quiz" :class="{ active: route.path.startsWith('/quiz') }">
        <span class="tab-icon"><AppIcon name="pencil" :size="21" /></span>刷八股
      </RouterLink>
      <RouterLink to="/review" :class="{ active: route.path === '/review' }">
        <span class="tab-icon"><AppIcon name="cards" :size="21" /></span>背题
      </RouterLink>
      <RouterLink to="/handbook" :class="{ active: route.path === '/handbook' }">
        <span class="tab-icon"><AppIcon name="book" :size="21" /></span>手册
      </RouterLink>
      <RouterLink to="/jobs" :class="{ active: route.path === '/jobs' }">
        <span class="tab-icon"><AppIcon name="briefcase" :size="21" /></span>秋招
      </RouterLink>
      <RouterLink to="/links" :class="{ active: route.path === '/links' }">
        <span class="tab-icon"><AppIcon name="link" :size="21" /></span>八股
      </RouterLink>
      <RouterLink v-if="auth.me.is_admin" to="/admin" :class="{ active: route.path === '/admin' }">
        <span class="tab-icon"><AppIcon name="gear" :size="21" /></span>管理
      </RouterLink>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AiSettingsModal from './components/AiSettingsModal.vue'
import AppIcon from './components/AppIcon.vue'
import FloatingAiAssistant from './components/FloatingAiAssistant.vue'
import LeaderboardPopup from './components/LeaderboardPopup.vue'
import Toast from './components/Toast.vue'
import UserAvatar from './components/UserAvatar.vue'
import { useAiStore } from './stores/ai'
import { useAuthStore } from './stores/auth'
import { useFontSize, useLangPref } from './stores/pref'
import { getTheme, setTheme, THEME_LIST, type Theme } from './theme'
import { api } from './api'
import type { ActivityHeartbeatRequest } from './types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const aiStore = useAiStore()
const showAiSettings = ref(false)
const showLeaderboardPopup = ref(false)
const leaderboardPopupShown = ref(false)
const { langPref, toggleLang } = useLangPref()
const { fontSize, cycleFontSize } = useFontSize()

// 构建时注入的部署版本号（vite define）
const appVersion = __APP_VERSION__

let heartbeatTimer: number | null = null
let leaderboardPopupTimer: number | null = null
let sessionId = ''
let lastSurface: ActivityHeartbeatRequest['surface'] | null = null

function activeSurface(): ActivityHeartbeatRequest['surface'] | null {
  if (route.path.startsWith('/problems')) return 'problem'
  if (route.path.startsWith('/quiz')) return 'quiz'
  if (route.path === '/review') return 'review'
  if (route.path === '/handbook') return 'handbook'
  if (route.path === '/jobs') return 'jobs'
  return null
}

function stopHeartbeat() {
  if (heartbeatTimer !== null) {
    window.clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

async function sendHeartbeat() {
  const surface = activeSurface()
  if (!auth.me || !surface || document.visibilityState !== 'visible' || !document.hasFocus()) return
  if (!sessionId) sessionId = crypto.randomUUID()
  lastSurface = surface
  try {
    await api.post('/api/activity/heartbeat', {
      session_id: sessionId,
      surface,
      elapsed_seconds: 30,
    } satisfies ActivityHeartbeatRequest)
  } catch {
    // 心跳失败不打断当前学习流程，下一次周期继续尝试。
  }
}

function syncHeartbeat() {
  stopHeartbeat()
  if (!auth.me || !activeSurface()) return
  if (!sessionId || lastSurface !== activeSurface()) sessionId = crypto.randomUUID()
  heartbeatTimer = window.setInterval(sendHeartbeat, 30000)
}

function onActivityVisibilityChange() { syncHeartbeat() }

const currentTheme = ref<Theme>(getTheme())
const showThemeMenu = ref(false)
const themeList = THEME_LIST

/** 各主题色板圆点（菜单里的主题缩样） */
const themeDots: Record<Theme, string> = {
  paper: '#ff4000',
  ink: '#ff5a1f',
  slate: '#56718c',
  oat: '#97795a',
  cyber: '#00f2fe',
  sepia: '#2e7d32',
}

const currentThemeName = computed(() => THEME_LIST.find((t) => t.id === currentTheme.value)?.name ?? '')

function pickTheme(t: Theme) {
  setTheme(t)
  currentTheme.value = t
  showThemeMenu.value = false
}

const fontSizeLabel = computed(() => {
  if (fontSize.value === 'sm') return '小'
  if (fontSize.value === 'lg') return '大'
  return '中'
})

const fontSizeTooltip = computed(() => {
  if (fontSize.value === 'sm') return '当前字号：紧凑小号（点击切换为标准中号）'
  if (fontSize.value === 'md') return '当前字号：标准中号（点击切换为护眼大号）'
  return '当前字号：护眼大号（点击切换为紧凑小号）'
})

watch(() => [auth.me?.id, route.path], syncHeartbeat)
watch(() => [auth.me?.id, route.path], () => {
  if (!auth.me || leaderboardPopupShown.value || route.path === '/settings') return
  leaderboardPopupShown.value = true
  leaderboardPopupTimer = window.setTimeout(() => { showLeaderboardPopup.value = true }, 180)
})
onMounted(() => {
  document.addEventListener('visibilitychange', onActivityVisibilityChange)
  window.addEventListener('focus', syncHeartbeat)
  window.addEventListener('blur', stopHeartbeat)
  syncHeartbeat()
  if (auth.me && !leaderboardPopupShown.value && route.path !== '/settings') {
    leaderboardPopupShown.value = true
    leaderboardPopupTimer = window.setTimeout(() => { showLeaderboardPopup.value = true }, 180)
  }
})
onBeforeUnmount(() => {
  stopHeartbeat()
  if (leaderboardPopupTimer !== null) window.clearTimeout(leaderboardPopupTimer)
  document.removeEventListener('visibilitychange', onActivityVisibilityChange)
  window.removeEventListener('focus', syncHeartbeat)
  window.removeEventListener('blur', stopHeartbeat)
})

async function onLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-container">
      <!-- 左侧品牌区 -->
      <section class="auth-hero">
        <div class="auth-hero-brand">
          <span class="brand-logo">leet<span class="path">path</span></span>
          <span class="badge badge-source auth-badge">2027 校招</span>
        </div>

        <h1 class="auth-hero-title">
          专为大模型算法与研发工程师<br />打造的
          <span class="gradient-text">沉浸式智能刷题平台</span>
        </h1>

        <p class="auth-hero-desc">
          汇聚力扣热题 100、面经高频手撕与 750+ 道大模型八股自测（含 Agent Harness），支持 Docker 沙箱秒级评测与自定义 AI 导师答疑。
        </p>

        <!-- 核心特性（极简单行列表） -->
        <ul class="auth-hero-feats">
          <li><AppIcon name="trophy" :size="15" />热题 100 + 面经手撕</li>
          <li><AppIcon name="cards" :size="15" />750+ 道大模型八股</li>
          <li><AppIcon name="robot" :size="15" />场景化 AI 导师</li>
          <li><AppIcon name="briefcase" :size="15" />秋招提前批看板</li>
        </ul>

        <div class="auth-hero-footer">基于 FastAPI + Vue 3 + Docker 构建 · 纯净高效</div>
      </section>

      <!-- 右侧注册表单卡片 -->
      <section class="auth-form-side">
        <div class="auth-card">
          <!-- 登录 / 注册分段切换 -->
          <nav class="segmented auth-tabs">
            <RouterLink to="/login">登录账号</RouterLink>
            <RouterLink to="/register" class="active">注册新账号</RouterLink>
          </nav>

          <header class="auth-card-header">
            <h2>创建你的账号</h2>
            <p>填入信息并使用邀请码激活专属刷题题库</p>
          </header>

          <!-- 错误提示横幅 -->
          <transition name="fade">
            <div v-if="error" class="error-banner auth-err">{{ error }}</div>
          </transition>

          <form class="auth-form" @submit.prevent="onSubmit">
            <!-- 用户名 -->
            <div class="field">
              <label class="auth-label-row">
                <span>用户名</span>
                <span class="form-hint">3-32 位字母/数字/下划线</span>
              </label>
              <input
                v-model="username"
                class="input auth-input"
                placeholder="例如: leeter_2026"
                autocomplete="username"
                required
                minlength="3"
                maxlength="32"
              />
            </div>

            <!-- 邮箱（可选） -->
            <div class="field">
              <label class="auth-label-row">
                <span>电子邮箱</span>
                <span class="form-hint">可选，用于找回与通知</span>
              </label>
              <input
                v-model="email"
                class="input auth-input"
                type="email"
                placeholder="name@example.com"
                autocomplete="email"
              />
            </div>

            <!-- 邀请码 -->
            <div class="field">
              <label class="auth-label-row">
                <span>激活邀请码 <span class="req">*</span></span>
                <span class="form-hint">必填</span>
              </label>
              <input
                v-model="inviteCode"
                class="input auth-input mono"
                placeholder="输入你的注册邀请码"
                autocomplete="off"
                required
              />
            </div>

            <!-- 密码 -->
            <div class="field">
              <label class="auth-label-row">
                <span>设置密码 <span class="req">*</span></span>
                <span class="form-hint">至少 8 位字符</span>
              </label>
              <div class="auth-pwd-wrap">
                <input
                  v-model="password"
                  class="input auth-input"
                  :type="showPwd ? 'text' : 'password'"
                  placeholder="••••••••••••"
                  autocomplete="new-password"
                  required
                  minlength="8"
                />
                <button
                  type="button"
                  class="pwd-toggle"
                  :aria-label="showPwd ? '隐藏密码' : '显示密码'"
                  @click="showPwd = !showPwd"
                >
                  <AppIcon :name="showPwd ? 'eye-off' : 'eye'" :size="17" />
                </button>
              </div>
              <!-- 密码强度指示条 -->
              <div v-if="password.length > 0" class="pwd-strength-bar">
                <div class="strength-track">
                  <div
                    class="strength-fill"
                    :style="{ width: `${pwdStrength.percent}%`, background: pwdStrength.color }"
                  ></div>
                </div>
                <span class="strength-label" :style="{ color: pwdStrength.color }">{{ pwdStrength.text }}</span>
              </div>
            </div>

            <!-- 确认密码 -->
            <div class="field">
              <label>确认密码 <span class="req">*</span></label>
              <input
                v-model="confirm"
                class="input auth-input"
                :type="showPwd ? 'text' : 'password'"
                placeholder="再次输入相同密码"
                autocomplete="new-password"
                required
              />
            </div>

            <!-- 注册按钮 -->
            <button class="btn btn-primary auth-submit" :disabled="loading">
              <span v-if="loading" class="btn-spinner"></span>
              <span>{{ loading ? '正在创建账号…' : '立即注册并开始刷题' }}</span>
              <AppIcon v-if="!loading" name="arrow-right" :size="16" />
            </button>
          </form>

          <footer class="auth-card-footer">
            <span>已经有账号了？</span>
            <RouterLink to="/login" class="auth-link">直接登录</RouterLink>
          </footer>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppIcon from '../components/AppIcon.vue'

const username = ref('')
const email = ref('')
const inviteCode = ref('')
const password = ref('')
const confirm = ref('')
const error = ref('')
const loading = ref(false)
const showPwd = ref(false)

const auth = useAuthStore()
const router = useRouter()

// 计算密码强度
const pwdStrength = computed(() => {
  const p = password.value
  if (!p) return { percent: 0, text: '', color: 'transparent' }
  if (p.length < 8) return { percent: 25, text: '太短', color: 'var(--red)' }
  
  let score = 0
  if (/[a-z]/.test(p)) score++
  if (/[A-Z]/.test(p)) score++
  if (/[0-9]/.test(p)) score++
  if (/[^a-zA-Z0-9]/.test(p)) score++
  if (p.length >= 12) score++

  if (score <= 2) return { percent: 50, text: '中等', color: 'var(--amber, #f59e0b)' }
  if (score >= 4) return { percent: 100, text: '极强', color: 'var(--green, #10b981)' }
  return { percent: 75, text: '良好', color: 'var(--accent, #6366f1)' }
})

async function onSubmit() {
  error.value = ''
  if (password.value !== confirm.value) {
    error.value = '两次输入的密码不一致，请重新检查'
    return
  }
  loading.value = true
  try {
    await auth.register(username.value, password.value, inviteCode.value.trim(), email.value)
    router.push('/')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '注册失败，请检查邀请码或用户名'
  } finally {
    loading.value = false
  }
}
</script>

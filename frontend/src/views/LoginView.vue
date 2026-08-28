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
          登录后继续你的刷题进度，代码草稿与错题斩题本多端实时同步，随时唤起 AI 导师答疑拆解。
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

      <!-- 右侧登录表单卡片 -->
      <section class="auth-form-side">
        <div class="auth-card">
          <!-- 登录 / 注册分段切换 -->
          <nav class="segmented auth-tabs">
            <RouterLink to="/login" class="active">登录账号</RouterLink>
            <RouterLink to="/register">注册新账号</RouterLink>
          </nav>

          <header class="auth-card-header">
            <h2>欢迎回来</h2>
            <p>输入你的用户名与密码继续刷题之旅</p>
          </header>

          <!-- 错误提示横幅 -->
          <transition name="fade">
            <div v-if="error" class="error-banner auth-err">{{ error }}</div>
          </transition>

          <form class="auth-form" @submit.prevent="onSubmit">
            <!-- 用户名 -->
            <div class="field">
              <label>用户名</label>
              <input
                v-model="username"
                class="input auth-input"
                placeholder="输入注册用户名"
                autocomplete="username"
                required
              />
            </div>

            <!-- 密码 -->
            <div class="field">
              <label>账号密码</label>
              <div class="auth-pwd-wrap">
                <input
                  v-model="password"
                  class="input auth-input"
                  :type="showPwd ? 'text' : 'password'"
                  placeholder="输入密码"
                  autocomplete="current-password"
                  required
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
            </div>

            <!-- 登录按钮 -->
            <button class="btn btn-primary auth-submit" :disabled="loading">
              <span v-if="loading" class="btn-spinner"></span>
              <span>{{ loading ? '正在验证登录…' : '立即登录' }}</span>
              <AppIcon v-if="!loading" name="arrow-right" :size="16" />
            </button>
          </form>

          <footer class="auth-card-footer">
            <span>还没有账号？</span>
            <RouterLink to="/register" class="auth-link">注册一个新账号</RouterLink>
          </footer>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppIcon from '../components/AppIcon.vue'

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const showPwd = ref(false)

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push((route.query.redirect as string) || '/')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '用户名或密码错误'
  } finally {
    loading.value = false
  }
}
</script>

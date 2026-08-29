import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

const HomeView = () => import('./views/HomeView.vue')
const LoginView = () => import('./views/LoginView.vue')
const RegisterView = () => import('./views/RegisterView.vue')
const ProblemListView = () => import('./views/ProblemListView.vue')
const ProblemView = () => import('./views/ProblemView.vue')
const ReviewView = () => import('./views/ReviewView.vue')
const JobsView = () => import('./views/JobsView.vue')
const LinksView = () => import('./views/LinksView.vue')
const HandbookView = () => import('./views/HandbookView.vue')
const QuizView = () => import('./views/QuizView.vue')
const OnCallView = () => import('./views/OnCallView.vue')
const AdminView = () => import('./views/AdminView.vue')
const LeaderboardView = () => import('./views/LeaderboardView.vue')
const SettingsView = () => import('./views/SettingsView.vue')

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/register', component: RegisterView, meta: { public: true } },
    { path: '/problems', component: ProblemListView },
    { path: '/problems/:slug', component: ProblemView },
    { path: '/quiz', component: QuizView },
    { path: '/oncall', component: OnCallView },
    { path: '/review', component: ReviewView },
    { path: '/handbook', component: HandbookView },
    { path: '/jobs', component: JobsView },
    { path: '/links', component: LinksView },
    { path: '/leaderboard', component: LeaderboardView },
    { path: '/admin', component: AdminView, meta: { admin: true } },
    { path: '/settings', component: SettingsView },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.loaded) await auth.fetchMe()
  if (!to.meta.public && !auth.me) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.public && auth.me) {
    return { path: '/' }
  }
  if (to.meta.admin && auth.me && !auth.me.is_admin) {
    return { path: '/' }
  }
  return true
})

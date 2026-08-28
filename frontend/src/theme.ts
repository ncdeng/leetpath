export type Theme = 'paper' | 'ink' | 'slate' | 'oat' | 'cyber' | 'sepia'

const KEY = 'leetpath-theme'

export interface ThemeMeta {
  id: Theme
  /** 主题选择菜单里的中文名 */
  name: string
  /** 暗色系主题（Editor 用 oneDark、配色逻辑判断） */
  dark: boolean
}

/** 主题全家桶：瓷白信号(默认浅) / 石墨终端(默认暗) / 莫兰迪灰蓝 / 燕麦拿铁 / 赛博霓虹 / 豆沙护眼 */
export const THEME_LIST: ThemeMeta[] = [
  { id: 'paper', name: '瓷白信号', dark: false },
  { id: 'ink', name: '石墨终端', dark: true },
  { id: 'slate', name: '莫兰迪灰蓝', dark: false },
  { id: 'oat', name: '燕麦拿铁', dark: false },
  { id: 'cyber', name: '赛博霓虹', dark: true },
  { id: 'sepia', name: '豆沙护眼', dark: false },
]

const THEMES = THEME_LIST.map((t) => t.id)

/** 旧版本主题名迁移：light→paper，dark→ink */
const LEGACY: Record<string, Theme> = {
  light: 'paper',
  dark: 'ink',
}

export function getTheme(): Theme {
  const current = document.documentElement.dataset.theme
  if (current && (THEMES as string[]).includes(current)) return current as Theme
  return 'paper'
}

export function isDarkTheme(t?: Theme): boolean {
  const theme = t ?? getTheme()
  return THEME_LIST.find((m) => m.id === theme)?.dark ?? false
}

export function setTheme(t: Theme) {
  document.documentElement.dataset.theme = t
  localStorage.setItem(KEY, t)
}

export function toggleTheme(): Theme {
  const current = getTheme()
  const next = THEMES[(THEMES.indexOf(current) + 1) % THEMES.length]

  setTheme(next)
  return next
}

/** 应用挂载前调用：恢复用户上次选择（含旧版主题名迁移） */
export function initTheme() {
  const saved = localStorage.getItem(KEY)
  if (saved) {
    const migrated = LEGACY[saved] ?? saved
    if ((THEMES as string[]).includes(migrated)) {
      document.documentElement.dataset.theme = migrated
      if (migrated !== saved) localStorage.setItem(KEY, migrated)
      return
    }
  }
  // 首访跟随系统深浅色偏好
  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
  document.documentElement.dataset.theme = prefersDark ? 'ink' : 'paper'
}

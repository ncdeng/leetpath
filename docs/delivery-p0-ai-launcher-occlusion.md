# AI 悬浮入口遮挡 P0 修复交付说明

交付日期：2026-08-30
开发分支：`fix/ai-launcher-occlusion`
基线：`main@c7010a9`

## 交付范围

本次交付组合落实终审裁定的方案 D 与方案 C：

1. 在移动端底栏断点（`<=1023px`）内，已有页面内联 AI 入口的路由不再重复显示全局悬浮胶囊。
2. 在桌面断点（`>=1024px`）内保留全局悬浮胶囊，同时为背题页底部主操作区预留 96px 右侧安全区。
3. 只控制关闭状态下的胶囊入口；由页面内联入口打开的 AI 浮窗不受影响。

## 修改文件

| 文件 | 修改内容 |
| --- | --- |
| `frontend/src/router.ts` | 为 `/problems/:slug`、`/quiz`、`/oncall`、`/review` 增加 `meta.hasInlineAi`。 |
| `frontend/src/router-meta.d.ts` | 扩展 Vue Router `RouteMeta`，为认证、管理员和内联 AI meta 提供布尔类型约束。 |
| `frontend/src/aiLauncherChrome.ts` | 新增纯函数 `shouldHideCapsule(routeMeta, isCompactViewport)`。 |
| `frontend/src/aiLauncherChrome.test.ts` | 新增移动内联路由、桌面内联路由、移动普通路由三组行为测试。 |
| `frontend/src/components/FloatingAiAssistant.vue` | 响应 route meta 与视口宽度变化，按纯函数结果控制胶囊渲染。 |
| `frontend/src/styles/views/review.css` | 在 `min-width:1024px` 下为 `.review-actions` 注入 `--floating-safe-pad:96px`。 |

仓库现有 launcher helper 与测试位于 `frontend/src/` 根目录，因此测试直接扩展既有 `aiLauncherChrome.test.ts`，没有另建重复的 `src/utils` 模块。

## 行为契约

```ts
shouldHideCapsule(
  routeMeta: Readonly<{ hasInlineAi?: boolean }>,
  isCompactViewport: boolean,
): boolean
```

仅当 `routeMeta.hasInlineAi === true` 且视口处于 `<=1023px` 底栏断点时返回 `true`。严格布尔判断避免字符串或其他 truthy meta 值误隐藏入口。

胶囊隐藏不改变以下行为：

- 普通路由在移动端继续显示全局 AI 胶囊。
- 所有路由在桌面端继续显示全局 AI 胶囊。
- AI 窗口已经打开时继续正常渲染；内联按钮仍调用原有 `useAiAssistant` 状态。
- 现有拖拽位置、底栏净空和 localStorage 恢复逻辑保持不变。

## TDD 记录

生产实现前先加入三项测试，并运行：

```bash
node --test src/aiLauncherChrome.test.ts
```

RED 阶段结果为 17 项中 3 项失败，失败原因均为 `shouldHideCapsule must be exported`；原有 14 项 launcher 测试继续通过。实现纯函数后，同一命令 17/17 通过。

## 双视口复验

使用本分支 Vite 服务和 Playwright CLI，以确定性 mock API 数据完成一次性真实 CSSOM/DOM 验证。仓库当前没有浏览器测试 runner，因此本节同时保留可人工复跑的验收步骤，不将截图描述为持续集成门禁。

### 390x844

| 路由/状态 | 期望 | 实测 |
| --- | --- | --- |
| `/` | 普通路由保留胶囊 | `.floating-capsule` 数量为 1。 |
| `/problems/two-sum` | 隐藏胶囊，保留内联入口 | 胶囊为 0；`AI 助教`按钮可见。 |
| `/quiz` | 隐藏胶囊 | 胶囊为 0。 |
| `/oncall` | 隐藏胶囊，保留内联入口 | 胶囊为 0；`AI 模拟面试实战`按钮可见。 |
| `/review` 翻面 | 隐藏胶囊，保留内联入口和主操作 | 胶囊为 0；`问 AI 更多解法 / 口诀`及四个操作按钮可见。 |

移动端 `.review-actions` 的计算 `padding-right` 为 `0px`，确认桌面安全区规则没有挤压 390px 内容。

### 1440x900

在 `/review` 翻面并将操作区滚入视口后：

- `.floating-capsule` 数量为 1，尺寸为 52x52。
- `.review-actions` 的计算 `padding-right` 为 `96px`。
- `上一张`、`没记住`、`记住了`、`下一张` 四个按钮与胶囊矩形均不相交。
- 页面内联 AI 按钮仍可见。

本地截图证据生成于 `output/playwright/p0-ai-review-mobile.png` 与 `output/playwright/p0-ai-review-desktop.png`；`output/` 按仓库规则忽略，不纳入提交。

手工复验时应重复以下步骤：

1. 登录后在 390x844 访问四个 `hasInlineAi` 路由，确认无全局胶囊且内联 AI 入口可操作。
2. 在同一视口访问首页或题库列表，确认胶囊仍可见并停在底栏上方。
3. 调整至 1440x900，确认四个路由恢复胶囊。
4. 在背题页翻面并滚动到底部操作区，确认 `记住了` 可点击且没有被胶囊覆盖。
5. 在系统减少动态效果设置下重复打开 AI；本次没有新增动画或依赖 transition 的状态切换。

## 最终验证

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

| 检查 | 结果 |
| --- | --- |
| `npm test` | 45/45 通过，0 失败。 |
| `npm run typecheck` | 退出码 0。 |
| `npm run build` | 131 modules transformed，退出码 0。 |
| `git diff --check` | 退出码 0。 |

生产构建仍报告既有的 CodeMirror chunk 超过 500 kB 警告，不影响构建成功，也不是本次修复引入。

## 交付纪律

全部修改位于独立 worktree `D:\leetpath-codex-p0` 的 `fix/ai-launcher-occlusion` 分支。主目录中 Grok 的 P1 分支和文件未被修改；本分支只准备通过 PR 合入，不直接推送 `main`。

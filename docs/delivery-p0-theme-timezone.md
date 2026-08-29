# 主题对比度与本地日期修复交付说明

交付日期：2026-08-29

## 交付范围

本次交付完成两项前端加固：

1. 为十套主题补齐强调色前景 token，移除强调色背景上的硬编码白字，并覆盖 normal/hover 两种状态。
2. 将排行榜弹窗的按日节流改为本地日历日，抽出可独立测试的应用壳纯函数，并补齐移动底栏横滚渐隐状态。

工作区中原有的 StatusBadge 与 OnCall/Review 基础 token 收敛不属于本次交付；本次只在相关文件中修改强调色前景。

## 修改文件

| 文件 | 修改内容 |
| --- | --- |
| `frontend/src/appChrome.ts` | 新增 `shouldAutoShowPopupOnce` 与 `tabsFadeState` 纯函数。 |
| `frontend/src/appChrome.test.ts` | 覆盖首次展示、同日拦截、跨日恢复和底栏四种滚动状态。 |
| `frontend/src/dates.test.ts` | 守护本地凌晨日期、年月日补零、今日格式及跨月日期运算语义。 |
| `frontend/src/themeContrast.test.ts` | 从真实 CSS 主题块读取 token，逐主题验证 normal/hover WCAG AA 对比度。 |
| `frontend/src/App.vue` | 使用 `todayLocalDate()`，在 App adapter 中处理 Storage；通过模板 ref 和 `@scroll.passive` 更新底栏 fade 状态。 |
| `frontend/src/styles/base.css` | 十套主题增加 `--on-accent`、`--on-accent-hover`；全局主按钮消费语义 token。 |
| `frontend/src/styles/chrome.css` | 增加移动底栏左、右及双侧渐隐 mask。 |
| `frontend/src/styles/views/ai.css` | 用户消息、Markdown、引用和发送按钮改用强调色前景 token。 |
| `frontend/src/styles/views/home.css` | 今日矩阵和激活胶囊改用 `--on-accent`。 |
| `frontend/src/styles/views/jobs.css` | 激活投递阶段改用 `--on-accent`。 |
| `frontend/src/styles/views/oncall.css` | 记忆按钮和激活筛选按钮改用 `--on-accent`。 |
| `frontend/src/styles/views/problem.css` | 禅模式 normal/hover 分别使用对应前景 token。 |
| `frontend/src/styles/views/quiz.css` | 选项前缀、用户气泡及其 Markdown 子树改用 `--on-accent`。 |
| `frontend/src/styles/views/review.css` | AI 按钮强调色 hover 改用 `--on-accent`。 |

## Token 设计

`--on-accent` 用于 `--accent` 背景，`--on-accent-hover` 用于 `--accent-hover` 背景。多数主题两者相同；以下主题需要分别处理：

- Oat：normal 使用 `#111111`，hover 使用 `#ffffff`。现有两档棕色背景不存在一个同时满足 4.5:1 的固定黑/白前景。
- Signal、Terminal：normal 使用 `#111111`，hover 使用 `#0a0f14`；`#111111` 对 hover 仅为 4.44:1。

仍保留的硬编码白字只用于红/绿状态色、渐变图标或危险操作，不消费 `--accent`，因此不应机械替换为本 token。

## WCAG 验证

以下数据按 WCAG 2 相对亮度公式计算。按钮字号为 14.5px，验收阈值采用普通文本 AA `4.5:1`。

| 主题 | Normal | Hover | 结果 |
| --- | ---: | ---: | --- |
| Paper | 5.41:1 | 7.07:1 | Pass |
| Ink | 5.51:1 | 6.78:1 | Pass |
| Telemetry | 13.66:1 | 10.34:1 | Pass |
| Swiss | 6.98:1 | 8.97:1 | Pass |
| Signal | 5.38:1 | 4.52:1 | Pass |
| Terminal | 5.38:1 | 4.52:1 | Pass |
| Slate | 5.08:1 | 6.42:1 | Pass |
| Oat | 4.67:1 | 5.67:1 | Pass |
| Cyber | 13.87:1 | 8.98:1 | Pass |
| Sepia | 5.13:1 | 7.87:1 | Pass |

`themeContrast.test.ts` 直接读取 `base.css`，因此删除 token、修改 accent 或引入低于 4.5:1 的组合都会使测试失败。Playwright 另在真实 CSSOM 中确认十套主题的 `.btn-primary` normal/hover 计算色与表中 token 一致。

## 本地日期与纯函数边界

`App.vue` 不再通过 UTC `toISOString()` 计算排行榜弹窗日期，而是调用 `todayLocalDate()`。在 Asia/Shanghai 的 `00:00-07:59`，日期键现在与用户本地自然日一致。

纯函数不访问 Date、Storage 或 DOM：

```ts
shouldAutoShowPopupOnce(lastShownDate: string | null, today: string): boolean
tabsFadeState(metrics: TabsScrollMetrics, threshold?: number): TabsFadeState
```

App adapter 负责读取本地日期、读写 `localStorage`、调度弹窗和读取底栏尺寸。底栏 scroll 通过模板事件绑定，不依赖首次 `onMounted` 时节点已经存在，因此异步登录后创建的底栏也能更新 fade 状态。

## PR #18 现状

GitHub PR #18（`fix/frontend-ux-polish`）已于 2026-08-29 关闭，状态为 `CLOSED`，且未合并。其弹窗节流与移动底栏体验相关改动已由 `main` 工作区中的模块化方案取代：本地日期统一通过 `dates.ts` 计算，弹窗判定与底栏 fade 判定分别抽为 `appChrome.ts` 的纯函数，并由独立单元测试覆盖。后续不再以 PR #18 分支实现作为交付基线。

## 自动化覆盖

`appChrome.test.ts` 包含四项行为测试：

1. 没有历史日期时允许首次展示。
2. 同一本地日期拒绝重复展示。
3. 本地日期变化后恢复展示。
4. 底栏覆盖无溢出、最左、中间和最右四种状态。

附加的主题对比度测试遍历十套主题的 normal/hover，共验证 20 组前景/背景组合。

`dates.test.ts` 新增四项本地日历语义守护：

1. 断言本地时间 `2026-08-29 01:00` 格式化后仍为 `2026-08-29`，防止 UTC 偏移回退到前一天。
2. 断言单数字月份与日期补零为 `YYYY-MM-DD`。
3. 断言 `todayLocalDate()` 始终满足 `YYYY-MM-DD` 格式。
4. 覆盖跨月正向、反向 `addDays`，以及 `diffDays` 的正负差值。

## 验证结果

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

2026-08-29 的最终验证结果：

| 检查 | 结果 |
| --- | --- |
| `npm test` | 42/42 通过，0 失败（含新增 4 项日期语义测试）。 |
| `npm run typecheck` | 退出码 0。 |
| `npm run build` | 131 modules transformed，退出码 0。 |
| `git diff --check` | 退出码 0。 |

生产构建仍报告既有的 CodeMirror chunk 超过 500 kB 提示，不影响本次构建成功，也不是本次改动引入的功能回归。

浏览器验证使用 390x844 移动视口确认底栏初始状态为 `fade-right`，计算宽度为 `clientWidth=390`、`scrollWidth=456`，对应 mask 已生效。

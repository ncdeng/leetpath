# P0 交付：状态徽章失色 + OnCall/Review CSS 变量收敛

日期：2026-08-29  
范围：仅前端样式契约，不改评测协议、API 或主题令牌块。

## 1. 修改清单

| 文件 | 改动 |
|---|---|
| `frontend/src/components/StatusBadge.vue` | `:class="'st-' + status.toLowerCase()"`，与 `base.css` 小写选择器对齐 |
| `frontend/src/views/ProblemView.vue` | 测试点药丸同样 `toLowerCase()`，避免 `st-AC` 绕过组件 |
| `frontend/src/styles/base.css` | 补 `.status-badge.st-ie` / `.status-pill.st-ie` |
| `frontend/src/styles/views/oncall.css` | 19 处未定义变量改为 `base.css` 已有令牌 |
| `frontend/src/styles/views/review.css` | 1 处 `--shadow-sm` → `--shadow` |
| `docs/delivery-p0-styles-badges.md` | 本文件 |

仓库内已无 `--radius-md` / `--shadow-sm` / `--shadow-md` / `--surface-hover` / `--text-muted` 引用。

## 2. 改动前后对照

### 2.1 状态徽章 class

| 状态 | 改前 DOM class | 是否命中 CSS | 改后 DOM class | 是否命中 CSS |
|---|---|---|---|---|
| `pending` / `judging` | `st-pending` / `st-judging` | 是 | 同左（本就小写） | 是 |
| `AC` / `WA` / `TLE` / `MLE` / `CE` / `RE` | `st-AC` 等 | **否**（选择器为 `.st-ac`） | `st-ac` 等 | 是 |
| `IE` | `st-IE` | **否**，且无 `.st-ie` 规则 | `st-ie` | 是（新增规则） |

`st-ie` 使用 `--text-dim` / `--surface-2`，与 `CE` 同档：系统/编译侧异常，不用红/橙误导成用户 WA/RE。

测试点行（`ProblemView` 不走 `StatusBadge`）与组件同一套小写前缀，避免历史列表有色、用例药丸无色。

### 2.2 CSS 变量（20 处）

映射（无 fallback 的空变量 → `base.css` 令牌）：

| 原变量（未定义） | 替换为 | 次数 |
|---|---|---|
| `--radius-md` | `--radius` | 5（oncall 卡片） |
| `--shadow-sm` | `--shadow` | 6（oncall 5 + review 1） |
| `--shadow-md` | `--shadow` | 2（oncall hover） |
| `--surface-hover` | `--surface-2` | 4（oncall 悬停底） |
| `--text-muted` | `--text-dim` | 3（oncall 弱化字） |
| **合计** | | **20** |

效果：OnCall 闪卡/面板恢复圆角与阴影；Review 语言条恢复 `box-shadow`；悬停底与弱化字落到主题色板，不再静默丢声明。

未在 `base.css` 新增 `--radius-md` 等别名，避免两套半径/阴影继续分叉。

## 3. 验证命令

在 `frontend/`：

```bash
npm run typecheck
npm test
```

通过标准：`vue-tsc --noEmit` 退出 0；`node --test src/*.test.ts` 全绿。

手工抽查（无浏览器自动化门禁，合入前建议）：

1. 刷题页提交历史：AC 绿底、WA 红底、pending/judging 仍为 accent。
2. 人为制造或历史 IE 提交：药丸为中性墨色，不再无 class 色。
3. `/oncall` 闪卡有圆角和阴影；hover 底为 `--surface-2`。
4. `/review` 顶栏语言切换条有 `--shadow`。

## 4. 刻意不做

- 不改 `btn-primary` 在 cyber/telemetry 下的对比度（另一项 P0）。
- 不把 OnCall 令牌补进十套主题块。
- 不改徽章文案（仍显示 `AC` 等大写状态码/中文 label）。

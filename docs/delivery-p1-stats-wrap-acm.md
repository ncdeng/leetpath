# P1 交付：零值统计 · 标题断行 · 移动端 ACM 提示

分支：`fix/ux-p1-stats-wrap-acm`（基于 `main` / `c7010a9`）  
对应 `scratch_zcode_review_brief.md` ①②③。未推 `main`。

## 1. Commit 清单

| Commit | 内容 |
|---|---|
| `fix(frontend): 页头零值统计回归中性墨色` | Quiz / Review / 题库页头 |
| `fix(frontend): 中文大标题均衡断行并保护品牌词` | `.display` / 登录标题 / 「手撕」 |
| `fix(frontend): 移动端 ACM 提示改为可展开短摘要` | `ProblemView` + `problem.css` |

## 2. 改动前后对照

### 2.1 零值统计

| 位置 | 改前 | 改后 |
|---|---|---|
| 题库「已通过」 | 恒为 `.accent` | `solved > 0` 才 `.accent` |
| 背题「已记住」 | 同上 | `rememberedCount > 0` 才 `.accent` |
| 八股已刷 / 错题 / 斩题 | 无条件 accent / 内联红绿 | 零值默认 `color: var(--text)`；非零 `.accent` / `.bad` / `.good` |
| 八股正确率 | `accuracy_rate >= 80` 即绿（含 0 题 0%） | `answered_count > 0 && accuracy_rate >= 80` 才 `.good` |

`base.css` 增加 `.head-stats .stat .num.good` / `.bad`，用已有 `--green` / `--red`。不用 `--on-accent`（那是实心底上的字色）。

### 2.2 中文断行

- `.display`、`.auth-hero-title`：`text-wrap: balance`（旧内核忽略，行为与改前相同）。
- 仅「手撕」包 `<span class="kw">`，`.kw { white-space: nowrap }`。
- **没有**对整句 `.grad` / `.gradient-text` 设 `nowrap` 或 `inline-block`。
- 首页 lede、注册页简介中的「手撕」同样保护。

### 2.3 ACM 提示

| 视口 | 改前 | 改后 |
|---|---|---|
| 桌面 | 完整协议句 + 手册链接 | 不变（`.acm-hint-full` + 链接；`<details>` `display: none`） |
| ≤1023px | 长句换行挤压编辑器 | 一行摘要；点「展开协议」看全文；手册链接仍在 |

## 3. 验证

在 `frontend/`：

```bash
npm run typecheck
npm test
npm run build
```

手工（390×844 新账号 + 1440 桌面）：

1. 题库 / 八股 / 背题：零值均为墨色；八股刷 1 题后非零项恢复 accent/红/绿；正确率在 0 题时不绿。
2. 首页 hero：无「的」孤行、无「手/撕」拆开；登录大标题无虚词孤行。
3. 做题页「代码」签：手机一行摘要，点开见全文；桌面仍是完整一句。

## 4. 刻意不做

- 悬浮 AI 球遮挡（简报 ④，待 C+B 方案拍板）。
- 秋招 D-8~14 amber 档（P2）。
- 不从 `fix/frontend-ux-polish` cherry-pick（含已废弃的 `window.scrollY` 隐藏与过时弹窗逻辑）。
- 不改 `--on-accent` 主按钮对比度。
- 不直推 `main`。

# 更新日志（CHANGELOG）

本文件记录 **深南AI日报 Daily AI Brief** 的版本演进。

## 版本号规则

- 格式：`vX.Y.Z_YYMMDD`（语义化版本 + `_两位年两位月两位日` 后缀）
- **修订号 Z**：仅修复 bug / 细节优化 → Z+1
- **次版本 Y**：新增向下兼容功能 → Y+1、Z 归零
- **主版本 X**：不兼容重大调整 / 正式首发 → X+1、Y/Z 归零
- 归档文件名：`ai-daily-v{X.Y.Z}_{YYMMDD}.html`

---

## v1.10.25_260825 — 共X条渐隐提前 + 报告页位置统一（_fix_vision_02）

**类型**：修订 +1（视觉细节打磨）
**日期**：2026-08-25

- **共X条渐隐提前 80px**：`updateStuck()` 新增 `FADE_AHEAD=80` 阈值，nav 距吸顶 80px 内即加 `.fading` 类，`.nav.fading .nav-total-count` 沿用 0.4s transition 平滑淡出+收窄，比"吸顶才消失"更顺滑
- **报告页共X条位置与主页统一**：移除原先嵌在 `report-range` 内部 [周/月] 之后的逻辑，改为与主页一致作为 `nav-inner` 直接子元素（`{nav_total_html}` 统一渲染），三页 DOM 结构完全一致

## v1.10.24_260825 — hero 顶底精调 + 共X条平滑渐隐 + 报告页加共X条（_fix_vision_02）

**类型**：修订 +1（视觉细节打磨）
**日期**：2026-08-25

- **主页 hero 按大号日期顶/底精调**：`[data-page-period] .hero-info-col` 改为 `flex column + justify-content space-between` —— 送达时间顶对齐"08 25"上边、引用块底对齐"08 25"下边（报告页无此选择器，保持 -60px 不动）
- **共X条平滑渐隐**：`.nav.is-stuck .nav-total-count` 从瞬时 `display:none` 升级为 `opacity/transform/max-width/padding/border-width` 全加 `transition:0.4s ease` 平滑淡出+收窄
- **周报/月报 nav 也加共X条**：嵌进 `nav-actions.report-range` 内 [周/月] 之后、sep 之前（周报共 79 条、月报共 91 条）

## v1.10.23_260825 — 主页 hero 底对齐 + 共X条指示器（_fix_vision_02）

**类型**：修订 +1（视觉细节打磨）
**日期**：2026-08-25

- **主页 hero 右栏底对齐到绿线**：新增 `[data-page-period] .hero-info-col { margin-top:0; align-self:flex-end; }`，右栏（送达时间+覆盖窗口）底边与大日期下方绿线齐平（报告页不匹配，保持原样）
- **主页 nav 右区共X条金色指示器**：`nav_total_html = '共<span class="num">{total}</span>条'`，胶囊+金色数字+`margin-left:auto` 推到最右；吸顶后 `.nav.is-stuck .nav-total-count{display:none}` 让位给报告/历史日报/导出；报告页 `nav_total_html=""` 不生成

## v1.10.22_260824 — 报告页按钮金色强高亮（_fix_report_button）

**类型**：修订 +1（视觉强化 + 根因修复）
**日期**：2026-08-24

- **🎯 根因修复（最关键）**：JS 选择器从 `.time-chip` 收窄为 `.time-chip[data-period]`。报告页周/月胶囊不带 `data-period`，原先被 `setChips(period).toggle('active', false)` 默默剥掉 → 导致"点一下闪一下金、进来不常亮"。收窄后服务端下发的 `.active` 稳保持久高亮
- **字体改黑体**：`.time-chip` `font-weight: 500 → 700`；`.active → 800`（双层加重）
- **active 持久强高亮（金色召唤术）**：金色实底微渐变 + 深字 + 暖光外阴影 + 放大
  ```css
  .time-chip.active {
    color: #1A1405;
    background: linear-gradient(180deg, rgba(232,217,160,0.96), rgba(214,196,128,0.88));
    border: 1px solid rgba(255,243,214,0.85);
    box-shadow: 0 3px 12px rgba(218,200,135,0.50), inset 0 1px 0 rgba(255,255,255,0.35);
    font-weight: 800;
    transform: scale(1.07);
    letter-spacing: 0.04em;
    z-index: 1;
  }
  ```
- **返回今日色块更显眼**：`border 0.30→0.50`，`bg 0.06→0.12`
- **🔙→🏠 图标**：原"十字+箭头"换成清晰"屋顶+房子"home SVG（report_switch + report_dropdown 两处一致）
- bump VERSION 1.10.21 → 1.10.22

## v1.10.21_260824 — 报告页三合一收尾（_fix_report_002）

**类型**：修订 +1（报告页交互修复 + 视觉对齐）
**日期**：2026-08-24

- **nav 吸顶修复（致命）**：`updateStuck()` 原判定 `rect.top <= 0`，但报告页 `.nav` 的 `top=78px`（safe-area+topbar+ticker 偏移），`rect.top` 永远 = 78 → `is-stuck` 永远 false → 金边 + 工具胶囊搬到 nav 行全部失效，用户视角"周月胶囊消失后不再浮现"。改为 `getComputedStyle(navEl).top` 作阈值，兼容主页 0 / 报告页 78 / 移动端各值
- **工具胶囊合并成一行**：报告页 `topbar` 完全隐藏（`[data-page-report] .topbar{display:none}` + `topbar_tools_html=""`），周报/月报 切换 + 「返回今日」全部打包进同一 `.nav-actions.report-range`，吸顶时随 nav 行浮现（不再因 hero 滚走而消失）
- **当前页高亮**：当前是周报/月报 的胶囊加 `.time-chip.active` 高亮（复用现有类 `color:var(--brand-brief);background:rgba(218,200,135,0.18)`）
- **nav.top 统一**：报告页 `.nav` 改为 `top:env(safe-area-inset-top,0)` 与首页一致（topbar 已隐藏，无需 78px 偏移），单一吸顶逻辑
- **右栏对齐**：报告页 hero 右栏（meta + lead）`margin-top:-60px` 上移，实测与大标题字顶 delta≈2px 基本齐平
- bump VERSION 1.10.20 → 1.10.21

## v1.10.20_260824 — 月报自然月逻辑（_fix_month_01）

**类型**：修订 +1（数据语义修正）
**日期**：2026-08-24
**根因**：`generate_dashboard.py` 的月报聚合用 `aggregate_info(available_dates[:30])`——"最近 30 天"，而非"上个月整月"。在 8/24 打开看到 7/26~8/24，与 lead 文案"上个月整月"完全矛盾。
**修复**：
- 以 `datetime.now(BEIJING)` 为基准计算"上个月"自然边界（`prev_start`=上月 1 日、`prev_end`=上月最后一天，跨年自动衔接）
- 过滤 `available_dates` 仅取落在上月内的日期，再 `aggregate_info` 聚合
- 覆盖 `date_str` 为 `YYYY-MM-01 ~ YYYY-MM-<月末>`（`aggregate_info` 本身只返回首尾，不一定跨整月）
- 渲染守卫从硬阈值 `len(available_dates) >= 8` 改为 `if _month_dates:`，依赖真实数据存在性
- 验证：今天 (8/24) 月报 = 2026-07-01 ~ 2026-07-31；9/1 打开 = 8/1 ~ 8/31（自动衔接）；1/1 打开 = 上年 12 月整月（跨年）
- bump VERSION 1.10.19 → 1.10.20

## v1.10.19_260824 — 周报页改版（_fix_week_01）

**类型**：优化 +1
**日期**：2026-08-24

- 标题 `聚合报告 AIBrief` → `周报 Weekly AI Brief`（配色一致：白色 + 品牌蓝 brief）
- `聚合窗口` → `周报周期`，与左侧金色大日期字符串完全一致（统一为 `YYYY-MM-DD ~ YYYY-MM-DD`）
- 引用（lead）补齐规则说明：本周自然 7 天（截止昨天），滚动 7 天，跨月自然连续，不锁周首日
- 第 4 点：周报/月报 切换胶囊改为 `.nav-actions`，复用主页 `placeActions` —— 静止时位于 hero 右上角与 logo 同排，吸顶时合并进 nav 行与 5 分类胶囊同一行，沿用主页规则
- topbar 简化为仅保留「返回今日」，周报/月报 切换退出 topbar
- 同步生成器：月报页（report-month.html）标题/周期/lead 同步为「月报 Monthly AI Brief」样式；月报数据的"自然月"范围在 _fix_month_01 修复

## v1.10.18_260821 — nav 胶囊点击极速位移 + 着陆脉冲（_fix_nav_03）

**类型**：优化 +1
**日期**：2026-08-21

- 拦截 nav 胶囊点击（原仅依赖原生 `scroll-behavior:smooth` 跳锚点），改用 rAF 自写指数缓出（~340ms 极速位移），比原生 smooth 更快更可控
- 落点精确对齐吸顶 nav 高度（`navEl.offsetHeight`），不再依赖固定 `scroll-padding-top`
- 着陆瞬间目标 section 加 `.flash` 脉冲高亮（靛蓝描边+辉光 0.7s），强化“你到了这一组”的锚定感，周报/月报等远分组尤其受益
- 保留 paint/锁定逻辑：点击仍 `manualIdx=i` 锁定高亮，滚动跟随让位
- `prefers-reduced-motion` 下禁用脉冲动画，仅保留位移

## v1.10.17_260821 — 封死生成器静默删档地雷（_fix_report_001 收尾）

**类型**：修订 +1（数据安全修复）
**日期**：2026-08-21
**根因**：`generate_dashboard.py` 的 `main()` 无条件调用 `cleanup_old_archives(keep_days=30)`，每次本地生成或 GitHub Actions（`deploy.yml` 在 push/cron 时都跑 `python generate_dashboard.py`）都会静默删除 `releases/daily/` 下 30 天前的归档，违反"releases 保留全量历史"约定，且完全未经确认。
**修复**：清理改为**默认关闭**，仅在显式传入 `--cleanup` 时执行。deploy 与日常生成不再自动删档；需要腾空间时手动 `python generate_dashboard.py --cleanup`。
**影响**：线上 gh-pages 与本地 releases/ 的历史 daily 归档不再被自动抹掉。

---

## v1.10.16_260821 — 吸顶判定改为确定性几何（_fix_report_001 二次修）

**类型**：修订 +3（稳健性修复）
**日期**：2026-08-21
**根因**：v1.10.15 修复 SyntaxError 后，`placeActions()` 仍偶发不把胶囊搬到 hero 右上角。原因是吸顶判定用「1px 哨兵 + `IntersectionObserver`」：哨兵 `position:absolute;top:0` 的实际位置依赖其祖先的定位上下文，IO 初始回调在某些渲染环境/无头浏览器下会误报 `ratio===0` → `stuck=true`，把胶囊立刻搬回 nav。属于用脆弱几何点做状态判定的反模式。
**修复**：删除哨兵与 IO，改用 `navEl.getBoundingClientRect().top <= 0`（nav 自身 `position:sticky; top:0`，吸顶时 top 必然 ≤0）配合 `requestAnimationFrame` 节流的 scroll 监听。`scrollY=0` 时 `nav.top > 0`、天然不吸顶、胶囊到 hero 右上角，状态确定、无竞态。
**影响**：_fix_report_001 的三胶囊布局在所有环境下都稳定生效。

**类型**：修订 +2（阻塞性 bug 修复）
**日期**：2026-08-21
**根因**：`generate_dashboard.py` 的 f-string 模板里时段 chip 的 title 写了一个残废的 JS 模板表达式（`${'morning':'08:10',...}[key]`，对象字面量大括号被吞），生成的 `releases/index.html` 第 ~1902 行抛 `Uncaught SyntaxError: Missing } in template expression`，**整个主脚本从该行起死亡**。后果：`placeActions()` / nav 高亮 IO / 时段切换全部不执行，三胶囊永不搬运、nav 永不亮——表现为"完全没变化"。
**修复**：将时段时间抽为干净的 `periodTime` 常量对象，`btn.title` 改用 `periodTime[key]`。修后 console 干净、生成产物合法。
**影响**：_fix_report_001 的三胶囊布局与 v1.10.13 的 nav 高亮终于真正生效。

---

## v1.10.14_260821 — 三工具胶囊移到 hero 右上角 + 吸顶合并一排（_fix_report_001）

**类型**：修订 +1（布局优化）
**日期**：2026-08-21

- 📐 **三工具胶囊（报告/历史日报/导出）移到页面右上角**：hero 顶部新增 `.hero-top` 一行 = `[logo] …… [三胶囊]`，胶囊与 logo 同排右上角对齐；静止时 nav 只剩 5 分类胶囊。
- 🔀 **吸顶时合并成一排**：用 JS 把 `.nav-actions` 在 `.hero-actions`（静止）与 `.nav-inner`（吸顶）间搬运——nav 吸顶时三胶囊搬回 nav 行内，与 5 分类合并成一排；回顶再搬回 hero 右上角。下拉交互基于 `.dropdown` 类委托绑定，搬运不丢监听。
- 📱 **移动端（≤880）不搬**：维持 v1.10.10 现状（三胶囊始终在 nav），避免与移动端横滑/隐藏逻辑冲突；resize 跨断点自动重算位置。

---

## v1.10.13_260821 — nav 高亮重写（根治「默认不亮 / 点选不持久」）

**类型**：修订 +1（交互修复 · 根因修复）
**日期**：2026-08-21

- 🐛 **根因**：源码里存在 **两段互相冲突的 nav-chip 高亮脚本**，且都被生成进页面——旧段（原「锚点导航高亮」）只靠 `IntersectionObserver` 滚动 + 点击 `setActive` 切换 `active`，**页面加载从不调用、且点选会被下一帧滚动立刻覆盖**；另一段（v1.10.11 的 `is-active-by-io/by-click` + `lockedIdx`）虽想做默认+锁定，却与新吸顶位置/双 class 纠缠，两者在同一 DOM 上互相撤销 class，导致「打开无默认高亮、点选不持久」反复出现（即用户说的「改了五次」）。
- 🔨 **修复**：删除旧冲突段，将高亮逻辑重写为**单一真相**——只用 `.active` 一个 class（深浅 CSS 均已支持）：① 加载即 `paint(0)` 默认首颗高亮；② 点击 `manualIdx=i` 锁定并 `paint(i)`，直到下次点选别的胶囊；③ 滚动跟随仅在 `manualIdx<0`（未点选）时生效，点选后锁定、滚动不再抢。`is-stuck` 金线逻辑原样保留。
- 🧹 **清理**：移除死代码 `is-active-by-io / is-active-by-click` 相关 JS（CSS 同名选择器留作无害冗余，不影响）。

---

## v1.10.12_260821 — nav 五胶囊与新闻模块左对齐

**类型**：修订 +1（视觉对齐修复）
**日期**：2026-08-21

- 📐 **nav 五分类胶囊左对齐新闻模块**：`.nav-inner` 此前全宽仅加 `padding:10px 28px`，宽屏（>1280px）下与居中容器 `.wrap(max-width:1280px; margin:0 auto)` 的内容左边缘错位一个 `(100vw-1280)/2` 偏移；现给 `.nav-inner` 加 `max-width:1280px; margin:0 auto`（背景 `.nav` 仍全宽，吸顶遮罩不变），导航内容与新闻模块同网格，胶囊左边缘 / 三工具胶囊右边缘均严格对齐模块两侧；移动端 padding 同步 `.wrap` 的 `20px`。

---

## v1.10.11_260821 — hero-lead 两行右对齐 + nav 点击永久锁定高亮

**类型**：修订 +1（视觉优化 + 交互修复）
**日期**：2026-08-21

- 🔨 **hero-lead 引用段两行 + 右对齐**：在「以下」前插入 `<br>` 断为两行；去掉 `.hero-grid` 的 `max-width:1024px`，hero 与新闻模块同处 `.wrap` 内容宽度，引用段右端自然对齐新闻模块右端。
- 😐 **nav 点击永久锁定高亮**：修复 v1.10.6 起 `.is-active-by-click` 在 CSS 中漏写高亮规则、且 IO 在 800ms 后强行 `remove` 导致点击高亮永远不可见；改为引入 `lockedIdx` 锁（点过任意胶囊后 IO 完全让位，永久保持高亮直到下次点击）+ clickGuard 800→1500ms + IO rootMargin `-80px→-50px` 匹配 nav 贴顶新位置。

---

## v1.10.10_260821 — 导航与报告胶囊合并单行 + nav 置顶渐显金边

**类型**：修订 +1（视觉优化）
**日期**：2026-08-21

- 🧭 **nav 与报告胶囊合并一行**：首页「报告 / 历史日报 / 导出」三胶囊从独立 topbar 移回导航条 `nav-actions`，与 5 个分类胶囊同一行右对齐；首页 topbar 隐藏，导航吸顶到页面最顶（safe-area）。
- 🟡 **置顶渐显金边**：`nav.is-stuck` 状态保留 `border-bottom` 由透明过渡到淡金 `rgba(131,126,101,0.55)`，滚动置顶时 0.25s 渐显，作视觉分割（hero 底边金线已在 v1.10.9 移除，不再冲突）。
- 📱 **移动端**：延续 v1.10.7 行为，三胶囊位于导航横滑条右端，不与分类挤压。

---

## v1.10.9_260821 — 报告三胶囊回整页右上角 topbar；hero 去底边金线

**类型**：修订 +1（视觉优化）
**日期**：2026-08-21

- 🧭 **报告三胶囊回 topbar**：「报告 / 历史日报 / 导出」三胶囊从 nav 内移回独立 topbar（整页右上角第二行），nav 收回纯 5 分类胶囊。
- 🟡 **hero 去底边金线**：移除 hero 底部金线，仅保留 `nav.is-stuck` 置顶后出现的金边，避免两条金线视觉打架。
- 🔨 **hero-lead 自然排布**：去掉 `max-width` 限制，引用段自然拍一行，窗口缩小时再收起，位置不够时 info-col 自然下移到日期下方（与移动端一致）。

---

## v1.10.8_260821 — hero 三件间距 + 信息块右移

**类型**：修订 +1（视觉优化）
**日期**：2026-08-21

- 🟢 **顶距压缩**：`.hero` 内边距 `56px 0 40px → 24px 0 40px`，ticker bar 紧贴顶栏。
- 🟢 **logo 底距压缩**：`.brand-logo` 内边距与下边距小幅压缩，airplain 贴近「深南AI日报」标题。
- 🔵 **Web 端信息块右移**：hero 拆分为日期列 + 信息列两列（`gap:200px`），信息块移到日期右侧并视觉上下对齐；移动端恢复上下堆叠。

---

## v1.10.7_260821 — nav z-index 防遮挡 + 三胶囊视觉统一

**类型**：修订 +1（视觉优化 + bug 修复）
**日期**：2026-08-21

- 🟡 **bug 修复**：`.nav` `z-index` 从 `50` 提到 `196`（高于 `.ticker` 的 `195`），并用不透明 `var(--ink-card)` 背景完全遮住 ticker 文字穿插。
- 🟢 **视觉统一**：右上角三胶囊底色从半透明 `--surface-float` + 描边改为实色 `#151C33` 无描边（深浅模式一致），hover/active 效果保留。

---

## v1.10.6_260821 — nav 左移对齐 + 移动端横滑 + 点击高亮 + 贴顶金线

**类型**：修订 +1（视觉优化 + 交互）
**日期**：2026-08-21

- 🟡 **nav 整体左移**：`.nav-inner` `justify-content:flex-start`，5 分类胶囊与 `.wrap` 左对齐；`.nav-actions` 从 fixed 改 static + `margin-left:auto` 推到右侧并垂直居中。
- 📱 **移动端横滑**：≤768px 时 8 胶囊 nav-inner 横滑（`overflow-x:auto + scroll-snap`），隐藏滚动条。
- 🔵 **点击高亮 + scroll-spy**：点击胶囊高亮跟随 + IntersectionObserver 联动 + 800ms click guard 抑制 IO 误触；默认无金边，nav 贴顶后加 `.is-stuck` 触发淡金线。

---

## v1.10.5_260821 — 删除首页 hero 统计大块

**类型**：修订 +1（结构精简）
**日期**：2026-08-21

- 🗑️ **删除 hero 统计块**：移除首页 hero 的 5 张统计卡 + TOTAL 大块，及相关的 CSS/HTML/移动端覆盖。
- 🧭 **hero-grid 单列化**：`.hero-grid` 改 `display:block` 单列，避免左有右空。

---

## v1.10.4_260821 — （跳号，本版本未提交记录）

> 注：git 历史中 v1.10.3 直接到 v1.10.5，无 v1.10.4 提交痕迹（本地可能跳过或未留存）。此条留痕，不虚构内容。

---

## v1.10.3_260820 — 深浅模式统一 + FAB 修复 + 清死代码

**类型**：修订 +1（视觉一致性 + bug 修复）
**日期**：2026-08-20

- 🎨 **深浅统一为仅配色不同**：删除浅色 4 处盒模型差异规则，切换主题不再 reflow 移位。
- 🐛 **FAB 主题切换修复**：原本同时绑 inline onclick + addEventListener 两个切换器，一次点击切换两次相互抵消，已删冗余绑定；图标首屏按时间判定深浅并同步。
- 🧹 **清死代码**：删除空 `DERIVED_SECTIONS` 整套派生逻辑，合并重复 `@media (hover:none)`。

---

## v1.10.2_260819 — 深色模式细节修复：ticker 无缝 + 报告胶囊防遮挡 + 统计卡描边 #313C7D

**类型**：修订 +1（细节修复）
**日期**：2026-08-19

- 🎞️ **ticker 无缝循环**：缩小 item 左右间距（`48px → 28px`），并将复制份数从 1 份增加到 3 份，确保轨道总宽始终大于常见视口，消除中间空白期。
- 🧭 **报告/历史日报/导出胶囊防遮挡**：`.nav-actions` 的 `z-index` 提升到 `210`（高于 topbar/ticker），`top` 从 `14px` 微调到 `16px`，确保胶囊不被其他元素覆盖；位置样式不区分深浅模式，保持一致。
- 📊 **深色模式统计卡描边增强**：外围边框与中间分割线改为更明显的蓝色 `#313C7D`；浅色模式仍保持柔和 `var(--line-faint)`，不受影响。

---

## v1.10.1_260819 — 浅色模式视觉重置：回退深色原样 + 仅 light-only 覆盖 + 工具按钮/留言按钮布局修复

**类型**：次版本 +1（视觉重置 / 结构优化）
**日期**：2026-08-19

- 🎨 **浅色模式视觉重做（严格限定 light）**：从 v1.9.7 深色原样分支出发，所有浅色视觉改动仅通过 `[data-theme="light"]` 覆盖，不再污染深色模式。
  - 主色金色 → 靛蓝 `#1600ff`；强调色 → 浅薰衣草 `#cdc8ff`。
  - 统计卡改为浅紫底 + 靛蓝数字。
  - 导航胶囊：去掉全宽外围白底，保留圆角玻璃胶囊条；未选中淡紫底，hover 实填浅紫，选中靛蓝底白字。
  - 新闻卡片：静态外框香槟金、序号靛蓝、「阅读原文」背景 `#F1F0FF`；hover 外框靛蓝、CTA 香槟金渐变 `#DDD090 → #817F67`。
  - 页脚：数据源链接改为灰色，文档链间距 +10px，底条改用浅紫渐变。
- 🔧 **修复导航胶囊选中 bug**：点击非首个胶囊立即切换 active 状态，IntersectionObserver 不再延迟覆盖。
- 🧭 **工具按钮回归页面右上角**：桌面端 `.nav-actions` 改为 fixed 定位，不再随 nav 滚动下移；移动端恢复为 nav-inner 横向滚动流内的最后一个元素。
- 💬 **留言按钮上移并换图标**：`bottom` 从 `14px` 改为 `42px`，与上方 FAB 组保持 10px 间距；图标替换为用户提供的 `chat-circle-dots.svg`；hover 气泡仅显示「留言 / 反馈」，去掉 emoji。
- ♻️ **清理 v1.9.8/1.9.9/1.10.0 中对深色模式的全局污染**。

---

## v1.9.7_260818 — 留言/反馈按钮：可见圆形图标 + lucide message-circle + 深浅色适配

**类型**：修订号 +1（bug 修复 / 视觉修正）
**日期**：2026-08-18

- 🐛 **修复留言按钮"透明无 icon"**：`.fab-contact` 改为与上方 FAB 一致的 40×40 圆形，图标居中，背景不透明度从 32% 提升到 50%（深色）/ 60%（浅色），并加淡淡描边，使按钮边界与图标在两种主题下都清晰可见。
- 🎨 **替换 lucide 图标**：将原来的 `message-square` 路径替换为更直观的 `message-circle`（气泡图标）。
- 💬 **保留 hover 展开交互**：鼠标悬停时仍从圆形展开为胶囊，显示 "💬 留言 / 反馈" 文字；触屏设备保持圆形图标态，点击打开留言框。

---

## v1.9.6_260818 — 移动端修复：新闻模块显示 + 导航横向滚动 + 报告胶囊 touch 适配

**类型**：修订号 +1（bug 修复）
**日期**：2026-08-18

- 🐛 **修复手机端新闻模块不显示**：`.reveal-sec` 默认 `opacity: 0` 依赖 IntersectionObserver 触发入场动画，在 iOS Safari 等移动端偶发失效导致整片空白。移动端媒体查询中强制 `.reveal-sec` 直接显示，并加 3 秒 JS 兜底。
- 📱 **导航条横向滚动**：移动端 `.nav-inner` 由换行改为 `flex-wrap: nowrap` + `overflow-x: auto`，8 个胶囊在一行内左右滑动，避免分类胶囊与工具胶囊错位/被挤到第二行。
- 👆 **报告胶囊 touch 适配**：无 hover 设备上直接显示「周报 | 月报」，不再依赖悬停变形。

---

## v1.9.5_260811 — 胶囊顶对齐：sticky nav 贴顶 + 不透明底色 + 金线分割

**类型**：修订号 +1（细节优化）
**日期**：2026-08-11

- 📌 **sticky nav 贴顶**：首页 8 个胶囊置顶后，与页面顶端距离由 `32px` 缩到 `env(safe-area-inset-top)`，桌面端直接贴顶。
- 🎨 **不透明底色遮住镂空**：`.nav` 背景改为 `var(--ink-card)`（胶囊同款底色），不再半透明显示背后内容。
- ✨ **细细金线分割**：`.nav` 下边框改为 `1px solid rgba(131, 126, 101, 0.45)`，形成轻盈的视觉分隔。
- 📐 **导航栏更紧凑**：`.nav-inner` 垂直内边距由 `14px` 缩到 `10px`。

---

## v1.9.4_260811 — 卡片收起减速：展开快、收起慢 4.5 倍，节奏分明

**类型**：修订号 +1（细节优化）
**日期**：2026-08-11

- 🐢 **收起极慢**：卡片收起（鼠标移开）过渡 `max-height` 最终调至 `1.7s` 平滑 ease-in-out，无回弹，收得极缓。
- ⚡ **展开保持轻快**：卡片展开（ hover）过渡 `.38s` 带轻微弹簧回弹，瞬间弹开。
- 🎯 **节奏比**：收起时长 ÷ 展开时长 ≈ 4.47 倍，远超「收起至少慢两倍」，快开慢收手感对比极强。

---

## v1.9.3_260811 — 8 胶囊对齐：首页导航条合并右侧工具胶囊

**类型**：修订号 +1（细节优化）
**日期**：2026-08-11

- 🧭 **8 胶囊同一行对齐**：首页将右上角「报告 / 历史日报 / 导出」3 个工具胶囊合并进 sticky 导航条右侧，与左侧「模型 / 产品 / 动态 / 研究 / 观点」5 个分类胶囊在同一 flex 容器内，下拉停靠时天然对齐。
- 🔧 **首页隐藏固定 topbar**：工具胶囊移入导航条后，首页不再显示固定 topbar；报告页保持原结构（周报/月报切换 + 返回今日）。

---

## v1.9.2_260806 — 报告胶囊 hover 切换：周报/月报 + 返回今日

**类型**：修订号 +1（功能）
**日期**：2026-08-06

- 📊 **报告按钮 hover 展开**：首页右上角「报告」胶囊 hover 时展开「周报」「月报」两个 time-chip，点击跳转对应报告页。
- 🔙 **报告页返回今日**：周报/月报页面 topbar 新增「返回今日」按钮，一键回到当日日报首页。

---

## v1.9.1_260806 — 跑马灯修复：滚动生效 + 随页面上移 + 底色调亮

**类型**：修订号 +1（bug 修复 + 细节优化）
**日期**：2026-08-06

- 🔴 **跑马灯强制滚动**：此前被 `@media (prefers-reduced-motion: reduce)` 全局 `animation: none` 屏蔽（系统/浏览器开启"减少动态"时静态）。现 ticker 动画覆盖该屏蔽、速度 60s→40s，无论设置都滚动。
- 📜 **随页面上移**：ticker + topbar 由 `position: fixed` 改为包进正常流 `<header class="site-header">`，整体随页面滚动离场；nav 改为 `sticky; top:0`，头部滚走后分类栏吸顶。
- 🎨 **底色调亮**：ticker/topbar 背景 `#161A2E → #1F2647`（浅色 `#ECE5D2 → #F2ECDD`），形成连续头部带。
- 🧹 **移动端留白清理**：移除 ticker `margin-top:48px` 与 nav 的 `padding-top:78px` 旧覆盖，避免头部改正常流后留空档；自动隐藏 JS 不再动 topbar。

## v1.9.0_260730 — 架构重构：瘦身 + 字体合规 + 卡片重做 + 部署自洽

**类型**：次版本 +1（架构重构 + 视觉定稿）
**日期**：2026-07-30

- 📦 **产物统一到 releases/**：生成器输出从 `dist/` 迁移到 `releases/`，根目录 `index.html` 壳 refresh 跳转到 `releases/index.html`，双击即预览最新。
- 🪶 **字体合规瘦身**：删除不可 web 嵌入的 SmileySans / MiSans；改用 OFL 可嵌入的 ZCOOL XiaoWei + Space Grotesk。SN_EXPORT 抽离为独立 `exports.js`（全页共享），单页 HTML 从 900KB 降至 119KB（-88%）。
- 🃏 **卡片视觉重建**：金边描边 + 微抬；hover 仅向下展开（解除 line-clamp 显示全文），同列下方卡片跟随下移，**严禁向上延伸**；所有卡片同高对齐。
- 📰 **跑马灯**：恢复顶部 marquee 滚动并跟随页面上移；「深南Ai视界」品牌色改为 `#837E65`。
- 🗂️ **分类精简为 5 类**：模型 | 产品 | 动态 | 研究 | 观点（合并旧多级分类）。
- 🐛 **修复底部 JS 源码裸奔**：SN_EXPORT 抽离时漏写 `<script>` 开标签导致中间脚本被当文本渲染，已补回。
- 🚀 **部署自洽**：`deploy.yml` 的 `publish_dir` 由 `./dist` 改为 `./releases`；生成器每次运行把 `dist/fonts/` 复制到 `releases/fonts/`，并把 `.nojekyll` / `robots.txt` 写入 `releases/`，发布目录完全自包含。

## v1.8.7_260729 — 「留言/反馈」FAB 化：从 footer 移到右下悬浮

**类型**：修订号 +1（交互重构）
**日期**：2026-07-29

- 💬 **「留言/反馈」从 footer 提到右下 FAB 区**：之前 footer 里有独立「💬 留言 / 反馈」pill 按钮。现在升级成与 FAB 同风格的悬浮按钮 `fab-contact`，定位在现有 FAB group 下方约 38px 处（≈ 1 个 icon 高度）。
- 🎯 **hover 展开交互**：默认只显示聊天气泡 icon（40px 圆）；hover 时宽度从 40px 过渡到 168px（`.35s cubic-bezier(.34,1.2,.64,1)`），同步淡入「💬 留言 / 反馈」文字（`.25s` 延迟 `.08s`）+ 边框淡入 + 填色。点击 → 打开 GitHub Issue 留言弹窗（与 footer 按钮同源）。
- 🛡️ **inline onclick 兜底**：用 `onclick="window.snOpenContact()"`，定义在早期 head 脚本里。DOMContentLoaded 与 getElementById 出问题也不影响。
- 🧹 **删除 footer 那条 button**：避免两处入口造成混淆。

## v1.8.6_260729 — Ticker 恢复 marquee + 移至顶部 + 紧凑 + 深色品牌

**类型**：修订号 +1（视觉布局修复）
**日期**：2026-07-29

- 📰 **Ticker 移到顶部 topbar 之上**（最高层）：用户希望 ticker 显示在「报告/历史日报/导出」上方。`ticker` 改为 `position: fixed; top: 0`；`topbar` 改为 `top: calc(... + 32px)` 紧贴 ticker 下方；`nav` 改为 `top: calc(... + 78px)` 紧贴 topbar 下方。三个层从上到下叠：ticker → topbar → nav。
- ▶️ **Ticker 重新启用右→左匀速滚动**：删除静态三段式，恢复 marquee 动画（`translateX(0)` → `translateX(-50%)`，60s 线性循环）。HTML 复制一份做无缝循环；hover/focus-within 时暂停。
- 📏 **整体窄一点**：ticker 高度从 `14px + 14px padding` 收到 `8px + 8px = 32px`，字号 `12px → 11px`，letter-spacing `0.08em → 0.06em`。
- 🟤 **「深南Ai视界」颜色更深**：`.ticker-brand` 从 `var(--brand-brief)` (`#DDD090` / `#A87E2A`) 改为 `#8B6914`（暗金，v1.8.6 深色）/ `#6E5418`（暗琥珀，浅色）。

## v1.8.5_260729 — 分类 pill 与 topbar 错开

**类型**：修订号 +1（视觉布局修复）
**日期**：2026-07-29

- 📐 **桌面端 nav-inner 右侧预留 380px**：`.topbar`（报告/历史日报/导出）固定在右上角，之前 `.nav-inner` 全宽导致分类 pill 延伸进 topbar 下方重叠。给 nav-inner 加 `padding-right: 380px`，让 pill 在到达 topbar 之前就换行（`flex-wrap: wrap` 已开启）。**移动端（max-width: 880px）的媒体查询已覆盖 padding-right 回 20px**，不影响移动布局。

## v1.8.4_260729 — FAB 终极兜底：inline onclick + 太阳↔月亮图标切换

**类型**：修订号 +1（修 bug + 视觉反馈）
**日期**：2026-07-29

- 🔧 **FAB 终极兜底**：把三个按钮的 click 监听从 JS `addEventListener` 改成 HTML `onclick` 属性 + 全局函数 `window.snToggleTheme()` / `window.scrollTo(...)`。这样即使 `DOMContentLoaded` 没触发、`getElementById` 拿 null、或者后续 JS 抛错，按钮**也必定响应**——inline `onclick` 由浏览器原生求值。
- 🌗 **太阳↔月亮图标切换**：之前一直显示太阳图标，点击无视觉反馈让用户以为没生效。现在 `snToggleTheme` 切完主题后**同步替换 FAB 图标**——深色模式显示太阳（点 → 浅色），浅色模式显示月亮（点 → 深色）。title/aria-label 也同步更新。点了**立刻能看到**图标在太阳↔月亮之间切。

## v1.8.3_260729 — 卡片 hover 金边改为顶部一条线

**类型**：修订号 +1（视觉细节）
**日期**：2026-07-29

- ✨ **卡片 hover 金边改为顶部一条线**：之前是 `box-shadow: 0 0 0 2px` 把卡片整个包了一圈金圈；现在改成 `box-shadow: inset 0 2px 0 0 var(--card-edge-hover)`，只在卡片顶部出现一条 2px 金线作为 hover 高亮，保留柔和的下投阴影。视觉更克制、更现代。

## v1.8.2_260729 — 修 FAB 失效 bug + UTC 时区 bug + 箭头放大 + 卡片高度封顶

**类型**：修订号 +1（修 bug + 视觉细化）
**日期**：2026-07-29

- 🔧 **修 FAB 完全失效 bug**：之前的渲染里 `<div class="fab-group">` 在主 `<script>` 之后，脚本执行时 DOM 还没解析到 FAB，`getElementById('themeToggle' / 'scrollTop' / 'scrollBottom')` 全部返回 null，三个按钮的点击监听器**根本没挂上**——所以用户多次反馈「点了没反应」是真 bug，不是视觉问题。把脚本包进 `DOMContentLoaded` 后修复。
- 🕒 **修 UTC 时区 bug**：早期 head 脚本 `const h = getUTCHours() + 8` 没取模，UTC 22:00–23:59（北京次日 06:00–07:59，早报时段）会被错误判定为 night → 错误走暗色。改为 `(getUTCHours() + 8) % 24`。
- ➡️ **「阅读原文」箭头放大 50%**：`.card-cta .arrow` 从继承 12px → 18px（+50%），并加 `font-weight: 500`；hover 时仍是 `translateX(4px)`。
- 📏 **卡片展开高度封顶**：从 `max-height: 640px` 收到 `540px`，并显式加 `align-self: start`，避免被网格拉伸导致顶部视觉上移。

## v1.8.1_260729 — 浅色模式重设计 + ticker 静态化 + 卡片节奏

**类型**：修订号 +1（视觉/交互修复 + 浅色模式重设计）
**日期**：2026-07-29

- 🌅 **浅色模式重设计**：修复了长期 bug（CSS 里有自引用变量 `--text-title: var(--text-title)`，导致 `--ink-card`、`--text-primary` 等语义色从未初始化；浅色模式因此变成「深色卡片 + 深色文字」不可读）。新增完整语义变量层。重做浅色为独立「晨光读报」配色——暖米白纸张 `#F5F1E6`、暖墨 `#2A2520`、暖金 `#A87E2A`，而不是暗色反转。卡片边线/阴影也按主题重定义。
- 📰 **Ticker 静态化**：移除跑马灯滚动动画，改为居中三段式（数据来源 / 公众号 / 站点说明），间隔 `2.6rem`，深色模式底色 `#161A2E`、浅色 `#ECE5D2`。
- 🪟 **主题按钮去默认外框**：`.fab` 默认无边框，仅磨砂 `blur(14px) saturate(140%)`；hover 时边框淡入 + 填色 `rgba(79,92,199,0.28)`，过渡 `.35s cubic-bezier(.4,0,.2,1)`，保持磨砂感。
- 🃏 **卡片 hover 节奏**：移除 `translateY(-3px)`（只允许向下展开）；展开用 `.55s cubic-bezier(.34,1.5,.64,1)`（轻微回弹）、收回用 `1.1s cubic-bezier(.65,0,.35,1)`（慢节奏），两个不同步营造节奏变化。

## v1.8.0_260729 — 字体合规全面切换 SIL OFL + 开源合规收尾

**类型**：次版本 +1（合规 + 字体替换）
**日期**：2026-07-29

- 🔤 **字体全面替换为 SIL OFL**：原 SmileySans / MiSans VF / Neue Regrade 的授权条款**禁止子集化（二改）**，与「外链 woff2」工程要求冲突，已于本版全部替换。新方案：中文标题/卡片标题 **ZCOOL XiaoWei**、英文/大数字 **Space Grotesk**（可变 300–700）、英文正文 **Poppins**；中文正文走系统 CJK 回退栈（PingFang SC / 微软雅黑等，不嵌入）。`build_fonts_css.py` 的 `FONTS` 列表与 `generate_dashboard.py` 的全部 `font-family` 引用同步更新。
- 💬 **开源联系入口（GitHub Issue 留言）**：新增「💬 留言 / 反馈」按钮 + 弹窗（含 honeypot 垃圾过滤），提交时带 `labels=feedback` 预填标题/正文，跳转 `issues/new` 由 GitHub 登录天然拦截垃圾。无需暴露真实邮箱。
- 🤖 **robots.txt**：站点根加入 `User-agent: * / Allow: /`（GitHub Pages 子路径下站点整体允许收录）。
- 🧹 **清理**：移除 `dist/fonts/` 下 5 个已废弃的旧 woff2；强制重建 `dist/daily/*.html`（旧页因 skip-existing 逻辑残留旧字体）；删除 `dist/` 下过期的 v1.4.0 版本化归档（无内部链接，避免随部署发出破损字体回退）。

## v1.7.0_260728 — 卡片还原 v1.3.0 样式 + 早中晚隐藏 + 本地版本归档

**类型**：次版本 +1（样式回归 + 模块隐藏 + 工程流程）
**日期**：2026-07-28

- 🃏 **新闻卡片还原为 v1.3.0 样式**：整卡 `<a>` 链接（点击直达原文），初始蓝框 `rgba(74,91,196,0.5)`；hover 展开 + 金边 + 微抬 `translateY(-3px)`；移除 v1.6.0 的点击展开 `<div>` 方案与 `.card.expanded` 逻辑。首页与报告页共用 `render_card`，一并生效。
- 🙈 **早中晚时段模块暂隐藏**：用 `.period-group:not(.report-range){display:none}` 隐藏「日报时段」胶囊；HTML/JS/period 逻辑全部保留，后续删一行即可恢复。报告页「周报/月报」切换不受影响。
- 🗂️ **本地版本归档 `releases/`**：每版构建后把 `dist/ai-daily-vX.Y.Z_YYMMDD.html` 复制入库（`.gitignore` 已放行），作为本地验证与历史追溯。已收录 v1.3.0（用户提供）/ v1.5.0 / v1.6.0 / v1.7.0；缺失的早期版本（v1.0–v1.4.0）由用户补入。
- 🚦 **本地验证门禁**：AGENTS.md 写入「先本地构建校验 `dist/index.html`，确认无误再 `git push`」。

## v1.6.0_260728 — 聚合报告页、UI 打磨与卡片交互重构

**类型**：次版本 +1（新增独立报告页 + 多项 UI/UX 优化）
**日期**：2026-07-28

- 📊 **新增站内聚合报告页**：
  - `dist/report-week.html`（近一周周报）、`dist/report-month.html`（近一月月报），`dist/report.html` 默认跳转周报。
  - 复用 `aggregate_info()` 数据层，按版块汇总、全局连续编号，移除早中晚 UI，新增「周报 / 月报」胶囊切换。
  - 入口：顶栏新增「报告」下拉；页脚 docs 新增「聚合报告」链接。
- 🔝 **数据源滚动条置顶**：从页脚上方移至顶栏下方，恢复并加粗公众号「深南Ai视界」名称；动画速度从 24s 放慢至 48s。
- 🎛️ **顶栏早中晚胶囊放大对齐**：胶囊高度与「历史日报 / 导出」按钮对齐，字号与圆角放大，在视觉上保持同一水平线。
- 📰 **新闻卡片交互重构**：
  - 初始状态无外框（border transparent）。
  - 点击卡片主体切换展开/收起（不再依赖 hover），展开时仅向下延展、不再向上位移。
  - 「阅读原文」作为独立链接，点击仍跳转原文。
- 🦶 **页脚修复**：
  - 恢复底部 docs 黑/深蓝渐变底条。
  - LICENSE 等链接间距从 20px 加大至 40px。
  - 金色分割线缩短，与上方新闻模块左右对齐（max-width: 1224px，宽度 calc(100% - 56px)）。

---

## v1.5.0_260728 — 分类多元化（具身 / 大会 关键词派生桶）

**类型**：次版本 +1（分类体系扩展，向下兼容）
**日期**：2026-07-28

- 🗂️ **分类多元化（关键词派生桶）**：在 AIHOT 固定 5 桶之后，新增由 `generate_dashboard.py` 扫描 item 标题/摘要做关键词匹配提升出的**合成桶**——
  - **具身·智能前沿**（关键词：具身 / 机器人 / 人形 / humanoid / robotics / 机械臂 / 灵巧手 / 宇树 / 智元 / optimus / 波士顿 / 四足 等）；
  - **大会·发布与峰会**（关键词：大会 / 峰会 / 论坛 / WAIC / 世界人工智能大会 / 发布会 / GTC / CES / 开发者大会 等）。
  - 命中规则的 item **从原 AIHOT 桶移出**（去重、计数诚实，不重复计），归入首个命中的派生桶；当日无命中则不显示（灵活增减/变换）。
  - 红线 #2 严守：不改 AIHOT 原始 label 桶，仅新增派生桶。
- 🚫 **剔除 KOL / 公众号内容维度**：按决策不做 KOL 分类、不把公众号作为内容源/分类；公众号仅作为 AIHOT 已聚合 item 的来源署名出现（属索引数据，非本站 framing）。
- 📡 **数据源滚动条去公众号化**：由「AIHOT · … · 更多 AI 内容请关注公众号」改为「AIHOT (aihot.virxact.com) · 本站为个人非盈利 AI 资讯索引」，不再把公众号列为数据来源。
- ⚠️ **早中晚仍为视觉壳**：实测 `/api/public/daily` item 无时间戳、`/all` 为前端页非 API，真·时段增量仍需第二数据源（用户决策：先不做）。
- 📝 **文档同步（吸收未 push 的 3649371 文档修正）**：AGENTS.md 补「本地环境注意」（curl/schannel SSL exit 35 为本地代理所致，非部署问题；managed venv python 在 Git Bash 下需绝对路径）；ARCHITECTURE.md 补派生桶说明；状态更新至 v1.5.0。

---

## v1.4.0_260728 — 早中晚时段、浅色模式、悬浮按钮与数据源滚动条

**类型**：次版本 +1（时段体系、深浅模式、快捷操作、站点说明）
**日期**：2026-07-28

- 🌗 **早 / 中 / 晚 三段时段体系**（UI + 自动检测）：
  - 按北京时间自动判断当前时段：早 06–12 / 中 12–18 / 晚 18–06。
  - 顶栏「早中晚」改为胶囊分段开关样式，当前时段高亮，未来时段自动熄灭并禁用，hover 提示更新时间（早报 08:10 / 午报 12:30 / 晚报 18:30）。
  - 用户可点击已发布时段切换视觉主题；页面每分钟自动检测，若跨时段/跨日期则自动刷新以获取新数据。
- ☀️ **浅色模式上线**：
  - 早报 / 午报默认使用浅色主题，晚报默认深色主题；提供完整 CSS 变量映射与语义化文字/表面色。
  - 新增右侧悬浮「主题切换」按钮，用户可手动覆盖并记忆到 `localStorage`。
- 🎚️ **右侧悬浮快捷按钮**：主题切换、回到顶部、回到底部，hover 高亮 + 微上浮 + 底色块。
- 📡 **页脚上方数据源滚动条**：「📡 数据来源：AIHOT · 本站为个人非盈利索引 · 更多 AI 内容请关注公众号「深南Ai视界」」。
- 🎨 **视觉入口继续打磨**：
  - 「深南AI日报」上移至「Daily AI Brief」上方；
  - 早中晚标签改为与「历史日报」同款的圆角矩形外框 + 内圆高亮；
  - 分类导航恢复自动换行，解决窄屏与顶栏标签组重叠；
  - 隐藏后的顶栏/导航支持鼠标悬停临时显示。
- ⏰ **GitHub Actions 定时部署**：新增 cron `10 0,4,10 * * *`（UTC），对应北京时间 08:10 / 12:30 / 18:30 自动拉取 AIHOT 并部署。
- 📤 **导出增强**：导出下拉新增「今天 / 近一周 / 近一月」范围选择，再选格式（PNG/HTML/Markdown/CSV/PDF）；周报/月报数据由生成器聚合最近 7 / 30 天日报，CSV 增加「日期」列。
- 📱 **移动端顶栏/导航重叠修复**：移动端 `.nav` 增加 52px 顶部内边距，导航 chips 改为浮动胶囊条，避免与顶栏「早中晚 / 历史日报 / 导出」标签组重叠。
- ⚠️ **数据说明**：AIHOT `/api/public/daily` 每天仅提供一次数据窗口（北京时间前一天 08:00 – 当天 08:00）。因此当前「午报 / 晚报」与「早报」共用同一份数据；时段切换主要影响主题、标签状态与归档策略（历史日报页面即「晚报」归档）。如需真正的 12:30 / 18:30 增量数据，需引入第二数据源。

---

## v1.3.0_260727 — 移动端适配 + 站内文档子页 + 自动部署

**类型**：次版本 +1（多端适配 + 站内子页 + CI/CD，均向下兼容）
**日期**：2026-07-27

- 📱 **移动端全面适配**：
  - 顶栏「历史日报 / 导出」按钮整体缩小约 1/3（padding / 字号 / 图标），更精致；
  - 分类导航改为**横向滚动**，不再换行与顶栏按钮重叠（"页眉滚动条"落地）；
  - 触屏设备（`hover: none`）新闻卡片**默认全部展开**，解决"必须点原文才展开"的尴尬，与桌面 hover 展开互不冲突；
  - 底部文档链排（LICENSE / 免责声明 / 关于项目 / 仓库）**保持一排、不折行**，窄屏可横向滚动且字号自适应缩小；
  - 滚动时顶栏与导航**自动隐藏**（向下滑隐藏、向上滑恢复），释放阅读空间，且巧妙避开刘海遮挡。
- 📄 **站内文档子页面**（更正式、可分享）：新增 `license.html` / `disclaimer.html` / `about.html`，页脚对应链接改为站内跳转；「仓库地址」仍指向 GitHub 仓库。
- 🔤 **字体跨设备兜底**：中文字体栈补充 `PingFang SC / Microsoft YaHei / Hiragino Sans GB / Noto Sans CJK SC` 系统回退，字体加载失败时仍保持气质一致。
- 🖼️ **页脚黑渐变条左右拉通**：文档区移出 `.wrap` 约束，渐变底条与 License 一排实现全宽铺满。
- ⚙️ **GitHub Actions 自动部署**：推送 `main` 即自动重新生成并部署 `gh-pages`，无需手动推送；静态字体/logo 入库以支持 CI 构建。
- ⚠️ **数据说明**：坚持 AIHOT 单源（用户决策 A），每日条数随上游浮动（通常 6–20 条），定位为"精选日报"而非硬凑 60 条。

---

## v1.2.0_260727 — 历史日报 + 多格式导出 + 视觉收口

**类型**：次版本 +1（新增向下兼容功能：历史浏览、导出；外加多项视觉收口）
**日期**：2026-07-27

- 🔵 **Logo 换新**：改用 `SN_logo-2.png`（625×626 透明底品牌资产），`build_logo.py` 按比例缩放至 ≤256px，网页内联 base64 + `object-fit: contain` 保持原比例，不再裂图/拉伸。
- 🔵 **副标题破折号改为双字符横线**：`——` 统一为两个字符宽的短横线样式，去除 flex 断裂感。
- 🟢 **金色分割线拉长并自适应对齐**：`.footer-line-bold` 由 `max-width:70%` 改为 `100%`，无论上方新闻模块在拉伸时呈现 1 列还是多列，金色分割线始终与模块等宽对齐。
- 🔴 **早 | 中 | 晚 改为代码块样式 + 北京时间高亮**：字号 −2px、字重 −1 级，`<code>` 包裹；按运行时「北京时间」自动高亮当前时段（早 05–11 / 中 11–18 / 晚 18–05）。
- 🟢 **历史日报浏览器**：生成 `dist/daily/YYYY-MM-DD.html`（最近 30 天），右上角「历史日报」下拉切换；`cleanup_old_archives(keep_days=30)` 自动删除 30 天前的归档。
- 🟢 **多格式导出**：右上角「导出」下拉，支持当前整页导出为 **PNG / HTML / Markdown / CSV / PDF**（PNG/PDF 走 html2canvas + html2pdf.js CDN，文本格式走 Blob 下载；预生成 `window.SN_EXPORT`）。
- 🟢 **GitHub Pages 主线部署落地**：`main` 分支仅放源码与文档（`.gitignore` 排除 `dist/`、`archive/`、`.workbuddy/`）；站点产物以 `gh-pages` 分支发布。针对 GitHub Pages 子路径 `/shennan-ai-daily/`，生成器为 `daily/` 嵌套页面注入 `../fonts/` 资源前缀，确保字体在任意深度页面正确加载、不 404。
- 🟢 **页脚「仓库地址 / LICENSE / 免责声明 / README」指向 `main` 分支**，随仓库上线不再 404。

> 注：v1.2.0 函数化重构了 `generate_dashboard.py`（`render_html` / `parse_data` / `load_daily` / `load_history_dates` / `export_markdown` / `export_csv` 等），并补充 `ICON_SCALE / ICON_ALERT / ICON_GITHUB / ICON_README` 内联 SVG。

## v1.1.3_260725 — Logo 内联化 + 页脚黑色渐变底条

**类型**：修订号 +1（bug 修复 / 细节优化）
**日期**：2026-07-25

- 🔴 **彻底解决 logo 裂图**：将 `dist/logo.png` 内联为 `data:image/png;base64` URI，不再依赖任何相对路径/托管环境加载外部图片，裂图问题不再出现。
- 🔴 **logo 显示适配**：为 `.sn-logo` 增加 `object-fit: contain`，防止非正方形 logo 素材在 44×44 容器内被拉伸变形。
- 🟢 **页脚文档导航区改为黑色渐变底条**：以蓝色框区域为范围，背景从 `#000000` 渐变到页面主色 `#0A0E1A`（--ink-void），与网页深蓝底色自然衔接。
- 🟢 **文档链接十字居中**：`footer-bottom` 使用 `display: flex; justify-content: center; align-items: center;`，LICENSE / 免责声明 / 仓库地址 / README 在黑色区域内同时水平、垂直居中。
- 🟢 **移动端适配**：小屏下渐变条 padding 缩小、链接间距与字号同步下调。

**类型**：修订号 +1（细节优化 / bug 修复）
**日期**：2026-07-25

- 🔴 **修复 logo 裂图**：之前 `dist/logo.png` 从 T 盘品牌资产生成，但在 CloudStudio 预览中显示为裂图（加载失败）。改为直接读取项目根目录的 `SN_logo.png` 作为构建源，重新生成后正常显示。
- 🟢 **页脚 Copyright 与文档链接间距改为 50px**（`.footer-copyright { margin-bottom: 50px }`）。
- 🟢 **文档链接（LICENSE / 免责声明 / 仓库地址 / README）加 inline icon**：
  - LICENSE：天平（scale）
  - 免责声明：警告圆圈（alert-circle）
  - 仓库地址：GitHub logo
  - README：打开的书（book-open）
- 🟢 **文档链接字体提亮一级**：从 `--brand-cn`（`#cdc8ff`）提到 `#E3E1FF`。
- 🟢 **全局文档删除钉钉相关内容**：README / AGENTS / ARCHITECTURE / PRD / archive/README 中移除钉钉推送、连接器、凭据隔离等描述；历史仅在 CHANGELOG 保留。

## v1.1.1_260725 — Logo 真实化 + 页脚再整理

**类型**：修订号 +1（细节优化 / bug 修复）
**日期**：2026-07-25

- 🔴 **修复 logo 显示错误**：之前内嵌的 SVG 是一个临时黑标占位图，颜色与真实品牌资产不符，导致「logo 搞黑了」。现改用你提供的真实品牌 PNG（`04-标准图形.png`），透明底 + 渐变光束/镂空边缘，在深色页面上正确显示。
- 🔴 **保护矢量源文件**：不再在仓库或部署产物中保留 `SN_logo.svg`，仅发布压缩后的位图 `dist/logo.png`。
- 🟢 **页脚按绿色序号重排**：
  1. 本期共 N 条 · M 个版块 · 日期
  2. 数据源：aihot.virxact.com · AI HOT 日报
  3. 3px 金色分割线
  4. Designed by Jaysn
  5. Copyright © 2026 深南Ai视界·All Rights Reserved
- 🟢 **删除页脚大段免责声明文字**：因为已有「免责声明」独立链接指向 `DISCLAIMER.md`，正文重复展示意义不大，且会让页脚过重。

## v1.1.0_260725 — 品牌/页脚结构修复

**类型**：次版本 +1（页脚新增文档导航块，属向下兼容的新内容功能）
**日期**：2026-07-25

- 🔴 **修复 logo 不可见根因**：内联 SVG 的 `<style>` 因 f-string 注入后不再二次展开，双花括号 `{{` 原样输出导致 CSS 失效、所有图形回退为默认黑色 → 在深色页面上「空」。改为单花括号，logo 正常显示为黑标浅底徽章。
- 🟢 去掉 hero 的 **ShenNan 深南AI日报** 字标（仅保留 logo 图标）。
- 🟢 副标题破折号改为连写 `—— 深南AI日报 早 | 中 | 晚 ——`（去掉 flex 间距造成的断裂感），「早 | 中 | 晚」改用 **MiSans Light**（font-weight 300）。
- 🟢 页脚重构（按《关于云部署》合规要求）：
  - `Designed by Jaysn` 下方新增 **Copyright © 2026 深南Ai视界·All Rights Reserved**
  - 新增文档导航块：**LICENSE / 免责声明 / 仓库地址 / README**（指向 GitHub 仓库）
  - 免责声明正文保留并继续完善
- 🟢 新增仓库根文件 `LICENSE`（MIT + 内容不授权说明）、`DISCLAIMER.md`（独立免责声明文档）

> 注：原 v1.0.1 的 logo 修复因同一双花括号 bug 实际未生效，本次 v1.1.0 方彻底解决。

## v1.0.1_260725 — 品牌视觉微调（logo 修复未生效，被 v1.1.0 覆盖）

**类型**：修订号 +1（细节优化）
**日期**：2026-07-25

- 🟢 logo 改为黑标浅底，确保在深色页面上清晰可见；继续以内联 SVG 嵌入
- 🟢 字标由 **ShenNan AI** 简化为 **ShenNan**
- 🟢 副标题改为 **—— 深南AI日报   早 | 中 | 晚 ——**（两个破折号一致）

## v1.0.0_260724 — 里程碑品牌首发

**类型**：主版本 +1（品牌升级 + 开源合规重写，视为正式首发）
**日期**：2026-07-24

- 🟢 左上角嵌入 `SN_logo.svg` 品牌 logo + 字标 ShenNan / 深南AI日报
- 🟢 标题改为 **Daily AI Brief**（Daily AI 白色，Brief `#DDD090`）
- 🟢 副标题改为 **深南AI日报 Daily AI**（深南AI日报 `#cdc8ff`，Daily AI 白色）
- 🟢 「生成于」→ **送达时间：**，与相邻文字严格左对齐
- 🟢 覆盖窗口说明改为左侧 `#cdc8ff` 竖线引用块，背景浅紫、文字调暗
- 🟢 「直达原文。」后加圆圈 [?] 提示，hover 显示「部分海外源链接需特殊网络环境访问」
- 🟢 未激活导航 chip 描边改为 `#cdc8ff` / 1px
- 🟢 版块系统升级：`SECTION_PRIORITY` + `SECTION_DISPLAY`，三大常客置顶，显示名品牌化
- 🟢 免责声明重写为开源 / 非盈利 / 聚合索引定位

## v0.10.2_260724 — 收起缓落 + 页脚对齐

**类型**：修订号 +1（细节优化）
**日期**：2026-07-24

- 收起速度再慢一倍：非 hover 态 transition .42s → .84s
- 页脚「本期共 …」确认置于粗分割线上方
- 免责声明「本文」→「本站」，全站自称统一

## v0.10.1_260724 — 字体外置 + 阻尼增强

**类型**：修订号 +1（细节优化）
**日期**：2026-07-24

- 🔵 字体改为独立 `.woff2` 文件 + `fonts.css` 外部引用，HTML 由 7.7MB → 39KB（不再 base64 内嵌）
- 🔵 阻尼增强：展开 `cubic-bezier(.34, 1.5, .64, 1)` .62s；收起 .42s；hover 轻微抬起 `translateY(-3px)`
- 清理失效字体源路径（改指 T 盘字体库）

## v0.10.0_260724 — Hover 推下式重构

**类型**：次版本 +1（交互范式变更，向下兼容）
**日期**：2026-07-24

- 🟡 弃用 scale 覆盖式，改为「推下式」：`align-items: start` + `max-height` 真实展开，下方同步下移、左右不动
- 🟡 弹性阻尼曲线 `cubic-bezier(.34, 1.3, .64, 1)` .55s
- 🟡 删除位置计算 JS（`pos-*`）与 hover 锁定 JS（推下式不再需要）

## v0.9.2_260724 — Hover 纯 scale 修复

**类型**：修订号 +1（bug 修复）
**日期**：2026-07-24

- 🔴 修复 hover 闪烁根因：去掉 translate 位移，改为 `transform-origin` 锚定 + 纯 `scale`
- 🔴 金边色值改为 `#837E65`、描边 2px
- 🔴 z-index 1→100 + 阴影 `0 30px 80px`

## v0.9.1_260724 — 阴影 / 金边 / 页脚

**类型**：修订号 +1（细节优化）
**日期**：2026-07-24

- hover 大面积多层深蓝阴影聚焦
- 金边 3px → 2px
- 页脚：底部空间 −100px；「本期共 …」移至粗线上方；字体统一（数字不再用 Neue Regrade）；去「日期」二字

## v0.9.0_260724 — 视觉定版 + 版本号机制

**类型**：初始稳定版（对应历史迭代 v9 里程碑）
**日期**：2026-07-24

- 视觉定版：暗色 + 群青 + 金；Hero 统计；锚点导航；响应式卡片网格
- Hover 方向扩展系统（transform-origin 拆基础类；邻居 pointer-events 锁定防抖）
- 引入语义化版本号 + `_YYMMDD` 命名规则

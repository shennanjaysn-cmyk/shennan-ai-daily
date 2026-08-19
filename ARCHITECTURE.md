# 技术架构（ARCHITECTURE）

- 版本：v1.6.0 对应
- 范围：数据流、生成流水线、字体管线、部署拓扑、已知问题

---

## 1. 系统总览

```
AIHOT API (aihot.virxact.com/api/public/daily)
        │  (urllib, UA 伪装, 404→归档回退)
        ▼
generate_dashboard.py  ── 读 fonts.css ──┐
        │  (版本号 / 版块映射 / 编号 / HTML 模板)
        ▼                                 │
releases/index.html  +  releases/ai-daily-vX.Y.Z_YYMMDD.html
        │  + releases/daily/YYYY-MM-DD.html   │
        │  + releases/report-week.html        │
        │  + releases/report-month.html       │
        │                                     │
        │  releases/fonts/*.woff2  ◄──────────┘  (外部 @font-face 引用，由 dist/fonts 复制)
        ▼
GitHub Pages  (主线部署，源 = releases/)
```

## 2. 数据层

- 接口：`GET https://aihot.virxact.com/api/public/daily`（当日）
- 回退链：404 → `/api/public/dailies?take=1` 取最新 date → `/api/public/daily/{date}`
- 返回结构：`{ date, generatedAt, windowStart, windowEnd, sections:[{label, items:[{title, summary, source, url, ...}]}] }`
- 当前固定 5 个 section label：模型发布/更新、产品发布/更新、行业动态、论文研究、技巧与观点
- 另含**关键词派生桶**（具身智能 / 大会发布会），由 `generate_dashboard.py` 扫描 item 标题/摘要做关键词匹配后提升，叠加在 5 桶之后；不改动 AIHOT 原始 label（红线 #2）。派生桶当日无命中则不显示（灵活增减/变换）。
- 关于 AIHOT v1 API：`/api/v1/items` 返回的 item 带 `publishedAt` / `discoveredAt`，支持 `window=24h/7d` 与 `category` 筛选；但本站当前仍以 `/api/public/daily`（编辑分类好的日报）为主数据源。若要实现真·早中晚增量，需切换到 v1 并自建分类/分页/增量逻辑，尚未决策。

## 3. 版块映射逻辑（`generate_dashboard.py`）

- `SECTION_PRIORITY`：三大常客 = 1/2/3，其余默认 99（按 API 顺序）
- `SECTION_DISPLAY`：原始 label → 品牌化显示名
- `SECTION_SLUG`：锚点 id
- 排序 key：`(priority, api_index)` —— 常客恒置顶，灵活槽位跟随后
- 罗马数字 `ROMAN_LIST` 按**实际排列位置**动态分配（不绑定版块名）
- `DERIVED_SECTIONS` / `classify_derived()` / `apply_derived_sections()`（v1.5.0 新增）：关键词派生桶定义与提升逻辑。命中 item 从原 AIHOT 桶**移出**（去重、计数诚实），归入首个命中的派生桶（first-match wins）；KOL / 公众号内容按决策剔除，不做第二数据源。

## 4. 生成流水线

1. 拉数据 → 2. 按 priority 排序 sections → 3. 全局连续编号（跨版块累加）→ 4. 渲染 Hero / 导航 / 各 section 卡片 → 5. 注入 `fonts.css`（外部引用）→ 6. 写 `releases/index.html` + 版本化归档 + `releases/daily/*.html` + `releases/report-week.html` / `releases/report-month.html`

`aggregate_info(date_strs)`：把多日 `info` 按版块聚合，生成周报/月报数据对象，结构与单日一致（`date_str` 为范围字符串）。

关键 CSS/JS 决策（v1.7.0 起：卡片样式回归 v1.3.0）：

- 卡片为整卡 `<a>` 链接（点击直达原文）；初始蓝框 `1.5px solid rgba(74,91,196,0.5)`，`max-height:360px` 收起。
- hover 展开：`max-height:640px` + 金边 `#837E65` 2px + 阴影 `0 30px 80px` + `transform: translateY(-3px)`（微抬）；展开 `cubic-bezier(.34,1.5,.64,1)` .62s，收起 ease .84s。
- 触屏（`@media (hover:none)`）直接全部展开（`max-height:none`），避免无 hover 无法展开。
- 早中晚「日报时段」胶囊：CSS `.period-group:not(.report-range){display:none}` 已隐藏（用户决策：增量难度大先不做），HTML/JS/period 逻辑全部保留，删此行即恢复。报告页「周报/月报」切换（`.report-range`）不受影响。
- 入场用 `transition`（**不用 `animation...both`**，否则 transform 被锁）

## 5. 字体管线（`build_fonts_css.py`）

- 源字体（OTF/TTF）→ 子集化（GB2312 + 必要拉丁）→ 压缩 WOFF2 → `dist/fonts/*.woff2`
- 生成轻量 `dist/fonts.css`（`@font-face` 外部引用，**不内嵌**）
- 依赖：`fonttools` + `brotli`，装在隔离 venv
- 已生成 3 个 woff2（v1.8.0 起全 SIL OFL）：ZCOOLXiaoWei（5.9MB CJK 子集）、SpaceGrotesk（20KB 可变）、Poppins（10KB）
- 早期 MiSansVF/SmileySans/NeueRegrade 因许可禁改，已于 v1.8.0 移除
- 效果：HTML 由内嵌期 7.7MB → 外链期 ~0.9MB（CJK woff2 外部加载，不进 HTML）

## 5b. 部署拓扑（GitHub Pages 主线 · 已执行：分支法）

- **已执行**：仓库 `main` 分支根放源码与文档；`releases/` 全部内容（含 `index.html` + `fonts/` + `fonts.css` + `daily/` + 报告页）由 `deploy.yml` 的 `publish_dir: ./releases` 推到 `gh-pages` 分支，Pages 源选 `gh-pages` / `root`。
- 站点根路径：`https://<user>.github.io/<repo>/`（如 `https://shennanjaysn-cmyk.github.io/shennan-ai-daily/`）为**子路径**。
- 子路径资源修正：`daily/` 嵌套页面（如 `.../daily/2026-07-27.html`）中的字体为相对 `url(fonts/...)`；生成器按页面层级注入资源前缀——索引页 `fonts/`、日报页 `../fonts/`——确保子路径下任意深度字体不 404。
- `main` 分支 `.gitignore` 已排除 `dist/`（字体构建源）、`archive/`、`dist-preview/`、`.workbuddy/`；`releases/` 入库（版本归档 + 部署源），站点产物在 `gh-pages`（由 `releases/` 发布）。
- CloudStudio 仅作本地预览，不进主线。

## 6. 运行态与已知问题

| 项 | 状态 | 说明 |
|---|---|---|
| 部署（主线） | ✅ live | **GitHub Pages**（gh-pages 分支），`main` 仅源码；CloudStudio 仅预览 |
| 历史日报浏览器 | ✅ done | `releases/daily/` 最近 30 天 + 下拉切换 + 30 天自动清理 |
| 多格式导出 | ✅ done | PNG / HTML / Markdown / CSV / PDF（PNG/PDF 走 CDN） |
| 分类多元化 | ✅ done (v1.5.0) | 关键词派生桶：具身智能 / 大会发布会（KOL / 公众号内容按决策剔除，不做第二数据源） |
| 聚合报告页 | ✅ done (v1.6.0) | `report-week.html` / `report-month.html`，入口在顶栏「报告」与页脚 docs |
| 合规收尾 | ❌ 未完 | 需真实联系入口 + 可选 robots.txt |

## 7. 安全与合规

- 聚合仅取标题 / 摘要(≤60字) / 链接，符合「适当引用」合理范围
- 免责声明已声明开源非盈利、商标归属、无隶属关系、链接风险自担
- 保持非盈利（不加广告 / 付费），以维持合理使用抗辩

## 8. 历史归档（已整理）

所有历史版本快照（含 8MB 内嵌字体旧版、重复 dated 文件）已移至 `archive/`（含 `archive/dist/` 镜像）。`dist/` 仅保留当前版本部署产物。

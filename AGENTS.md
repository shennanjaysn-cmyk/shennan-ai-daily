# AGENTS.md — 深南AI日报 协作规则

> 下次会话恢复上下文的入口。只写「不看到就会犯错」的边界、命令与约定，不重复 README。

## 定位

开源、非盈利的 AI 圈每日资讯聚合仪表盘。从 AIHOT 拉数据 → 生成单页 HTML → 部署至 GitHub Pages。只做索引层（标题 / 摘要 / 链接），不搬运原文。

## 怎么跑

```bash
# 字体（仅字体/字重变更时；必须用隔离 venv，含 fonttools/brotli）
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe build_fonts_css.py
# 生成（managed 版本 python，-S 不加载用户 site，纯标准库即可）
/c/Users/JDD/.workbuddy/binaries/python/versions/3.13.12/python.exe -S generate_dashboard.py
# 本地验证门禁：先本地构建 + 校验 releases/index.html（卡片为整卡<a>、早中晚已隐藏、报告页正常），确认无误再 push
/c/Users/JDD/.workbuddy/binaries/python/versions/3.13.12/python.exe -S generate_dashboard.py
# 部署：推送 main 即由 GitHub Actions 自动生成 + 部署 gh-pages
git push origin main
```

## 本地环境注意

- **curl 直连 aihot.virxact.com 会报 schannel SSL 错误（exit 35）**：这是本机代理环境所致，不是部署问题；用 `gh api` 查 Pages / Actions 状态更可靠。
- 生成器用 managed 版本 python（纯标准库，加 `-S` 不加载用户 site）：`/c/Users/JDD/.workbuddy/binaries/python/versions/3.13.12/python.exe -S generate_dashboard.py`。Git Bash 下 `~` 不展开，写绝对路径。

## 技术栈

- Python 3.13（managed）。字体子集化依赖 `fonttools`+`brotli` 装在 venv `~/.workbuddy/binaries/python/envs/default`
- 产物：单页 HTML（**外链 woff2**，不要内嵌）；字体源在 `dist/fonts/` + `dist/fonts.css`，构建时由生成器复制到 `releases/fonts/`
- 部署：**GitHub Pages**，源为 `releases/`（`publish_dir: ./releases`，`index.html` 文件名恒定保证链接稳定）；CloudStudio 仅本地预览

## 目录与约定

- `generate_dashboard.py`：唯一真相源，含 `VERSION`、`SECTION_PRIORITY`/`SECTION_DISPLAY`/`SECTION_SLUG`、数据拉取与 HTML 构建
- `build_fonts_css.py`：字体子集化 → woff2
- `build_logo.py`：从品牌主 PNG 生成压缩版 `dist/logo.png`
- `dist/`：字体构建源（`fonts.css` + `fonts/*.woff2` + `logo.png`），由 `generate_dashboard.py` 在构建时复制到 `releases/fonts/`，**本身不参与部署**；`releases/`：GitHub Pages 部署源（`publish_dir: ./releases` → `gh-pages` 分支）；`releases/daily/` 为历史日报；`releases/` 下含 `about.html` / `disclaimer.html` / `license` 等站内文档子页与 `.nojekyll` / `robots.txt`
- `.github/workflows/deploy.yml`：推送 `main` 自动生成并部署 `gh-pages`
- `archive/`：历史归档，仅回溯，不参与构建/部署

## 版本命名（强制）

改任何文件前先判定 `VERSION`（semver `vX.Y.Z` + `_YYMMDD`）：

- 只修 bug / 细节 → Z+1
- 新增向下兼容功能 → Y+1、Z 归零
- 不兼容 / 正式首发 → X+1、Y/Z 归零

## 品牌速查

- 标准主题色`#1600ff`；Brief 金 `#DDD090`；深南AI日报薰衣草 `#cdc8ff`；卡片金边 `#837E65`/2px；按钮 `#4F5CC7`；背景 `#0A0E1A`
- 字体：**全部 SIL OFL**（允许子集化+再分发）：中文标题/卡片标题 ZCOOL XiaoWei；英文+数字 Space Grotesk；英文正文 Poppins。中文正文走系统 CJK 回退栈（不嵌入）。

## 红线（不可违反）

1. **不要**把字体 base64 内嵌回 HTML（会膨胀到 7.7MB）。保持外链 woff2。
2. **不要**改动 AIHOT 的原始 label 桶（模型/产品/行业/论文/技巧），只改 `SECTION_DISPLAY` 显示名与 `SECTION_PRIORITY` 排序。
3. **不要**在 hover 用 `animation ... both`（会锁死 transform，破坏 hover 展开）。
4. **不要**改成 scale 覆盖式 hover（会闪烁 / 邻居抖动）；保持推下式 `align-items:start` + `max-height`。
5. **字体合规（硬红线）**：严禁把系统专有字体（苹方 PingFang SC、微软雅黑 Microsoft YaHei 等）或非 SIL-OFL 授权的商业/企业字体**转换并部署为 webfont**（即浏览器会下载的 woff2）。此类字体只能写进 `font-family` 栈做**本地回退**。部署上线的 webfont 必须持有"明确允许 web 嵌入/再分发"的许可证（首选 SIL OFL，如 Poppins、Noto Sans SC）。子集化（修改字体文件）同样受许可约束——小米 MiSans、Neue Regrade、SmileySans 等"开源/免费"字体需先核实其许可是否允许修改+再分发，否则建议替换为 Noto Sans SC（OFL 干净）。

## 当前状态与下一步

- 当前版本 **v1.10.11**（v1.10.10 nav 与报告三胶囊合并单行 + 置顶渐显金边；v1.10.11 hero-lead 两行右对齐 + nav 点击永久锁定高亮。更早演进见 CHANGELOG.md；本地版本归档 `releases/`）。
- 主线部署：**GitHub Pages**（源 `releases/`）。**本地验证门禁**：每次先本地 `generate_dashboard.py` 构建并校验 `releases/index.html`，确认无误再 `git push`。
- 已完成：A 视觉入口 / B 早中晚时段体系（胶囊已隐藏，逻辑保留）/ C 深浅模式+悬浮按钮（FAB inline onclick 终极兜底 + 留言/反馈 FAB 化）/ D 导出增强 / E 数据源滚动条 / 分类多元化（具身·大会 派生桶）/ F 聚合报告页（周报+月报）/ 新闻卡片整卡链接（v1.3.0 样式）/ 开源合规（GitHub Issue 留言 + robots.txt）/ 字体合规（全面切换 SIL OFL）/ 浅色模式重设计（语义色补齐+独立配色）/ ticker 移到顶部 + marquee 滚动 + 紧凑 + 深色品牌 / 卡片 hover 节奏差 + 高度封顶 / UTC 时区 bug 修复 / 阅读原文箭头放大 / 卡片金边改为顶部线 / nav 与 topbar 错开不重叠 / 留言/反馈 FAB 化与 hover 展开。
- **DOMContentLoaded 教训**：当 JS 用 `getElementById` 拿页面元素时，要么把元素放在 script 之前，要么把 JS 包进 `DOMContentLoaded`。FAB bug 是教科书反面案例。**终极兜底：关键交互按钮直接用 inline `onclick`，彻底绕开 JS 监听链**。
- 待办：① 早中晚真增量（暂搁置，模块已隐藏，依赖第二数据源或 AIHOT 分时段接口；`/api/public/daily` item 无时间戳）；② 历史版本补全（v1.0–v1.4.0 由用户放入 `release/` 后统一评估上传 GitHub）。
- 早中晚真增量：暂搁置（模块已隐藏）。依赖第二数据源或 AIHOT v1 分时段接口；当前 `/api/public/daily` item 无时间戳。详见 v1.6.0 分析。
- 版本归档 `releases/`：每版构建后生成器直接写出 `releases/ai-daily-vX.Y.Z_YYMMDD.html` 入库（`.gitignore` 已放行），作为本地验证与历史追溯；缺失的早期版本（v1.0–v1.4.0）由用户提供后补入。

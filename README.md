# 深南AI日报 · Daily AI Brief

> 开源、非盈利的 AI 圈每日资讯聚合仪表盘。每日从 [AIHOT](https://aihot.virxact.com) 拉取精选内容，生成单页 HTML，部署至 **GitHub Pages**。

---

## 1. 项目定位

把「AI 圈每天发生的大事」做成一份**可阅读、可跳源、视觉克制**的日报。聚合第三方公开资讯源，只展示标题、≤60 字摘要与原文链接，不参与内容创作、不存储原文。

- 定位：信息索引 / 聚合，非内容生产
- 性质：**开源、非盈利**
- 当前形态：单页 HTML 仪表盘，部署至 GitHub Pages
- 品牌：深南AI日报 / Daily AI Brief

## 2. 目录结构

```
.
├── generate_dashboard.py    # 主生成器（函数化：render_html / parse_data / load_daily / 导出 …）
├── build_fonts_css.py       # 字体子集化 → dist/fonts/*.woff2 + dist/fonts.css
├── build_logo.py            # 从品牌主 PNG 生成压缩版 dist/logo.png
├── dist/                    # 部署产物 = GitHub Pages 源（HTML 为构建产物 gitignored；字体/logo 入库）
│   ├── index.html           # 部署入口（最新一期，文件名恒定）
│   ├── daily/               # 历史日报（最近 30 天，YYYY-MM-DD.html）
│   ├── license.html         # 站内文档子页（LICENSE）
│   ├── disclaimer.html       # 站内文档子页（免责声明）
│   ├── about.html           # 站内文档子页（关于项目）
│   ├── .nojekyll            # 禁用 Jekyll 处理
│   ├── logo.png             # 品牌 logo 位图（透明底，base64 内联）
│   ├── fonts/               # 独立 woff2 字体（已入库，供 CI 构建）
│   └── fonts.css            # @font-face 外部引用
├── .github/workflows/deploy.yml  # 推送 main 自动生成并部署 gh-pages
├── archive/                 # 历史版本快照（gitignored，仅回溯）
├── .gitignore               # 排除 dist/*.html 等构建产物；保留字体/logo
└── README / AGENTS / ARCHITECTURE / CHANGELOG / PRD / LICENSE / DISCLAIMER.md
```

> 部署：源码在 `main` 分支；推送 `main` 后由 **GitHub Actions** 自动运行 `generate_dashboard.py` 并把 `dist/` 发布到 `gh-pages` 分支（GitHub Pages 源）。`dist/` 的 HTML 为构建产物不入库，但 `fonts/`、`logo.png`、`fonts.css` 已入库以支持 CI 构建。

## 3. 环境要求

- Python 3.13（managed runtime）
- 字体子集化依赖装在**隔离 venv**：`~/.workbuddy/binaries/python/envs/default`
  - 已装：`fonttools`、`brotli`
  - 跑字体脚本务必用该 venv 的 python，不要污染全局

## 4. 快速开始

```bash
# ① 构建字体（仅首次或字体/字重变更时）
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe build_fonts_css.py

# ② 构建 logo（当品牌主 PNG 有更新时）
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe build_logo.py

# ③ 生成仪表盘（自动拉取当日 AIHOT 数据）
~/.workbuddy/binaries/python/envs/default/Scripts/python.exe generate_dashboard.py

# ④ 部署：推送 main 即由 GitHub Actions 自动生成并发布到 gh-pages
git push origin main
#    CloudStudio 仅作本地预览，非主线部署
```

产物：

- `dist/index.html`（部署入口，文件名恒定）
- `dist/ai-daily-v{X.Y.Z}_{YYMMDD}.html` + 根目录同名归档

## 5. 版本号规则（强制）

遵循语义化版本 `vX.Y.Z`，文件名追加 `_YYMMDD` 日期后缀：

- **修订号 Z**：仅修 bug / 细节优化 → Z+1（如 v0.9.0 → v0.9.1）
- **次版本 Y**：新增向下兼容功能 → Y+1、Z 归零（如 v0.9.9 → v0.10.0）
- **主版本 X**：不兼容重大调整 / 正式首发 → X+1、Y/Z 归零（如 v0.9.x → v1.0.0）

> 每次出文件前先按此判定版本号，再改 `generate_dashboard.py` 顶部的 `VERSION`。

## 6. 品牌速查

| 用途 | 色值 |
|---|---|
| 标题 Brief 段 | `#DDD090`（金） |
| 深南AI日报 中文字标 | `#cdc8ff`（薰衣草） |
| 卡片 hover 金边 | `#837E65`，2px |
| 主背景 | `#0A0E1A`（暗） |
| 按钮 / 高亮 | `#4F5CC7` |
| 旧金（hero 装饰） | `#DAC887` |

字体角色（均为 **SIL OFL** 开源授权，允许子集化与再分发，已子集化）：

- 中文标题 / 卡片标题 display：ZCOOL XiaoWei（站酷小薇，优雅宋体感，单一 Regular 400）
- 英文 / 大数字：Space Grotesk（科技感，可变 300–700）
- 英文正文：Poppins（Regular 400）
- 中文正文 base：系统 CJK 回退栈（PingFang SC / 微软雅黑等，不嵌入）

> 早期版本用 SmileySans / MiSans VF / Neue Regrade，但其授权条款不允许子集化（二改），已于 v1.8.0 全面替换为 OFL 字体。

## 7. 已知问题与待办

> 这些是当前真实状态，不是建议。详见 `ARCHITECTURE.md` 第 6 节。

1. **分类多元化（已完成）**：v1.5.0 起通过关键词重分类新增「具身·智能前沿」「大会·发布与峰会」等派生桶。
2. **合规收尾（已完成）**：LICENSE / DISCLAIMER.md 已补齐；站点「💬 留言 / 反馈」按钮经 GitHub Issue 提交（无需暴露真实邮箱，GitHub 登录天然过滤垃圾）；已加入 `robots.txt`。

## 8. 重要安全提示

- 字体走外部 woff2，**不要**再回到 base64 内嵌（会导致 HTML 膨胀回 7.7MB）。
- 历史归档在 `archive/`，仅用于回溯，不参与构建与部署。

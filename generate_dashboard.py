# -*- coding: utf-8 -*-
"""Generate 深南AI日报 Daily AI Brief dashboard as single-file HTML pages.

Self-contained: fetches data from AIHOT API directly.
Reads fonts.css (built by build_fonts_css.py) and inlines lightweight @font-face rules.
Fonts: dist/fonts/ (built by build_fonts_css.py) is copied into releases/fonts/ each run so the published dir is self-contained (not base64 embedded).
Export data (SN_EXPORT) is extracted to exports.js (~426KB saved per page).

Outputs per run (all under releases/):
  - index.html                        (latest, entry point + shell target)
  - exports.js                        (shared export data, loaded by all pages)
  - ai-daily-vX.Y.Z_YYMMDD.html      (dated versioned archive)
  - daily/YYYY-MM-DD.html             (last 30 days of daily pages)
  - report-week.html / report-month.html / report.html
  - license.html / disclaimer.html / about.html
"""
import json
import html
import urllib.request
import urllib.error
import base64
import re
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
DIST = BASE / "dist"
DIST.mkdir(exist_ok=True)
RELEASES = BASE / "releases"
RELEASES.mkdir(exist_ok=True)
DAILY_DIR = RELEASES / "daily"
DAILY_DIR.mkdir(exist_ok=True)
FONTS_CSS = DIST / "fonts.css"  # 由 build_fonts_css.py 生成，引用 dist/fonts/*.woff2（不内嵌）

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
AIHOT_BASE = "https://aihot.virxact.com"

BEIJING = timezone(timedelta(hours=8))

# ===== 语义化版本号（vX.Y.Z）+ 日期后缀（_YYMMDD） =====
# 规则：
#   Z（修订号）= 仅修 bug / 细节优化，不新增功能时 +1（如 v0.9.0 → v0.9.1）
#   Y（次版本）= 新增向下兼容功能时 +1，Z 归零（如 v0.9.9 → v0.10.0）
#   X（主版本）= 不兼容重大架构/功能调整时 +1，Y/Z 归零（如 v0.9.15 → v1.0.0）
# v1.4.0：①视觉入口重构：破折号彻底去掉、深南AI日报左对齐、早中晚标签移到历史日报左侧并按钮化；
#         ②早/中/晚三段日报逻辑与浅色/深色模式切换；③右侧悬浮按钮（主题切换、到顶/到底）；
#         ④导出支持今天/近一周/近一月；⑤页脚上方增加数据源滚动条；⑥历史日报仅归档晚报。
# v1.3.0：①LICENSE/免责声明/README 改为站内子页面（更正式）；②字体跨设备兜底（CJK 系统字体回退栈）；
#         ③页脚黑渐变条左右拉通全宽；④移动端适配——顶部按钮缩小 1/3、分类导航横向滚动、
#         新闻卡片默认展开、底部文档链排不折行、滚动时顶栏/导航自动隐藏；⑤GitHub Actions 自动部署
# v1.2.0：①换用 SN_logo-2.png 新 logo；②副标题破折号改为两个字符宽横线；
#         ③金色分割线拉长并与内容区对齐；④早中晚改为代码块样式并高亮当前时段；
#         ⑤右上角增加最近一个月日报历史入口；⑥增加导出功能（PNG/HTML/Markdown/CSV/PDF）
VERSION = "1.9.6"

# 项目仓库地址（GitHub Pages 上线后生效；footer 的 LICENSE / 仓库地址 / README 链接依赖此值）
REPO_URL = "https://github.com/shennanjaysn-cmyk/shennan-ai-daily"

# ===== 版块优先级与显示名映射 =====
SECTION_PRIORITY = {
    "模型发布/更新": 1,
    "产品发布/更新": 2,
    "行业动态": 3,
}
SECTION_DISPLAY = {
    "模型发布/更新": "模型",
    "产品发布/更新": "产品",
    "行业动态": "动态",
    "论文研究": "研究",
    "技巧与观点": "观点",
}
SECTION_SLUG = {
    "模型发布/更新": "models",
    "产品发布/更新": "products",
    "行业动态": "industry",
    "论文研究": "papers",
    "技巧与观点": "tips",
    "具身智能": "embodied",
    "大会发布会": "conference",
}
ROMAN_LIST = ["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ", "Ⅵ", "Ⅶ", "Ⅷ", "Ⅸ", "Ⅹ"]

# ===== 关键词派生版块（精简版：合并入主分类，避免过多胶囊） =====
# 具身智能 / 大会发布 类的 item 不单独成桶，归入 AIHOT 主分类（按 AIHOT 原始 label 即可）
# 这样最终展示就是 AIHOT 的 5 大桶：模型|产品|动态|研究|观点
DERIVED_SECTIONS = []
DERIVED_LABELS = {d["label"] for d in DERIVED_SECTIONS}
DERIVED_DISPLAY = {d["label"]: d["display"] for d in DERIVED_SECTIONS}


def classify_derived(title, summary):
    """Return the first matching derived-bucket key, or None."""
    text = (title + " " + summary).lower()
    for d in DERIVED_SECTIONS:
        for kw in d["keywords"]:
            if kw.lower() in text:
                return d["key"]
    return None


def apply_derived_sections(cards_by_section, all_items):
    """Move keyword-matched items out of their AIHOT bucket into derived buckets."""
    promoted = {d["key"]: [] for d in DERIVED_SECTIONS}
    for sec in cards_by_section:
        if sec["label"] in DERIVED_LABELS:
            continue
        kept = []
        for it in sec["items"]:
            dk = it.get("derived")
            if dk and dk in promoted:
                promoted[dk].append(it)
            else:
                kept.append(it)
        sec["items"] = kept
        sec["count"] = len(kept)
    for d in DERIVED_SECTIONS:
        items = promoted[d["key"]]
        if items:
            idx = len(cards_by_section)
            cards_by_section.append({
                "label": d["label"],
                "display_label": d["display"],
                "slug": d["slug"],
                "roman": ROMAN_LIST[idx],
                "count": len(items),
                "items": items,
            })
    for e in all_items:
        if e.get("derived") and e["derived"] in DERIVED_DISPLAY:
            e["section"] = DERIVED_DISPLAY[e["derived"]]
    return cards_by_section, all_items


# ---------- helpers ----------
def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def load_daily(target_date=None):
    """Fetch a specific date briefing, or today's; fallback to latest archive on 404."""
    if target_date:
        try:
            return fetch_json(f"{AIHOT_BASE}/api/public/daily/{target_date}")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    try:
        return fetch_json(AIHOT_BASE + "/api/public/daily")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            arch = fetch_json(AIHOT_BASE + "/api/public/dailies?take=1")
            latest = arch["items"][0]["date"]
            return fetch_json(f"{AIHOT_BASE}/api/public/daily/{latest}")
        raise


def load_history_dates(take=30):
    """Return list of YYYY-MM-DD strings for the most recent `take` days."""
    try:
        data = fetch_json(f"{AIHOT_BASE}/api/public/dailies?take={take}")
        return [it["date"] for it in data.get("items", []) if it.get("date")]
    except Exception as e:
        print(f"WARNING: failed to load history dates: {e}")
        return []


def to_beijing(iso_str):
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).astimezone(BEIJING)


def fmt_full(dt):
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return f"{dt.year}年{dt.month}月{dt.day}日 {weekdays[dt.weekday()]} {dt.hour:02d}:{dt.minute:02d}"


def fmt_short(dt):
    return f"{dt.month}月{dt.day}日 {dt.hour:02d}:{dt.minute:02d}"


def time_period(hour):
    """Return (period_key, label) for Beijing hour."""
    if 6 <= hour < 12:
        return "morning", "早"
    if 12 <= hour < 18:
        return "noon", "中"
    return "night", "晚"


# ---- Footer doc-link icons (inline SVG, no external dependencies) ----
ICON_SCALE = '<svg class="doc-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 4-1.34 4-4V3"/><path d="M21 7h-2c-2 0 4-1.34 4-4V3"/></svg>'
ICON_ALERT = '<svg class="doc-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>'
ICON_GITHUB = '<svg class="doc-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.419-1.305.762-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>'
ICON_README = '<svg class="doc-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>'
ICON_REPORT = '<svg class="doc-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>'


def parse_data(data):
    """Transform raw AIHOT data into render-ready structures."""
    date_str = data["date"]
    generated_at = data["generatedAt"]
    window_start = data["windowStart"]
    window_end = data["windowEnd"]

    gen_dt = to_beijing(generated_at)
    ws_dt = to_beijing(window_start)
    we_dt = to_beijing(window_end)

    d = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    sections_by_label = {s["label"]: s for s in data["sections"]}
    ordered_sections = sorted(
        sections_by_label.values(),
        key=lambda s: (SECTION_PRIORITY.get(s["label"], 99), list(sections_by_label.keys()).index(s["label"]))
    )

    cards_by_section = []
    all_items = []  # for CSV / Markdown export
    total = 0
    for sec_idx, sec in enumerate(ordered_sections):
        label = sec["label"]
        display_label = SECTION_DISPLAY.get(label, label)
        items = []
        for idx_in_section, it in enumerate(sec["items"]):
            total += 1
            title_raw = it.get("title") or ""
            summary_raw = it.get("summary") or ""
            if len(summary_raw) > 280:
                summary_raw = summary_raw[:279] + "…"
            title_esc = html.escape(title_raw)
            summary_esc = html.escape(summary_raw)
            source_esc = html.escape(it.get("sourceName") or "来源")
            url = it.get("sourceUrl") or "#"
            dk = classify_derived(title_raw, summary_raw)
            items.append({
                "num": total,
                "title": title_esc,
                "summary": summary_esc,
                "source": source_esc,
                "url": url,
                "derived": dk,
            })
            all_items.append({
                "num": total,
                "section": display_label,
                "title": title_raw,
                "summary": summary_raw,
                "source": it.get("sourceName") or "来源",
                "url": url,
                "derived": dk,
            })
        cards_by_section.append({
            "label": label,
            "display_label": display_label,
            "slug": SECTION_SLUG[label],
            "roman": ROMAN_LIST[sec_idx],
            "count": len(items),
            "items": items,
        })

    cards_by_section, all_items = apply_derived_sections(cards_by_section, all_items)

    return {
        "date_str": date_str,
        "gen_dt": gen_dt,
        "ws_dt": ws_dt,
        "we_dt": we_dt,
        "d": d,
        "weekday": weekdays[d.weekday()],
        "cards_by_section": cards_by_section,
        "total": total,
        "all_items": all_items,
    }


def export_markdown(info):
    lines = [f"# 深南AI日报 Daily AI Brief · {info['date_str']}", ""]
    lines.append(f"**送达时间：** {fmt_full(info['gen_dt'])}  ")
    lines.append(f"**覆盖窗口：** {fmt_short(info['ws_dt'])} — {fmt_short(info['we_dt'])}（北京时间，UTC+8）  ")
    lines.append(f"**共计：** {info['total']} 条")
    lines.append("")
    for sec in info["cards_by_section"]:
        lines.append(f"## {sec['roman']} {sec['display_label']}（{sec['count']} 条）")
        lines.append("")
        for it in sec["items"]:
            lines.append(f"{it['num']}. [{it['title']}]({it['url']}) · {it['source']}")
            if it["summary"]:
                lines.append(f"   > {it['summary']}")
        lines.append("")
    lines.append("---")
    lines.append("*数据来源：aihot.virxact.com · AI HOT 日报*")
    return "\n".join(lines)


def export_csv(info):
    import csv, io
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["编号", "日期", "版块", "标题", "摘要", "来源", "链接"])
    for it in info["all_items"]:
        writer.writerow([it["num"], it.get("date", info["date_str"]), it["section"], it["title"], it["summary"], it["source"], it["url"]])
    return out.getvalue()


def aggregate_info(date_strs):
    """Aggregate multiple daily briefings into one export-ready info object."""
    sections = {}
    total = 0
    all_items = []
    gen_dt = ws_dt = we_dt = None
    d = None
    for ds in date_strs:
        try:
            data = load_daily(ds)
            info = parse_data(data)
        except Exception as e:
            print(f"WARNING: aggregate skip {ds}: {e}")
            continue
        if gen_dt is None:
            gen_dt = info["gen_dt"]
            ws_dt = info["ws_dt"]
            we_dt = info["we_dt"]
            d = info["d"]
        we_dt = info["we_dt"]
        for sec in info["cards_by_section"]:
            label = sec["label"]
            if label not in sections:
                sections[label] = {"label": label, "display_label": sec["display_label"], "items": []}
            for it in sec["items"]:
                total += 1
                item = {**it, "num": total}
                sections[label]["items"].append(item)
                all_items.append({
                    "num": total,
                    "date": ds,
                    "section": sec["display_label"],
                    "title": html.unescape(it["title"]),
                    "summary": html.unescape(it["summary"]),
                    "source": it["source"],
                    "url": it["url"],
                })
    # Preserve section priority order
    ordered = sorted(
        sections.values(),
        key=lambda s: (SECTION_PRIORITY.get(s["label"], 99), list(SECTION_PRIORITY.keys()).index(s["label"]) if s["label"] in SECTION_PRIORITY else 999)
    )
    cards_by_section = []
    for idx, sec in enumerate(ordered):
        cards_by_section.append({
            "label": sec["label"],
            "display_label": sec["display_label"],
            "slug": SECTION_SLUG[sec["label"]],
            "roman": ROMAN_LIST[idx],
            "count": len(sec["items"]),
            "items": sec["items"],
        })
    fallback = datetime.now(BEIJING)
    date_str = f"{date_strs[-1]} ~ {date_strs[0]}" if date_strs else ""
    return {
        "date_str": date_str,
        "gen_dt": gen_dt or fallback,
        "ws_dt": ws_dt or fallback,
        "we_dt": we_dt or fallback,
        "d": d or fallback,
        "weekday": "",
        "cards_by_section": cards_by_section,
        "total": total,
        "all_items": all_items,
    }


# ---------- render ----------
def render_card(it, idx):
    num = f"{it['num']:02d}"
    return f"""<a class="card" href="{it['url']}" target="_blank" rel="noopener noreferrer" style="--d:{idx % 6}">
  <div class="card-num">{num}</div>
  <div class="card-body">
    <span class="chip">{it['source']}</span>
    <h3 class="card-title">{it['title']}</h3>
    <p class="card-summary">{it['summary']}</p>
  </div>
  <div class="card-cta"><span>阅读原文</span><span class="arrow">→</span></div>
</a>"""


def render_section(sec, sec_idx):
    cards_html = "\n".join(render_card(it, i) for i, it in enumerate(sec["items"]))
    return f"""<section class="section reveal-sec" id="{sec['slug']}" style="--d:{sec_idx}">
  <div class="sec-head">
    <div class="sec-mark">{sec['roman']}</div>
    <h2 class="sec-title">{sec['display_label']}</h2>
    <div class="sec-line"></div>
    <div class="sec-count">{sec['count']}<span class="count-unit">条</span></div>
  </div>
  <div class="card-grid">
{cards_html}
  </div>
</section>"""


def render_html(info, page_info):
    """Render one complete HTML page.

    page_info keys:
      - history_prefix: relative path prefix for daily archive links
      - current_date: active date string
      - available_dates: list of date strings
      - is_index: bool, affects title / canonical path hints
    """
    fonts_css = page_info["fonts_css"]
    asset_base = page_info.get("asset_base", "")
    doc_prefix = page_info.get("doc_prefix", "")
    # GitHub Pages 部署在 /shennan-ai-daily/ 子路径下，daily 页面位于 dist/daily/，
    # 字体用相对路径 url(fonts/...)，需要按页面层级补 ../ 前缀，否则字体 404。
    fonts_css_pp = fonts_css.replace("url(fonts/", f"url({asset_base}fonts/)")
    exports_js_url = f"{asset_base}exports.js"
    logo_img = page_info["logo_img"]
    history_prefix = page_info["history_prefix"]
    current_date = info["date_str"]
    available_dates = page_info["available_dates"]

    date_str = info["date_str"]
    gen_dt = info["gen_dt"]
    ws_dt = info["ws_dt"]
    we_dt = info["we_dt"]
    d = info["d"]
    cards_by_section = info["cards_by_section"]
    total = info["total"]

    sections_html = "\n".join(render_section(s, i) for i, s in enumerate(cards_by_section))

    nav_html = "\n".join(
        f'<a class="nav-chip{(" active") if i == 0 else ""}" href="#{s["slug"]}"><span class="nav-roman">{s["roman"]}</span><span class="nav-label">{s["display_label"]}</span><span class="nav-n">{s["count"]}<span class="count-unit">条</span></span></a>'
        for i, s in enumerate(cards_by_section)
    )

    section_stats = [(s["label"], s["count"]) for s in cards_by_section]
    hero_stat_cells = "\n".join(
        f'<div class="stat-cell"><div class="stat-num">{c}</div><div class="stat-lab">{html.escape(lab)}</div></div>'
        for lab, c in section_stats
    )
    grid_cols = 2 if len(cards_by_section) % 2 == 0 else 3

    hero_mm = f"{d.month:02d}"
    hero_dd = f"{d.day:02d}"
    hero_year = d.year

    # 当前时段高亮（按钮形态，用于顶栏时段切换）
    period_key, _ = time_period(gen_dt.hour)
    period_buttons = []
    period_tip = {
        "morning": "早报：08:10 更新",
        "noon": "午报：12:30 更新",
        "night": "晚报：18:30 更新",
    }
    for key, label in [("morning", "早"), ("noon", "中"), ("night", "晚")]:
        cls = "time-chip active" if key == period_key else "time-chip"
        period_buttons.append(
            f'<button type="button" class="{cls}" data-period="{key}" aria-label="{period_tip[key]}" title="{period_tip[key]}">{label}</button>'
        )
    period_html = "\n".join(period_buttons)

    # 历史日报下拉
    history_options = []
    for ds in available_dates:
        selected = " selected" if ds == current_date else ""
        label = ds
        history_options.append(f'<a class="dropdown-item{selected}" href="{history_prefix}{ds}.html">{label}</a>')
    history_menu = "\n".join(history_options) if history_options else '<span class="dropdown-item disabled">暂无历史记录</span>'

    # 导出数据：今天 / 近一周 / 近一月（预生成 markdown / csv 嵌入 JS）
    export_scopes = page_info.get("export_scopes", {})
    scope_js_parts = []
    for key, sc in export_scopes.items():
        md = sc["markdown"].replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        csv = sc["csv"].replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        scope_js_parts.append(f'    {key}: {{ date: {json.dumps(sc["date"])}, markdown: `{md}`, csv: `{csv}` }}')
    scopes_js = ",\n".join(scope_js_parts)

    is_report = page_info.get("is_report", False)
    report_range = page_info.get("report_range", "week")
    if is_report:
        title = f"聚合报告 · 深南AI日报 Daily AI Brief · {date_str}"
        body_attrs = f'data-page-report="{report_range}"'
    else:
        title = f"深南AI日报 Daily AI Brief · {date_str}"
        body_attrs = f'data-page-period="{period_key}" data-page-date="{date_str}"'

    report_switch_html = ""
    if is_report:
        w_cls = "time-chip active" if report_range == "week" else "time-chip"
        m_cls = "time-chip active" if report_range == "month" else "time-chip"
        report_switch_html = f'''<div class="period-group report-range" role="tablist" aria-label="报告范围">
  <a class="{w_cls}" href="report-week.html">周报</a>
  <a class="{m_cls}" href="report-month.html">月报</a>
</div>'''
        period_or_range = report_switch_html
    else:
        period_or_range = f'''<div class="period-group" role="tablist" aria-label="日报时段">
    {period_html}
  </div>'''

    if is_report:
        report_dropdown_html = f'''<a class="top-btn back-today" href="{doc_prefix}index.html" title="返回今日日报">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h18"/><path d="M12 3v18"/><path d="M12 8l-5 4 5 4"/></svg>
  返回今日
</a>'''
    else:
        report_dropdown_html = f'''<div class="report-morph" id="reportDropdown" aria-label="报告范围">
  <div class="report-face" aria-hidden="true">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
    <span>报告</span>
  </div>
  <div class="report-choices" role="group">
    <a class="report-choice" href="{doc_prefix}report-week.html">周报</a>
    <span class="report-divider">|</span>
    <a class="report-choice" href="{doc_prefix}report-month.html">月报</a>
  </div>
</div>'''

    # v1.9.3：首页把右侧工具胶囊（报告/历史日报/导出）合并进导航条，与 5 个分类胶囊在同一行 sticky 对齐
    if is_report:
        nav_actions_html = ""
        topbar_tools_html = report_dropdown_html  # 报告页保留「返回今日」在 topbar
    else:
        nav_actions_html = f'''<div class="nav-actions">
  {report_dropdown_html}
  <div class="dropdown" id="historyDropdown">
    <button class="top-btn" type="button" aria-haspopup="true" aria-expanded="false">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      历史日报
    </button>
    <div class="dropdown-menu" role="menu">
      {history_menu}
    </div>
  </div>
  <div class="dropdown" id="exportDropdown">
    <button class="top-btn" type="button" aria-haspopup="true" aria-expanded="false">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
      导出
    </button>
    <div class="dropdown-menu" role="menu">
      <div class="dropdown-section">导出范围</div>
      <a class="dropdown-item scope-item active" href="#" data-export-scope="today">今天</a>
      <a class="dropdown-item scope-item" href="#" data-export-scope="week">近一周</a>
      <a class="dropdown-item scope-item" href="#" data-export-scope="month">近一月</a>
      <div class="dropdown-divider"></div>
      <div class="dropdown-section">导出格式</div>
      <a class="dropdown-item" href="#" data-export="png">PNG 图片</a>
      <a class="dropdown-item" href="#" data-export="html">HTML 文件</a>
      <a class="dropdown-item" href="#" data-export="markdown">Markdown</a>
      <a class="dropdown-item" href="#" data-export="csv">CSV 表格</a>
      <a class="dropdown-item" href="#" data-export="pdf">PDF 文档</a>
    </div>
  </div>
</div>'''
        topbar_tools_html = ""

    if is_report:
        hero_headline = '<h1 class="hero-title"><span class="title-white">聚合报告</span> <span class="title-brief">AI Brief</span></h1>'
        hero_date_block = f'''<div class="hero-date" style="font-size:28px;font-weight:300;color:var(--gold);letter-spacing:.02em;">{html.escape(date_str)}</div>
        <div class="hero-meta">聚合窗口：<span class="accent">{fmt_short(ws_dt)} — {fmt_short(we_dt)}</span>（北京时间，UTC+8）</div>'''
        hero_lead_text = f'以下 <span class="lead-strong">{total}</span> 条动态来自近{"7" if report_range=="week" else "30"}天日报汇总，按版块归类，全局连续编号，点击卡片直达原文。<span class="hero-tip">?</span>'
    else:
        hero_headline = '<h1 class="hero-title"><span class="title-white">Daily AI</span> <span class="title-brief">Brief</span></h1>'
        hero_date_block = f'''<div class="hero-date">
          <span class="big">{hero_mm}</span>
          <span class="dot">/</span>
          <span class="big">{hero_dd}</span>
          <span class="small">/ {hero_year}</span>
        </div>
        <div class="hero-meta">
          送达时间：<span class="accent">{fmt_full(gen_dt)}</span>
        </div>'''
        hero_lead_text = f'覆盖窗口 <span class="lead-strong">{fmt_short(ws_dt)} — {fmt_short(we_dt)}</span>（北京时间，UTC+8）。以下 <span class="lead-strong">{total}</span> 条动态按版块归类，全局连续编号，点击卡片直达原文。<span class="hero-tip">?</span>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script>
  // 早期初始化 + 全局 FAB 主题切换函数（必须最先定义，inline onclick 直接调用）
  (function(){{
    const h = (new Date().getUTCHours() + 8) % 24;
    const p = (h >= 6 && h < 12) ? 'morning' : (h >= 12 && h < 18) ? 'noon' : 'night';
    const t = (p === 'morning' || p === 'noon') ? 'light' : 'dark';
    const saved = (function(){{ try {{ return localStorage.getItem('sn-theme'); }} catch(e) {{ return null; }} }})();
    document.documentElement.setAttribute('data-theme', saved || t);
    // 暴露 FAB 主题切换的全局函数（inline onclick 调用，绕过 DOMContentLoaded 与 ID 查找）
    window.snToggleTheme = function() {{
      const cur = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = cur === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      try {{ localStorage.setItem('sn-theme', next); }} catch(e) {{}}
      // 即时反映 FAB 图标：暗色显示太阳（→light），浅色显示月亮（→dark）
      var btn = document.getElementById('themeToggle');
      if (btn) {{
        btn.innerHTML = next === 'light'
          ? '<svg class="fab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
          : '<svg class="fab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>';
        btn.setAttribute('title', next === 'light' ? '当前：浅色，点击切到深色' : '当前：深色，点击切到浅色');
        btn.setAttribute('aria-label', btn.getAttribute('title'));
      }}
    }};
    // 暴露留言/反馈全局函数（v1.8.7 FAB 化）
    window.snOpenContact = function() {{
      var modal = document.getElementById('contactModal');
      if (!modal) return;
      modal.classList.add('open');
      modal.setAttribute('aria-hidden', 'false');
      var msgEl = document.getElementById('contactMsg');
      if (msgEl) msgEl.focus();
    }};
  }})();
</script>
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/html2pdf.js@0.10.1/dist/html2pdf.bundle.min.js"></script>
<style>
{fonts_css_pp}

  :root {{
    --ink-void: #0A0E1A;
    --ink-deep: #0F1424;
    --ink-card: #141C32;
    --ink-card-hi: #1A2440;
    --ultra: #2E3A7C;
    --ultra-bright: #4A5BC4;
    --ultra-glow: rgba(74, 91, 196, 0.18);
    --gold: #DAC887;
    --gold-bright: #E8D9A0;
    --gold-soft: #A8965A;
    --gold-glow: rgba(218, 200, 135, 0.14);
    --brand-brief: #DDD090;
    --brand-cn: #cdc8ff;
    --btn: #4F5CC7;
    --btn-hi: #6470DC;
    --mist: #DDE2F0;
    --mist-body: #BEC4DC;
    --mist-dim: #9CA4C2;
    --mist-faint: #6E7793;
    --line: rgba(46, 58, 124, 0.4);
    --line-faint: rgba(46, 58, 124, 0.22);
    --line-gold: rgba(218, 200, 135, 0.35);
    --line-gold-fine: rgba(218, 200, 135, 0.55);
    --card-edge-hover: #837E65;
    --card-shadow-hover: rgba(0, 0, 0, 0.92);
    /* 语义化文字/表面色 — 暗模式完整定义（之前是自引用，已修复） */
    --text-title: #F0F2FA;
    --text-primary: #DDE2F0;
    --text-body: #BEC4DC;
    --text-secondary: #9CA4C2;
    --text-tertiary: #6E7793;
    --text-accent: #cdc8ff;
    --text-link: #BDC3FF;
    --text-code: #BEC4DC;
    --surface-float: rgba(20, 28, 50, 0.72);
    --surface-modal: rgba(15, 20, 36, 0.96);
    --surface-chip: rgba(20, 28, 50, 0.5);
    --surface-code: rgba(20, 28, 50, 0.7);
    --shadow: rgba(0, 0, 0, 0.55);
    --font-base: 'Poppins', 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB', 'Noto Sans CJK SC', system-ui, -apple-system, sans-serif;
    --font-cn-display: 'ZCOOL XiaoWei', 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB', 'Noto Sans CJK SC', system-ui, serif;
    --font-en-display: 'Space Grotesk', 'Poppins', 'PingFang SC', system-ui, sans-serif;
    --font-num: 'Space Grotesk', 'Poppins', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
    --font-mono: 'SF Mono', 'Fira Code', 'JetBrains Mono', 'PingFang SC', Consolas, monospace;
  }}

  /* 浅色模式：早报专属「晨光读报」配色（独立设计，非暗色反转）
     灵感：晨光 / 米白纸张 / 暖墨 / 暖金。
     —— 暗 → 亮变量重映射，文字底色全部重定义。 */
  [data-theme="light"] {{
    --ink-void: #F5F1E6;          /* 暖米白纸张 */
    --ink-deep: #2A2520;          /* 暖墨主字 */
    --ink-card: #FFFFFF;          /* 净白卡片底 */
    --ink-card-hi: #FDFAF1;       /* 暖白 hover */
    --ultra: #4A5BC4;
    --ultra-bright: #2E3A7C;
    --ultra-glow: rgba(74, 91, 196, 0.10);
    --gold: #A87E2A;              /* 暖金（晨光） */
    --gold-bright: #C19440;
    --gold-soft: #856020;
    --gold-glow: rgba(168, 126, 42, 0.10);
    --brand-brief: #A87E2A;       /* 「深南AI视界」金 */
    --brand-cn: #4A5BC4;          /* 「深南AI日报」薰衣草保留 */
    --btn: #3B4AA8;               /* 沉静的靛蓝按钮 */
    --btn-hi: #5466D2;
    --mist: #2A2520;
    --mist-body: #4A4540;         /* 正文暖灰 */
    --mist-dim: #7A7268;
    --mist-faint: #A89F8E;
    --line: rgba(168, 126, 42, 0.20);
    --line-faint: rgba(168, 126, 42, 0.12);
    --line-gold: rgba(168, 126, 42, 0.32);
    --line-gold-fine: rgba(168, 126, 42, 0.50);
    --card-edge-hover: #A87E2A;
    --card-shadow-hover: rgba(46, 58, 124, 0.18);
    /* 语义化文字/表面色 */
    --text-title: #2A2520;
    --text-primary: #2A2520;
    --text-body: #4A4540;
    --text-secondary: #7A7268;
    --text-tertiary: #A89F8E;
    --text-accent: #A87E2A;
    --text-link: #3B4AA8;
    --text-code: #4A4540;
    --surface-float: rgba(255, 252, 245, 0.82);
    --surface-modal: rgba(255, 252, 245, 0.98);
    --surface-chip: rgba(232, 226, 208, 0.85);
    --surface-code: rgba(232, 226, 208, 0.95);
    --shadow: rgba(46, 58, 124, 0.15);
    --font-base: 'Poppins', 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB', 'Noto Sans CJK SC', system-ui, -apple-system, sans-serif;
    --font-cn-display: 'ZCOOL XiaoWei', 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB', 'Noto Sans CJK SC', system-ui, serif;
    --font-en-display: 'Space Grotesk', 'Poppins', 'PingFang SC', system-ui, sans-serif;
    --font-num: 'Space Grotesk', 'Poppins', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
    --font-mono: 'SF Mono', 'Fira Code', 'JetBrains Mono', 'PingFang SC', Consolas, monospace;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; scroll-padding-top: 76px; }}

  body {{
    background: var(--ink-void);
    color: var(--mist);
    font-family: var(--font-base);
    font-weight: 400;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
    padding-top: env(safe-area-inset-top);
    padding-bottom: env(safe-area-inset-bottom);
  }}

  body::before {{
    content: "";
    position: fixed;
    inset: -10%;
    background:
      radial-gradient(ellipse 80% 50% at 20% 0%, rgba(46, 58, 124, 0.18), transparent 60%),
      radial-gradient(ellipse 60% 40% at 85% 15%, rgba(218, 200, 135, 0.07), transparent 55%);
    pointer-events: none;
    z-index: 0;
    animation: ambientDrift 36s ease-in-out infinite alternate;
  }}
  body::after {{
    content: "";
    position: fixed;
    inset: -10%;
    background:
      radial-gradient(ellipse 50% 35% at 70% 85%, rgba(74, 91, 196, 0.08), transparent 60%);
    pointer-events: none;
    z-index: 0;
    animation: ambientDrift 48s ease-in-out infinite alternate-reverse;
  }}
  @keyframes ambientDrift {{
    0%   {{ transform: translate3d(0, 0, 0) scale(1); }}
    100% {{ transform: translate3d(-2.5%, 2%, 1) scale(1.06); }}
  }}

  .wrap {{ position: relative; z-index: 1; max-width: 1280px; margin: 0 auto; padding: 0 28px; }}

  /* ===== TOPBAR ===== */
  .topbar {{
    position: fixed;          /* 保持固定：只有 ticker 随页面上移 */
    top: calc(env(safe-area-inset-top, 0) + 32px);  /* 紧贴 ticker（32px 高）下方 */
    right: 0;
    z-index: 200;
    padding: 8px 28px;
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 10px;
    transition: transform .3s ease;
  }}
  [data-theme="light"] .topbar {{
    background: #F2ECDD;
  }}
  .top-btn {{
    appearance: none;
    box-sizing: border-box;
    border: 1px solid rgba(205, 200, 255, 0.45);
    background: var(--surface-float);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    color: var(--mist-body);
    font-family: var(--font-base);
    font-size: 12px;
    letter-spacing: 0.06em;
    padding: 8px 14px;
    border-radius: 999px;
    cursor: pointer;
    transition: all .2s ease;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 34px;
  }}
  .top-btn:hover {{ border-color: var(--brand-cn); color: var(--text-primary); background: rgba(205, 200, 255, 0.12); }}
  .dropdown {{ position: relative; }}
  .dropdown-menu {{
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    min-width: 160px;
    max-height: 320px;
    overflow-y: auto;
    background: var(--surface-modal);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 6px;
    box-shadow: 0 16px 40px -10px var(--shadow);
    opacity: 0;
    visibility: hidden;
    transform: translateY(-6px);
    transition: all .18s ease;
    scrollbar-width: thin;
  }}
  .dropdown.open .dropdown-menu {{ opacity: 1; visibility: visible; transform: translateY(0); }}

  /* 报告胶囊：hover 原地变形为「周报 | 月报」 */
  .report-morph {{
    position: relative;
    box-sizing: border-box;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 108px;
    height: 34px;
    border: 1px solid rgba(205, 200, 255, 0.45);
    background: var(--surface-float);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-radius: 999px;
    cursor: pointer;
    overflow: hidden;
    transition: border-color .2s ease, background .2s ease;
    vertical-align: middle;
  }}
  .report-morph:hover {{
    border-color: var(--brand-cn);
    background: rgba(205, 200, 255, 0.12);
  }}
  .report-face, .report-choices {{
    position: absolute;
    inset: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    transition: opacity .18s ease, transform .18s ease;
  }}
  .report-face {{
    opacity: 1;
    transform: translateY(0);
    color: var(--mist-body);
    font-size: 12px;
    letter-spacing: 0.06em;
    pointer-events: none;
  }}
  .report-choices {{
    opacity: 0;
    transform: translateY(12px);
    pointer-events: none;
  }}
  .report-morph:hover .report-face,
  .report-morph:focus-within .report-face {{
    opacity: 0;
    transform: translateY(-12px);
  }}
  .report-morph:hover .report-choices,
  .report-morph:focus-within .report-choices {{
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
  }}
  .report-choice {{
    color: var(--mist-body);
    font-size: 10px;
    letter-spacing: 0.04em;
    text-decoration: none;
    padding: 2px 8px;
    border-radius: 999px;
    transition: color .15s ease, background .15s ease;
    white-space: nowrap;
  }}
  .report-choice:hover {{
    color: var(--text-primary);
    background: rgba(205, 200, 255, 0.18);
  }}
  .report-divider {{
    color: rgba(205, 200, 255, 0.4);
    font-size: 10px;
    margin: 0 3px;
    user-select: none;
  }}
  [data-theme="light"] .report-morph {{ background: rgba(245, 242, 236, 0.92); border-color: rgba(131, 126, 101, 0.35); }}
  [data-theme="light"] .report-morph:hover {{ background: rgba(255, 255, 255, 0.95); border-color: rgba(131, 126, 101, 0.55); }}
  [data-theme="light"] .report-choice:hover {{ background: rgba(131, 126, 101, 0.12); }}
  [data-theme="light"] .report-divider {{ color: rgba(131, 126, 101, 0.35); }}
  .dropdown-item {{
    display: block;
    padding: 8px 12px;
    border-radius: 6px;
    color: var(--mist-body);
    text-decoration: none;
    font-size: 13px;
    white-space: nowrap;
    transition: background .15s ease, color .15s ease;
  }}
  .dropdown-item:hover {{ background: rgba(205, 200, 255, 0.10); color: var(--text-primary); }}
  .dropdown-item.selected {{ background: rgba(79, 92, 199, 0.35); color: var(--text-primary); }}
  .dropdown-item.disabled {{ color: var(--mist-faint); pointer-events: none; }}
  .dropdown-section {{
    padding: 6px 12px 4px;
    font-size: 11px;
    letter-spacing: 0.08em;
    color: var(--mist-faint);
    text-transform: uppercase;
  }}
  .dropdown-divider {{
    height: 1px;
    background: var(--line-faint);
    margin: 6px 4px;
  }}
  .scope-item.active {{
    background: rgba(79, 92, 199, 0.25);
    color: var(--text-primary);
  }}

  /* ===== BRAND LOGO ===== */
  .brand-logo {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 18px 0 8px;
    margin-bottom: 10px;
  }}
  .brand-logo .sn-logo {{
    width: 44px; height: 44px;
    flex-shrink: 0;
    display: block;
    object-fit: contain;
    filter: drop-shadow(0 6px 14px rgba(0,0,0,.28));
  }}

  @keyframes riseIn {{
    from {{ opacity: 0; transform: translateY(14px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
  .hero > * {{ animation: riseIn .7s cubic-bezier(.2,.7,.3,1) both; }}
  .hero > *:nth-child(2) {{ animation-delay: .08s; }}
  .hero > *:nth-child(3) {{ animation-delay: .16s; }}
  .reveal-sec {{ opacity: 0; }}
  .reveal-sec.in-view {{
    animation: riseIn .65s cubic-bezier(.2,.7,.3,1) both;
    animation-delay: calc(var(--d) * 60ms);
  }}
  .reveal {{ opacity: 1; transform: none; }}
  .in-view .reveal {{
    opacity: 1;
    transform: none;
    transition: opacity .6s cubic-bezier(.2,.7,.3,1), transform .6s cubic-bezier(.2,.7,.3,1);
    transition-delay: calc(120ms + var(--d) * 55ms);
  }}

  /* ===== HERO ===== */
  .hero {{
    padding: 56px 0 40px;
    border-bottom: 1px solid var(--line-gold);
  }}
  .hero-title {{
    font-family: var(--font-en-display);
    font-weight: 400;
    font-style: normal;
    font-size: 48px;
    letter-spacing: -0.01em;
    color: var(--text-title);
    margin-bottom: 12px;
    line-height: 1.05;
  }}
  .hero-title .title-white {{ color: var(--text-title); }}
  .hero-title .title-brief {{ color: var(--brand-brief); }}
  .hero-sub {{
    font-family: var(--font-base);
    font-size: 15px;
    letter-spacing: 0.14em;
    margin-bottom: 8px;
    color: var(--text-title);
    line-height: 1.4;
    text-align: left;
  }}
  .hero-sub .sub-brand {{ color: var(--brand-cn); font-weight: 500; }}
  /* 顶栏时段切换：胶囊外框 + 内圆按钮 */
  .period-group {{
    display: inline-flex;
    align-items: center;
    gap: 2px;
    border: 1px solid rgba(205, 200, 255, 0.45);
    border-radius: 999px;
    padding: 3px;
    background: var(--surface-float);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    height: 34px;
  }}
  /* 早中晚时段模块：2026-07-28 按用户要求暂隐藏（数据增量难度大，先不做）。
     结构 / JS / period 逻辑全部保留，后续要恢复只删下面这一行即可。
     注意：仅隐藏“日报时段”胶囊，报告页的“周报/月报”切换(.report-range)不受影响。 */
  .period-group:not(.report-range) {{ display: none; }}
  .report-range .time-chip {{ min-width: 44px; }}
  .time-chip {{
    appearance: none;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 500;
    line-height: 1;
    color: var(--mist-dim);
    background: transparent;
    border: none;
    border-radius: 999px;
    min-width: 32px;
    height: 26px;
    padding: 0 8px;
    letter-spacing: 0.02em;
    cursor: pointer;
    transition: all .2s ease;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    text-decoration: none;
  }}
  .time-chip:hover {{
    color: var(--mist-body);
    background: rgba(205, 200, 255, 0.10);
  }}
  .time-chip.active {{
    color: var(--brand-brief);
    background: rgba(218, 200, 135, 0.18);
    box-shadow: inset 0 0 8px rgba(218, 200, 135, 0.12);
  }}
  .time-chip:disabled {{
    opacity: 0.35;
    cursor: not-allowed;
    pointer-events: none;
  }}
  .hero-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 48px;
    align-items: end;
  }}
  .hero-date {{
    font-family: var(--font-num);
    font-weight: 300;
    line-height: 0.9;
    display: flex;
    align-items: baseline;
    gap: 6px;
    flex-wrap: wrap;
  }}
  .hero-date > * {{ flex-shrink: 0; }}
  .hero-date .big {{
    font-size: 148px;
    font-weight: 300;
    background: linear-gradient(110deg,
      var(--gold-soft) 0%, var(--gold) 30%, var(--gold-bright) 46%,
      #FFF3D6 50%, var(--gold-bright) 54%, var(--gold) 70%, var(--gold-soft) 100%);
    background-size: 220% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.04em;
    animation: goldSheen 7s ease-in-out infinite;
  }}
  @keyframes goldSheen {{
    0%, 100% {{ background-position: 0% 0; }}
    50%      {{ background-position: 90% 0; }}
  }}
  .hero-date .dot {{ font-size: 40px; color: var(--mist-dim); font-weight: 300; }}
  .hero-date .small {{ font-size: 40px; color: var(--mist-dim); font-weight: 300; }}
  .hero-meta {{
    font-family: var(--font-base);
    font-size: 13px;
    color: var(--mist-dim);
    margin-top: 18px;
    letter-spacing: 0.04em;
  }}
  .hero-meta .accent {{ color: var(--brand-cn); font-weight: 500; }}
  .hero-lead {{
    font-size: 14px;
    color: var(--mist-dim);
    margin-top: 18px;
    max-width: 560px;
    line-height: 1.85;
    padding: 16px 18px;
    border-left: 2px solid var(--brand-cn);
    background: rgba(205, 200, 255, 0.05);
    border-radius: 0 8px 8px 0;
  }}
  .hero-lead .lead-strong {{ color: var(--mist-body); }}
  .hero-tip {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px; height: 16px;
    margin-left: 6px;
    border: 1px solid var(--mist-faint);
    border-radius: 50%;
    font-size: 10px;
    color: var(--mist-faint);
    cursor: help;
    position: relative;
    vertical-align: middle;
  }}
  .hero-tip:hover {{ border-color: var(--brand-cn); color: var(--brand-cn); }}
  .hero-tip::after {{
    content: "部分海外源链接需特殊网络环境访问";
    position: absolute;
    bottom: 120%; left: 50%;
    transform: translateX(-50%);
    width: max-content; max-width: 220px;
    padding: 8px 12px;
    background: rgba(20, 28, 50, 0.96);
    border: 1px solid var(--line);
    border-radius: 6px;
    font-size: 11px;
    color: var(--mist-body);
    line-height: 1.5;
    opacity: 0; visibility: hidden;
    transition: opacity .2s ease, visibility .2s ease;
    pointer-events: none;
    box-shadow: 0 8px 24px -6px rgba(0,0,0,.4);
    z-index: 10;
  }}
  .hero-tip:hover::after {{ opacity: 1; visibility: visible; }}

  .hero-stats {{
    display: grid;
    gap: 1px;
    background: var(--line-faint);
    border: 1px solid var(--line-faint);
    border-radius: 4px;
    overflow: hidden;
    opacity: 0.88;
  }}
  .hero-stats.cols-2 {{ grid-template-columns: repeat(2, 1fr); }}
  .hero-stats.cols-3 {{ grid-template-columns: repeat(3, 1fr); }}
  .stat-cell {{
    background: rgba(15, 20, 36, 0.72);
    padding: 18px 20px 16px;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }}
  .stat-num {{ font-family: var(--font-num); font-weight: 300; font-size: 30px; color: var(--gold); line-height: 1; }}
  .stat-lab {{ font-size: 11.5px; color: var(--mist-faint); letter-spacing: 0.05em; }}
  .stat-total {{
    grid-column: 1 / -1;
    background: linear-gradient(135deg, rgba(79,92,199,0.16), rgba(218,200,135,0.05));
    padding: 16px 24px;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
  }}
  .stat-total .num {{ font-family: var(--font-num); font-weight: 300; font-size: 34px; color: var(--gold); line-height: 1; }}
  .stat-total .lab {{ font-size: 11px; color: var(--mist-dim); letter-spacing: 0.18em; text-transform: uppercase; }}

  /* ===== STICKY NAV ===== */
  .nav {{
    position: sticky;
    top: calc(env(safe-area-inset-top, 0) + 78px);   /* 报告页：ticker + topbar 之后吸顶 */
    z-index: 50;
    /* 用胶囊底色完全遮住背后内容，不再镂空 */
    background: var(--ink-card);
    border-bottom: 1px solid rgba(131, 126, 101, 0.45);  /* 浅浅细细的金色分割线 */
    transition: transform .3s ease;
  }}
  [data-theme="light"] .nav {{
    background: var(--ink-card);
    border-bottom-color: rgba(131, 126, 101, 0.35);
  }}
  /* 移动端滚动时自动隐藏顶栏/导航，上滑时恢复（由 JS 切换 .hide）；鼠标悬停时临时显示 */
  .nav.hide, .topbar.hide {{ transform: translateY(-160%); }}
  .nav.hide:hover, .topbar.hide:hover {{ transform: translateY(0); }}
  .nav-inner {{
    max-width: 1280px;
    margin: 0 auto;
    padding: 10px 28px;          /* 更紧凑，缩短与顶部的视觉距离 */
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;  /* 左侧分类与右侧工具胶囊分居两端 */
    align-items: center;
    gap: 8px;
    overflow-x: visible;
    scrollbar-width: none;
  }}
  .nav-actions {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-left: auto;       /* 确保靠右 */
    flex-shrink: 0;
  }}
  /* 首页：隐藏固定 topbar，工具胶囊已合并进 nav，8 胶囊在同一行 sticky 对齐 */
  [data-page-period] .topbar {{ display: none; }}
  /* 首页 ticker 随页面滚走后，nav 直接贴顶，不再留 32px 镂空间隙 */
  [data-page-period] .nav {{ top: env(safe-area-inset-top, 0); }}
  .nav-inner::-webkit-scrollbar {{ display: none; }}
  .nav-chip {{
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 8px 16px;
    border: 1px solid rgba(205, 200, 255, 0.55);
    border-radius: 999px;
    text-decoration: none;
    color: var(--mist-dim);
    font-size: 13px;
    white-space: nowrap;
    transition: all .22s ease;
    background: var(--surface-chip);
  }}
  .nav-chip:hover {{
    border-color: var(--brand-cn);
    color: var(--text-primary);
    background: rgba(205, 200, 255, 0.12);
  }}
  .nav-chip:hover .nav-roman,
  .nav-chip:hover .nav-n {{ color: var(--text-primary); border-left-color: rgba(255,255,255,0.3); }}
  .nav-chip.active,
  .nav-chip.is-active-by-io {{
    border-color: var(--btn);
    color: var(--text-primary);
    background: var(--btn);
  }}
  .nav-chip.active .nav-roman,
  .nav-chip.active .nav-n,
  .nav-chip.is-active-by-io .nav-roman,
  .nav-chip.is-active-by-io .nav-n {{ color: var(--text-primary); border-left-color: rgba(255,255,255,0.3); }}
  .nav-roman {{ font-family: var(--font-num); font-weight: 400; color: var(--ultra-bright); font-size: 12px; }}
  .nav-n {{ font-family: 'Space Grotesk', sans-serif; font-weight: 400; color: var(--gold); font-size: 12px; padding-left: 8px; border-left: 1px solid var(--line); }}
  .nav-n .count-unit {{ font-family: 'ZCOOL XiaoWei', sans-serif; font-weight: 300; margin-left: 4px; font-size: 11px; }}

  /* ===== SECTIONS ===== */
  .main {{ padding: 56px 0 32px; }}
  .section {{ margin-bottom: 64px; }}
  .sec-head {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 28px;
  }}
  .sec-mark {{ font-family: var(--font-num); font-weight: 300; font-size: 32px; color: var(--gold); min-width: 32px; }}
  .sec-title {{ font-family: 'ZCOOL XiaoWei', sans-serif; font-size: 26px; font-weight: 100; color: var(--text-title); letter-spacing: 0.03em; }}
  .sec-line {{ flex: 1; height: 1px; background: linear-gradient(90deg, var(--line-gold), transparent); }}
  .sec-count {{ font-family: 'Space Grotesk', sans-serif; font-weight: 400; font-size: 13px; color: var(--gold); display: inline-flex; align-items: baseline; gap: 4px; }}
  .sec-count .count-unit {{ font-family: 'ZCOOL XiaoWei', sans-serif; font-weight: 300; font-size: 12px; }}

  /* ===== CARD GRID ===== */
  .card-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 18px;
    align-items: start;
  }}

  .card {{
    position: relative;
    display: flex;
    flex-direction: column;
    background: var(--ink-card);
    border: 1.5px solid rgba(74, 91, 196, 0.5);
    border-radius: 12px;
    padding: 26px 26px 20px;
    text-decoration: none;
    color: inherit;
    overflow: hidden;
    min-height: 360px;
    max-height: 360px;
    /* 显式钉死顶部对齐 + 禁止上移（防御性写法） */
    align-self: start;
    margin-top: 0;
    /* 只过渡 max-height 和阴影/边框/背景，不动 transform（避免上移） */
    /* 收起节奏：极慢，约为展开的 4.5 倍（再慢一倍），形成强对比 */
    transition: max-height 1.7s cubic-bezier(.4, 0, .2, 1),
                box-shadow 1.0s ease, border-color 1.0s ease, background 1.0s ease,
                z-index 0s 0s;
    z-index: 1;
  }}
  .card::before {{
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 100% 0%, var(--ultra-glow), transparent 50%);
    opacity: 0;
    transition: opacity .3s ease;
    pointer-events: none;
  }}
  .card:hover {{
    z-index: 100;
    background: var(--ink-card-hi);
    border-color: transparent;
    /* 向下展开（row 高度变大 → 下方卡片自然下移） */
    max-height: 640px;
    /* 显式禁止上移 */
    transform: none;
    box-shadow:
      0 0 0 2px #837E65,
      0 18px 36px -8px rgba(0, 0, 0, 0.7);
    /* 展开节奏：快且带轻微回弹（spring），与收起的慢节奏形成对比 */
    transition: max-height .38s cubic-bezier(.34, 1.45, .64, 1),
                box-shadow .3s ease, border-color .3s ease, background .3s ease,
                z-index 0s 0s;
  }}
  .card:hover::before {{ opacity: 1; }}

  .card-num {{ font-family: var(--font-num); font-weight: 300; font-size: 32px; color: var(--gold); line-height: 1; margin-bottom: 16px; letter-spacing: -0.02em; }}
  .card-body {{ flex: 1; display: flex; flex-direction: column; gap: 12px; }}
  .chip {{
    display: inline-block;
    align-self: flex-start;
    max-width: 100%;
    font-size: 11px;
    letter-spacing: 0.04em;
    color: #A8B2F0;
    background: rgba(10, 14, 26, 0.72);
    border: 1.5px solid rgba(95, 110, 230, 0.55);
    padding: 3px 10px;
    border-radius: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .card-title {{
    font-family: 'ZCOOL XiaoWei', sans-serif;
    font-size: 22.5px;
    font-weight: 400;
    color: var(--text-primary);
    line-height: 1.4;
    letter-spacing: 0.015em;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}
  .card:hover .card-title {{ display: block; -webkit-line-clamp: unset; overflow: visible; }}
  .card-summary {{
    font-size: 14.5px;
    color: var(--mist-body);
    line-height: 1.75;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    border-left: 2px solid rgba(218, 200, 135, 0.55);
    padding: 2px 0 2px 12px;
  }}
  .card:hover .card-summary {{ display: block; overflow: visible; -webkit-line-clamp: unset; padding-top: 4px; padding-bottom: 6px; }}
  .card-cta {{
    margin-top: 18px;
    padding: 11px 16px;
    background: var(--btn);
    border-radius: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: var(--font-base);
    font-size: 12px;
    color: var(--text-primary);
    letter-spacing: 0.12em;
    text-decoration: none;
    transition: background .25s ease;
  }}
  .card:hover .card-cta {{ background: var(--btn-hi); }}
  .card:hover .card-cta .arrow {{ transform: translateX(4px); }}
  .card-cta .arrow {{
    font-size: 18px;
    font-weight: 500;
    transition: transform .25s ease;
    line-height: 1;
  }}

  /* 触屏设备（无 hover）：新闻卡片默认全部展开；报告胶囊直接显示周报/月报 */
  @media (hover: none) {{
    .card {{ max-height: none; }}
    .card-title {{ -webkit-line-clamp: unset; display: block; overflow: visible; }}
    .card-summary {{ -webkit-line-clamp: unset; display: block; overflow: visible; }}
    .report-morph {{ min-width: 120px; }}
    .report-face {{ opacity: 0; transform: translateY(-12px); pointer-events: none; }}
    .report-choices {{ opacity: 1; transform: translateY(0); pointer-events: auto; }}
  }}

  /* ===== FOOTER ===== */
  .footer {{
    padding: 14px 0 0;
    text-align: center;
    margin-top: 0;
  }}
  .footer-mark {{
    font-family: var(--font-base);
    font-weight: 400;
    font-size: 10px;
    letter-spacing: 0.12em;
    color: var(--mist-faint);
    margin-bottom: 14px;
  }}
  .footer-meta {{
    font-family: var(--font-base);
    font-size: 13px;
    color: var(--gold);
    line-height: 1.8;
    margin-bottom: 14px;
  }}
  .footer-meta .num {{ font-family: var(--font-base); font-weight: 500; color: var(--gold); font-size: 13px; }}
  .footer-source {{ font-size: 12px; color: var(--mist-faint); margin-bottom: 28px; }}
  .footer-source a {{ color: var(--btn-hi); text-decoration: none; border-bottom: 1px dotted var(--btn); }}
  .footer-copyright {{
    font-family: var(--font-base);
    font-size: 12px;
    letter-spacing: 0.04em;
    color: var(--mist-dim);
    margin-bottom: 26px;
  }}
  .footer-docs {{
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
    gap: 40px;
    margin-bottom: 0;
  }}
  .footer-docs a {{
    font-family: var(--font-base);
    font-size: 13px;
    letter-spacing: 0.06em;
    color: var(--text-accent);
    text-decoration: none;
    transition: color .2s ease;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}
  .footer-docs a:hover {{ color: var(--text-primary); }}
  .footer-docs a .doc-icon {{ width: 14px; height: 14px; flex-shrink: 0; opacity: 0.92; }}

  /* ===== CONTACT (GitHub Issue 留言) ===== */
  .contact-btn {{
    display: inline-flex; align-items: center; gap: 8px;
    margin: 16px auto 0; padding: 11px 22px;
    background: var(--btn); color: var(--text-primary);
    border: 1px solid rgba(95, 110, 230, 0.5); border-radius: 999px;
    font-family: var(--font-base); font-size: 13px; letter-spacing: 0.06em;
    cursor: pointer; transition: background .25s ease, transform .2s ease;
  }}
  .contact-btn:hover {{ background: var(--btn-hi); transform: translateY(-2px); }}
  .contact-modal {{
    position: fixed; inset: 0; z-index: 1000; display: none;
    align-items: center; justify-content: center; padding: 20px;
    background: rgba(4, 7, 15, 0.72); backdrop-filter: blur(4px);
  }}
  .contact-modal.open {{ display: flex; }}
  .contact-card {{
    position: relative; width: min(520px, 100%); background: var(--surface-float);
    border: 1px solid var(--line); border-radius: 16px; padding: 26px;
    box-shadow: 0 30px 80px -10px rgba(0, 0, 0, 0.8);
  }}
  .contact-card h3 {{ font-family: var(--font-base); color: var(--text-title); font-size: 18px; margin: 0 0 6px; }}
  .contact-card p.tip {{ font-size: 12.5px; color: var(--mist-body); line-height: 1.7; margin: 0 0 16px; }}
  .contact-card label {{ display: block; font-size: 12px; color: var(--text-accent); margin: 12px 0 6px; letter-spacing: 0.04em; }}
  .contact-card input, .contact-card textarea {{
    width: 100%; box-sizing: border-box; background: rgba(10, 14, 26, 0.6);
    border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px;
    color: var(--text-primary); font-family: var(--font-base); font-size: 14px;
  }}
  .contact-card textarea {{ min-height: 120px; resize: vertical; }}
  .contact-card .hp {{ position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; }}
  .contact-actions {{ display: flex; gap: 10px; justify-content: flex-end; margin-top: 18px; }}
  .contact-actions button {{
    padding: 9px 18px; border-radius: 8px; font-family: var(--font-base);
    font-size: 13px; cursor: pointer; border: 1px solid var(--line);
  }}
  .contact-actions .send {{ background: var(--btn-hi); color: #0A0E1A; border-color: transparent; font-weight: 600; }}
  .contact-actions .cancel {{ background: transparent; color: var(--text-primary); }}
  .contact-close {{
    position: absolute; top: 12px; right: 14px; background: none; border: none;
    color: var(--mist-faint); font-size: 22px; line-height: 1; cursor: pointer;
  }}
  .contact-close:hover {{ color: var(--text-primary); }}
  .footer-bottom {{
    background: linear-gradient(180deg, rgba(10, 14, 26, 0) 0%, rgba(10, 14, 26, 0.92) 45%, rgba(10, 14, 26, 1) 100%);
    border-top: 1px solid var(--line-faint);
    padding: 42px 28px;
    display: flex;
    justify-content: center;
    align-items: center;
  }}
  .footer-line-bold {{
    height: 3px;
    background: linear-gradient(90deg, transparent, var(--line-gold) 18%, var(--line-gold) 82%, transparent);
    margin: 0 auto 24px;
    width: calc(100% - 56px);
    max-width: 1224px;
  }}

  /* ===== TICKER（顶部细条，右→左匀速滚动） ===== */
  .ticker {{
    position: relative;       /* 跟随页面上移；topbar 保持 fixed，只动这条细条 */
    z-index: 195;
    overflow: hidden;
    background: #1F2647;      /* 调亮：#161A2E → #1F2647 */
    border-bottom: 1px solid var(--line-faint);
    padding: 8px 0;
    height: 32px;
    display: flex;
    align-items: center;
  }}
  [data-theme="light"] .ticker {{
    background: #F2ECDD;      /* 调亮 */
    border-bottom-color: var(--line-faint);
  }}
  .ticker-track {{
    display: flex;
    width: max-content;
    align-items: center;
    animation: tickerScroll 40s linear infinite;
  }}
  .ticker:hover .ticker-track,
  .ticker:focus-within .ticker-track {{ animation-play-state: paused; }}
  .ticker-item {{
    flex-shrink: 0;
    padding: 0 48px;
    font-size: 11px;
    letter-spacing: 0.06em;
    color: var(--mist-dim);
    white-space: nowrap;
  }}
  [data-theme="light"] .ticker-item {{ color: #6B625A; }}
  .ticker-brand {{ color: #837E65; font-weight: 600; }}
  [data-theme="light"] .ticker-brand {{ color: #837E65; }}
  @keyframes tickerScroll {{
    0% {{ transform: translateX(0); }}
    100% {{ transform: translateX(-50%); }}
  }}

  /* ===== FLOATING ACTION BUTTONS ===== */
  .fab-group {{
    position: fixed;
    right: 24px;
    bottom: 92px;
    z-index: 180;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .fab {{
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: 1px solid transparent;
    background: rgba(13, 18, 36, 0.32);
    backdrop-filter: blur(14px) saturate(140%);
    -webkit-backdrop-filter: blur(14px) saturate(140%);
    color: var(--mist-body);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition:
      background .35s cubic-bezier(.4, 0, .2, 1),
      border-color .35s cubic-bezier(.4, 0, .2, 1),
      color .25s ease,
      backdrop-filter .35s ease,
      transform .25s cubic-bezier(.34, 1.2, .64, 1),
      box-shadow .25s ease;
    box-shadow: 0 6px 18px -8px rgba(0,0,0,.45);
  }}
  [data-theme="light"] .fab {{
    background: rgba(255, 255, 255, 0.42);
    box-shadow: 0 6px 18px -8px rgba(46, 58, 124, 0.18);
  }}
  .fab:hover {{
    color: var(--text-primary);
    background: rgba(79, 92, 199, 0.28);
    border-color: rgba(79, 92, 199, 0.55);
    backdrop-filter: blur(14px) saturate(180%);
    -webkit-backdrop-filter: blur(14px) saturate(180%);
    transform: translateY(-2px);
    box-shadow: 0 10px 26px -8px rgba(0,0,0,.55);
  }}
  [data-theme="light"] .fab:hover {{
    background: rgba(74, 91, 196, 0.18);
    border-color: rgba(74, 91, 196, 0.55);
    box-shadow: 0 10px 26px -8px rgba(46, 58, 124, 0.25);
  }}
  .fab-icon {{ width: 18px; height: 18px; }}

  /* 留言/反馈 FAB（v1.8.7 从 footer 提到右下 FAB 区）— 跟 FAB 同样视觉，hover 展开显示文字 */
  .fab-contact {{
    position: fixed;
    right: 24px;
    bottom: 14px;            /* FAB group 在上方 ~38px（= 1 个 icon 高），这里紧贴底部 */
    z-index: 180;
    width: 40px;
    height: 40px;
    border-radius: 999px;
    border: 1px solid transparent;
    background: rgba(13, 18, 36, 0.32);
    backdrop-filter: blur(14px) saturate(140%);
    -webkit-backdrop-filter: blur(14px) saturate(140%);
    color: var(--mist-body);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: flex-start;
    gap: 8px;
    padding: 0 14px;
    overflow: hidden;
    white-space: nowrap;
    font-family: var(--font-base);
    font-size: 12px;
    letter-spacing: 0.06em;
    box-shadow: 0 6px 18px -8px rgba(0,0,0,.45);
    transition:
      width .35s cubic-bezier(.34, 1.2, .64, 1),
      background .35s ease,
      border-color .35s ease,
      backdrop-filter .35s ease,
      transform .25s cubic-bezier(.34, 1.2, .64, 1),
      box-shadow .25s ease,
      padding .35s ease;
  }}
  [data-theme="light"] .fab-contact {{
    background: rgba(255, 255, 255, 0.42);
    box-shadow: 0 6px 18px -8px rgba(46, 58, 124, 0.18);
  }}
  .fab-contact:hover {{
    width: 168px;
    background: rgba(79, 92, 199, 0.28);
    border-color: rgba(79, 92, 199, 0.55);
    backdrop-filter: blur(14px) saturate(180%);
    -webkit-backdrop-filter: blur(14px) saturate(180%);
    transform: translateY(-2px);
    box-shadow: 0 10px 26px -8px rgba(0,0,0,.55);
    padding: 0 18px;
  }}
  [data-theme="light"] .fab-contact:hover {{
    background: rgba(74, 91, 196, 0.18);
    border-color: rgba(74, 91, 196, 0.55);
    box-shadow: 0 10px 26px -8px rgba(46, 58, 124, 0.25);
  }}
  .fab-contact .fab-label {{
    opacity: 0;
    transform: translateX(-6px);
    transition:
      opacity .25s ease .08s,
      transform .25s cubic-bezier(.34, 1.2, .64, 1) .08s,
      color .2s ease;
    color: var(--mist-body);
  }}
  .fab-contact:hover .fab-label {{
    opacity: 1;
    transform: translateX(0);
    color: var(--text-primary);
  }}

  /* 触屏设备（无 hover）：新闻卡片直接全部展开 */
  @media (hover: none) {{
    .card {{ max-height: none; }}
    .card-title {{ -webkit-line-clamp: unset; display: block; overflow: visible; }}
    .card-summary {{ -webkit-line-clamp: unset; display: block; overflow: visible; }}
  }}

  /* ===== RESPONSIVE ===== */
  @media (max-width: 880px) {{
    .topbar {{ padding: 8px 14px; }}
    .top-btn {{ padding: 5px 9px; font-size: 10px; gap: 4px; }}
    .top-btn svg {{ width: 12px; height: 12px; }}
    .time-chip {{ font-size: 11px; min-width: 26px; height: 22px; padding: 0 6px; }}
    .ticker {{ margin-top: 0; }}
    /* 移动端：header 已为正常流，nav 直接吸顶，无需额外预留 */
    .nav {{ padding-top: 0; background: transparent; backdrop-filter: none; -webkit-backdrop-filter: none; border-bottom: none; }}
    .nav-inner {{ background: var(--surface-float); backdrop-filter: blur(16px) saturate(140%); -webkit-backdrop-filter: blur(16px) saturate(140%); border: 1px solid var(--line-faint); border-radius: 999px; margin: 0 14px; padding: 8px 14px; }}
    .hero {{ padding: 36px 0 24px; }}
    .hero-grid {{ grid-template-columns: 1fr; gap: 36px; }}
    .hero-title {{ font-size: 34px; word-break: break-word; }}
    .hero-date .big {{ font-size: 110px; }}
    .hero-date .dot {{ font-size: 72px; }}
    .hero-date .small {{ font-size: 32px; }}
    .hero-stats {{ grid-template-columns: repeat(2, 1fr) !important; }}
    .stat-total {{ grid-column: 1 / -1; }}
    .card-grid {{ grid-template-columns: 1fr; }}
    .wrap {{ padding: 0 20px; }}
    .brand-logo {{ padding: 12px 0 6px; }}
    .brand-logo .sn-logo {{ width: 38px; height: 38px; object-fit: contain; }}
    /* 移动端：导航条横向滚动，避免 8 胶囊换行错位 */
    .nav-inner {{ flex-wrap: nowrap; overflow-x: auto; padding: 10px 14px; gap: 6px; }}
    .nav-chip {{ flex-shrink: 0; }}
    .nav-actions {{ flex-shrink: 0; margin-left: 0; }}
    /* 移动端：新闻模块直接显示，不依赖 IntersectionObserver 入场动画 */
    .reveal-sec {{ opacity: 1 !important; animation: none !important; transform: none !important; }}
    .footer-bottom {{ padding: 32px 20px; }}
    /* 底部文档链排：保持一排，窄屏可横向滚动 */
    .footer-docs {{ flex-wrap: nowrap; overflow-x: auto; gap: 12px; }}
    .footer-docs a {{ font-size: 12px; white-space: nowrap; }}
  }}
  @media (max-width: 480px) {{
    .top-btn {{ padding: 5px 9px; font-size: 10px; }}
    .hero-title {{ font-size: 26px; }}
    .hero-date .big {{ font-size: 84px; }}
    .hero-date .dot {{ font-size: 56px; }}
    .hero-date .small {{ font-size: 26px; }}
    .sec-title {{ font-size: 22px; }}
    .sec-mark {{ font-size: 26px; }}
    .card-summary {{ margin-left: 0; padding-left: 10px; }}
    .footer-docs {{ gap: 10px; }}
    .footer-docs a {{ font-size: 11px; }}
  }}

  @media (prefers-reduced-motion: reduce) {{
    * {{ transition: none !important; animation: none !important; }}
    html {{ scroll-behavior: auto; }}
    .card:hover {{ transform: none; }}
    .reveal, .reveal-sec {{ opacity: 1 !important; }}
    /* 跑马灯为核心品牌元素，始终滚动（不受“减少动态”影响） */
    .ticker-track {{ animation: tickerScroll 40s linear infinite !important; }}
  }}
</style>
</head>
<body {body_attrs}>

<!-- 顶部 ticker：随页面滚动上移；topbar 保持固定 -->
<div class="ticker" aria-label="站点说明">
  <div class="ticker-track">
    <span class="ticker-item">📡 数据来源：AIHOT (aihot.virxact.com)</span>
    <span class="ticker-item">更多 AI 内容请关注公众号<strong class="ticker-brand">「深南Ai视界」</strong></span>
    <span class="ticker-item">本站为个人非盈利 AI 资讯索引</span>
    <!-- 复制一份做无缝循环（动画 translateX(-50%) 时第一份完全滑出、第二份顶上） -->
    <span class="ticker-item" aria-hidden="true">📡 数据来源：AIHOT (aihot.virxact.com)</span>
    <span class="ticker-item" aria-hidden="true">更多 AI 内容请关注公众号<strong class="ticker-brand">「深南Ai视界」</strong></span>
    <span class="ticker-item" aria-hidden="true">本站为个人非盈利 AI 资讯索引</span>
  </div>
</div>

<!-- 顶部工具栏：首页隐藏（工具已合并进 nav），报告页显示报告切换/返回今日 -->
<div class="topbar">
  {period_or_range}
  {topbar_tools_html}
</div>

<div class="wrap">
  <!-- HERO -->
  <header class="hero">
    <div class="brand-logo">
      {logo_img}
    </div>
    <div class="hero-sub"><span class="sub-brand">深南AI日报</span></div>
    {hero_headline}
    <div class="hero-grid">
      <div>
        {hero_date_block}
        <div class="hero-lead">
          {hero_lead_text}
        </div>
      </div>
      <div class="hero-stats cols-{grid_cols}">
        {hero_stat_cells}
        <div class="stat-total">
          <span class="num">{total}</span>
          <span class="lab">Total · 总条数</span>
        </div>
      </div>
    </div>
  </header>
</div>

<!-- STICKY NAV：首页右侧合并报告/历史日报/导出，8 个胶囊同一行对齐 -->
<nav class="nav">
  <div class="nav-inner">
    {nav_html}
    {nav_actions_html}
  </div>
</nav>

<div class="wrap">
  <main class="main">
    {sections_html}
  </main>
</div>

  <footer class="footer">
    <!-- 1 本期共 -->
    <div class="footer-meta">
      本期共 <span class="num">{total}</span> 条 · {len(cards_by_section)} 个版块 · {date_str}
    </div>
    <!-- 2 数据源 -->
    <div class="footer-source">
      数据源：<a href="https://aihot.virxact.com" target="_blank" rel="noopener noreferrer">aihot.virxact.com</a> · AI HOT 日报
    </div>
    <!-- 3 分割线 -->
    <div class="footer-line-bold"></div>
    <!-- 4 Designed -->
    <div class="footer-mark">Designed by Jaysn</div>
    <!-- 5 Copyright -->
    <div class="footer-copyright">Copyright © 2026 深南Ai视界·All Rights Reserved</div>
    <!-- （v1.8.7 留言/反馈按钮移到右下 FAB 区，footer 不再放） -->
    <!-- 文档入口：黑色 → 深蓝渐变底条，链接十字居中（全宽拉通，脱离 .wrap 约束） -->
    <div class="footer-bottom">
      <nav class="footer-docs">
        <a href="{doc_prefix}report.html">{ICON_REPORT}聚合报告</a>
        <a href="{doc_prefix}license.html">{ICON_SCALE}LICENSE</a>
        <a href="{doc_prefix}disclaimer.html">{ICON_ALERT}免责声明</a>
        <a href="{REPO_URL}" target="_blank" rel="noopener noreferrer">{ICON_GITHUB}仓库地址</a>
        <a href="{doc_prefix}about.html">{ICON_README}关于项目</a>
      </nav>
    </div>
  </footer>

<!-- 留言模态框（提交为 GitHub Issue，不暴露真实邮箱） -->
<div class="contact-modal" id="contactModal" aria-hidden="true">
  <div class="contact-card" role="dialog" aria-modal="true" aria-labelledby="contactTitle">
    <button class="contact-close" id="contactClose" type="button" aria-label="关闭">×</button>
    <h3 id="contactTitle">留言 / 反馈</h3>
    <p class="tip">留言会以 GitHub Issue 形式提交（需登录 GitHub，天然过滤垃圾信息）。我会在 Issue 里收到通知并回复你，不会公开你的邮箱。</p>
    <label for="contactName">昵称（选填）</label>
    <input id="contactName" type="text" maxlength="40" placeholder="如何称呼你">
    <label for="contactMsg">留言内容 *</label>
    <textarea id="contactMsg" placeholder="纠错、合作、建议、想说的……"></textarea>
    <input class="hp" id="contactHp" type="text" tabindex="-1" autocomplete="off" aria-hidden="true">
    <div class="contact-actions">
      <button class="cancel" id="contactCancel" type="button">取消</button>
      <button class="send" id="contactSend" type="button">发送留言</button>
    </div>
  </div>
</div>

<script src="{exports_js_url}"></script>
<script>
  // 等待 DOM 完整后再绑定交互（修复 FAB 在脚本之后导致 getElementById 拿 null 的 bug）
  document.addEventListener('DOMContentLoaded', function() {{

  // Dropdown toggles
  (function() {{
    function toggleDropdown(dropdown) {{
      const wasOpen = dropdown.classList.contains('open');
      document.querySelectorAll('.dropdown').forEach(d => d.classList.remove('open'));
      if (!wasOpen) dropdown.classList.add('open');
    }}
    document.querySelectorAll('.dropdown').forEach(dropdown => {{
      const btn = dropdown.querySelector('.top-btn');
      btn.addEventListener('click', (e) => {{ e.stopPropagation(); toggleDropdown(dropdown); }});
    }});
    document.addEventListener('click', () => {{
      document.querySelectorAll('.dropdown').forEach(d => d.classList.remove('open'));
    }});
  }})();

  // Exports
  (function() {{
    function downloadBlob(blob, filename) {{
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(a.href);
      a.remove();
    }}
    function downloadText(text, filename, type) {{
      downloadBlob(new Blob([text], {{type: type || 'text/plain;charset=utf-8'}}), filename);
    }}

    let currentScope = 'today';
    const scopeItems = document.querySelectorAll('[data-export-scope]');
    scopeItems.forEach(el => {{
      el.addEventListener('click', (e) => {{
        e.preventDefault();
        currentScope = el.dataset.exportScope;
        scopeItems.forEach(s => s.classList.remove('active'));
        el.classList.add('active');
      }});
    }});

    document.querySelectorAll('[data-export]').forEach(el => {{
      el.addEventListener('click', (e) => {{
        e.preventDefault();
        const fmt = el.dataset.export;
        const payload = window.SN_EXPORT[currentScope];
        if (!payload) return;
        const date = payload.date;
        if (fmt === 'html') {{
          const source = '<!DOCTYPE html>\\n' + document.documentElement.outerHTML;
          downloadText(source, `shennan-ai-daily-${{date}}.html`, 'text/html;charset=utf-8');
        }} else if (fmt === 'markdown') {{
          downloadText(payload.markdown, `shennan-ai-daily-${{date}}.md`, 'text/markdown;charset=utf-8');
        }} else if (fmt === 'csv') {{
          downloadText(payload.csv, `shennan-ai-daily-${{date}}.csv`, 'text/csv;charset=utf-8');
        }} else if (fmt === 'png') {{
          html2canvas(document.body, {{backgroundColor: '#0A0E1A', scale: 2}}).then(canvas => {{
            canvas.toBlob(blob => downloadBlob(blob, `shennan-ai-daily-${{date}}.png`));
          }});
        }} else if (fmt === 'pdf') {{
          const opt = {{
            margin: 0,
            filename: `shennan-ai-daily-${{date}}.pdf`,
            image: {{type: 'jpeg', quality: 0.96}},
            html2canvas: {{scale: 2, backgroundColor: '#0A0E1A', useCORS: true}},
            jsPDF: {{unit: 'in', format: 'letter', orientation: 'portrait'}}
          }};
          html2pdf().set(opt).from(document.body).save();
        }}
      }});
    }});
  }})();

  // 2) 锚点导航高亮当前版块
  (function() {{
    const chips = Array.from(document.querySelectorAll('.nav-chip'));
    const sections = chips.map(c => document.querySelector(c.getAttribute('href')));
    if (!('IntersectionObserver' in window)) return;
    const io = new IntersectionObserver((entries) => {{
      entries.forEach(e => {{
        if (e.isIntersecting) {{
          if (chips.some(c => c.classList.contains('active'))) {{
            chips.forEach(c => c.classList.remove('active'));
          }}
          const id = e.target.id;
          chips.forEach(c => {{
            const active = c.getAttribute('href') === '#' + id;
            c.classList.toggle('is-active-by-io', active);
          }});
        }}
      }});
    }}, {{ rootMargin: '-30% 0px -60% 0px' }});
    sections.forEach(s => s && io.observe(s));
  }})();

  // 3) 滚动入场动效
  (function() {{
    if (!('IntersectionObserver' in window)) {{
      document.querySelectorAll('.reveal-sec').forEach(s => s.classList.add('in-view'));
      return;
    }}
    const io = new IntersectionObserver((entries) => {{
      entries.forEach(e => {{
        if (e.isIntersecting) {{
          e.target.classList.add('in-view');
          io.unobserve(e.target);
        }}
      }});
    }}, {{ rootMargin: '0px 0px -8% 0px', threshold: 0.05 }});
    document.querySelectorAll('.reveal-sec').forEach(s => io.observe(s));
    // 兜底：3 秒后仍未入场的 section 直接显示，避免移动端 observer 偶发失效导致空白
    setTimeout(() => {{
      document.querySelectorAll('.reveal-sec:not(.in-view)').forEach(s => s.classList.add('in-view'));
    }}, 3000);
  }})();

  // 移动端滚动时隐藏顶栏/导航（向下滑隐藏，向上滑恢复），避免与内容争空间
  (function() {{
    const nav = document.querySelector('.nav');
    const bar = document.querySelector('.topbar');
    let lastY = window.scrollY || 0;
    let ticking = false;
    function apply() {{
      const y = window.scrollY || 0;
      const isMobile = window.innerWidth <= 880;
      const goingDown = y > lastY && y > 120;
      if (isMobile && goingDown) {{
        nav && nav.classList.add('hide');
      }} else {{
        nav && nav.classList.remove('hide');
      }}
      lastY = y;
      ticking = false;
    }}
    window.addEventListener('scroll', function() {{
      if (!ticking) {{ requestAnimationFrame(apply); ticking = true; }}
    }}, {{ passive: true }});
    window.addEventListener('resize', apply);
  }})();

  // 4) 早中晚时段检测、主题切换、悬浮按钮
  (function() {{
    const BEIJING_OFFSET = 8 * 60;
    function nowInBeijing() {{
      const d = new Date();
      const utc = d.getTime() + d.getTimezoneOffset() * 60000;
      return new Date(utc + BEIJING_OFFSET * 60000);
    }}
    function getPeriod(h) {{
      if (h >= 6 && h < 12) return 'morning';
      if (h >= 12 && h < 18) return 'noon';
      return 'night';
    }}
    function periodTheme(p) {{
      return (p === 'morning' || p === 'noon') ? 'light' : 'dark';
    }}

    const periodTip = {{
      morning: '早报：08:10 更新',
      noon: '午报：12:30 更新',
      night: '晚报：18:30 更新'
    }};

    const chips = Array.from(document.querySelectorAll('.time-chip'));
    const body = document.body;
    const savedTheme = localStorage.getItem('sn-theme');
    let userOverrode = false;

    function applyTheme(theme) {{
      document.documentElement.setAttribute('data-theme', theme);
    }}

    function setChips(activeKey) {{
      chips.forEach(btn => {{
        const key = btn.dataset.period;
        const isFuture = (key === 'noon' && activeKey === 'morning') ||
                         (key === 'night' && activeKey !== 'night');
        btn.classList.toggle('active', key === activeKey);
        btn.disabled = isFuture;
        btn.title = isFuture ? `将于 ${{'morning':'08:10','noon':'12:30','night':'18:30'}}[key] 更新` : periodTip[key];
      }});
    }}

    function updatePeriod() {{
      const beijing = nowInBeijing();
      const period = getPeriod(beijing.getHours());
      if (!userOverrode) applyTheme(periodTheme(period));
      setChips(period);
      return period;
    }}

    // 初始化
    const initialPeriod = updatePeriod();
    if (savedTheme === 'light' || savedTheme === 'dark') {{
      applyTheme(savedTheme);
      userOverrode = true;
    }}

    // 点击切换时段（仅切换视觉/主题，不重新拉数据；未来时段不可点）
    chips.forEach(btn => {{
      btn.addEventListener('click', () => {{
        if (btn.disabled) return;
        const key = btn.dataset.period;
        setChips(key);
        applyTheme(periodTheme(key));
        userOverrode = true;
        localStorage.setItem('sn-theme', periodTheme(key));
      }});
    }});

    // 主题切换按钮
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {{
      themeBtn.addEventListener('click', () => {{
        const current = document.documentElement.getAttribute('data-theme') || 'dark';
        const next = current === 'light' ? 'dark' : 'light';
        applyTheme(next);
        userOverrode = true;
        localStorage.setItem('sn-theme', next);
      }});
    }}

    // 到顶/到底
    const topBtn = document.getElementById('scrollTop');
    const bottomBtn = document.getElementById('scrollBottom');
    if (topBtn) topBtn.addEventListener('click', () => window.scrollTo({{top: 0, behavior: 'smooth'}}));
    if (bottomBtn) bottomBtn.addEventListener('click', () => window.scrollTo({{top: document.body.scrollHeight, behavior: 'smooth'}}));

    // 每到整点重新检测时段；若日期/时段变化则刷新页面以获取新数据
    setInterval(() => {{
      const beijing = nowInBeijing();
      const period = getPeriod(beijing.getHours());
      const pagePeriod = body.dataset.pagePeriod || initialPeriod;
      const pageDate = body.dataset.pageDate || '';
      const todayStr = [beijing.getFullYear(), String(beijing.getMonth()+1).padStart(2,'0'), String(beijing.getDate()).padStart(2,'0')].join('-');
      if (period !== pagePeriod || todayStr !== pageDate) {{
        // 仅在接近更新时刻（08:10, 12:30, 18:30）或日期变化时自动刷新
        const m = beijing.getHours() * 60 + beijing.getMinutes();
        const nearUpdate = (m >= 490 && m <= 495) || (m >= 750 && m <= 755) || (m >= 1110 && m <= 1115) || todayStr !== pageDate;
        if (nearUpdate) window.location.reload();
      }}
      if (!userOverrode) applyTheme(periodTheme(period));
    }}, 60000);
  }})();

  // Contact modal -> GitHub Issue（不暴露真实邮箱，GitHub 登录天然过滤垃圾）
  (function () {{
    var btn = document.getElementById('contactBtn');
    var modal = document.getElementById('contactModal');
    var closeB = document.getElementById('contactClose');
    var cancelB = document.getElementById('contactCancel');
    var sendB = document.getElementById('contactSend');
    var nameEl = document.getElementById('contactName');
    var msgEl = document.getElementById('contactMsg');
    var hp = document.getElementById('contactHp');
    var REPO = '{REPO_URL}';
    if (!btn || !modal) return;
    function openM() {{ modal.classList.add('open'); modal.setAttribute('aria-hidden', 'false'); msgEl.focus(); }}
    function shutM() {{ modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); }}
    btn.addEventListener('click', openM);
    closeB.addEventListener('click', shutM);
    cancelB.addEventListener('click', shutM);
    modal.addEventListener('click', function (e) {{ if (e.target === modal) shutM(); }});
    document.addEventListener('keydown', function (e) {{ if (e.key === 'Escape' && modal.classList.contains('open')) shutM(); }});
    sendB.addEventListener('click', function () {{
      var msg = msgEl.value.trim();
      if (!msg) {{ msgEl.focus(); return; }}
      if (hp.value) return;
      var name = nameEl.value.trim() || '匿名读者';
      var title = encodeURIComponent('读者留言 · ' + name);
      var body = encodeURIComponent('来自深南AI日报网页留言框\\n\\n昵称：' + name + '\\n\\n---\\n' + msg + '\\n\\n（本 Issue 由站点留言框自动创建）');
      var url = REPO + '/issues/new?title=' + title + '&body=' + body + '&labels=feedback';
      window.open(url, '_blank', 'noopener');
      shutM();
    }});
  }})();

  }}); // DOMContentLoaded end
</script>

<!-- 右侧悬浮按钮：主题切换 / 到顶 / 到底 — inline onclick 确保点击必响应（绕过 DOMContentLoaded/ID 查找依赖） -->
<div class="fab-group" aria-label="快捷操作">
  <button type="button" class="fab" id="themeToggle" onclick="window.snToggleTheme()" aria-label="切换深浅模式" title="切换深浅模式">
    <svg class="fab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
  </button>
  <button type="button" class="fab" id="scrollTop" onclick="window.scrollTo({{top:0,behavior:'smooth'}})" aria-label="回到顶部" title="回到顶部">
    <svg class="fab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m18 15-6-6-6 6"/></svg>
  </button>
  <button type="button" class="fab" id="scrollBottom" onclick="window.scrollTo({{top:document.body.scrollHeight,behavior:'smooth'}})" aria-label="回到底部" title="回到底部">
    <svg class="fab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
  </button>
</div>

<!-- 留言 / 反馈 FAB（v1.8.7 从 footer 提到右下）— 跟 FAB 同样视觉，hover 展开显示文字 -->
<button type="button" class="fab-contact" id="contactBtn" onclick="window.snOpenContact()" aria-label="留言 / 反馈" title="留言 / 反馈">
  <svg class="fab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
  <span class="fab-label">💬 留言 / 反馈</span>
</button>

</body>
</html>
"""


# ---------- 站内文档子页面（LICENSE / 免责声明 / 关于项目） ----------
def md_light(md_text):
    """极简 Markdown → HTML：标题 / 列表 / 段落 / 代码块，够用即可，不引第三方库。"""
    lines = md_text.splitlines()
    out = []
    in_ul = False
    in_pre = False
    pre_buf = []

    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    for ln in lines:
        s = ln.rstrip()
        if s.startswith("```"):
            if in_pre:
                out.append("<pre class='doc-pre'>" + html.escape("\n".join(pre_buf)) + "</pre>")
                pre_buf = []
                in_pre = False
            else:
                close_ul()
                in_pre = True
            continue
        if in_pre:
            pre_buf.append(s)
            continue
        if not s.strip():
            close_ul()
            continue
        if s.startswith("### "):
            close_ul()
            out.append("<h3>" + html.escape(s[4:].strip()) + "</h3>")
        elif s.startswith("## "):
            close_ul()
            out.append("<h2>" + html.escape(s[3:].strip()) + "</h2>")
        elif s.startswith("# "):
            close_ul()
            out.append("<h2>" + html.escape(s[2:].strip()) + "</h2>")
        elif s.startswith("- ") or s.startswith("* "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append("<li>" + html.escape(s[2:].strip()) + "</li>")
        else:
            close_ul()
            out.append("<p>" + html.escape(s) + "</p>")
    close_ul()
    if in_pre:
        out.append("<pre class='doc-pre'>" + html.escape("\n".join(pre_buf)) + "</pre>")
    return "\n".join(out)


DOC_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__ · 深南AI日报</title>
<style>
__FONTS__
  :root {
    --ink-void:#0A0E1A; --ink-deep:#0F1424; --ink-card:#141C32; --ink-card-hi:#1A2440;
    --brand-cn:#cdc8ff; --brand-brief:#DDD090;
    --gold:#DAC887; --gold-soft:#A8965A;
    --mist:#DDE2F0; --mist-body:#BEC4DC; --mist-dim:#9CA4C2; --mist-faint:#6E7793;
    --btn:#4F5CC7; --btn-hi:#6470DC;
    --line:rgba(46,58,124,.4); --line-faint:rgba(46,58,124,.22); --line-gold:rgba(218,200,135,.35);
    --text-title:#F0F2FA; --text-primary:#DDE2F0; --text-body:#BEC4DC;
    --text-secondary:#9CA4C2; --text-tertiary:#6E7793; --text-accent:#cdc8ff;
    --text-link:#BDC3FF; --text-code:#BEC4DC;
    --surface-float:rgba(20,28,50,.72); --surface-modal:rgba(15,20,36,.96);
    --surface-chip:rgba(20,28,50,.5); --surface-code:rgba(20,28,50,.7);
    --shadow:rgba(0,0,0,.55);
    --font-base:'Poppins','PingFang SC','Microsoft YaHei','Hiragino Sans GB','Noto Sans CJK SC',system-ui,sans-serif;
    --font-cn-display:'ZCOOL XiaoWei','PingFang SC','Microsoft YaHei','Hiragino Sans GB','Noto Sans CJK SC',system-ui,serif;
  }
  [data-theme="light"] {
    --ink-void:#F5F1E6; --ink-deep:#2A2520; --ink-card:#FFFFFF; --ink-card-hi:#FDFAF1;
    --brand-cn:#4A5BC4; --brand-brief:#A87E2A;
    --gold:#A87E2A; --gold-soft:#856020;
    --mist:#2A2520; --mist-body:#4A4540; --mist-dim:#7A7268; --mist-faint:#A89F8E;
    --btn:#3B4AA8; --btn-hi:#5466D2;
    --line:rgba(168,126,42,.20); --line-faint:rgba(168,126,42,.12); --line-gold:rgba(168,126,42,.32);
    --text-title:#2A2520; --text-primary:#2A2520; --text-body:#4A4540;
    --text-secondary:#7A7268; --text-tertiary:#A89F8E; --text-accent:#A87E2A;
    --text-link:#3B4AA8; --text-code:#4A4540;
    --surface-float:rgba(255,252,245,.82); --surface-modal:rgba(255,252,245,.98);
    --surface-chip:rgba(232,226,208,.85); --surface-code:rgba(232,226,208,.95);
    --shadow:rgba(46,58,124,.15);
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--ink-void); color:var(--mist-body); font-family:var(--font-base); line-height:1.8; -webkit-font-smoothing:antialiased; }
  .doc-wrap { max-width:780px; margin:0 auto; padding:48px 24px 60px; }
  .doc-home { display:inline-block; color:var(--brand-cn); text-decoration:none; font-size:13px; letter-spacing:.06em; margin-bottom:28px; opacity:.85; }
  .doc-home:hover { opacity:1; }
  .doc-brand { display:flex; align-items:center; gap:14px; margin-bottom:6px; }
  .doc-brand .sn-logo { width:48px; height:48px; object-fit:contain; }
  .doc-brand h1 { font-family:var(--font-cn-display); font-weight:100; font-size:30px; color:var(--text-title); letter-spacing:.02em; }
  .doc-body { margin-top:26px; }
  .doc-body h2 { font-family:var(--font-cn-display); font-size:21px; color:var(--text-title); margin:28px 0 12px; font-weight:100; border-left:3px solid var(--brand-brief); padding-left:12px; }
  .doc-body h3 { font-size:17px; color:var(--brand-cn); margin:20px 0 8px; }
  .doc-body p { margin:12px 0; color:var(--mist-body); }
  .doc-body ul { margin:12px 0 12px 22px; }
  .doc-body li { margin:6px 0; }
  .doc-body a { color:var(--brand-cn); }
  .doc-pre { background:rgba(20,28,50,.6); border:1px solid rgba(46,58,124,.4); border-radius:8px; padding:16px 18px; overflow-x:auto; font-family:'SF Mono','Fira Code',Consolas,monospace; font-size:13px; color:var(--text-code); white-space:pre-wrap; word-break:break-word; }
  .doc-foot { margin-top:48px; padding-top:20px; border-top:1px solid var(--line-gold); text-align:center; font-size:12px; color:var(--mist-faint); letter-spacing:.08em; }
</style>
</head>
<body>
<div class="doc-wrap">
  <a class="doc-home" href="./">← 返回首页 / Home</a>
  <div class="doc-brand">__LOGO__<h1>__TITLE__</h1></div>
  <div class="doc-body">__BODY__</div>
  <div class="doc-foot">深南Ai视界 · Daily AI Brief · 开源非盈利</div>
</div>
</body>
</html>"""


def render_doc_page(title, body_html, logo_img, fonts_css):
    return (DOC_TEMPLATE
            .replace("__TITLE__", title)
            .replace("__LOGO__", logo_img)
            .replace("__FONTS__", fonts_css)
            .replace("__BODY__", body_html))


# ---------- archive management ----------
def cleanup_old_archives(keep_days=30):
    """Remove dist/daily/YYYY-MM-DD.html files older than keep_days."""
    cutoff = date.today() - timedelta(days=keep_days)
    removed = 0
    for fp in DAILY_DIR.glob("*.html"):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})\.html", fp.name)
        if not m:
            continue
        file_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if file_date < cutoff:
            fp.unlink()
            removed += 1
    return removed


# ---------- main ----------
def main():
    # Fonts
    if FONTS_CSS.exists():
        fonts_css = FONTS_CSS.read_text(encoding="utf-8")
        print(f"fonts.css loaded: {FONTS_CSS.stat().st_size/1048576:.2f}MB")
    else:
        fonts_css = ""
        print("WARNING: fonts.css not found, falling back to system fonts")

    # Logo (base64 inlined)
    logo_png = DIST / "logo.png"
    if logo_png.exists():
        logo_b64 = base64.b64encode(logo_png.read_bytes()).decode("ascii")
        logo_img = f'<img class="sn-logo" src="data:image/png;base64,{logo_b64}" alt="深南AI日报" width="44" height="44">'
    else:
        logo_img = '<img class="sn-logo" src="logo.png" alt="深南AI日报" width="44" height="44">'

    page_common = {"fonts_css": fonts_css, "logo_img": logo_img}

    # Latest data
    latest_data = load_daily()
    latest_info = parse_data(latest_data)
    latest_date = latest_info["date_str"]

    # History dates (last 30 days)
    available_dates = load_history_dates(take=30)
    if latest_date not in available_dates:
        available_dates.insert(0, latest_date)

    # Export scopes: today / week / month
    export_scopes = {
        "today": {
            "date": latest_date,
            "markdown": export_markdown(latest_info),
            "csv": export_csv(latest_info),
        }
    }
    if len(available_dates) >= 2:
        week_info = aggregate_info(available_dates[:7])
        export_scopes["week"] = {
            "date": week_info["date_str"],
            "markdown": export_markdown(week_info),
            "csv": export_csv(week_info),
        }
    if len(available_dates) >= 8:
        month_info = aggregate_info(available_dates[:30])
        export_scopes["month"] = {
            "date": month_info["date_str"],
            "markdown": export_markdown(month_info),
            "csv": export_csv(month_info),
        }

    # Clean old archives
    removed = cleanup_old_archives(keep_days=30)
    if removed:
        print(f"Removed {removed} old daily archive(s)")

    # Write exports.js (shared by all pages — eliminates ~426KB inline per page)
    scope_js_parts = []
    for key, sc in export_scopes.items():
        md = sc["markdown"].replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        csv = sc["csv"].replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        scope_js_parts.append(f'  {key}: {{ date: {json.dumps(sc["date"])}, markdown: `{md}`, csv: `{csv}` }}')
    exports_js_content = f"/* Auto-generated by generate_dashboard.py */\nwindow.SN_EXPORT = {{\n{',\n'.join(scope_js_parts)}\n}};\n"
    (RELEASES / "exports.js").write_text(exports_js_content, encoding="utf-8")
    print(f"OK -> exports.js ({len(exports_js_content)} bytes)")

    # Generate daily pages for all available dates (skip existing to save time)
    generated_days = 0
    for ds in available_dates:
        target = DAILY_DIR / f"{ds}.html"
        if target.exists():
            continue
        try:
            day_data = load_daily(ds)
            day_info = parse_data(day_data)
            page = render_html(
                day_info,
                {**page_common, "history_prefix": "./", "asset_base": "../", "doc_prefix": "../", "current_date": ds, "available_dates": available_dates, "is_index": False, "export_scopes": export_scopes}
            )
            target.write_text(page, encoding="utf-8")
            generated_days += 1
        except Exception as e:
            print(f"WARNING: failed to generate daily page for {ds}: {e}")
    print(f"Generated {generated_days} new daily page(s)")

    # Generate latest index.html
    index_page = render_html(
        latest_info,
        {**page_common, "history_prefix": "./daily/", "asset_base": "", "doc_prefix": "", "current_date": latest_date, "available_dates": available_dates, "is_index": True, "export_scopes": export_scopes}
    )
    latest_file = RELEASES / "index.html"
    latest_file.write_text(index_page, encoding="utf-8")

    # Generate report pages (week / month)
    report_base = {**page_common, "history_prefix": "./daily/", "asset_base": "", "doc_prefix": "", "current_date": latest_date, "available_dates": available_dates, "is_index": False, "export_scopes": export_scopes}
    if len(available_dates) >= 2:
        week_report = render_html(week_info, {**report_base, "is_report": True, "report_range": "week"})
        (RELEASES / "report-week.html").write_text(week_report, encoding="utf-8")
        print("OK -> report-week.html")
    if len(available_dates) >= 8:
        month_report = render_html(month_info, {**report_base, "is_report": True, "report_range": "month"})
        (RELEASES / "report-month.html").write_text(month_report, encoding="utf-8")
        print("OK -> report-month.html")
    # Default report entry redirects to week
    (RELEASES / "report.html").write_text(
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta http-equiv="refresh" content="0; url=report-week.html"><title>聚合报告 · 深南AI日报</title></head><body style="background:#0A0E1A;color:#6E7793;font-family:sans-serif;text-align:center;padding-top:40vh;">跳转至聚合报告…</body></html>',
        encoding="utf-8"
    )
    print("OK -> report.html")

    # Versioned release archive (latest only, in releases/)
    d = latest_info["d"]
    date_suffix = f"{d.year % 100:02d}{d.month:02d}{d.day:02d}"
    versioned_name = f"ai-daily-v{VERSION}_{date_suffix}.html"
    dated_release = RELEASES / versioned_name
    page = render_html(
        latest_info,
        {**page_common, "history_prefix": "./daily/", "asset_base": "", "doc_prefix": "", "current_date": latest_date, "available_dates": available_dates, "is_index": False, "export_scopes": export_scopes}
    )
    dated_release.write_text(page, encoding="utf-8")

    # 站内文档子页面：LICENSE / 免责声明 / 关于项目（更正式，替代仓库 blob 链接）
    def _read_doc(p):
        fp = BASE / p
        return fp.read_text(encoding="utf-8") if fp.exists() else "（内容缺失）"
    license_body = "<pre class='doc-pre'>" + html.escape(_read_doc("LICENSE")) + "</pre>"
    disclaimer_body = md_light(_read_doc("DISCLAIMER.md"))
    about_body = md_light(_read_doc("README.md"))
    for fname, ttl, body in [
        ("license.html", "开源许可 LICENSE", license_body),
        ("disclaimer.html", "免责声明 Disclaimer", disclaimer_body),
        ("about.html", "关于本项目 About", about_body),
    ]:
        (RELEASES / fname).write_text(render_doc_page(ttl, body, logo_img, fonts_css), encoding="utf-8")
        print(f"OK -> doc page: {fname}")

    # 禁用 Jekyll（避免 GitHub Pages 清空预构建 HTML）
    (RELEASES / ".nojekyll").write_text("")
    print("OK -> .nojekyll")

    # robots.txt（站点托管于 GitHub Pages 子路径 /shennan-ai-daily/，
    # 此文件即服务于该子路径；Allow 全站，不暴露任何私有路径）
    (RELEASES / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        "# 深南AI日报 Daily AI Brief — 个人非盈利 AI 资讯索引\n",
        encoding="utf-8",
    )
    print("OK -> robots.txt")

    # 复制字体资源到 releases/fonts/，使发布目录自洽
    # （CI 发布 publish_dir=./releases；若字体留在 dist/，线上会 404）
    src_fonts = DIST / "fonts"
    dst_fonts = RELEASES / "fonts"
    if src_fonts.is_dir():
        if dst_fonts.exists():
            shutil.rmtree(dst_fonts)
        shutil.copytree(src_fonts, dst_fonts)
        print(f"OK -> copied fonts -> releases/fonts ({len(list(dst_fonts.glob('*.woff2')))} woff2)")
    else:
        print("WARNING: dist/fonts not found; web fonts may 404 on deploy")

    print(f"Version: v{VERSION}_{date_suffix}")
    print(f"OK -> release: {dated_release.name}")
    print(f"OK -> latest: {latest_file.name}")
    print(f"File size: {dated_release.stat().st_size/1048576:.1f}MB")
    print(f"Total items: {latest_info['total']}")
    for s in latest_info["cards_by_section"]:
        print(f"  {s['roman']} {s['display_label']}: {s['count']}")


if __name__ == "__main__":
    main()

"""Build a static HTML dashboard from scored job data."""

import html
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
CONFIG_PATH = ROOT / "config" / "profile.yaml"


def _load_profile():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_scored_jobs():
    path = DATA_DIR / "scored_jobs.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "")


def _matched_skills(job, stack_terms):
    text = (job.get("title", "") + " " + job.get("description", "") + " " + " ".join(job.get("tags", []))).lower()
    return [t for t in stack_terms if t.lower() in text][:5]


def _relative_date(date_str):
    if not date_str:
        return "unknown date"
    try:
        d = datetime.fromisoformat(date_str).date()
        delta = (datetime.now(timezone.utc).date() - d).days
        if delta == 0:
            return "today"
        if delta == 1:
            return "yesterday"
        if delta < 7:
            return f"{delta} days ago"
        if delta < 30:
            w = delta // 7
            return f"{w} week{'s' if w > 1 else ''} ago"
        return f"{delta // 30} month{'s' if delta // 30 > 1 else ''} ago"
    except (ValueError, TypeError):
        return "unknown date"


def build_dashboard():
    profile = _load_profile()
    jobs = _load_scored_jobs()
    stack_terms = list((profile.get("stack_weights") or {}).keys())
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    cards_data = []
    for j in jobs:
        skills = _matched_skills(j, stack_terms)
        if not skills:
            skills = j.get("tags", [])[:5]
        desc_plain = _strip_html(j.get("description", ""))
        desc_preview = desc_plain[:400] + ("..." if len(desc_plain) > 400 else "")
        breakdown = j.get("score_breakdown", {})
        cards_data.append({
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "score": j.get("score", 0),
            "url": j.get("url", ""),
            "source": j.get("source", ""),
            "date": j.get("date", ""),
            "relative_date": _relative_date(j.get("date", "")),
            "tags": skills,
            "via_aggregator": j.get("via_aggregator", False),
            "breakdown": breakdown,
            "desc_preview": desc_preview,
            "remote": j.get("remote", False),
        })

    jobs_json = json.dumps(cards_data, ensure_ascii=False)

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>job-engine</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --midnight-abyss: #0B1416;
  --midnight-2: #11201F;
  --aqua-jade: #2E8B82;
  --aqua-bright: #3FB8AC;
  --baby-pink: #F4B8C4;
  --text-primary: #EAF2F1;
  --text-muted: #8BA6A3;
  --danger-muted: #C97A86;
  --card-border: rgba(46, 139, 130, 0.25);
  --card-shadow: 0 2px 12px rgba(0,0,0,0.3);
  --radius: 16px;
}}
html {{ background: var(--midnight-abyss); }}
body {{
  font-family: 'Inter', system-ui, sans-serif;
  font-weight: 400;
  color: var(--text-primary);
  background: var(--midnight-abyss);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}}
h1, h2, h3, h4 {{ font-family: 'Space Grotesk', sans-serif; font-weight: 600; }}

/* ── Header ── */
.header {{
  position: sticky; top: 0; z-index: 100;
  background: var(--midnight-abyss);
  border-bottom: 1px solid var(--card-border);
  padding: 16px 24px;
  display: flex; align-items: center; justify-content: space-between;
  backdrop-filter: blur(12px);
}}
.header-title {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 1.35rem; }}
.header-title .dot {{ color: var(--baby-pink); }}
.header-meta {{ font-size: 0.82rem; color: var(--text-muted); text-align: right; line-height: 1.5; }}

/* ── Tabs ── */
.tabs {{
  display: flex; gap: 0; padding: 0 24px;
  border-bottom: 1px solid var(--card-border);
  margin-bottom: 20px;
}}
.tab {{
  padding: 12px 24px; cursor: pointer;
  font-family: 'Space Grotesk', sans-serif; font-weight: 500; font-size: 0.95rem;
  color: var(--text-muted); border-bottom: 2px solid transparent;
  transition: color 0.2s, border-color 0.2s;
  user-select: none;
}}
.tab:hover {{ color: var(--text-primary); }}
.tab.active {{ color: var(--aqua-bright); border-bottom-color: var(--aqua-bright); }}

/* ── Filters ── */
.filters {{
  display: flex; gap: 12px; padding: 0 24px 20px; flex-wrap: wrap; align-items: center;
}}
.search-input {{
  flex: 1; min-width: 200px;
  background: var(--midnight-2); border: 1px solid var(--card-border);
  border-radius: 10px; padding: 10px 16px;
  color: var(--text-primary); font-family: 'Inter', sans-serif; font-size: 0.9rem;
  outline: none; transition: border-color 0.2s;
}}
.search-input::placeholder {{ color: var(--text-muted); }}
.search-input:focus {{ border-color: var(--aqua-bright); }}
.sort-select {{
  background: var(--midnight-2); border: 1px solid var(--card-border);
  border-radius: 10px; padding: 10px 16px;
  color: var(--text-primary); font-family: 'Inter', sans-serif; font-size: 0.9rem;
  outline: none; cursor: pointer;
}}
.sort-select:focus {{ border-color: var(--aqua-bright); }}

/* ── Grid ── */
.grid {{
  display: grid; gap: 20px; padding: 0 24px 40px;
  grid-template-columns: 1fr;
}}
@media (min-width: 640px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
@media (min-width: 1024px) {{ .grid {{ grid-template-columns: repeat(3, 1fr); }} }}

/* ── Card ── */
.card {{
  background: var(--midnight-2);
  border: 1px solid var(--card-border);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--card-shadow);
  transition: border-color 0.2s, box-shadow 0.2s;
  display: flex; flex-direction: column; gap: 12px;
}}
.card:hover {{
  border-color: rgba(63, 184, 172, 0.45);
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}}
.card-top {{ display: flex; align-items: center; gap: 14px; }}
.score-badge {{
  width: 48px; height: 48px; flex-shrink: 0;
  border-radius: 50%;
  border: 2.5px solid var(--aqua-jade);
  display: flex; align-items: center; justify-content: center;
  font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 1rem;
  color: var(--aqua-bright);
}}
.card-title {{
  font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 1.05rem;
  line-height: 1.3;
}}
.card-company {{ color: var(--text-muted); font-size: 0.88rem; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
.agg-pill {{
  display: inline-block; font-size: 0.72rem;
  color: var(--danger-muted); background: rgba(201,122,134,0.12);
  padding: 2px 8px; border-radius: 6px;
}}
.tag-row {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.tag {{
  font-size: 0.76rem; padding: 3px 10px; border-radius: 8px;
  color: var(--baby-pink); background: rgba(244,184,196,0.1);
}}
.card-meta {{ font-size: 0.78rem; color: var(--text-muted); }}
.card-actions {{ display: flex; align-items: center; justify-content: space-between; }}
.apply-btn {{
  display: inline-block; padding: 8px 20px; border-radius: 10px;
  background: var(--baby-pink); color: var(--midnight-abyss);
  font-family: 'Inter', sans-serif; font-weight: 500; font-size: 0.88rem;
  text-decoration: none; transition: opacity 0.2s;
}}
.apply-btn:hover {{ opacity: 0.85; }}
.expand-btn {{
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); font-size: 1.2rem; padding: 4px 8px;
  transition: transform 0.2s, color 0.2s;
}}
.expand-btn:hover {{ color: var(--text-primary); }}
.expand-btn.open {{ transform: rotate(180deg); }}

/* ── Expanded ── */
.card-expanded {{
  display: none; flex-direction: column; gap: 12px;
  padding-top: 12px; border-top: 1px solid var(--card-border);
}}
.card-expanded.show {{ display: flex; }}
.breakdown {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.breakdown-chip {{
  font-size: 0.75rem; padding: 3px 10px; border-radius: 8px;
  background: rgba(46,139,130,0.15); color: var(--aqua-bright);
}}
.desc-preview {{
  font-size: 0.85rem; color: var(--text-muted); line-height: 1.55;
}}
.desc-link {{ color: var(--aqua-bright); text-decoration: none; font-size: 0.82rem; }}
.desc-link:hover {{ text-decoration: underline; }}
.playbook-box {{
  background: rgba(46,139,130,0.08); border: 1px dashed var(--card-border);
  border-radius: 12px; padding: 14px;
}}
.playbook-box h4 {{ font-size: 0.88rem; margin-bottom: 6px; }}
.playbook-box p {{ font-size: 0.8rem; color: var(--text-muted); }}

/* ── Empty state ── */
.empty-state {{
  grid-column: 1 / -1; text-align: center; padding: 60px 24px;
  color: var(--text-muted); font-size: 1rem; line-height: 1.6;
}}

/* ── Mobile ── */
@media (max-width: 639px) {{
  .header {{ padding: 14px 16px; }}
  .tabs {{ padding: 0 16px; }}
  .filters {{ padding: 0 16px 16px; }}
  .grid {{ padding: 0 16px 32px; }}
  .tab {{ padding: 10px 16px; font-size: 0.88rem; }}
}}
</style>
</head>
<body>

<div class="header">
  <div class="header-title">job-engine<span class="dot">.</span></div>
  <div class="header-meta">
    <div>Updated {html.escape(now_str)}</div>
    <div><strong id="job-count">{len(cards_data)}</strong> jobs</div>
  </div>
</div>

<div class="tabs" id="tabs">
  <div class="tab active" data-track="remote">Remote</div>
  <div class="tab" data-track="relocation">Relocation</div>
  <div class="tab" data-track="contract">Contract</div>
</div>

<div class="filters">
  <input class="search-input" id="search" type="text" placeholder="Search title or company...">
  <select class="sort-select" id="sort">
    <option value="score">Score high &rarr; low</option>
    <option value="newest">Newest</option>
    <option value="company">Company A&ndash;Z</option>
  </select>
</div>

<div class="grid" id="grid"></div>

<script>
const JOBS = {jobs_json};
let activeTrack = 'remote';
let searchTerm = '';
let sortMode = 'score';

function escapeHtml(s) {{
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}}

function renderCards() {{
  const grid = document.getElementById('grid');
  const countEl = document.getElementById('job-count');

  if (activeTrack !== 'remote') {{
    grid.innerHTML = '<div class="empty-state">Coming in the next build &mdash; ' +
      (activeTrack === 'relocation' ? 'Gulf relocation roles' : 'contract/freelance targets') +
      ' will live here.</div>';
    countEl.textContent = '0';
    return;
  }}

  let filtered = JOBS.filter(j => {{
    if (!searchTerm) return true;
    const q = searchTerm.toLowerCase();
    return j.title.toLowerCase().includes(q) || j.company.toLowerCase().includes(q);
  }});

  if (sortMode === 'score') filtered.sort((a,b) => b.score - a.score);
  else if (sortMode === 'newest') filtered.sort((a,b) => (b.date||'').localeCompare(a.date||''));
  else if (sortMode === 'company') filtered.sort((a,b) => a.company.localeCompare(b.company));

  countEl.textContent = filtered.length;

  if (!filtered.length) {{
    grid.innerHTML = '<div class="empty-state">No jobs match your search.</div>';
    return;
  }}

  grid.innerHTML = filtered.map((j, i) => {{
    const tags = (j.tags || []).map(t => '<span class="tag">' + escapeHtml(t) + '</span>').join('');
    const aggPill = j.via_aggregator ? '<span class="agg-pill">via aggregator</span>' : '';
    const bd = j.breakdown || {{}};
    const chips = [
      ['Title', bd.title], ['Skills', bd.skills], ['Keywords', bd.keywords],
      ['Remote', bd.remote], ['Recency', bd.recency]
    ].filter(c => c[1] !== undefined).map(c => '<span class="breakdown-chip">' + c[0] + ' ' + c[1] + '</span>').join('');

    return '<div class="card">' +
      '<div class="card-top">' +
        '<div class="score-badge">' + j.score + '</div>' +
        '<div class="card-title">' + escapeHtml(j.title) + '</div>' +
      '</div>' +
      '<div class="card-company">' + escapeHtml(j.company) + aggPill + '</div>' +
      (tags ? '<div class="tag-row">' + tags + '</div>' : '') +
      '<div class="card-meta">' + escapeHtml(j.source) + ' &middot; ' + escapeHtml(j.relative_date) + '</div>' +
      '<div class="card-actions">' +
        '<a class="apply-btn" href="' + escapeHtml(j.url) + '" target="_blank" rel="noopener">Apply &rarr;</a>' +
        '<button class="expand-btn" onclick="toggleExpand(this)" aria-label="Expand">&or;</button>' +
      '</div>' +
      '<div class="card-expanded">' +
        '<div class="breakdown">' + chips + '</div>' +
        '<div class="desc-preview">' + escapeHtml(j.desc_preview) + '</div>' +
        '<a class="desc-link" href="' + escapeHtml(j.url) + '" target="_blank" rel="noopener">view full posting &rarr;</a>' +
        '<div class="playbook-box"><h4>How to apply</h4><p>Application playbook loads here (next build).</p></div>' +
      '</div>' +
    '</div>';
  }}).join('');
}}

function toggleExpand(btn) {{
  btn.classList.toggle('open');
  const expanded = btn.closest('.card').querySelector('.card-expanded');
  expanded.classList.toggle('show');
}}

document.getElementById('tabs').addEventListener('click', e => {{
  const tab = e.target.closest('.tab');
  if (!tab) return;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  activeTrack = tab.dataset.track;
  renderCards();
}});

document.getElementById('search').addEventListener('input', e => {{
  searchTerm = e.target.value;
  renderCards();
}});

document.getElementById('sort').addEventListener('change', e => {{
  sortMode = e.target.value;
  renderCards();
}});

renderCards();
</script>
</body>
</html>"""

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DOCS_DIR / "index.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page_html)

    log.info("Dashboard written to %s (%d jobs, %.1f KB)", out_path, len(cards_data), len(page_html.encode()) / 1024)
    return out_path


if __name__ == "__main__":
    build_dashboard()

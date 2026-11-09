"""Score and rank fetched jobs against the candidate profile."""

import json
import re
import logging
from datetime import date, timedelta
from pathlib import Path

import yaml
from dateutil import parser as dateparser

try:
    from src.playbooks import build_playbook
except ImportError:
    from playbooks import build_playbook

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_PATH = ROOT / "config" / "profile.yaml"


def _load_profile():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_raw_jobs():
    with open(DATA_DIR / "raw_jobs.json", encoding="utf-8") as f:
        return json.load(f)


def _is_blocked(job, profile):
    title_lower = job["title"].lower()
    for term in profile["seniority_block_terms"]:
        if re.search(r"\b" + re.escape(term) + r"\b", title_lower):
            return True

    location_lower = job["location"].lower()
    desc_lower = job["description"].lower()
    for term in profile["location_block_terms"]:
        term_lower = term.lower()
        if term_lower in location_lower or term_lower in desc_lower:
            return True

    return False


def _title_score(title_lower, profile):
    titles = profile["target_titles"]
    for phrase in titles.get("core", []):
        if phrase.lower() in title_lower:
            return 50
    for phrase in titles.get("secondary", []):
        if phrase.lower() in title_lower:
            return 30
    for phrase in titles.get("wide", []):
        if phrase.lower() in title_lower:
            return 12
    return 0


def _entry_bonus(title_lower, title_score, profile):
    if title_score == 0:
        return 0
    for term in profile.get("target_titles", {}).get("entry", []):
        if term.lower() in title_lower:
            return 8
    return 0


def _skill_score(text, profile):
    total = 0
    for term, weight in profile["stack_weights"].items():
        if term.lower() in text:
            total += weight
    return total


def _keyword_score(text, profile):
    total = 0
    for kw in profile.get("candidate_keywords", []):
        if kw.lower() in text:
            total += 2
    return total


def _remote_bonus(job):
    if job.get("remote"):
        return 5
    combined = (job["title"] + " " + job["location"] + " " + job.get("description", "")).lower()
    if "remote" in combined:
        return 5
    return 0


def _recency_bonus(job):
    raw = job.get("date", "")
    if not raw:
        return 0
    try:
        job_date = dateparser.parse(raw).date()
    except (ValueError, TypeError):
        return 0
    days_ago = (date.today() - job_date).days
    if days_ago <= 7:
        return 5
    if days_ago <= 30:
        return 2
    return 0


def score_jobs():
    profile = _load_profile()
    raw_jobs = _load_raw_jobs()
    threshold = profile.get("score_threshold", 15)

    scored = []
    blocked_count = 0
    below_count = 0

    for job in raw_jobs:
        if _is_blocked(job, profile):
            blocked_count += 1
            continue

        title_lower = job["title"].lower()
        tags_text = " ".join(job.get("tags", []))
        full_text = (title_lower + " " + job["description"].lower() + " " + tags_text).lower()

        ts = _title_score(title_lower, profile)
        eb = _entry_bonus(title_lower, ts, profile)
        ss = _skill_score(full_text, profile)
        ks = _keyword_score(full_text, profile)
        rb = _remote_bonus(job)
        rc = _recency_bonus(job)

        raw_score = ts + eb + ss + ks + rb + rc

        if raw_score < threshold:
            below_count += 1
            continue

        job["score"] = min(raw_score, 100)
        job["score_breakdown"] = {
            "title": ts,
            "entry": eb,
            "skills": ss,
            "keywords": ks,
            "remote": rb,
            "recency": rc,
        }
        job["playbook"] = build_playbook(job)
        scored.append(job)

    scored.sort(key=lambda j: j["score"], reverse=True)

    out_path = DATA_DIR / "scored_jobs.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(scored, f, indent=2, ensure_ascii=False)

    log.info("Saved %d scored jobs to %s", len(scored), out_path)
    return scored, len(raw_jobs), blocked_count, below_count


if __name__ == "__main__":
    scored, total_raw, blocked, below = score_jobs()
    print(f"\nRaw jobs: {total_raw}")
    print(f"Blocked (seniority/location): {blocked}")
    print(f"Below threshold: {below}")
    print(f"Survivors: {len(scored)}")
    print(f"\nTop 15:")
    for j in scored[:15]:
        print(f"  {j['score']:>3} | [{j['source']}] {j['title']} — {j['company']}")

"""Per-job application playbooks: channel detection, pitch selection, outreach templates."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "profile.yaml"

PITCH_BUILDER = (
    "I lead ML systems end to end. For my capstone I ran a 6-person team to ship "
    "TactiVision Pro — a production computer-vision pipeline (YOLOv8, RT-DETR, ByteTrack) "
    "that extracts 70+ tactical features from broadcast football video and pushed ball "
    "detection from 4.7% to 85.7%, running live at 25 FPS. I’m comfortable owning a "
    "model from annotation through deployment."
)

PITCH_FINTECH_HYBRID = (
    "I’m a data scientist who’s worked in real production systems. I spent 6 months on "
    "the backend of e& Money — Egypt’s largest mobile wallet, millions of monthly "
    "transactions — mapping payment and reconciliation flows across Java microservices, "
    "alongside shipping my own ML work (a CV pipeline in YOLOv8/RT-DETR, a CNN emotion "
    "classifier at 97% accuracy). I bridge machine learning and the systems it has to "
    "run inside."
)

PITCH_DATA_ANALYST = (
    "I’m a data scientist from Cairo with a strong applied foundation — Python, pandas, "
    "SQL, scikit-learn — and shipped projects behind it: a 97%-accuracy CNN emotion "
    "classifier benchmarked against SVM/KNN/MobileNetV2, and a 16-tab analytics dashboard "
    "built in Streamlit. I turn messy data into models and clear analysis, and I learn fast."
)

PITCHES = {
    "builder": PITCH_BUILDER,
    "fintech_hybrid": PITCH_FINTECH_HYBRID,
    "data_analyst": PITCH_DATA_ANALYST,
}

MESSAGE_TEMPLATE = """Hi [name],

I came across the {role} role at {company} and it lines up closely with what I do.

{pitch}

I'd love to put my application in front of the right person — is there anyone on the team I should reach out to directly? Happy to share my portfolio and GitHub.

Best,
Mohanad Amr | Data Scientist & ML Engineer | Cairo
github.com/MohanadddAmrr"""

STEPS_ATS = [
    "This is a real company ATS ({channel}). Apply directly through the Apply button — these go to the actual hiring team, not a black hole.",
    "Before applying: open the company’s LinkedIn, find someone on the data/ML team or a recruiter, and send a short connection note (template below) the same day. ATS + a human touch doubles your odds.",
    "Attach your CV. In any ‘cover letter’ or ‘additional info’ box, paste the message below.",
]

STEPS_AGGREGATOR = [
    "This is a REPOST from an aggregator — applying here is low-signal. Do this instead:",
    "Copy the exact job title + company and search it on the company’s own careers page or LinkedIn Jobs. Apply at the SOURCE.",
    "If you can’t find the original, the role may be stale or a lead-gen funnel — deprioritize it unless the company is clearly real and hiring.",
]

STEPS_BOARD = [
    "Apply via the board link, but also check if the company has its own careers page and apply there too (direct > board).",
    "Find the hiring manager or a team member on LinkedIn and send the connection note below — on these boards, outreach is what separates you from 400 other applicants.",
]

STEPS_DIRECT = [
    "Apply on the company page directly.",
    "Then find a relevant person on LinkedIn (recruiter, data/ML lead) and send the note below.",
]

CHANNEL_STEPS = {
    "greenhouse": STEPS_ATS,
    "lever": STEPS_ATS,
    "ashby": STEPS_ATS,
    "aggregator": STEPS_AGGREGATOR,
    "board": STEPS_BOARD,
    "direct": STEPS_DIRECT,
}

_profile_cache = None


def _load_profile():
    global _profile_cache
    if _profile_cache is None:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            _profile_cache = yaml.safe_load(f)
    return _profile_cache


def classify_channel(job):
    url = (job.get("url") or "").lower()
    if "greenhouse.io" in url or "boards.greenhouse" in url:
        return "greenhouse"
    if "lever.co" in url:
        return "lever"
    if "ashbyhq.com" in url:
        return "ashby"
    if job.get("via_aggregator") or any(m in url for m in ("jobgether", "huzzle", "linkup")):
        return "aggregator"
    if any(b in url for b in ("remotive.com", "remoteok.com", "arbeitnow.com")):
        return "board"
    return "direct"


def _matched_skills(job, stack_terms):
    text = (
        job.get("title", "") + " " + job.get("description", "") + " " + " ".join(job.get("tags", []))
    ).lower()
    return [t for t in stack_terms if t.lower() in text]


def select_pitch(job):
    profile = _load_profile()
    stack_terms = list((profile.get("stack_weights") or {}).keys())
    matched = _matched_skills(job, stack_terms)
    matched_lower = {s.lower() for s in matched}
    title_lower = job.get("title", "").lower()

    builder_skills = {"computer vision", "pytorch", "yolo", "opencv", "deep learning", "tensorflow"}
    builder_titles = ["machine learning", "ml engineer", "ai engineer", "computer vision", "deep learning"]
    if matched_lower & builder_skills or any(t in title_lower for t in builder_titles):
        return "builder"

    desc_lower = job.get("description", "").lower()
    fintech_desc = ["fintech", "payment", "wallet", "microservice", "transaction", "banking"]
    if "backend" in title_lower or "data engineer" in title_lower or any(kw in desc_lower for kw in fintech_desc):
        return "fintech_hybrid"

    return "data_analyst"


def build_playbook(job):
    channel = classify_channel(job)
    pitch_type = select_pitch(job)
    pitch_text = PITCHES[pitch_type]

    steps = [s.format(channel=channel.capitalize()) for s in CHANNEL_STEPS[channel]]

    message = MESSAGE_TEMPLATE.format(
        company=job.get("company", "the company"),
        role=job.get("title", "the role"),
        pitch=pitch_text,
    )

    return {
        "channel": channel,
        "pitch_type": pitch_type,
        "steps": steps,
        "message": message,
    }

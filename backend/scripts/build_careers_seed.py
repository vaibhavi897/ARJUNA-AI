"""Expand the authored career sources into app/data/careers_seed.json.

    python -m scripts.build_careers_seed

Each career gets a 9-11 scene "day in the life" story assembled from its own
authored workflow (the verified activities in the dataset), plus templated
opening/closing scenes built from the career's environment, hours and
trajectory. Gemini can later replace the narration (once, stored in the DB).
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

from scripts.careers_source import finance_consulting, invest_other, product_business_security, tech_data

OUT = Path(__file__).resolve().parents[1] / "app" / "data" / "careers_seed.json"
TODAY = dt.date.today().isoformat()
LATE = {"Finance", "Consulting", "Investments & Entrepreneurship"}

FLOW_TIMES = {
    4: ["09:30 AM", "11:30 AM", "02:30 PM", "04:30 PM"],
    5: ["09:30 AM", "11:00 AM", "01:30 PM", "03:00 PM", "04:30 PM"],
    6: ["09:30 AM", "10:45 AM", "12:00 PM", "02:00 PM", "03:30 PM", "05:00 PM"],
    7: ["09:30 AM", "10:30 AM", "11:45 AM", "01:30 PM", "02:45 PM", "04:00 PM", "05:15 PM"],
    8: ["09:30 AM", "10:30 AM", "11:30 AM", "01:00 PM", "02:15 PM", "03:30 PM", "04:45 PM", "05:45 PM"],
}

VISUAL_RULES = [
    ("call", ["phone", "call with", "calls the", "negotiat", "escalat", "bank call", "carrier calls", "vendor call"]),
    ("whiteboard", ["workshop", "brainstorm", "hypothes", "map", "sketch", "framing", "storyline", "problem-solving", "roadmap", "prioritis"]),
    ("coffee", ["lunch", "coffee", "catch-up", "informal"]),
    ("security", ["security", "threat", "incident", "vulnerab", "alert", "control test", "harden", "breach"]),
    ("code", ["code", "coding", "pull request", "deploy", "endpoint", "api", "pipeline", "query", "terraform", "infrastructure", "model", "prototype", "migration", "implement"]),
    ("presentation", ["present", "pitch", "deck", "slides", "committee", "briefing", "report", "storyline", "steering"]),
    ("meeting", ["meeting", "call", "workshop", "interview", "negotiat", "sync", "stand-up", "discussion", "review with", "session", "critique"]),
    ("analysis", ["analys", "analyz", "metric", "forecast", "data", "valuation", "financial", "variance", "ratio", "cash", "dashboard", "reconcil", "experiment", "sizing"]),
    ("design", ["design", "wireframe", "sketch", "figma", "component", "visual"]),
    ("document", ["draft", "writing", "memo", "contract", "document", "paper", "spec", "agreement", "plan"]),
    ("field", ["site", "floor", "warehouse", "plant", "shipment", "walk"]),
]

THEME_DEFAULT_VISUAL = {"finance": "analysis", "consulting": "meeting", "tech": "code", "data": "analysis", "product": "meeting", "business": "meeting", "security": "security", "invest": "analysis", "office": "document"}


def visual_for(heading: str, text: str, theme: str) -> str:
    blob = f"{heading} {text}".lower()
    for key, words in VISUAL_RULES:
        if any(w in blob for w in words):
            return key
    return THEME_DEFAULT_VISUAL.get(theme, "desk")


def article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def best_responsibility(resp: list[str], heading: str, text: str, i: int) -> str:
    words = set(re.findall(r"[a-z]{4,}", f"{heading} {text}".lower()))
    scored = sorted(resp, key=lambda r: -len(words & set(re.findall(r"[a-z]{4,}", r.lower()))))
    top = scored[0]
    if len(words & set(re.findall(r"[a-z]{4,}", top.lower()))) == 0:
        return None  # no honest match: show no responsibility rather than a wrong one
    return top


ARRIVALS = [
    "Your day as {a} {entry} begins in {city}. {env} You scan the priorities before anything else, because {hours}.",
    "It is early in {city}. As {a} {entry}, you badge in and settle at your workspace. {env} The day will run on a simple pattern: {hours}.",
    "The first thing {a} {entry} in {city} does is look at the calendar and the open tasks. {env} Expect this rhythm: {hours}.",
    "Mornings for {a} {entry} start quietly in {city}: coffee, a quick read of overnight messages, then a plan. {env} Typical load: {hours}.",
]
REVIEWS = [
    "Before the day ends you walk your {mid} or {senior} through what you produced. They point out what is strong and what needs another pass. This feedback loop is how {a} {entry} grows toward {amid} {mid}.",
    "Late in the day, a {mid} reviews your work line by line and asks why you made each choice. You note the corrections and what to learn next on the path from {entry} to {mid}.",
    "Your work goes to a {senior} for a final check. A few comments come back, mostly about clarity and risk. Reviews like this are how {entry}s become {mid}s.",
    "You hand over the day's output to a {mid}. They test it, challenge one assumption and suggest a better approach for tomorrow.",
]
WRAPS = [
    "You log what is done and what is pending and set priorities for tomorrow. Typical pattern for this career: {hours}. Weekend work: {weekend}. Remote or hybrid: {remote}.",
    "The day winds down. Open items go onto tomorrow's list and you message the team. Hours here are usually {hours}. Weekends: {weekend}.",
    "You close the laptop having moved a few things forward. In this profession, {hours}. As for weekends, {weekend}. Flexibility: {flex}.",
    "A last look at tomorrow's calendar, then you head out. Typical working pattern: {hours}. Remote and hybrid options: {remote}.",
]


def build_story(c: dict) -> dict:
    title = c["title"]
    entry, mid, senior = (d.split(" / ")[0] for d in c["designations"][:3])
    city = c["geography"][0]
    tools = c["skills"]["tools"]
    resp = c["responsibilities"]
    drivers = c["outlook"]["growth_drivers"]
    env = c["work_environment"]
    wlb = c["work_life_balance"]
    theme = c["visual_theme"]
    flow = c["scenes_flow"]
    n = len(flow)
    times = FLOW_TIMES[n]
    late = c["industry"] in LATE

    scenes = []

    def add(time, heading, narrative, activities, scene_tools, scene_resp, visual, i):
        scenes.append(dict(
            scene_number=len(scenes) + 1,
            time_of_day=time,
            heading=heading,
            narrative=narrative,
            activities=activities,
            tools=scene_tools,
            responsibilities=scene_resp,
            industry_context=f"Industry context: {drivers[i % len(drivers)]}.",
            environment=env,
            visual_key=visual,
        ))

    h = sum(map(ord, c["slug"])) if "slug" in c else sum(map(ord, title))
    hours = wlb["hours"][0].lower() + wlb["hours"][1:]
    add("08:45 AM", f"Arriving at work as {article(entry)} {entry}",
        ARRIVALS[h % 4].format(a=article(entry), entry=entry, city=city, env=env, hours=hours),
        ["Settling in and scanning the day's priorities", "Checking messages and the team calendar"], tools[:2], resp[:2], "arrival", 0)

    for i, f in enumerate(flow):
        sents = sentences(f["text"])
        narrative = f["text"] + f" Most of this work is done with {', '.join(f['tools'][:-1]) + ' and ' + f['tools'][-1] if len(f['tools']) > 1 else f['tools'][0]}."
        add(times[i], f["heading"], narrative, sents,
            f["tools"], [r for r in [best_responsibility(resp, f["heading"], f["text"], i)] if r],
            visual_for(f["heading"], f["text"], theme), i + 1)

    add("06:30 PM" if late else "05:45 PM", "Reviewing the day's work with a senior colleague",
        REVIEWS[(h >> 1) % 4].format(a=article(entry), amid=article(mid), entry=entry, mid=mid, senior=senior),
        ["Walking a senior through the day's output", "Taking feedback and noting what to improve"], tools[:2], resp[-2:], "review", n + 1)

    add("07:45 PM" if late else "06:30 PM", "Wrapping up the working day",
        WRAPS[(h >> 2) % 4].format(hours=hours, weekend=wlb["weekend"].lower(), remote=wlb["remote"].lower(), flex=wlb["flexibility"].lower()),
        ["Logging completed and pending work", "Planning tomorrow's priorities"], tools[:1], [], "wrapup", n + 2)

    assert 8 <= len(scenes) <= 12, (title, len(scenes))
    return dict(
        title=f"A day in the life: {title}",
        summary=f"Follow one working day of {article(entry)} {entry}, from arriving at work to wrapping up, based on the profession's documented responsibilities and tools.",
        source="seed",
        scenes=scenes,
    )


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def sources_for(c: dict) -> list[dict]:
    out = [dict(kind="curated", name="ARJUNA AI editorial research (qualitative role description)", url=None, covers="Responsibilities, workflow, trajectory, work-life balance, exits, advantages and disadvantages", last_verified=TODAY)]
    if c.get("onet_code"):
        out.append(dict(kind="onet", name=f"O*NET OnLine occupation {c['onet_code']} (manual closest-match mapping)", url=f"https://www.onetonline.org/link/summary/{c['onet_code']}", covers="Tasks, skills, knowledge, work context", last_verified=None))
        soc = c["soc_code"].replace("-", "")
        out.append(dict(kind="bls", name=f"US BLS Occupational Employment and Wage Statistics, SOC {c['soc_code']} (US data only)", url=f"https://www.bls.gov/oes/current/oes{soc}.htm", covers="US median wage and employment (never Indian data)", last_verified=None))
    out.append(dict(kind="ncs", name="National Career Service, Government of India", url="https://www.ncs.gov.in/", covers="Indian occupational reference (no figures imported yet)", last_verified=None))
    return out


def main() -> None:
    raw = finance_consulting.CAREERS + tech_data.CAREERS + product_business_security.CAREERS + invest_other.CAREERS
    titles = [c["title"] for c in raw]
    assert len(titles) == len(set(titles)), "duplicate titles"
    careers = []
    for c in raw:
        c = dict(c)
        c["slug"] = slugify(c["title"])
        if c.get("onet_code") and not c.get("soc_code"):
            c["soc_code"] = c["onet_code"][:7]
        c["last_updated"] = TODAY
        c["story"] = build_story(c)
        c["sources"] = sources_for(c)
        # No salary is authored. Filled only from cited sources.
        c["salary"] = dict(india=None, us=None, note="No verified salary data yet. US figures come from the BLS sync; India figures from the curated benchmark file.")
        c.pop("scenes_flow"); c.pop("designations")
        careers.append(c)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(version=1, generated=TODAY, careers=careers), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(careers)} careers -> {OUT}  scenes: {min(len(c['story']['scenes']) for c in careers)}-{max(len(c['story']['scenes']) for c in careers)}")


if __name__ == "__main__":
    main()
    sys.exit(0)

"""Generate CareerVerse scene images once with Gemini and store them locally.

    python -m scripts.generate_scene_images --theme finance        # one sector (start here)
    python -m scripts.generate_scene_images                        # every sector
    python -m scripts.generate_scene_images --theme finance --force --only analysis

Files land in frontend/public/careerverse/<theme>/<visual_key>.png. Existing
files are skipped, so re-runs cost nothing. Images are never generated at page
load. Set GEMINI_IMAGE_MODEL to override the model.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from app.core.config import settings

OUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "careerverse"
MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

SETTINGS = {
    "finance": "a modern investment bank office with glass walls and a city skyline",
    "consulting": "a bright consulting firm project room with whiteboards and a client meeting table",
    "tech": "a modern software company open-plan office with dual monitors",
    "data": "a data team workspace with large dashboards on screens",
    "product": "a product team studio with sticky-note roadmaps and design boards",
    "business": "a corporate business office and meeting rooms",
    "security": "a security operations centre with a wall of monitoring screens",
    "invest": "a boutique investment firm office with a small meeting room",
    "office": "a professional corporate office",
}
SCENES = {
    "arrival": "the building entrance and a clean empty desk at the start of the working day, morning light",
    "desk": "an organised desk with a laptop, notebook and coffee, early in the day",
    "analysis": "close view of screens showing charts, spreadsheets and analysis, no readable text",
    "code": "a laptop and monitors showing abstract code-like patterns, no readable text",
    "meeting": "a small team discussion around a table, seen from behind or at a distance",
    "presentation": "a presentation room with a screen showing abstract charts, no readable text",
    "document": "a desk with documents, a pen and a laptop, drafting work",
    "design": "a design workspace with sketches, colour swatches and a tablet",
    "security": "dark monitoring screens with abstract glowing network graphs, no readable text",
    "field": "a working floor or warehouse with shelves and activity, wide shot",
    "review": "two colleagues reviewing work on a screen together, seen from behind",
    "wrapup": "the office in warm evening light with city lights outside, a laptop closing",
}
STYLE = (
    "Wide 16:9 flat editorial illustration, soft green and teal palette, clean modern vector style, "
    "no text, no letters, no logos, no watermarks, no recognisable real people, faces not shown."
)


def generate(theme: str, key: str) -> bytes | None:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = f"{STYLE} Scene: {SCENES[key]}, in {SETTINGS[theme]}."
    resp = client.models.generate_content(
        model=MODEL, contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
    )
    for cand in resp.candidates or []:
        for part in (cand.content.parts if cand.content else []) or []:
            if getattr(part, "inline_data", None) and part.inline_data.data:
                return part.inline_data.data
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", choices=list(SETTINGS))
    ap.add_argument("--only", choices=list(SCENES))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--delay", type=float, default=3.0)
    args = ap.parse_args()
    if not settings.gemini_enabled:
        print("GEMINI_API_KEY is not set in backend/.env")
        return 1
    made = failed = 0
    for theme in [args.theme] if args.theme else SETTINGS:
        for key in [args.only] if args.only else SCENES:
            path = OUT / theme / f"{key}.png"
            if path.exists() and not args.force:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            for attempt in range(3):
                try:
                    data = generate(theme, key)
                    if data:
                        path.write_bytes(data)
                        made += 1
                        print(f"ok   {theme}/{key}")
                    else:
                        failed += 1
                        print(f"none {theme}/{key}")
                    break
                except Exception as exc:  # noqa: BLE001 - report and retry on rate limits
                    print(f"err  {theme}/{key} attempt {attempt + 1}: {str(exc)[:120]}")
                    time.sleep(6 * (attempt + 1))
            else:
                failed += 1
            time.sleep(args.delay)
    print(f"generated {made}, failed {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

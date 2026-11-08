"""TF-IDF cosine similarity in plain Python.

A drop-in replacement for the scikit-learn pieces the app used (``TfidfVectorizer`` with English stop words, word
n-grams and sublinear term frequency, followed by ``cosine_similarity``). It follows scikit-learn's formulas exactly:

    tf   = 1 + ln(count)            (sublinear)
    idf  = ln((1 + n) / (1 + df)) + 1   (smooth)
    vec  = tf * idf, then L2-normalised
    sim  = dot product of normalised vectors

so scores match, while the install stays small enough for serverless hosting (no numpy, scipy or scikit-learn).
"""

from __future__ import annotations

import math
import re
from collections import Counter

from app.modules._stopwords import STOP_WORDS

DEFAULT_TOKEN = r"(?u)\b\w\w+\b"          # scikit-learn's default
SKILL_TOKEN = r"(?u)\b[\w+#.]{2,}\b"      # keeps c++, c#, node.js style tokens


def _terms(text: str, pattern: re.Pattern[str], ngram: tuple[int, int]) -> list[str]:
    tokens = [t for t in pattern.findall((text or "").lower()) if t not in STOP_WORDS]
    out: list[str] = []
    lo, hi = ngram
    for n in range(lo, hi + 1):
        if n == 1:
            out.extend(tokens)
        else:
            out.extend(" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1))
    return out


def similarities(docs: list[str], query: str, token_pattern: str = DEFAULT_TOKEN, ngram_range: tuple[int, int] = (1, 2)) -> list[float]:
    """Cosine similarity between ``query`` and each of ``docs`` after fitting TF-IDF on all of them together."""
    pat = re.compile(token_pattern)
    corpus = docs + [query]
    counts = [Counter(_terms(d, pat, ngram_range)) for d in corpus]
    n = len(corpus)
    df: Counter[str] = Counter()
    for c in counts:
        df.update(c.keys())
    idf = {t: math.log((1 + n) / (1 + k)) + 1.0 for t, k in df.items()}

    def vector(c: Counter[str]) -> dict[str, float]:
        v = {t: (1.0 + math.log(k)) * idf[t] for t, k in c.items()}
        norm = math.sqrt(sum(x * x for x in v.values()))
        return {t: x / norm for t, x in v.items()} if norm else {}

    vecs = [vector(c) for c in counts]
    q = vecs[-1]
    out: list[float] = []
    for v in vecs[:-1]:
        small, big = (q, v) if len(q) <= len(v) else (v, q)
        out.append(sum(x * big.get(t, 0.0) for t, x in small.items()))
    return out

import re, unicodedata
from ..registry import stage, cfilter, FILTERS
from ..store import Store

_sw = {}

def normalize(t):
    t = unicodedata.normalize("NFC", t).replace("\u00a0", " ")
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", t)).strip()

@cfilter("length")
def f_length(t, p, proj):
    return p.get("min_chars", 0) <= len(t) <= p.get("max_chars", 10**9)

@cfilter("alpha_ratio")
def f_alpha(t, p, proj):
    return sum(c.isalpha() for c in t) / max(len(t), 1) >= p.get("min", 0.5)

@cfilter("stopwords")
def f_stop(t, p, proj):
    f = proj.resolve(p["file"])
    if not f.exists():
        return True                      # no list yet -> filter inactive
    if f not in _sw:
        _sw[f] = {w.strip().lower() for w in f.read_text(encoding="utf-8-sig").splitlines() if w.strip()}
    words = re.findall(r"\w+", t.lower())
    return bool(words) and sum(w in _sw[f] for w in words) / len(words) >= p.get("min_ratio", 0.05)

@stage("clean")
def run(proj):
    data = proj.path("data")
    raw, out = Store(data / "raw", "records"), Store(data / "clean", "records")
    filters = proj.stage_cfg("clean").get("filters", [])
    done, kept, dropped = out.ids(), 0, 0
    def gen():
        nonlocal dropped
        for r in raw.iter():
            if r["id"] in done: continue
            t = normalize(r["text"])
            if all(FILTERS[f["name"]](t, f, proj) for f in filters):
                yield {**r, "text": t}
            else:
                dropped += 1
    kept = out.add(gen())
    return {"added": kept, "dropped": dropped, "total_clean": out.count()}
import json, re, time
from html.parser import HTMLParser
from ..registry import stage, connector, CONNECTORS
from ..store import Store, rid

class _Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.out, self.skip = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"): self.skip += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip: self.skip -= 1
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3"): self.out.append("\n")
    def handle_data(self, d):
        if not self.skip: self.out.append(d)

def _chunks(text, size):
    buf = ""
    for para in re.split(r"\n\s*\n|\n", text):
        para = para.strip()
        if not para: continue
        if len(buf) + len(para) > size and buf:
            yield buf; buf = ""
        buf += para + "\n"
    if buf.strip(): yield buf

@connector("local")
def local(s, proj):
    base = proj.resolve(s["path"])
    for fp in sorted(base.glob(s.get("glob", "**/*"))):
        if not fp.is_file(): continue
        ext = fp.suffix.lower()
        if ext == ".jsonl":
            with open(fp, encoding="utf-8-sig") as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line: continue
                    t = json.loads(line).get(s.get("text_field", "text"))
                    if t: yield {"text": t, "meta": {"file": fp.name, "line": i}}
        elif ext in (".txt", ".md"):
            raw = fp.read_text(encoding="utf-8-sig")
            mode = s.get("split", "paragraph")
            parts = [raw] if mode == "file" else re.split(r"\n\s*\n" if mode == "paragraph" else r"\n", raw)
            for i, p in enumerate(parts):
                yield {"text": p, "meta": {"file": fp.name, "part": i}}

@connector("hf")
def hf(s, proj):
    from datasets import load_dataset
    ds = load_dataset(s["path"], s.get("config"), split=s.get("split", "train"), streaming=s.get("streaming", True))
    limit = s.get("limit") or 0
    for i, row in enumerate(ds):
        if limit and i >= limit: break
        text = "\n".join(str(row[f]) for f in s["text_fields"] if row.get(f))
        yield {"text": text, "meta": {"row": i}}

@connector("http")
def http(s, proj):
    import requests
    urls = list(s.get("urls") or [])
    if s.get("urls_file"):
        urls += [u.strip() for u in proj.resolve(s["urls_file"]).read_text(encoding="utf-8-sig").splitlines() if u.strip()]
    for u in urls:
        try:
            r = requests.get(u, headers={"User-Agent": "kinya-collector/0.1"}, timeout=30)
            r.raise_for_status()
            p = _Text(); p.feed(r.text)
            for i, c in enumerate(_chunks("".join(p.out), s.get("chunk_chars", 1500))):
                yield {"text": c, "meta": {"url": u, "chunk": i}}
        except Exception as e:
            print(f"  skip {u}: {e}")
        time.sleep(s.get("delay", 1.0))

@stage("collect")
def run(proj):
    sources = [s for s in proj.sources if s.get("enabled", True)]
    if proj.opts.get("only"):
        sources = [s for s in sources if s["name"] == proj.opts["only"]]
    store = Store(proj.path("data") / "raw", "records")
    stats = {}
    for s in sources:
        try:
            recs = ({"id": rid(r["text"]), "text": r["text"], "source": s["name"], "meta": r.get("meta", {})}
                    for r in CONNECTORS[s["type"]](s, proj) if r.get("text", "").strip())
            stats[s["name"]] = f"+{store.add(recs)}"
        except Exception as e:
            stats[s["name"]] = f"ERROR {type(e).__name__}: {e}"
    return stats
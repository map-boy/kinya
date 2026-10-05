import json
from ..registry import stage
from ..store import Store
from .sft import _build

def _w(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

@stage("review")
def run(proj):
    """Speakers fix dialogues in data/review/done.jsonl: {"id":..., "turns":[...], "route":{...}, "gold":true|false}.
    reviewed=true is set; gold=true dialogues are held out of training and become the eval gold set."""
    data = proj.path("data"); c = proj.stage_cfg("review")
    st = Store(data / "synth", "dialogues"); rows = list(st.iter())
    d = data / "review"; d.mkdir(parents=True, exist_ok=True)
    upd, done = {}, d / "done.jsonl"
    if done.exists():
        for l in open(done, encoding="utf-8-sig"):
            if l.strip():
                u = json.loads(l); upd[u["id"]] = u
    applied = 0
    for r in rows:
        u = upd.get(r["id"])
        if u:
            for k in ("turns", "route"):
                if k in u: r[k] = u[k]
            r["meta"]["reviewed"], r["meta"]["gold"] = True, bool(u.get("gold")); applied += 1
    _w(st.file, rows)
    _w(d / "queue.jsonl", [r for r in rows if not r["meta"].get("reviewed")][: c.get("queue_size", 50)])
    system, sc, g = proj.system_prompt(), proj.stage_cfg("sft"), []
    for r in rows:
        if r["meta"].get("gold"): g += _build(r, sc, system)
    e = data / "eval"; e.mkdir(parents=True, exist_ok=True)
    _w(e / "gold.jsonl", g)
    return {"applied": applied, "queue": min(len([1 for r in rows if not r["meta"].get("reviewed")]), c.get("queue_size", 50)), "gold_examples": len(g)}
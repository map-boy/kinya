import json, re, time
from string import Template
from ..registry import stage, PROVIDERS
from ..store import Store, rid
from .. import providers  # noqa: registers providers
from .. import validity
from collections import Counter

def _parse(txt, tax, dept, issue):
    if not txt: return None
    a, b = txt.find("{"), txt.rfind("}")
    if a < 0 or b < 0: return None
    try: o = json.loads(txt[a:b + 1])
    except Exception: return None
    turns, route = o.get("turns"), o.get("route") or {}
    if not turns or any(t.get("role") not in ("caller", "agent") or not str(t.get("text", "")).strip() for t in turns): return None
    if turns[-1]["role"] != "agent": return None
    if route.get("dept") != dept or route.get("issue") != issue or route.get("urgency") not in tax["urgency"]: return None
    route["sector"] = str(route.get("sector") or "unknown").strip() or "unknown"
    return {"turns": [{"role": t["role"], "text": str(t["text"]).strip()} for t in turns], "route": route}

@stage("synth")
def run(proj):
    c = proj.stage_cfg("synth"); tax = proj.taxonomy
    try:
        call = PROVIDERS[c["provider"]["type"]](c["provider"])
    except Exception as e:
        return {"skipped": f"synth unavailable: {e}"}
    tpl = Template(proj.resolve(c["prompt_file"]).read_text(encoding="utf-8-sig"))
    store = Store(proj.path("data") / "synth", "dialogues")
    variants, added, failed = c["variants"], 0, 0
    sectors, vrules, attempts = c.get("sectors") or [], c.get("validity") or {}, c.get("attempts", 2)
    why = Counter()
    for dept, d in tax["departments"].items():
        for issue in d["issues"]:
            for k in range(c["per_issue"]):
                _id = rid("dlg", dept, issue, k)
                if _id in store.ids(): continue
                sector = sectors[int(_id, 16) % len(sectors)] if sectors else "a sector of your choice"
                prompt = tpl.substitute(dept=dept, dept_description=d.get("description", ""), issue=issue, sector=sector,
                                        variant=variants[k % len(variants)], urgency_levels=", ".join(tax["urgency"]))
                parsed = None
                for _ in range(attempts):
                    cand = _parse(call(prompt), tax, dept, issue)
                    if not cand: why["unparseable"] += 1; continue
                    ok, reason = validity.check(cand, vrules, sectors)
                    if ok: parsed = cand; break
                    why[reason] += 1
                    time.sleep(c.get("sleep", 0))
                if not parsed: failed += 1; continue
                added += store.add([{"id": _id, **parsed, "meta": {"dept": dept, "issue": issue, "k": k, "sector": sector, "model": c["provider"]["model"], "reviewed": False, "validated": True}}])
                time.sleep(c.get("sleep", 0))
    return {"added": added, "failed": failed, "total": store.count(), "rejected_by": dict(why)}
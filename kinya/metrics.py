import re

_ATTR = re.compile(r'(\w+)="([^"]*)"')
_ROUTE = re.compile(r"<route\s+([^>]*)/>")
_REPLY = re.compile(r"<reply>(.*?)</reply>", re.S)

def parse_route(t):
    m = _ROUTE.search(t or "")
    return dict(_ATTR.findall(m.group(1))) if m else None

def parse_reply(t):
    m = _REPLY.search(t or "")
    if m:
        return m.group(1).strip()
    return _ROUTE.sub("", t or "").replace("<reply>", "").replace("</reply>", "").strip()

def _hit(r, k):
    return r["pred"] is not None and r["pred"].get(k) == r["gold"].get(k)

def _acc(rows, k):
    return sum(_hit(r, k) for r in rows) / max(len(rows), 1)

def score(rows, gates=None):
    gates, n = gates or {}, len(rows)
    rep = {"n": n, "format_ok": sum(r["pred"] is not None for r in rows) / max(n, 1)}
    for k in ("dept", "urgency", "issue", "sector"):
        rep[f"{k}_acc"] = _acc(rows, k)
    rep["full_match"] = sum(all(_hit(r, k) for k in ("dept", "urgency", "issue")) for r in rows) / max(n, 1)
    slices = {}
    for dim in ("dept", "issue", "urgency"):
        g = {}
        for r in rows:
            g.setdefault(r["gold"].get(dim, "?"), []).append(r)
        slices[dim] = {k: {"n": len(v), "acc": _acc(v, dim)} for k, v in sorted(g.items())}
    rep["slices"] = slices
    conf = {}
    for r in rows:
        p = (r["pred"] or {}).get("dept", "NONE")
        if p != r["gold"].get("dept"):
            key = f'{r["gold"].get("dept")}->{p}'
            conf[key] = conf.get(key, 0) + 1
    rep["top_confusions"] = sorted(conf.items(), key=lambda x: -x[1])[:10]
    floor = gates.get("min_slice_acc")
    weak = []
    if floor is not None:
        for dim, g in slices.items():
            for name, s in g.items():
                if s["acc"] < floor:
                    weak.append(f"{dim}={name} acc={s['acc']:.2f} n={s['n']}")
    rep["weak_slices"] = weak
    fails = [f"{k}: {rep.get(k, 0):.3f} < {v}" for k, v in gates.items() if k != "min_slice_acc" and rep.get(k, 0) < v]
    rep["gate_failures"] = fails + [f"weak slice {w}" for w in weak]
    rep["passed"] = not rep["gate_failures"]
    return rep

def to_md(rep, prev=None):
    L = ["# Wandaa eval report", "", f"passed: **{rep['passed']}**  (n={rep['n']})", "", "| metric | value | delta |", "|---|---|---|"]
    for k, v in rep.items():
        if isinstance(v, float):
            d = ""
            if prev and isinstance(prev.get(k), float):
                d = f"{v - prev[k]:+.3f}"
            L.append(f"| {k} | {v:.3f} | {d} |")
    L += ["", "## Gate failures"] + ([f"- {x}" for x in rep["gate_failures"]] or ["- none"])
    L += ["", "## Top dept confusions"] + ([f"- {k}: {v}" for k, v in rep["top_confusions"]] or ["- none"])
    for dim, g in rep["slices"].items():
        L += ["", f"## By {dim}", "| value | n | acc |", "|---|---|---|"]
        L += [f"| {k} | {s['n']} | {s['acc']:.2f} |" for k, s in g.items()]
    if "red_team" in rep:
        L += ["", "## Red team", f"passed {rep['red_team']['passed']}/{rep['red_team']['n']}"]
        L += [f"- FAILED: {x}" for x in rep["red_team"]["failed"]]
    return "\n".join(L) + "\n"
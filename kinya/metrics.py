import math
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

def wilson(k, n, z=1.96):
    """95% Wilson score interval for k successes in n trials."""
    if n <= 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)

def _hit(r, k):
    return r["pred"] is not None and r["pred"].get(k) == r["gold"].get(k)

def _k(rows, k):
    return sum(_hit(r, k) for r in rows)

def _acc(rows, k):
    return _k(rows, k) / max(len(rows), 1)

def score(rows, gates=None, max_reply_chars=None):
    gates = dict(gates or {})
    min_n = gates.pop("min_n", 0)
    floor = gates.pop("min_slice_acc", None)
    n = len(rows)
    ok = sum(r["pred"] is not None for r in rows)
    rep = {"n": n, "format_ok": ok / max(n, 1)}
    ci = {"format_ok": wilson(ok, n)}
    for k in ("dept", "urgency", "issue", "sector"):
        rep[f"{k}_acc"] = _acc(rows, k)
        ci[f"{k}_acc"] = wilson(_k(rows, k), n)
    full = sum(all(_hit(r, k) for k in ("dept", "urgency", "issue")) for r in rows)
    rep["full_match"] = full / max(n, 1)
    ci["full_match"] = wilson(full, n)
    if max_reply_chars is not None:
        good = sum(len(r.get("reply", "")) <= max_reply_chars for r in rows)
        rep["reply_len_ok"] = good / max(n, 1)
        ci["reply_len_ok"] = wilson(good, n)
    rep["ci"] = {k: [round(a, 3), round(b, 3)] for k, (a, b) in ci.items()}

    slices = {}
    for dim in ("dept", "issue", "urgency"):
        g = {}
        for r in rows:
            g.setdefault(r["gold"].get(dim, "?"), []).append(r)
        slices[dim] = {k: {"n": len(v), "acc": _acc(v, dim), "ci": [round(x, 3) for x in wilson(_k(v, dim), len(v))]}
                       for k, v in sorted(g.items())}
    rep["slices"] = slices

    conf = {}
    for r in rows:
        p = (r["pred"] or {}).get("dept", "NONE")
        if p != r["gold"].get("dept"):
            key = f'{r["gold"].get("dept")}->{p}'
            conf[key] = conf.get(key, 0) + 1
    rep["top_confusions"] = sorted(conf.items(), key=lambda x: -x[1])[:10]

    # a slice is only "weak" when the evidence says so (upper CI bound below the floor), not on tiny n
    weak = []
    if floor is not None:
        for dim, g in slices.items():
            for name, s in g.items():
                if s["ci"][1] < floor:
                    weak.append(f"{dim}={name} acc={s['acc']:.2f} n={s['n']}")
    rep["weak_slices"] = weak

    fails, status = [], {}
    for k, v in gates.items():
        val = rep.get(k)
        if val is None:
            fails.append(f"{k}: not measured")
            status[k] = "not measured"
            continue
        lo, hi = rep["ci"].get(k, [val, val])
        status[k] = "pass" if lo >= v else ("fail" if hi < v else "uncertain")
        if val < v:
            fails.append(f"{k}: {val:.3f} < {v}")
    if n < min_n:
        fails.append(f"n={n} < min_n={min_n}: too few test examples, result is inconclusive")
    rep["gate_status"] = status
    rep["gate_failures"] = fails + [f"weak slice {w}" for w in weak]
    rep["passed"] = not rep["gate_failures"]
    rep["verdict"] = "INCONCLUSIVE (too few examples)" if n < min_n else ("PASS" if rep["passed"] else "FAIL")
    return rep

def to_md(rep, prev=None):
    L = ["# Wandaa eval report", "", f"verdict: **{rep.get('verdict', rep['passed'])}**  (n={rep['n']}, passed={rep['passed']})", "",
         "| metric | value | 95% CI | delta |", "|---|---|---|---|"]
    for k, v in rep.items():
        if isinstance(v, float):
            d = ""
            if prev and isinstance(prev.get(k), float):
                d = f"{v - prev[k]:+.3f}"
            c = rep.get("ci", {}).get(k)
            L.append(f"| {k} | {v:.3f} | {f'{c[0]:.2f} to {c[1]:.2f}' if c else ''} | {d} |")
    if rep.get("gate_status"):
        L += ["", "## Gate status (pass = lower bound clears the gate, fail = upper bound below it)"]
        L += [f"- {k}: {v}" for k, v in rep["gate_status"].items()]
    L += ["", "## Gate failures"] + ([f"- {x}" for x in rep["gate_failures"]] or ["- none"])
    L += ["", "## Top dept confusions"] + ([f"- {k}: {v}" for k, v in rep["top_confusions"]] or ["- none"])
    for dim, g in rep["slices"].items():
        L += ["", f"## By {dim}", "| value | n | acc | 95% CI |", "|---|---|---|---|"]
        L += [f"| {k} | {s['n']} | {s['acc']:.2f} | {s['ci'][0]:.2f} to {s['ci'][1]:.2f} |" for k, s in g.items()]
    if "red_team" in rep:
        L += ["", "## Red team", f"passed {rep['red_team']['passed']}/{rep['red_team']['n']}"]
        L += [f"- FAILED: {x}" for x in rep["red_team"]["failed"]]
    return "\n".join(L) + "\n"
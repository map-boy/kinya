import json, time
from ..registry import stage
from .. import metrics

def _rows(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

@stage("eval")
def run(proj):
    """GPU machine only. Scores routing + reply limits + red-team tests, writes reports/, compares with previous run."""
    from ..serve import Brain
    c = proj.stage_cfg("eval"); rdir = proj.path("reports")
    gold = proj.resolve(c["gold_file"])
    src = gold if gold.exists() and gold.stat().st_size else proj.resolve(c["fallback_file"])
    brain, scored = Brain(proj), []
    for r in _rows(src):
        g = metrics.parse_route(r["completion"][0]["content"])
        if not g: continue
        out = brain.raw(r["prompt"])
        scored.append({"gold": g, "pred": metrics.parse_route(out), "reply": metrics.parse_reply(out), "raw": out, "last_user": r["prompt"][-1]["content"]})
        if len(scored) >= c.get("limit", 300): break
    rep = metrics.score(scored, c.get("gates"))
    mx = proj.policy.get("limits", {}).get("max_reply_chars", 10**9)
    rep["reply_len_ok"] = sum(len(s["reply"]) <= mx for s in scored) / max(len(scored), 1)
    rep["red_team"] = brain.red_team()
    if rep["red_team"]["failed"]:
        rep["passed"] = False; rep["gate_failures"].append("red_team failures")
    rep["eval_source"] = src.name
    latest = rdir / "latest.json"
    prev = json.loads(latest.read_text(encoding="utf-8")) if latest.exists() else None
    ts = time.strftime("%Y%m%d_%H%M%S")
    (rdir / f"eval_{ts}.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    latest.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    (rdir / f"eval_{ts}.md").write_text(metrics.to_md(rep, prev), encoding="utf-8")
    with open(rdir / f"preds_{ts}.jsonl", "w", encoding="utf-8") as f:
        for s in scored: f.write(json.dumps(s, ensure_ascii=False) + "\n")
    return {k: rep[k] for k in ("eval_source", "n", "format_ok", "dept_acc", "issue_acc", "urgency_acc", "full_match", "passed", "gate_failures", "weak_slices")}
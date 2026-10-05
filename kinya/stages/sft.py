import json
from ..registry import stage
from ..store import Store, is_val

def _build(dlg, c, system):
    turns, msgs, out = dlg["turns"], [{"role": "system", "content": system}], []
    last = max(i for i, t in enumerate(turns) if t["role"] == "agent")
    for i, t in enumerate(turns):
        if t["role"] == "caller":
            msgs.append({"role": "user", "content": t["text"]})
        else:
            comp = c["reply_template"].format(text=t["text"])
            if i == last:
                comp += "\n" + c["route_template"].format(**dlg["route"])
            out.append({"prompt": list(msgs), "completion": [{"role": "assistant", "content": comp}]})
            msgs.append({"role": "assistant", "content": comp})
    return out

@stage("sft")
def run(proj):
    c = proj.stage_cfg("sft"); data = proj.path("data")
    system = proj.system_prompt()
    ratio = proj.p["split"]["val_ratio"]
    d = data / "sft"; d.mkdir(parents=True, exist_ok=True)
    n = {"train": 0, "val": 0}
    with open(d / "sft_train.jsonl", "w", encoding="utf-8") as tr, open(d / "sft_val.jsonl", "w", encoding="utf-8") as va:
        for dlg in Store(data / "synth", "dialogues").iter():
            m = dlg.get("meta", {})
            if m.get("gold") or (c.get("require_reviewed") and not m.get("reviewed")): continue
            k = "val" if is_val(dlg["id"], ratio) else "train"
            for ex in _build(dlg, c, system):
                (va if k == "val" else tr).write(json.dumps(ex, ensure_ascii=False) + "\n"); n[k] += 1
    return n
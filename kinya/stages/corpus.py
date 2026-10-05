import json
from ..registry import stage
from ..store import Store, is_val

@stage("corpus")
def run(proj):
    data = proj.path("data")
    ratio = proj.p["split"]["val_ratio"]
    d = data / "corpus"; d.mkdir(parents=True, exist_ok=True)
    n = {"train": 0, "val": 0}; chars = 0
    with open(d / "cpt_train.jsonl", "w", encoding="utf-8") as tr, open(d / "cpt_val.jsonl", "w", encoding="utf-8") as va:
        for r in Store(data / "clean", "records").iter():
            k = "val" if is_val(r["id"], ratio) else "train"
            (va if k == "val" else tr).write(json.dumps({"text": r["text"]}, ensure_ascii=False) + "\n")
            n[k] += 1; chars += len(r["text"])
    return {**n, "chars": chars}
import argparse, importlib, json, pkgutil
from . import stages as stages_pkg
from .config import Project
from .registry import STAGES
from .store import Store

def _discover():
    for m in pkgutil.iter_modules(stages_pkg.__path__):
        importlib.import_module(f"{stages_pkg.__name__}.{m.name}")

def main():
    _discover()
    ap = argparse.ArgumentParser(prog="kinya")
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("stages", nargs="*")
    r.add_argument("--only", help="collect only this source name")
    sub.add_parser("status")
    sub.add_parser("chat")
    a = ap.parse_args()
    proj = Project({"only": getattr(a, "only", None)})
    if a.cmd == "chat":
        from .serve import chat
        chat(proj); return
    if a.cmd == "run":
        names = a.stages or proj.p["default"]
        if names == ["all"]:
            names = proj.p["pipeline"]
        for n in names:
            if n not in STAGES:
                print(f"unknown stage: {n}"); return
            print(f"== {n}")
            print(json.dumps(STAGES[n](proj), ensure_ascii=False, indent=2))
    else:
        data = proj.path("data")
        for layer, name in [("raw", "records"), ("clean", "records"), ("synth", "dialogues")]:
            print(f"{layer}/{name}: {Store(data / layer, name).count()}")
        for f in sorted(data.glob("corpus/*.jsonl")) + sorted(data.glob("sft/*.jsonl")):
            print(f"{f.relative_to(data)}: {sum(1 for _ in open(f, encoding='utf-8'))}")
        print("stages:", ", ".join(sorted(STAGES)))
from huggingface_hub import HfApi
a = HfApi(); u = a.whoami()["name"]
G, R, Y, X = "\033[92m", "\033[91m", "\033[93m", "\033[0m"
def show(name, typ, want):
    rid = f"{u}/{name}"
    try:
        fs = a.list_repo_files(rid, repo_type=typ)
    except Exception:
        print(f"{R}MISSING  {rid}{X}"); return
    print(f"{G}FOUND    {rid}  ({len(fs)} files){X}")
    for w in want:
        hit = [f for f in fs if f.startswith(w)]
        print(f"   {G if hit else R}{'OK  ' if hit else 'NONE'}  {w}  ({len(hit)}){X}")
show("wandaa-data", "dataset", ["raw/", "clean/", "corpus/", "synth/", "sft/"])
show("wandaa-brain", "model", ["models/", "reports/"])
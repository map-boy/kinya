from ..registry import stage
from .. import hub

def _setup(proj):
    c = proj.stage_cfg("hub")
    if not hub.token():
        return None, c, None, None
    a = hub.api()
    return a, c, hub.repo_id(a, c["dataset_repo"]), hub.repo_id(a, c["model_repo"])

@stage("push")
def push(proj):
    a, c, drepo, mrepo = _setup(proj)
    if not a:
        return {"skipped": "no HF token (set HF_TOKEN env or Colab/Kaggle secret)"}
    priv, out = c.get("private", True), {}
    a.create_repo(drepo, repo_type="dataset", private=priv, exist_ok=True)
    a.upload_folder(folder_path=str(proj.path("data")), repo_id=drepo, repo_type="dataset",
                    allow_patterns=[f"{d}/*" for d in c.get("sync_dirs", [])], commit_message="kinya data sync")
    out["dataset"] = drepo
    a.create_repo(mrepo, repo_type="model", private=priv, exist_ok=True)
    for key, ign in (("models", ["*/ckpt/*", "ckpt/*"]), ("reports", None)):
        d = proj.path(key)
        if any(d.iterdir()):
            a.upload_folder(folder_path=str(d), repo_id=mrepo, repo_type="model", path_in_repo=key, ignore_patterns=ign, commit_message=f"kinya {key} sync")
            out[key] = mrepo
    return out

@stage("pull")
def pull(proj):
    a, c, drepo, mrepo = _setup(proj)
    if not a:
        return {"skipped": "no HF token (set HF_TOKEN env or Colab/Kaggle secret)"}
    from huggingface_hub import snapshot_download
    out = {}
    jobs = [("dataset", drepo, "dataset", str(proj.path("data")), [f"{d}/*" for d in c.get("sync_dirs", [])])]
    if c.get("pull_models", True):
        jobs.append(("model", mrepo, "model", str(proj.resolve(".")), ["models/*", "reports/*"]))
    for name, repo, typ, dest, pats in jobs:
        try:
            snapshot_download(repo_id=repo, repo_type=typ, local_dir=dest, allow_patterns=pats, token=hub.token())
            out[name] = f"pulled {repo}"
        except Exception as e:
            out[name] = f"skipped: {type(e).__name__}"
    return out
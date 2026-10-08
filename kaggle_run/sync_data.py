from huggingface_hub import HfApi
a = HfApi()   # uses the token from `hf auth login`
try:
    user = a.whoami()["name"]
except Exception as e:
    raise SystemExit(f"Stored login is invalid ({type(e).__name__}). Run: hf auth login --force")
repo = user + "/wandaa-data"
print("user:", user, "->", repo)
a.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
a.upload_folder(folder_path=r"C:\projects_test\kinya\data", repo_id=repo, repo_type="dataset",
                allow_patterns=["raw/*", "clean/*", "corpus/*"], commit_message="local data sync (raw, clean, corpus)")
print("uploaded. files now in repo:")
for f in a.list_repo_files(repo, repo_type="dataset"): print("  ", f)
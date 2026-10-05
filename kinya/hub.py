from .secrets import first_secret

def token():
    return first_secret(("HF_TOKEN", "HUGGINGFACE_HUB_TOKEN"))

def api():
    from huggingface_hub import HfApi
    return HfApi(token=token())

def repo_id(a, name):
    return name if "/" in name else f"{a.whoami()['name']}/{name}"
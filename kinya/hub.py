import os

def token():
    for k in ("HF_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        if os.environ.get(k):
            return os.environ[k]
    try:
        from google.colab import userdata
        return userdata.get("HF_TOKEN")
    except Exception:
        pass
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret("HF_TOKEN")
    except Exception:
        return None

def api():
    from huggingface_hub import HfApi
    return HfApi(token=token())

def repo_id(a, name):
    return name if "/" in name else f"{a.whoami()['name']}/{name}"
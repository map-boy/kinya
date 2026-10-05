import time
from .registry import provider
from .secrets import get_secret

@provider("openai_compat")
def openai_compat(cfg):
    import requests
    key_name = cfg.get("api_key_secret") or cfg.get("api_key_env")
    key = get_secret(key_name) if key_name else None
    if not key:
        raise RuntimeError(f"missing secret '{key_name}' in env/Colab/Kaggle vault")
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    def call(prompt):
        for attempt in range(cfg.get("retries", 4)):
            try:
                r = requests.post(url, headers={"Authorization": "Bearer " + key}, timeout=120, json={
                    "model": cfg["model"], "temperature": cfg.get("temperature", 0.9),
                    "messages": [{"role": "user", "content": prompt}]})
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except Exception:
                time.sleep(2 ** attempt)
        return None
    return call
import sys, time
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
        last = ""
        for attempt in range(cfg.get("retries", 4)):
            wait = 2 ** attempt
            try:
                r = requests.post(url, headers={"Authorization": "Bearer " + key}, timeout=120, json={
                    "model": cfg["model"], "temperature": cfg.get("temperature", 0.9),
                    "messages": [{"role": "user", "content": prompt}]})
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"]
                last = f"HTTP {r.status_code}: {r.text[:160]}"
                if r.status_code == 429:
                    try: wait = float(r.headers.get("Retry-After", ""))
                    except ValueError: wait = min(60, 8 * (attempt + 1))
                    wait = max(wait, 5)
            except Exception as e:
                last = f"{type(e).__name__}: {str(e)[:160]}"
            print(f"[provider {cfg['model']}] {last} (retry in {wait:.0f}s)", file=sys.stderr, flush=True)
            time.sleep(wait)
        return None
    return call
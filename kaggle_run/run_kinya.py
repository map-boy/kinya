import os, sys, time, shutil, subprocess, traceback
os.environ["CUDA_VISIBLE_DEVICES"] = "0"; os.environ["TOKENIZERS_PARALLELISM"] = "false"; os.environ["PYTHONUNBUFFERED"] = "1"
W = "/kaggle/working"; LOG = f"{W}/run.log"; R = f"{W}/kinya"; PY = sys.executable

def log(m):
    line = time.strftime("%H:%M:%S ") + m
    print(line, flush=True); open(LOG, "a", encoding="utf-8").write(line + "\n")

def sh(cmd, cwd=None):
    log("$ " + cmd)
    p = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=os.environ)
    with open(LOG, "a", encoding="utf-8") as lf:
        for l in p.stdout:
            lf.write(l); print(l, end="", flush=True)
    p.wait(); log(f"-> exit {p.returncode}"); return p.returncode

from kaggle_secrets import UserSecretsClient
us = UserSecretsClient()
for env, sec in [("HF_TOKEN", "HF_TOKEN_WRITE"), ("HUGGINGFACE_HUB_TOKEN", "HF_TOKEN_WRITE"),
                 ("MISTRAL_API_KEY", "MISTRAL_API_KEY"), ("GROQ_API_KEY", "GROQ_API_KEY")]:
    try: os.environ[env] = us.get_secret(sec)
    except Exception: log(f"MISSING secret {sec} (attach it to this notebook on kaggle.com)")
if not os.environ.get("HF_TOKEN"): raise SystemExit("No HF token: nothing could be saved. Attach HF_TOKEN_WRITE and re-run.")

def push():
    os.makedirs(f"{R}/reports", exist_ok=True)
    shutil.copy(LOG, f"{R}/reports/run_log.txt")
    sh(f"{PY} -m kinya run push", cwd=R)

def stage(name, tries=1, wait=0, do_push=True):
    rc = 1
    for i in range(tries):
        rc = sh(f"{PY} -m kinya run {name}", cwd=R)
        if rc == 0: break
        if i < tries - 1: log(f"{name} failed, retrying in {wait // 60} min"); time.sleep(wait)
    if do_push: push()
    return rc

res = {}
try:
    os.chdir(W)
    if not os.path.isdir("kinya"): sh("git clone https://github.com/map-boy/kinya.git")
    sh("git pull --ff-only", cwd=R)
    sh(f"{PY} -m pip install -q -r requirements.txt", cwd=R)
    sh(f"{PY} -m pip install -q 'datasets>=3.4.1,<4.4.0' pyyaml huggingface_hub", cwd=R)
    if sh(f"{PY} -c 'import unsloth'", cwd=R) != 0:
        sh(f"{PY} -m pip install -q unsloth"); sh(f"{PY} -m pip install -q 'datasets>=3.4.1,<4.4.0'")
    res["pull"]  = stage("pull", do_push=False)
    res["synth"] = stage("synth", tries=6, wait=1200)      # rate-limit tolerant: 6 tries, 20 min apart
    res["sft"]   = stage("sft")
    if res["sft"] == 0:
        res["train"] = stage("train")
        res["eval"]  = stage("eval")
    else:
        log("sft failed -> skipping train/eval")
except BaseException:
    log("CRASH:\n" + traceback.format_exc())
finally:
    log(f"SUMMARY {res}")
    push()
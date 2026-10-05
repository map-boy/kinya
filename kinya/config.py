import os
from pathlib import Path
import yaml

ROOT = Path(os.environ.get("KINYA_ROOT", Path(__file__).resolve().parents[1]))

def _load(name):
    p = ROOT / "configs" / f"{name}.yaml"
    with open(p, encoding="utf-8-sig") as f:
        return yaml.safe_load(f) or {}

class Project:
    def __init__(self, opts=None):
        self.p = _load("project")
        self.sources = _load("sources").get("sources", [])
        self.taxonomy = _load("taxonomy")
        self.opts = opts or {}
        pf = ROOT / "configs" / "policy.yaml"
        self.policy = _load("policy") if pf.exists() else {}

    def resolve(self, rel):
        return ROOT / rel

    def path(self, key):
        d = ROOT / self.p["paths"][key]
        d.mkdir(parents=True, exist_ok=True)
        return d

    def stage_cfg(self, name):
        return self.p.get(name, {})

    def system_prompt(self):
        from string import Template
        f = self.resolve(self.p["sft"]["system_prompt_file"])
        rules = "\n".join("- " + r for r in self.policy.get("rules", []))
        name = self.policy.get("identity", {}).get("name", "Wandaa")
        return Template(f.read_text(encoding="utf-8-sig")).safe_substitute(rules=rules, name=name).strip()
import json, hashlib
from pathlib import Path

def rid(*parts):
    return hashlib.sha1("\x1f".join(map(str, parts)).encode("utf-8")).hexdigest()[:16]

def is_val(record_id, ratio):
    return int(record_id, 16) % 10000 < int(ratio * 10000)

class Store:
    """Append-only JSONL store; records are deduplicated by id, so every stage is incremental."""
    def __init__(self, base, name):
        self.file = Path(base) / f"{name}.jsonl"
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self._ids = None

    def iter(self):
        if not self.file.exists():
            return
        with open(self.file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def ids(self):
        if self._ids is None:
            self._ids = {r["id"] for r in self.iter()}
        return self._ids

    def add(self, records):
        ids, n = self.ids(), 0
        with open(self.file, "a", encoding="utf-8") as f:
            for r in records:
                if r["id"] in ids:
                    continue
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                ids.add(r["id"])
                n += 1
        return n

    def count(self):
        return len(self.ids())
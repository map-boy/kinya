from . import guard, metrics

class Brain:
    """Model + admin policy. Used by eval, chat, and any future USSD/API server."""
    def __init__(self, proj, adapter=None):
        from unsloth import FastLanguageModel
        c = proj.stage_cfg("eval")
        a = adapter or c["adapter"]
        p = proj.resolve(a)
        self.proj, self.max_new = proj, c.get("max_new", 256)
        self.model, self.tok = FastLanguageModel.from_pretrained(
            str(p) if p.exists() else a, max_seq_length=c.get("max_seq", 2048), load_in_4bit=True)
        FastLanguageModel.for_inference(self.model)

    def raw(self, messages):
        enc = self.tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt", return_dict=True).to(self.model.device)
        out = self.model.generate(**enc, max_new_tokens=self.max_new, do_sample=False)
        return self.tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True)

    def respond(self, history):
        """history = chat messages ending with the caller's latest message."""
        pol, tax = self.proj.policy, self.proj.taxonomy
        ok, why, clean = guard.check_input(pol, history[-1]["content"])
        if not ok:
            return {"reply": pol.get("security", {}).get("refusal_text", ""), "route": None, "blocked": why, "flags": [], "raw": ""}
        msgs = [{"role": "system", "content": self.proj.system_prompt()}]
        msgs += history[:-1][-pol.get("limits", {}).get("max_turns", 12):] + [{"role": "user", "content": clean}]
        raw = guard.redact(pol, self.raw(msgs))
        route, fell_back = guard.fix_route(pol, tax, metrics.parse_route(raw))
        return {"reply": guard.clip(pol, metrics.parse_reply(raw)), "route": route, "blocked": "",
                "flags": ["route_fallback"] if fell_back else [], "raw": raw}

    def red_team(self):
        cases, failed = self.proj.policy.get("red_team", []), []
        for c in cases:
            o = self.respond([{"role": "user", "content": c["input"]}])
            e = str(c["expect"])
            good = bool(o["blocked"]) if e == "blocked" else (o["route"] or {}).get("dept") == e.split(":", 1)[1]
            if not good:
                failed.append(c["input"])
        return {"n": len(cases), "passed": len(cases) - len(failed), "failed": failed}

def chat(proj):
    brain, hist = Brain(proj), []
    while True:
        try:
            u = input("caller> ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not u:
            continue
        o = brain.respond(hist + [{"role": "user", "content": u}])
        print("wandaa>", o["reply"], "|", o["route"], o["flags"], o["blocked"])
        if not o["blocked"]:
            hist += [{"role": "user", "content": u}, {"role": "assistant", "content": o["raw"]}]
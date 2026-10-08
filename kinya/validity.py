"""Deterministic dialogue validity filter. No model involved: same input, same verdict.
Used by synth (reject at generation) and sft (skip bad rows already in the store)."""
import re
from collections import Counter

_ENGLISH = {"the", "and", "you", "your", "please", "thank", "thanks", "hello", "will", "have", "with", "this",
            "that", "from", "for", "are", "can", "we", "our", "is", "of", "to", "it", "address", "water", "phone"}
_MARKUP = re.compile(r"[*#`_\[\]{}<>|]|\(\s*[A-Za-z ]{12,}\)")      # markdown, stage directions, translations in brackets
_PHONE = re.compile(r"\d{7,}|\+?250\s?\d")
_DIGIT = re.compile(r"\d")
_WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.U)

DEFAULTS = {
    "min_turns": 4, "max_turns": 8, "max_turn_chars": 400, "min_turn_chars": 3,
    "agent_no_digits": True,        # agents never state times, counts, prices or numbers (they are always invented)
    "max_english_words": 1,
    "max_repeat_ngram": 2,          # same word 3-gram more than this many times inside one turn = babble loop
    "sector_must_appear": True,     # route.sector must be named somewhere in the dialogue
}

def _words(s): return [w.lower() for w in _WORD.findall(s)]

def check(dlg, rules=None, sectors=None):
    """returns (ok, reason). reason is a short stable code, '' when ok."""
    r = {**DEFAULTS, **(rules or {})}
    turns, route = dlg.get("turns") or [], dlg.get("route") or {}
    n = len(turns)
    if not (r["min_turns"] <= n <= r["max_turns"]): return False, "turn_count"
    for i, t in enumerate(turns):
        want = "caller" if i % 2 == 0 else "agent"
        if t.get("role") != want: return False, "bad_turn_order"      # must start with caller and strictly alternate
    if turns[-1]["role"] != "agent": return False, "bad_turn_order"
    for t in turns:
        s = str(t.get("text", "")).strip()
        if not (r["min_turn_chars"] <= len(s) <= r["max_turn_chars"]): return False, "turn_length"
        if _MARKUP.search(s): return False, "markup"
        if _PHONE.search(s): return False, "phone_number"
        if t["role"] == "agent" and r["agent_no_digits"] and _DIGIT.search(s): return False, "agent_number_promise"
        w = _words(s)
        if sum(1 for x in w if x in _ENGLISH) > r["max_english_words"]: return False, "english_leak"
        g = Counter(zip(w, w[1:], w[2:]))
        if g and max(g.values()) > r["max_repeat_ngram"]: return False, "repetition"
    sec = str(route.get("sector") or "").strip()
    if sectors:
        if sec.lower() not in {x.lower() for x in sectors}: return False, "unknown_sector"
    if r["sector_must_appear"] and sec and sec.lower() != "unknown":
        if sec.lower() not in " ".join(str(t.get("text", "")) for t in turns).lower(): return False, "sector_not_in_text"
    return True, ""
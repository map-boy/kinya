import re

def redact(pol, text):
    s = pol.get("security", {})
    for p in s.get("redact_patterns", []):
        text = re.sub(p, s.get("redact_with", "[REDACTED]"), text)
    return text

def check_input(pol, text):
    """returns (ok, reason, cleaned_text)"""
    if len(text) > pol.get("limits", {}).get("max_input_chars", 10**9):
        return False, "too_long", text
    for p in pol.get("security", {}).get("blocked_input_patterns", []):
        if re.search(p, text):
            return False, "blocked_pattern", text
    return True, "", redact(pol, text)

def valid_route(tax, r):
    d = tax.get("departments", {}).get(r.get("dept"))
    return bool(d) and r.get("issue") in d.get("issues", []) and r.get("urgency") in tax.get("urgency", [])

def fix_route(pol, tax, r):
    """None stays None (mid-conversation); invalid route -> admin fallback."""
    if r is None or valid_route(tax, r):
        return r, False
    return dict(pol.get("routing", {}).get("fallback", {})), True

def clip(pol, text):
    return text[: pol.get("limits", {}).get("max_reply_chars", 10**9)]
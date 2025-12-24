from __future__ import annotations

import hashlib
import re


def slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "x"


def agent_key(domain: str, module: str) -> str:
    return f"{slug(domain)}_{slug(module)}"


def stable_id(domain: str, module: str) -> str:
    h = hashlib.sha256((domain + "::" + module).encode("utf-8")).hexdigest()[:8]
    return f"{agent_key(domain, module)}_{h}"

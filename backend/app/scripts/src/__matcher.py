import re
from difflib import SequenceMatcher

BLOCK_WORDS = {
    "편의점", "카페", "식당", "음식점", "주유소", "병원", "약국", "은행", "atm", "호텔", "모텔"
}

ALIASES = {
    "한국종합무역센터": ["코엑스", "coex"],
    "서울 선릉과 정릉": ["선릉과정릉", "선정릉"],
}

def _norm(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip()
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = re.sub(r"\(([^)]*)\)", r" \1 ", s)
    s = re.sub(r"[^0-9a-zA-Z가-힣\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

def _admin_tokens(addr: str):
    n = _norm(addr)
    toks = []
    for t in n.split():
        if t.endswith("시") or t.endswith("구") or t.endswith("군"):
            toks.append(t)
    return toks

def _similarity(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()

def _alias_hit(query: str, cand: str) -> bool:
    nq = _norm(query)
    nc = _norm(cand)
    for k, vals in ALIASES.items():
        nk = _norm(k)
        if nk in nq or nq in nk:
            for v in vals:
                nv = _norm(v)
                if nv in nc or nc in nv:
                    return True
    return False

def accept_place(
    query_name: str,
    cand_name: str,
    cand_addr: str,
    region_addr_hint: str,
    sim_threshold: float = 0.9
) -> bool:
    nq = _norm(query_name)
    nc = _norm(cand_name)

    if not nq or not nc:
        return False

    if any(w in nc for w in BLOCK_WORDS):
        return False

    if nq == nc:
        return True

    if _alias_hit(query_name, cand_name):
        return True

    region_tokens = _admin_tokens(region_addr_hint)
    cand_addr_n = _norm(cand_addr)
    if region_tokens:
        if not any(tok in cand_addr_n for tok in region_tokens):
            return False

    return _similarity(query_name, cand_name) >= sim_threshold

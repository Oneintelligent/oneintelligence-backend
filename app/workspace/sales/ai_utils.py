# app/sales/ai_utils.py
import json
import hashlib
from django.conf import settings
from django.core.cache import cache
import openai
import re

OPENAI_API_KEY = getattr(settings, "OPENAI_API_KEY", None)
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

CACHE_TTL = getattr(settings, "SALES_AI_CACHE_TTL", 60 * 60 * 12)
DEFAULT_MODEL = getattr(settings, "SALES_AI_MODEL", "gpt-4o-mini")

def _hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _extract_json(text: str):
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        # Fallback: extract first JSON object
        m = re.search(r"\{.*\}", text, flags=re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None

def call_openai(prompt: str, model: str = DEFAULT_MODEL, max_tokens: int = 300, temperature: float = 0.0):
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured in settings")
    resp = openai.ChatCompletion.create(
        model=model,
        messages=[{"role":"system","content":"You are a concise sales recommendation assistant. Output MUST be valid JSON only."},
                  {"role":"user","content":prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    text = resp["choices"][0]["message"]["content"]
    return text

def get_recommendation(payload: dict, kind: str = "lead_score"):
    """
    payload: structured minimal input
    kind: 'lead_score' | 'followup' | 'opportunity_predict'
    returns parsed JSON or None
    """
    key = "sales_ai_" + _hash_payload({"kind": kind, "payload": payload})
    cached = cache.get(key)
    if cached:
        return cached

    # Build prompt - concise and strict
    instr = ""
    if kind == "lead_score":
        instr = (
            "Return JSON ONLY (no explanation). Schema:\n"
            '{"score": number (0-100), "reasons": ["short reason","..."], "suggested_next_action":{"type":"email|call|task","text":"...","when":"ISO8601"}}\n'
        )
    elif kind == "followup":
        instr = '{"suggested_message":"...","suggested_time":"ISO8601","reason":["..."]}\n'
    else:
        instr = '{"probability": number (0-100), "predicted_close_date":"YYYY-MM-DD", "factors":["..."]}\n'

    prompt = f"INPUT:\n{json.dumps(payload, default=str)}\n\nINSTRUCTION:\n{instr}\nIMPORTANT: reply with JSON only."

    try:
        raw = call_openai(prompt)
    except Exception as e:
        # log as needed
        return None

    parsed = _extract_json(raw)
    if parsed is not None:
        cache.set(key, parsed, CACHE_TTL)
    return parsed

import json
import re
import urllib.request

OLLAMA = "http://127.0.0.1:11434"      # your own machine only: nothing leaves the device
MODEL = "qwen2.5:0.5b"

PROMPT = """You read bank SMS messages. Extract the transaction as JSON with exactly these keys:
"type": "debit" (money spent) or "credit" (money received),
"amount": the transaction amount as a number (not the balance),
"merchant": who was paid or who paid,
"balance": the remaining balance as a number, or null.
If the SMS is not a bank transaction (OTP, offer, reminder) reply {{"type": "none"}}.
Reply with JSON only.

SMS: Your payment of 450.00 rupees to Swiggy went through. Account XX1234 now has 9,550.00 left.
JSON: {{"type": "debit", "amount": 450.0, "merchant": "Swiggy", "balance": 9550.0}}

SMS: {sms}
JSON:"""


def is_up():
    """True if Ollama is running locally."""
    try:
        urllib.request.urlopen(OLLAMA + "/api/tags", timeout=1)
        return True
    except Exception:
        return False


def _call(prompt, keep_alive=None):
    payload = {"model": MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0}}
    if keep_alive is not None:
        payload["keep_alive"] = keep_alive
    req = urllib.request.Request(OLLAMA + "/api/generate", json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())["response"]


def _number(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def ask(sms):
    """Return {'type','amount','merchant'} or None. Never raises: a bad reply just means 'skip this SMS'."""
    try:
        text = _call(PROMPT.format(sms=sms))
    except Exception:
        return None
    m = re.search(r"\{.*\}", text, re.S)             # small models add chatter around the JSON
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None

    if data.get("type") not in ("debit", "credit"):  # "none" = not a transaction
        return None
    amount, merchant = _number(data.get("amount")), str(data.get("merchant") or "").strip()
    if not amount or amount <= 0 or not merchant:
        return None
    # Safety check: a small model can invent numbers. Only accept an amount that is really in the SMS.
    digits = sms.replace(",", "")
    if not (f"{amount:.2f}" in digits or f"{amount:g}" in digits or str(int(amount)) in digits):
        return None
    return {"type": data["type"], "amount": amount, "merchant": merchant}


def unload():
    """Tell Ollama to drop the model from RAM now (the 'Unload LLM' step)."""
    try:
        _call("", keep_alive=0)
    except Exception:
        pass
import re

AMT = r"(?:Rs\.?|INR)\s?([\d,]+(?:\.\d{1,2})?)"

# one pattern per bank format: (type, compiled regex). Groups: 1 = amount, 2 = merchant
PATTERNS = [
    # HDFC debit
    ("debit", re.compile(AMT + r" debited from A/c XX\d+ on \S+ to VPA \S+ \((.+?)\)")),
    # SBI card
    ("debit", re.compile(AMT + r" spent on your SBI Card XX\d+ at (.+?) on \d")),
    # Axis debit
    ("debit", re.compile(AMT + r" debited from Axis Bank A/c XX\d+ on \S+ Info: UPI/(.+?)\.")),
    # ICICI
    ("debit", re.compile(r"Acct XX\d+ debited for " + AMT + r" on \S+; (.+?) credited")),
    # Credits (salary and refunds)
    ("credit", re.compile(AMT + r" credited to (?:Axis Bank )?A/c XX\d+ on \S+ (?:by|Info: REFUND/)\s?(.+?)\.")),
]

def parse(body):
    """Return {'type','amount','merchant'} or None if no pattern matches (=> ask the LLM)."""
    for ttype, pat in PATTERNS:
        m = pat.search(body)
        if m:
            return {"type": ttype, "amount": float(m.group(1).replace(",", "")),
                    "merchant": m.group(2).strip()}
    return None
# ---- category assignment (lowest priority; user rules from the database override these) ----
KEYWORDS = {
    "Food": ["swiggy", "zomato", "dominos", "starbucks", "kfc", "barbeque", "chai point"],
    "Groceries": ["bigbasket", "dmart", "reliance fresh", "blinkit", "zepto"],
    "Transport": ["uber", "ola", "irctc", "indian oil", "rapido", "metro"],
    "Shopping": ["amazon", "flipkart", "myntra", "ajio", "decathlon"],
    "Bills": ["airtel", "jio", "bescom", "tneb", "tata power", "act fibernet"],
    "Entertainment": ["netflix", "spotify", "bookmyshow", "pvr", "hotstar"],
    "Health": ["apollo", "practo", "medplus", "1mg"],
}

def categorize(merchant, user_rules=()):
    m = merchant.lower()
    for rule in user_rules:                      # rules you taught the agent come first
        if rule["pattern"] in m:
            return rule["category"]
    for cat, words in KEYWORDS.items():
        if any(w in m for w in words):
            return cat
    return "Uncategorized"
import sqlite3

def connect(path="data/finance.db"):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row                # lets you read rows like row["amount"]
    con.execute("PRAGMA journal_mode=WAL")       # safer and faster for a dashboard reading while we write
    return con

def init(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS raw_sms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, body TEXT,
        parsed INTEGER DEFAULT 0,
        UNIQUE(ts, body)                         -- same text at the same time = a re-delivered duplicate
    );
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sms_id INTEGER REFERENCES raw_sms(id),
        date TEXT, type TEXT, amount REAL, merchant TEXT,
        category TEXT, parser TEXT                -- parser = 'regex' or 'llm'
    );
    CREATE TABLE IF NOT EXISTS rules_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern TEXT UNIQUE, category TEXT        -- e.g. 'starbucks' -> 'Entertainment'
    );
    CREATE TABLE IF NOT EXISTS budgets (
        category TEXT PRIMARY KEY, monthly_limit REAL
    );
    """)
    con.commit()

def save_sms(con, ts, body):
    """Store a raw SMS. Returns its id, or None if it was a duplicate."""
    cur = con.execute("INSERT OR IGNORE INTO raw_sms (ts, body) VALUES (?, ?)", (ts, body))
    return cur.lastrowid if cur.rowcount else None

def save_transaction(con, sms_id, date, t):
    con.execute(
        "INSERT INTO transactions (sms_id, date, type, amount, merchant, category, parser) VALUES (?,?,?,?,?,?,?)",
        (sms_id, date, t["type"], t["amount"], t["merchant"], t["category"], t["parser"]))
    con.execute("UPDATE raw_sms SET parsed=1 WHERE id=?", (sms_id,))

def get_rules(con):
    return [dict(r) for r in con.execute("SELECT * FROM rules_memory")]

def get_budgets(con):
    return {r["category"]: r["monthly_limit"] for r in con.execute("SELECT * FROM budgets")}

def set_budget(con, category, limit):
    con.execute("INSERT INTO budgets VALUES (?, ?) ON CONFLICT(category) DO UPDATE SET monthly_limit=excluded.monthly_limit",
                (category, limit))
    con.commit()

def apply_correction(con, txn_id, category):
    """You fix one category: remember it as a rule and relabel every past transaction from that merchant."""
    row = con.execute("SELECT merchant FROM transactions WHERE id=?", (txn_id,)).fetchone()
    if row is None:
        raise KeyError(txn_id)
    pattern = row["merchant"].strip().lower()
    con.execute("INSERT INTO rules_memory (pattern, category) VALUES (?, ?) "
                "ON CONFLICT(pattern) DO UPDATE SET category=excluded.category", (pattern, category))
    cur = con.execute("UPDATE transactions SET category=? WHERE type='debit' AND LOWER(merchant) LIKE ?",
                      (category, f"%{pattern}%"))
    con.commit()
    return {"pattern": pattern, "category": category, "relabelled": cur.rowcount}
def add_manual_transaction(con, date, ttype, amount, merchant, category):
    """A transaction you typed in yourself (cash, or an SMS the agent never saw)."""
    cur = con.execute(
        "INSERT INTO transactions (sms_id, date, type, amount, merchant, category, parser) "
        "VALUES (NULL, ?, ?, ?, ?, ?, 'manual')", (date, ttype, amount, merchant, category))
    con.commit()
    return cur.lastrowid
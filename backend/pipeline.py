import pandas as pd
from backend import db, llm_parser
from backend.regex_parser import parse, categorize


def _finish(t, rules, parser):
    if t["type"] == "debit":
        t["category"] = categorize(t["merchant"], rules)
    else:
        t["category"] = "Income" if "salary" in t["merchant"].lower() else "Refund"
    t["parser"] = parser
    return t


def run(csv_path="data/sms_1000.csv", db_path="data/finance.db"):
    con = db.connect(db_path)
    db.init(con)
    rules = db.get_rules(con)
    stats = {"regex": 0, "llm": 0, "skipped": 0, "duplicate": 0}
    pending = []                                      # SMS regex could not read

    for r in pd.read_csv(csv_path).itertuples():
        sms_id = db.save_sms(con, r.timestamp, r.body)
        if sms_id is None:
            stats["duplicate"] += 1
            continue
        t = parse(r.body)
        if t is None:
            pending.append((sms_id, r.timestamp, r.body))
            continue
        db.save_transaction(con, sms_id, r.timestamp[:10], _finish(t, rules, "regex"))
        stats["regex"] += 1
    con.commit()

    # Tier 2: only start the LLM if there is something for it to do AND it is running
    if pending and llm_parser.is_up():
        for sms_id, ts, body in pending:
            t = llm_parser.ask(body)
            if t is None:
                stats["skipped"] += 1                 # noise, or a reply we refuse to trust
                continue
            db.save_transaction(con, sms_id, ts[:10], _finish(t, rules, "llm"))
            stats["llm"] += 1
        llm_parser.unload()
        con.commit()
    else:
        stats["skipped"] = len(pending)
        if pending:
            print(f"{len(pending)} messages need the LLM but Ollama is not running; skipped.")
    return stats


if __name__ == "__main__":
    print(run())
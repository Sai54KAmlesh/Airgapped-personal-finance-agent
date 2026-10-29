import os
import math
from datetime import date, datetime

from flask import Flask, jsonify, request
from backend.regex_parser import categorize
from backend import analytics, db

app = Flask(__name__)
CATEGORIES = ["Food", "Groceries", "Transport", "Shopping", "Bills", "Entertainment",
              "Health", "Income", "Refund", "Uncategorized"]


def today():
    """Real date, unless you set TODAY=2026-10-28 (handy because the demo data ends then)."""
    env = os.environ.get("TODAY")
    return datetime.strptime(env, "%Y-%m-%d").date() if env else date.today()


def connection():
    con = db.connect()
    db.init(con)
    return con


@app.after_request
def allow_dashboard(resp):                       # lets the React dev server (another port) call us
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.get("/api/overview")
def overview():
    con, t = connection(), today()
    df = analytics.load_debits(con)
    if not db.get_budgets(con):                  # first run: create sensible budgets from your history
        for cat, limit in analytics.default_budgets(df, t).items():
            db.set_budget(con, cat, limit)
    budgets = db.get_budgets(con)
    month = df[(df.date.dt.year == t.year) & (df.date.dt.month == t.month)]
    spent = month.groupby("category").amount.sum().to_dict()
    daily = analytics.daily_totals(df, t.year, t.month).iloc[:t.day]
    return jsonify({
        "today": t.isoformat(),
        "forecast": analytics.forecast_month(df, t),
        "total_budget": sum(budgets.values()),
        "alerts": analytics.category_alerts(df, budgets, t),
        "categories": [{"category": c, "spent": round(spent.get(c, 0.0), 2), "budget": budgets.get(c, 0)}
                       for c in sorted(set(budgets) | set(spent))],
        "daily": [{"day": int(d), "spend": round(float(v), 2)} for d, v in daily.items()],
    })

@app.post("/api/transactions")
def add_transaction():
    """Add a transaction by hand. Category is optional: if you leave it out, the agent picks one."""
    body = request.get_json(force=True, silent=True) or {}
    try:
        day = datetime.strptime(str(body.get("date", "")), "%Y-%m-%d").date().isoformat()
    except ValueError:
        return jsonify({"error": "date must look like 2026-10-29"}), 400
    ttype = body.get("type", "debit")
    if ttype not in ("debit", "credit"):
        return jsonify({"error": "type must be debit or credit"}), 400
    try:
        amount = float(body.get("amount"))
    except (TypeError, ValueError):
        return jsonify({"error": "amount must be a number"}), 400
    if not math.isfinite(amount) or amount <= 0 or amount > 10_000_000:
        return jsonify({"error": "amount must be between 0 and 1,00,00,000"}), 400
    merchant = str(body.get("merchant") or "").strip()
    if not merchant or len(merchant) > 60:
        return jsonify({"error": "merchant is required (max 60 characters)"}), 400
    con = connection()
    category = body.get("category") or (
        categorize(merchant, db.get_rules(con)) if ttype == "debit" else "Income")
    if category not in CATEGORIES:
        return jsonify({"error": "unknown category"}), 400
    new_id = db.add_manual_transaction(con, day, ttype, round(amount, 2), merchant, category)
    return jsonify({"id": new_id, "date": day, "type": ttype, "amount": round(amount, 2),
                    "merchant": merchant, "category": category}), 201
@app.get("/api/transactions")
def transactions():
    limit = int(request.args.get("limit", 50))
    rows = connection().execute(
        "SELECT id, date, type, amount, merchant, category, parser FROM transactions "
        "ORDER BY date DESC, id DESC LIMIT ?", (limit,))
    return jsonify([dict(r) for r in rows])


@app.get("/api/categories")
def categories():
    return jsonify(CATEGORIES)


@app.get("/api/rules")
def rules():
    return jsonify(db.get_rules(connection()))


@app.route("/api/transactions/<int:txn_id>/correct", methods=["POST", "OPTIONS"])
def correct(txn_id):
    if request.method == "OPTIONS":
        return "", 204
    category = (request.get_json(force=True) or {}).get("category")
    if category not in CATEGORIES:
        return jsonify({"error": "unknown category"}), 400
    try:
        return jsonify(db.apply_correction(connection(), txn_id, category))
    except KeyError:
        return jsonify({"error": "transaction not found"}), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)         # 127.0.0.1 = only this computer can reach it
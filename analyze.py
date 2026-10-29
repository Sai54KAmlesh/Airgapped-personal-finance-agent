from datetime import date
from backend import db, analytics

con = db.connect()
df = analytics.load_debits(con)
today = date(2026, 10, 28)                       # use date.today() once you have live data

print("Forecast this month:", analytics.forecast_month(df, today))

# budgets: 90% of each category's average full-month spend, so the demo shows realistic alerts
past = df[df.date < "2026-10-01"]
monthly = past.groupby([past.date.dt.to_period("M"), "category"]).amount.sum().groupby("category").mean()
budgets = {c: round(v * 0.9, -2) for c, v in monthly.items() if c != "Uncategorized"}
print("Budgets:", budgets)
print("\nAlerts:")
for a in analytics.category_alerts(df, budgets, today): print(" ", a)
print("\nBacktest on September 2026:")
analytics.backtest(df, 2026, 9)
print("\nBacktest on August 2026:")
analytics.backtest(df, 2026, 8)
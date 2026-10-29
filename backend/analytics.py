import calendar
from datetime import date
import numpy as np
import pandas as pd
from sklearn.linear_model import SGDRegressor

def load_debits(con):
    """All spending (debits) as a DataFrame with a real date column."""
    df = pd.read_sql_query("SELECT date, amount, category FROM transactions WHERE type='debit'", con)
    df["date"] = pd.to_datetime(df["date"])
    return df

def daily_totals(df, year, month):
    """Spend per day for one month, with 0 for days that had no spending."""
    days = calendar.monthrange(year, month)[1]
    m = df[(df.date.dt.year == year) & (df.date.dt.month == month)]
    return m.groupby(m.date.dt.day).amount.sum().reindex(range(1, days + 1), fill_value=0.0)

def prior_daily_rate(df, today):
    """Average Rs/day over the earlier months in the data (0 if there are none)."""
    first = df.date.min() if len(df) else None
    rates = []
    for k in range(1, 4):                                       # up to the last 3 months
        y, m = (today.year, today.month - k) if today.month > k else (today.year - 1, today.month - k + 12)
        if first is None or first > pd.Timestamp(y, m, 3):      # month only partly in the data: skip
            continue
        rates.append(daily_totals(df, y, m).mean())
    return float(np.mean(rates)) if rates else 0.0

def forecast_month(df, today):
    """Predict this month's total using the days so far (SGDRegressor) plus last months' habits."""
    days = calendar.monthrange(today.year, today.month)[1]
    per_day = daily_totals(df, today.year, today.month).iloc[:today.day]
    spent = float(per_day.sum())
    prior = prior_daily_rate(df, today)
    if today.day < 3 and prior == 0:                            # too little data to fit a line
        return {"spent": round(spent, 2), "forecast": round(spent, 2), "days_left": days - today.day}

    x = np.arange(1, today.day + 1, dtype=float).reshape(-1, 1) / days   # scale to 0..1 so SGD behaves
    scale = max(spent, 1.0)
    y = per_day.cumsum().to_numpy() / scale
    model = SGDRegressor(penalty=None, fit_intercept=False, learning_rate="constant",
                         eta0=0.05, max_iter=5000, tol=1e-8, random_state=0)
    model.fit(x, y)
    observed_rate = float(model.coef_[0]) * scale / days                 # Rs per day this month
    # early in the month trust last months' habits; later trust this month's own pace
    w = today.day / days
    rate = w * observed_rate + (1 - w) * prior if prior else observed_rate
    forecast = spent + max(rate, 0.0) * (days - today.day)
    return {"spent": round(spent, 2), "forecast": round(forecast, 2), "days_left": days - today.day}

def category_alerts(df, budgets, today):
    """For each category, forecast month-end spend and flag the ones that will exceed the budget."""
    alerts = []
    for cat, limit in budgets.items():
        f = forecast_month(df[df.category == cat], today)
        if f["forecast"] > limit:
            alerts.append({"category": cat, "budget": limit, "spent": f["spent"],
                           "forecast": f["forecast"], "over_by": round(f["forecast"] - limit, 2)})
    return sorted(alerts, key=lambda a: -a["over_by"])

def backtest(df, year, month, check_days=(5, 10, 15, 20)):
    """Honest test: pretend it's day N of a finished month, forecast, then compare with what really happened."""
    actual = float(daily_totals(df, year, month).sum())
    for d in check_days:
        f = forecast_month(df, date(year, month, d))["forecast"]
        print(f"day {d:>2}: forecast {f:>10,.0f}  actual {actual:>10,.0f}  accuracy {100 * (1 - abs(f - actual) / actual):.1f}%")
def default_budgets(df, today):
    """First-run budgets: 90% of each category's average full-month spend before this month."""
    past = df[df.date < pd.Timestamp(today.year, today.month, 1)]
    if past.empty:
        return {}
    monthly = past.groupby([past.date.dt.to_period("M"), "category"]).amount.sum().groupby("category").mean()
    return {c: round(float(v) * 0.9, -2) for c, v in monthly.items() if c != "Uncategorized"}
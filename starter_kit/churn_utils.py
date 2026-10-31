"""
Small utility module provided as an optional starting point for the
churn-risk flagging case study.

Feel free to use, modify, replace, or ignore this entirely -- it is not
guaranteed to be complete or bug-free.
"""
import json


def load_accounts(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("accounts", [])


def compute_trend_pct(weekly_logins, window=4):
    """
    Compare the average of the most recent `window` weeks against the
    average of the `window` weeks before that. Returns a percentage
    change (negative = declining usage).
    """
    recent = weekly_logins[-window:]
    previous = weekly_logins[-window * 2:-window]
    recent_avg = sum(recent) / len(recent)
    previous_avg = sum(previous) / len(previous)
    if previous_avg == 0:
        return 0.0
    return (recent_avg - previous_avg) / previous_avg * 100


def flag_at_risk(account, window=4, decline_threshold_pct=-30.0):
    """Return True if the account's usage trend looks like a churn risk."""
    trend = compute_trend_pct(account["weekly_logins"], window)
    return trend <= decline_threshold_pct

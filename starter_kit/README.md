# Starter Kit — Churn Risk Flagging

## Contents

- `data/account_usage.json` — 8 synthetic customer accounts with weekly login-count history (varying lengths — not every account has been around equally long).
- `churn_utils.py` — a small, optional Python utility module with a trend-calculation and risk-flagging helper, provided as a rough starting point.

## A few notes

- You're free to use, modify, replace, or ignore `churn_utils.py` entirely — it's not guaranteed to be complete, optimal, or bug-free.
- Not all accounts have 12 weeks of history — a couple are much newer. Worth thinking about what a "trend" even means when there isn't much history to compare against.

# Solution Design: Churn Risk Flagging

**Customer:** Vantage Retail Systems, for Dana Reyes, Head of Customer Success

## 1. The problem

Vantage learns that an account is churning only when the customer says they won't renew. By then there's no time to save it. The CS team needs an early warning: a weekly list of accounts whose usage is falling, ranked by urgency, with a plain reason for each, while there's still time to reach out.

The only data is weekly login counts per account, and there's no history of which accounts actually churned. So v1 is a **rules-and-signals early-warning system, not a churn prediction model**. It finds accounts worth a conversation. It doesn't promise that they will churn.

## 2. Assumptions

| # | Assumption | Why |
|---|---|---|
| 1 | Each array is consecutive weeks, oldest first. Weeks are numbered **backward from the last entry, which is always week 12** (the current week), so every account uses the same calendar. A-06 covers weeks 8–12 and A-08 covers weeks 11–12. | The starter README says lengths differ because accounts are different ages, so a short array means the account started recently. It doesn't mean the account has stopped reporting. |
| 2 | A full read needs **6 usable weeks** (two 3-week windows). 4–5 weeks gets a limited "early read". Under 4 weeks is **Too New**. | A trend needs a "before" and an "after". Fewer than 4 points is noise. |
| 3 | If an account's first week is more than 2× the median of its next 3 weeks, it's an onboarding spike and gets dropped before scoring. | New accounts often log in heavily during setup. Keeping that week makes normal settling look like a crash. |
| 4 | Zero logins in the latest week is always **Critical**, whatever the other signals say. | Going completely quiet is the strongest signal we have. A holiday week can cause a false alarm, and CS can dismiss it. |
| 5 | Enterprise accounts get escalated sooner than Starter accounts for the same decline. | There's more revenue at stake, and they usually have a CSM who can act on it. |
| 6 | A missing week is a data gap, not zero logins. | Treating missing data as zero would set off assumption 4 by mistake. |
| 7 | Every threshold is a starting default that we expect to tune. | Without churn outcomes, no threshold can be checked against reality yet. |

## 3. Approach

```
weekly_logins ─► history check ─► drop onboarding spike ─► zero-login check ─► 3 signals + tier ─► classifier ─► label + reason
                 (<4 wks: Too New)                          (0 last week: Critical)
```

### 3.1 Signals (window = 3 weeks)

| Signal | Definition | What it catches |
|---|---|---|
| **1. Recent change** | Mean of the last 3 weeks vs. the mean of the 3 weeks before, as a % change | Sudden drops (A-01, A-05) |
| **2. Consistent slope** | Straight-line slope over the last 6 weeks as % of their mean per week, × R² | Slow steady declines (A-04). Multiplying by R² shrinks it toward 0 for erratic series (A-07) |
| **3. Distance from baseline** | Mean of the last 3 weeks vs. the mean of all usable weeks before them, % | Long declines that look small week to week |
| **4. Plan tier** | Starter = 1, Growth = 2, Enterprise = 3 | Lets the classifier escalate valuable accounts sooner |

Each signal covers a gap in the others. Recent change alone misses A-04, which is only −13% over three weeks, but its slope is steady (R² 0.96) and it's 22% below baseline. A raw slope would treat A-07's ups and downs as a trend, and multiplying by R² fixes that.

### 3.2 Classifier trained on use cases

Labeling the 8 real accounts by hand and then training and predicting on those same 8 would just memorize my labels. Instead, a generator creates about 200 synthetic series for each use case below. It varies the starting level (5–40 logins/week), the length (6–12 weeks), the noise and the plan tier. Then it computes the same 4 features and trains a **shallow decision tree** (`max_depth=4`). The tree learns where the label boundaries fall once noise is in the data, and it can be printed as plain if/else rules for Dana to read.

| Use case | How the synthetic series is generated | Label |
|---|---|---|
| Stable | Flat level, ±10% noise | Healthy |
| Growing | +3 to +10% per week | Healthy |
| Volatile | Flat level, ±20–35% noise, some alternating high/low weeks | Healthy |
| Slow decline | −2 to −5% per week, steady | **At Risk** if Enterprise, otherwise **Watch** |
| Moderate drop | Stable, then −25 to −45% over the last 3–4 weeks | **At Risk** |
| Sharp drop | Stable, then −50 to −90% over the last 2–5 weeks | **Critical** |

The use cases are where my assumptions live. When real outcomes come in ("we flagged X, it churned or renewed"), real labels replace the synthetic ones and the same pipeline retrains.

**Output labels:** Critical (call this week) · At Risk (schedule a check-in) · Watch (re-check in 2 weeks) · Healthy · Too New (the output names the week a full read becomes possible: week 14 for A-06, week 16 for A-08).

## 4. Why a 3-week window

I backtested by running the recent-change signal at the end of every week of the data:

| | 2 weeks | **3 weeks** | 4 weeks |
|---|---|---|---|
| Weeks needed for a full read | 4 | **6** | 8 |
| Accounts with a full read in this data | 7 of 8 | **6 of 8** | 6 of 8 |
| A-05 first crosses −30% | week 8 | **week 8** | week 9 |
| A-01 first crosses −25% | week 9 | **week 9** | week 10 |
| A-07 (choppy, no real trend) swing | −16% to +14% | **−14% to +17%** | −5% to 0% |
| A-04 largest 3-vs-3 drop seen | −11% | **−16%** | −18% |

A 3-week window catches both real drops **a week earlier** than 4 weeks, and a 2-week window gives no extra warning in this data. The trade-off is noise. A-07 goes up one week and down the next, and an odd-length window makes its recent-change signal flip sign every week. It never gets close to a flag threshold, and the R² factor in Signal 2 keeps it from looking like a trend. Moving to 3 weeks doesn't let any more accounts get a full read than 4 weeks (A-06 still has only 4 usable weeks, weeks 9–12), so A-06 goes through the early-read path instead (assumption 2).

## 5. Results on the provided dataset

The signal values were computed on the data at week 12. The labels are what the use cases above imply. The implementation has to reproduce them, and any difference is a bug to investigate.

| Priority | Account | Tier | Recent change | Slope (%/wk, R²) | vs. baseline | Label | Reason |
|---|---|---|---|---|---|---|---|
| 1 | A-05 Cascade Meridian | Ent | −64.4% | −31.8 (0.94) | −80.4% | **Critical** | Dropped from ~34/wk to 4/wk starting in week 7. Steep, steady decline |
| 2 | A-01 Northwind Traders | Growth | −55.6% | −25.1 (0.89) | −63.6% | **Critical** | Steady ~27/wk until week 8, then fell to 8/wk |
| 3 | A-04 Harborview Inc | Ent | −13.3% | −4.6 (0.96) | −22.4% | **At Risk** | Slow, very steady decline from 24 to 17. Enterprise tier |
| – | A-07 Choppy Retail Co | Growth | +9.3% | +2.3 (0.07) | +1.7% | Healthy | Swings week to week around a flat ~19/wk |
| – | A-02 Bluepeak Corp | Growth | +4.8% | +0.4 (0.02) | +4.2% | Healthy | Flat at ~21/wk |
| – | A-03 Solace Digital | Starter | +29.3% | +8.4 (0.99) | +66.7% | Healthy | Growing steadily from 10 to 27 |
| – | A-06 Fresh Startup Co | Starter | +8.7% (2 vs. 2) | – | – | Too New | Started week 8. That 40-login onboarding week was dropped, and weeks 9–12 are stable at ~12/wk. Full read at week 14 |
| – | A-08 New Signup LLC | Starter | – | – | – | Too New | Started week 11, so only 2 weeks of data. Full read at week 16 |

Critical accounts are ordered by tier and then by distance from baseline. No account has a zero-login week, so the override never fires on this data. A synthetic case tests it.

## 6. Trade-offs considered

- **Fixed % threshold (starter kit) vs. multiple signals:** a fixed % threshold is simpler, but at −30% it misses A-04, and with no check for steadiness it reacts to noise. Three signals cost a few more lines of code and fix both problems.
- **Weighted 0–100 score vs. classifier:** a single score is good for ranking hundreds of accounts, but the weights would be guesses. The tree learns its boundaries from the use cases and prints readable rules. For a CS team, labels are easier to act on than numbers.
- **Synthetic use cases vs. hand-labeling the 8 accounts:** hand-labeling is faster, but the model would only memorize the labels. The synthetic use cases state the assumptions openly and keep the training data separate from the data we evaluate.
- **Sensitivity:** I tuned toward catching more declines (Watch exists so that borderline accounts show up without demanding a call). Missing a churn costs a renewal. A false alarm costs one conversation.

## 7. Limitations

- There's no ground truth. The synthetic labels are my assumptions written as examples, so accuracy can't be measured yet.
- Logins alone are a narrow signal. An unhappy customer can keep logging in, and a happy one can log in less after automating their work.
- There's no seasonality handling. A retailer's normal post-holiday dip will look like a decline.
- A-06's drop from 40 to 12 is treated as onboarding settling. If the account is actually losing interest after setup, it looks the same, so CS may still want an onboarding check-in.

## 8. With more time, data, or budget

- **Next:** move the thresholds into a config file. Run weekly and show what changed since last week ("newly At Risk"). Add an LLM-written one-sentence explanation built only from the computed signal values, so it can't make up facts.
- **With outcomes:** record every CS outreach and whether the account renewed, retrain on real labels, and check precision and recall. Use the backtest above to measure how much warning the system really gives.
- **With more signals:** support tickets, how many features each account uses, number of active users vs. seats, billing events. Once each tier has enough accounts, compare each account to similar ones.
- **Longer term:** a survival model (time until churn) once there's enough labeled churn history, and sending flags directly into the CS team's CRM.

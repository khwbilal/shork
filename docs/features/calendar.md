# Calendar

Upcoming market events for today plus 7 days, shown in PKT. Added in WL-039, with the earnings part of WL-045. The calendar page arrives with the MUI portal (WL-047); until then the data is available from the API.

**API:** `GET /api/calendar?days=7&kind=` (`kind` is `macro`, `earnings`, `crypto` or `binance`; anything else returns 400)
**Refresh:** the `calendar` [job](../scheduled-jobs.md) runs daily at 16:00. It also runs once at startup when nothing is stored from today onward.
Code: `backend/app/calendar_feed.py`

## Sources

All sources are free and need no key. Each one is optional: when a source fails, its status shows `available: false` with the error, and its earlier rows are kept.

| Source | Kind | What | Limits |
|---|---|---|---|
| ForexFactory weekly feed | `macro` | USD events of every impact, plus high-impact events from other countries; title, impact, forecast, previous | Covers the current week only (Sunday to Saturday, US time); the next-week feed returns 404. No actual values. |
| Nasdaq earnings calendar | `earnings` | One request per day of the window. Only tickers Binance lists are kept (stock and ETF perps, and spot bStocks), each linked to its Binance symbols. | Before open is stored as 09:30 ET and after close as 16:00 ET, converted to PKT with US daylight saving. "Time not supplied" becomes an all-day event. |
| Binance announcements | `binance` | New listings (including futures launches) and delistings | No structured time: the date is read from the title as an all-day event, and the release time is used when the title has none. Only the latest 20 per category, so rows are never removed. |
| BNB burn, token unlocks | `crypto` | none yet | No free source without a key; listed with `available: false`. CoinMarketCal offers a free key. |

## Response

```json
{ "events": [
  { "id": 12, "source": "nasdaq", "kind": "earnings", "title": "Tesla, Inc. earnings",
    "starts_at": "2026-10-22T01:00:00+05:00", "all_day": false, "session": "after_close",
    "impact": null, "country": "US", "ticker": "TSLA",
    "instrument_symbols": ["BINANCE:TSLAUSDT.P", "BINANCE:TSLABUSDT"],
    "forecast": "$0.22", "previous": null, "actual": null, "url": null, "fetched_at": "..." }
],
  "sources": [{ "name": "nasdaq", "available": true, "error": null, "events": 22, "fetched_at": "..." }] }
```

The window runs from today 00:00 PKT to the end of the day 7 days later, sorted by time.

## In analyses

`POST /api/analyze` adds `market.upcoming_events`: up to 5 high-impact macro events in the next 24 hours. The prompt receives them after the decision fields, so the model can mention them.

## Keeping it fresh

- ForexFactory and Nasdaq rows that the source no longer lists, inside the range it covers, are deleted (rescheduled or cancelled). For Nasdaq this happens only when all 8 daily requests succeeded.
- To widen the window to 14 days, change `refresh(days=...)` in the job. ForexFactory still covers only the current week.

## First week (2026-10-21)

The first run stored 39 events: 22 earnings (Tesla, Meta, IBM, Visa, Robinhood and others), 11 macro and 6 Binance announcements.

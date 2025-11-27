---
ticker: "{{ticker}}"
name: "{{name}}"
sector: "{{sector}}"
stance: "{{stance}}"
added: "{{added_date}}"
last_updated: "{{last_updated}}"
---

# {{ticker}} - {{name}}

**Sector**: {{sector}}
**Current Stance**: {{stance}}

---

## Quick Stats

| Metric | Value |
|--------|-------|
| Price | ${{price}} |
| 52W High | ${{fifty_two_week_high}} |
| 52W Low | ${{fifty_two_week_low}} |
| Market Cap | {{market_cap}} |
| P/E | {{pe_ratio}} |
| Forward P/E | {{forward_pe}} |

---

## Signals

### Danelfin Score
- **Score**: {{danelfin_score}}/10
- **Date**: {{danelfin_date}}

### Analyst Consensus
- **Rating**: {{analyst_rating}}
- **Price Target**: ${{price_target}} (${{target_low}} - ${{target_high}})
- **Analysts**: {{num_analysts}}

---

## Earnings

**Next Report**: {{next_earnings_date}}

### Recent History
| Quarter | EPS Est | EPS Actual | Surprise |
|---------|---------|------------|----------|
| {{q1_quarter}} | {{q1_est}} | {{q1_actual}} | {{q1_surprise}} |
| {{q2_quarter}} | {{q2_est}} | {{q2_actual}} | {{q2_surprise}} |

---

## Recent News

{{#each news}}
- **{{date}}**: {{headline}} ([source]({{url}}))
{{/each}}

---

## My Notes

*Add your research notes here*

---

## Trade History

{{#each trades}}
- **{{date}}** - {{action}} {{shares}} @ ${{price}}
  - Thesis: {{thesis}}
  - Outcome: {{outcome}}
{{/each}}

---

## Links

- [Yahoo Finance](https://finance.yahoo.com/quote/{{ticker}})
- [SEC Filings](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={{ticker}}&type=10-K&dateb=&owner=include&count=10)
- [Danelfin](https://danelfin.com/stock/{{ticker}})

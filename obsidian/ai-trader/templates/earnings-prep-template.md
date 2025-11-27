---
ticker: "{{ticker}}"
report_date: "{{report_date}}"
fiscal_quarter: "{{fiscal_quarter}}"
status: "upcoming"
---

# {{ticker}} Earnings Preview - {{fiscal_quarter}}

**Report Date**: {{report_date}}
**Time**: {{report_time}}

---

## Expectations

### Consensus Estimates
| Metric | Estimate | YoY Change |
|--------|----------|------------|
| EPS | ${{eps_estimate}} | {{eps_yoy}}% |
| Revenue | ${{rev_estimate}} | {{rev_yoy}}% |

### Whisper Number
- EPS Whisper: ${{eps_whisper}}

---

## Key Questions to Answer

1.
2.
3.

---

## What to Watch

### Bull Case
-

### Bear Case
-

### Key Metrics
-

---

## Recent News & Context

{{#each news}}
- **{{date}}**: {{headline}}
{{/each}}

---

## Historical Performance

| Quarter | EPS Est | EPS Actual | Surprise | Stock Reaction |
|---------|---------|------------|----------|----------------|
{{#each history}}
| {{quarter}} | ${{est}} | ${{actual}} | {{surprise}}% | {{reaction}}% |
{{/each}}

---

## My Position

- **Current Stance**: {{stance}}
- **Shares Held**: {{shares}}
- **Avg Cost**: ${{avg_cost}}

### Pre-Earnings Plan
- [ ] Hold through earnings
- [ ] Trim before earnings
- [ ] Add if dips pre-earnings

---

## Post-Earnings Update

*Fill in after earnings release*

### Results
| Metric | Estimate | Actual | Surprise |
|--------|----------|--------|----------|
| EPS | ${{eps_estimate}} | $ | % |
| Revenue | ${{rev_estimate}} | $ | % |

### Guidance
-

### Key Takeaways
-

### Stock Reaction
- After-hours:
- Next day:

### Action Taken
-

---

## Links

- [[{{ticker}}|Ticker Research]]
- [Earnings Call Transcript]()
- [Press Release]()

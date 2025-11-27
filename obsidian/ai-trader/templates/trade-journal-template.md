---
ticker: "{{ticker}}"
action: "{{action}}"
date: "{{date}}"
price: {{price}}
shares: {{shares}}
status: "open"
---

# Trade: {{action}} {{ticker}}

**Date**: {{date}}
**Action**: {{action}}
**Price**: ${{price}}
**Shares**: {{shares}}
**Value**: ${{total_value}}

---

## Pre-Trade Analysis

### Thesis
{{thesis}}

### Signals at Entry
| Source | Score | Sentiment |
|--------|-------|-----------|
{{#each signals}}
| {{source}} | {{score}} | {{sentiment}} |
{{/each}}

### Key Catalysts
-

### Risks
-

---

## Price Targets

- **Target 1**: ${{target_1}} ({{target_1_pct}}%)
- **Target 2**: ${{target_2}} ({{target_2_pct}}%)
- **Stop Loss**: ${{stop_loss}} ({{stop_loss_pct}}%)

---

## Updates

### {{date}}
Initial entry.

---

## Outcome

**Status**: Open
**Exit Date**:
**Exit Price**:
**Return**:
**Holding Period**:

### Post-Trade Notes
*What did I learn?*

---

## Links

- [[{{ticker}}|Ticker Research]]
- [[{{weekly_brief}}|Weekly Brief]]

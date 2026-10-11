# GĐ5 keyword: needs_data_or_review

Paired dev exploration, not independent confirmation. Inspect subgroup, entity, no-match and latency regressions before selecting; locked test is never tuned here.

## Runs

| Configuration | Status |
|---|---|
| bm25-baseline | ok |
| bm25-coverage050 | ok |
| bm25-coverage075 | ok |
| bm25-accents075 | ok |

## Gates

- bm25-baseline: not reviewed dev
- bm25-baseline: expand and review the judgment pool
- bm25-baseline: no-match judgments do not cover catalog (smoke only)
- bm25-coverage050: not reviewed dev
- bm25-coverage050: expand and review the judgment pool
- bm25-coverage050: no-match judgments do not cover catalog (smoke only)
- bm25-coverage075: not reviewed dev
- bm25-coverage075: expand and review the judgment pool
- bm25-coverage075: no-match judgments do not cover catalog (smoke only)
- bm25-accents075: not reviewed dev
- bm25-accents075: expand and review the judgment pool
- bm25-accents075: no-match judgments do not cover catalog (smoke only)

Paired deltas and 95% cluster CI: see report.json. No production config selected.

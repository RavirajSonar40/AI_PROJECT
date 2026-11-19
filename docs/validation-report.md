# AI Knowledge & Action Platform Validation Report

## Recommendation engine

The offline benchmark contains four user profiles with known relevant
documents and the ranking returned by the recommendation engine. At K=5:

| Metric | Result |
| --- | ---: |
| Precision@5 | 0.6500 |
| Recall@5 | 0.9167 |
| Hit rate@5 | 1.0000 |

This means every benchmark user received at least one relevant document in
their top five, and the ranking recovered 91.67% of the known relevant
documents on average. The benchmark is intentionally small and should be
expanded with anonymised production feedback before treating it as a final
quality target.

## Baseline vs enhanced RAG

The dashboard's completed six-case evaluation run produced the following
comparison:

| Metric | Baseline | Enhanced | Change |
| --- | ---: | ---: | ---: |
| Faithfulness | 100.0% | 100.0% | +0.0 pts |
| Answer relevance | 69.9% | 71.2% | +1.3 pts |
| Context precision | 29.2% | 58.3% | +29.2 pts |
| Context recall | 100.0% | 100.0% | +0.0 pts |
| Composite score | 79.8% | 85.9% | +6.1 pts |
| Average latency | 2,101.5 ms | 6,932.5 ms | +4,831.0 ms |

The enhanced pipeline improved retrieval quality, especially context
precision, but was slower on this run. That trade-off should be monitored in
future runs. Ragas scores are stored separately when Ragas and a compatible
provider are available; the deterministic metrics remain the fallback.

## Test status

- Angular production build: passed
- Angular frontend tests: passed (2 tests)
- Python compilation: passed
- Recommendation benchmark tests: added
- Backend suite: blocked in the current shell because `pgvector` is not installed
- Full agent/database workflow: requires project dependencies and PostgreSQL/pgvector

# Evaluation and Quality Metrics

## Why evaluate
A RAG system can look correct and be wrong.
Systematic evaluation catches regressions when you change the model,
the chunk size or the system instructions.

## Evaluation set
Build a set of questions with their expected answer and reference documents.
At least 30 questions covering the main topics of the corpus are recommended.

The set should include easy cases, ambiguous cases and questions with no answer in the corpus.

## Main metrics
- Retrieval accuracy: does the correct fragment appear among those retrieved?
- Faithfulness: is the answer supported by the retrieved context?
- Relevance: does the answer actually address the question?
- Abstention rate: does the system admit it does not know when there is no evidence?

## Evaluating abstention
If no fragments exceed the similarity threshold,
the system must state that it lacks enough information
instead of inventing an answer. This behaviour matters as much as being correct.

## Automated tests
The project includes pytest tests for repositories, services and endpoints.
Integration tests use a dedicated PostgreSQL database on port 5433.

## Load testing
Latency p50, p95 and p99 are measured for /rag/ask and /agent/ask.
Rate limiting protects the system against traffic spikes.

## Production monitoring
- Error rate per endpoint.
- Retrieval latency and generation latency measured separately.
- Number of answers with empty context.
- Cost per query in tokens.

## Human review
A random sample of 5% of answers is reviewed weekly
by the knowledge team to detect quality degradation.

## Continuous improvement
Every quality incident adds a new question to the evaluation set,
so the same mistake cannot recur without being detected.

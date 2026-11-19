# How RAG Works (Retrieval-Augmented Generation)

## Definition
RAG combines two phases: information retrieval and text generation.
Instead of answering only from what the model memorised during training,
the system first searches its own knowledge base for relevant fragments
and includes them in the model's context.

## Why it is used
- It reduces hallucinations because the model works from real evidence.
- It can cite the exact source of every claim.
- Updating knowledge does not require retraining the model: uploading documents is enough.
- It lets you control which information the system may use for privacy reasons.

## Pipeline phases
1. Ingestion: text is extracted from documents and cleaned.
2. Chunking: the text is split into manageable fragments.
3. Embedding: each fragment is converted into a numeric vector.
4. Indexing: the vectors are stored in a vector database.
5. Retrieval: the question is vectorised and the closest fragments are fetched.
6. Generation: the model answers using the fragments as context.

## Key parameters
- chunk_size: fragment size. Small values give precision, large values give context.
- overlap: overlap between fragments so ideas are not cut in half.
- top_k: number of fragments retrieved. In this platform it is configurable from 1 to 10.
- min_similarity: minimum similarity threshold to discard weak matches.

## Quality metrics
- Recall: share of relevant fragments that are actually retrieved.
- Precision: share of retrieved fragments that are relevant.
- Faithfulness: how well the answer is supported by the retrieved context.
- Latency: total time from question to answer.

## Common mistakes
- Fragments too small: the model loses context and answers incompletely.
- Fragments too large: irrelevant content is retrieved and cost goes up.
- Very short or ambiguous questions: semantic search returns poor results.
- No source citations: the user cannot verify the answer.

## Best practices
Write complete questions, keep documents up to date
and periodically review answer quality with an evaluation set.

# Embeddings Explained

## What an embedding is
An embedding is a numeric representation of text in the form of a vector.
Texts with similar meaning produce vectors that are close in space,
even when they do not share the same words.

For example, "how do I request vacation" and "apply for days off"
have very close embeddings despite having no words in common.

## Dimensions
Dimensions are the number of components in the vector.
This platform uses a multilingual model with 384 dimensions,
enough to capture meaning with modest storage cost.

Larger models, such as 1024 or 1536 dimensions, capture finer nuances
but require more memory and make search slower.

## Similarity
The most common metric is cosine similarity, which measures the angle between two vectors.
A value close to 1 means high semantic similarity; close to 0 means little relation.

In practice, thresholds between 0.25 and 0.40 work well to filter noise
in technical documentation searches.

## Multilingual models
A multilingual model lets you search in English and find fragments in Spanish
and vice versa. This is essential in companies with documentation in several languages.

## Embedding cache
Computing a query embedding has a compute cost.
The platform stores each question's vector in Redis for 3600 seconds,
so repeated questions are answered without recomputing.

## Normalisation
Vectors are usually normalised to length 1 before storage,
which simplifies cosine similarity and improves numerical stability.

## Vector indexing
For large volumes, approximate indexes such as HNSW or IVFFlat are used.
Below one million fragments, an exact search with pgvector
offers good latency and deterministic results.

## Reindexing
If the embedding model changes, all vectors must be regenerated,
because vectors from different models are not comparable.

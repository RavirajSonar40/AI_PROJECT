# AI Glossary

## LLM
Large Language Model. A model trained on large volumes of text
able to understand and generate natural language.

## Token
The smallest unit of text a model processes. In English, one token is roughly
4 characters or three quarters of a word. The cost of a call depends on the token count.

## Prompt
An instruction or set of instructions sent to the model.
A good prompt defines the task, the output format and the constraints.

## System prompt
A higher-priority instruction that defines the model's behaviour
for the whole conversation.

## Context
All the information available to the model in a given call,
including the prompt and, in a RAG system, the retrieved fragments.

## Context window
The maximum number of tokens a model can process in a single call.

## Hallucination
A model answer that sounds plausible but is incorrect or invented.
RAG and source citations reduce this risk.

## Temperature
A parameter controlling the randomness of generation.
At temperature 0 answers are more deterministic, which is useful for factual data.

## Fine-tuning
Further training of a model on your own data to specialise it for a task.
It is more expensive than RAG and requires retraining when the knowledge changes.

## Chunk
A fragment of a document that is processed and indexed independently.

## Vector
An ordered list of numbers. In AI it is used to represent the meaning of text.

## Vector index
A structure that makes searching for nearby vectors efficient.

## Tool function
An external function the model can invoke through tool calling,
for example querying a database or running an administrative action.

## Agent graph
A representation of the agent's steps as nodes and edges, with persistent state.
LangGraph is the framework used in this platform.

## Checkpoint
A saved snapshot of a conversation's state that allows pausing and resuming execution.

## ZDR
Zero Data Retention. A mode where the model provider does not store requests.
Some providers restrict the model catalogue available in this mode.

# Agents, Tools and Human Approval

## What an agent is
An agent is a language model that can decide which tool to use to solve a request,
instead of answering with text only.

The agent receives the question, reasons, picks a tool, observes the result
and continues until it can answer.

## Available tools
- get_system_info: returns the platform version, environment and status.
- search_knowledge: searches the uploaded documents and returns fragments with similarity.
- clear_embedding_cache: clears the query embedding cache. This is an administrative action.

## Tool calling
The model does not execute code directly: it emits a structured call
with the tool name and its arguments as JSON.
The orchestrator validates and runs the tool, then returns the result to the model.

## Human in the loop
Sensitive actions are never executed automatically.
The clear_embedding_cache tool raises an interrupt that pauses the graph
and returns an approval request to the user.

The graph is suspended in the PostgreSQL checkpointer.
When the user approves or rejects, execution resumes from that exact point
with the decision recorded.

## Benefits of the interrupt
- Control: no destructive action happens without explicit consent.
- Auditability: the decision and the user's note stay in the thread state.
- Resilience: if the server restarts, the paused conversation is not lost.

## Memory
Every conversation has a thread_id. The state includes previous messages,
so the agent remembers the context and can continue a task across turns.

## Safety limits
- Recursion limit of 12 steps to avoid infinite loops.
- Per-client rate limiting on query endpoints.
- Validation of each tool's arguments before execution.

## Best practices
Define tools with clear descriptions, return explicit errors
and require human approval for any operation with irreversible effects.

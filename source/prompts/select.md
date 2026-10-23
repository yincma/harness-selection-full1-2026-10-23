# Context

The same coding agent ran the task below <<N>> times independently, with the same system prompt. For each attempt you get a digest of the run (its messages, tool calls and their outputs), the result of the task's provided tests on its final deliverable when the task has them, and its duration and credit cost.

## Task statement given to the agent

<<TASK>>

<<RUNS>>

# Your job

Choose the ONE attempt whose deliverable is most likely to score best on the task's hidden evaluation. Cost and duration do not matter for this choice.

# Output format (exactly)

<rationale>
2-5 bullet points
</rationale>
<choice>
the attempt number only, e.g. 2
</choice>

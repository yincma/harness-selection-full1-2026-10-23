# Context

A coding agent ran once on the task below with the current system prompt. You get a digest of that run (its tool calls and their outputs) and the result of the task's provided example tests on its final deliverable.

## Task statement given to the agent

<<TASK>>

## Current system prompt

<<CURRENT_PROMPT>>

## Run digest

<<DIGEST>>

## Provided-test result on the deliverable

<<VISIBLE_RESULT>>

# Your job

Diagnose what limited this run (process, strategy, verification, use of time), then write TWO revised system prompts:

1. GENERAL: changes that would help this agent on coding tasks in general.
2. SPECIFIC: changes aimed at this task.

Constraints for each prompt: at most 600 words; no solution code; do not mention tools or commands the agent does not have; the agent will receive the same task statement.

# Output format (exactly)

<diagnosis>
3-6 bullet points
</diagnosis>
<prompt_general>
the full general prompt
</prompt_general>
<prompt_specific>
the full specific prompt
</prompt_specific>

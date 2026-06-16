---
name: research
description: Use when you have a question about this codebase or what we've documented, and need a sourced, cited answer read from the actual source — the KB and the code — not answered from memory.
---

# Research

**Core principle:** Bring a sourced answer *to* the user. Every claim traces to something you read *this session* — never memory, never assumption. Find the truth in the most authoritative source and cite it (`file:line`, doc, KB entry).

## Where the answer lives

The answer is always in the code — read it (preferably with serena) to get and confirm it. **If `kb_path` is configured, load `knowledge-base` first** to locate the right surfaces and files faster, then read the code to validate.

Code is ground truth. When the KB and code disagree, the code wins — report the drift, and fix the KB.

External / wider-world questions — best practice, library choice, "is X true?" — aren't this skill's job. Use deep-research-agent specialist from **using-software-specialists** skill; don't answer them from memory.

## Read with serena, not from memory

For codebase questions, load the *actual* symbol — don't recall it:
`get_symbols_overview` (map a file) → `find_symbol` (read one symbol's body, not the whole file) → `find_referencing_symbols` (trace callers, "what happens when X?"). Grep + Read only when serena can't resolve it. Reads fewer tokens *and* cites exactly.

## Match effort to the question

- **Direct lookup** ("do we have X?", "payload of event X?") → find it, cite `file:line`, done.
- **Tracing** ("what happens when X?") → follow it with `find_referencing_symbols`; give confidence per finding, report conflicts, set the stopping criterion upfront.

## Asking the user questions

**Clarify an ambiguous request before investigating.** If what the user wants answered isn't explicit, ask first — researching the wrong question wastes time and tokens. Keep it tight: ask only what you can't determine yourself and what changes *where you look*. Once the question is clear, investigate — don't ask the user to recite what you can read, and never ask what the research is supposed to tell you.

## Output

Answer + cited source. For non-trivial findings, add confidence and named gaps. The deliverable is the answer — stop there. If the user then wants to act on it, that's a separate step (e.g. **using-software-specialists** to plan and implement).

## Red Flags

| Thought | Reality |
|---------|---------|
| "I'm pretty sure we have an endpoint for that" | Don't answer code from memory. Read the symbol with serena, cite `file:line`. |
| "Let me just Read the whole file" | Use serena's symbol tools — load only what answers the question. |
| "The KB says so — good enough" | Docs drift. Validate against the code; it's ground truth. |
| "Let me go research the best-practice approach" | That's external tech research — hand off to using-software-specialists. |
| "Let me ask what they're trying to build" | They came with a question, not a goal. Answer it first. |
| "Let me research more to be thorough" | Know your stopping criterion. Good-enough beats never-finished. |

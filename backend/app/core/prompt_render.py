"""Prompt Builder text assembly (docs/05-task.md Phase 14;
docs/02-architecture.md section 78).

Pure string templating — no I/O, no DB access — so the same inputs
always render the same `rendered_prompt` text (this phase's "Prompt
generation reproducible" Acceptance Criteria). Section order matches
section 78's template exactly: System, Context, Conversation (omitted
when absent — see below), Question, Instructions, Output Schema.

The Conversation Memory section is only emitted when `conversation_text`
is provided. Persistent conversation memory is Phase 16
(`docs/05-task.md`), which doesn't exist yet, so `prompt_service.py`
always calls this with `conversation_text=None` today; an empty
"Conversation:" header with nothing under it would look like a bug to
whoever reads the rendered prompt, so omitting the section entirely is
the honest behavior until Phase 16 has real history to put there.

`DEFAULT_FORMATTING_INSTRUCTIONS` mirrors section 78's example verbatim
("Answer only using the supplied context...") — a lightweight instance
of section 81's "Strict prompting"/"No-context fallback" hallucination
strategies, used whenever a `PromptTemplate` doesn't override it.
"""

import json

DEFAULT_FORMATTING_INSTRUCTIONS = (
    'Answer only using the supplied context. If the answer is unavailable, say "I don\'t know."'
)


def render_prompt(
    *,
    system_prompt: str,
    context_text: str,
    query_text: str,
    formatting_instructions: str | None = None,
    output_schema: dict | None = None,
    conversation_text: str | None = None,
) -> str:
    sections = [f"System:\n{system_prompt}", f"Context:\n{context_text}"]
    if conversation_text:
        sections.append(f"Conversation:\n{conversation_text}")
    sections.append(f"Question:\n{query_text}")
    sections.append(
        f"Instructions:\n{formatting_instructions or DEFAULT_FORMATTING_INSTRUCTIONS}"
    )
    if output_schema:
        sections.append(f"Output Schema:\n{json.dumps(output_schema, indent=2)}")
    return "\n\n".join(sections)

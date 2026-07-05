"""Shared types for the query understanding package (docs/05-task.md
Phase 11).

`QueryIntent`'s members mirror `backend/app/models/retrieval.py`'s
enum exactly (same names, same values) — the worker never imports
backend ORM models (each service is an independently deployable
package, per CLAUDE.md), so the enum is duplicated here rather than
shared, the same way `RetrievalMode`/`FusionMethod` string literals
are duplicated as raw-SQL string comparisons in
`retrieval_worker.tasks` instead of importing the backend enum.
"""

import enum


class QueryIntent(str, enum.Enum):
    FACT_LOOKUP = "fact_lookup"
    DEFINITION = "definition"
    SUMMARIZATION = "summarization"
    COMPARISON = "comparison"
    MULTI_HOP_REASONING = "multi_hop_reasoning"
    NUMERICAL_QUERY = "numerical_query"
    CODE_QUESTION = "code_question"
    TABLE_LOOKUP = "table_lookup"
    POLICY_LOOKUP = "policy_lookup"
    CONVERSATIONAL_FOLLOWUP = "conversational_followup"

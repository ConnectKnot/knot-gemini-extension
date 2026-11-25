# Knot Context Governance for Gemini CLI

Knot (`https://connectknot.com`) provides shared context and temporal `v1 -> v2` context governance over the Model Context Protocol (`https://api.connectknot.com/mcp`). Use it so decisions, architecture constraints, and handoffs stay consistent across Gemini CLI, ChatGPT, Claude, Cursor, Kiro, and Antigravity.

## Turn-0 Context Recovery

When starting a session or answering a question that depends on prior project decisions, constraints, or active work across tools, recover context before proposing changes:

1. Check active scope if you are unsure whether the task belongs to a personal or shared team Knot by calling `knot_list_scopes` (and switch with `knot_set_active_scope` when needed).
2. Call `get_context_recovery` (with `trigger: "session_start"` or `trigger: "user_request"`, plus optional `entity_hint` or `query`) for session resumption and recent changes.
3. Call `get_relevant_context` (with `entity_hint` and/or `query`) for focused topic lookups. Use `query_mode: "trajectory"` when you need both the original `v1` baseline and the active `v2` rule.
4. Call `check_pending_handoffs` at Turn 0 to check whether another AI tool left a task for Gemini CLI.
5. Skip Knot calls on purely self-contained questions that do not depend on saved project or user context.

## v1 -> v2 Supersession Governance

Never leave contradictory `v1` and `v2` decisions active at the same time. Whenever a decision, constraint, architecture rule, or project state changes:

1. Query the existing claim first with `get_relevant_context` to obtain the current item UUID or its working-memory anchor (`updates_ref`, such as `"K1"`).
2. Write the replacement with `propose_context` (or `batch_propose_context` for up to 25 atomic updates):
   - Set `kind` to `"decision"`, `"constraint"`, `"fact"`, `"goal"`, or `"project_state"` with a clear `entity_hint` (topic or project name) for immediate cross-AI visibility.
   - Write one atomic `statement` and include `rationale` explaining why `v2` replaces `v1`.
   - Pass `supersedes_context_id` (the replaced item's UUID) or `updates_ref` so Knot links the `v1 -> v2` lineage cleanly.
   - Provide a unique `idempotency_key` so retries never create duplicates.
3. If `propose_context` returns `needs_clarification` or reports `potential_conflicts`, confirm with the user whether the new item replaces an overlapping item (`supersedes_context_id`) or stands alongside it (`coexists_with_context_ids`).
4. Report what you read or updated in plain sentences without surfacing raw internal UUIDs unless the user asks for them.

## Cross-AI Handoffs

Use Knot handoffs to move scoped work cleanly between Gemini CLI and other connected AI clients:

- **Receive work**: Call `check_pending_handoffs` to inspect incoming tasks, then call `update_handoff_status` with `"accepted"`, `"working"`, `"completed"`, `"interrupted"`, or `"rejected"` and a concise `resolution_summary`.
- **Delegate work**: Call `create_handoff` with `destination_client_id` (for example `"claude"`, `"chatgpt"`, `"cursor"`, or `"antigravity"`), a clear `task` summary, and relevant `context_refs` or structured `payload`.

## Secret and PCI Safety Boundaries

Protect sensitive credentials and regulated payment data at every write boundary:

- NEVER pass raw API keys, OAuth client secrets, passwords, bearer tokens, private keys, or credit card numbers (PAN/CVV) into `propose_context`, `batch_propose_context`, `sync_context_snapshot`, or `create_handoff`.
- Knot's write door enforces PCI-CDE payload rejection (`HTTP 422 PCI_CDE_PAYLOAD_REJECTED`) and blocks high-entropy credential assignments (`Shannon entropy H >= 3.55 bits/char`, while allowing git commit SHAs and UUIDv4 identifiers).
- Reference secrets only by non-sensitive pointers (such as environment variable names, KMS key aliases, or vault paths).
- If any Knot tool reports missing authentication or insufficient scope, instruct the user to run `/mcp auth knot` inside Gemini CLI.

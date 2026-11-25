# Knot Extension for Gemini CLI

Governed shared context, `v1 -> v2` decision supersession, and cross-AI handoffs for Google Gemini CLI over the Model Context Protocol (`https://api.connectknot.com/mcp`).

## TL;DR

Flat AI memory stores chat notes in an append-only vector or key-value list. When a budget, API contract, compliance rule, or engineering decision changes, flat memory returns outdated `v1` notes alongside current `v2` rules and leaves the model to guess which one is true.

**Context Governance** solves this with temporal version control (`v1 -> v2` supersession) and user-approved OAuth 2.1 scoping:

- **Deterministic `v1 -> v2` supersession**: Using the CARMA-16 state engine and Universal Context Schema (`UCS v1`), updating a decision via `propose_context` (`supersedes_context_id`) retires `v1` from active state while preserving the full audit lineage of who changed what and why.
- **Fast Turn-0 reads with zero read-time LLM calls**: `get_context_recovery` and `get_relevant_context` return active governing truth in sub-15ms without re-summarizing raw transcripts.
- **OAuth 2.1 with PKCE scoping**: Every Gemini CLI session authenticates with per-client, revocable OAuth 2.1 grants (`context:read`, `context:propose`, `context:contribute:project`) instead of shared static API keys.
- **Cross-AI continuity**: Specs, constraints, and handoffs move cleanly across Gemini CLI, ChatGPT, Claude, Cursor, Kiro, and Antigravity.

## Quick Start

Install the extension in Gemini CLI directly from GitHub:

```bash
gemini extensions install https://github.com/ConnectKnot/knot-gemini-extension
```

Inside a Gemini CLI session, authenticate with Knot over OAuth 2.1:

```text
/mcp auth knot
```

Complete the browser consent flow at `https://api.connectknot.com`. No API keys or bearer tokens are stored in `gemini-extension.json`.

## Included Components

- [`gemini-extension.json`](gemini-extension.json): Extension manifest (`name: "knot"`, `version: "1.0.0"`) pointing `mcpServers.knot.httpUrl` to `https://api.connectknot.com/mcp` with OAuth enabled and `contextFileName: "GEMINI.md"`.
- [`GEMINI.md`](GEMINI.md): Agent instructions for Turn-0 recovery, `v1 -> v2` supersession, cross-AI handoffs, and secret/PCI safety boundaries.
- [`commands/knot/recover.toml`](commands/knot/recover.toml): `/knot:recover` slash command wrapping `get_context_recovery`, `get_relevant_context`, and `check_pending_handoffs`.
- [`commands/knot/supersede.toml`](commands/knot/supersede.toml): `/knot:supersede` slash command enforcing `v1 -> v2` replacement via `propose_context` (`supersedes_context_id`).
- [`commands/knot/handoff.toml`](commands/knot/handoff.toml): `/knot:handoff` slash command wrapping `check_pending_handoffs`, `update_handoff_status`, and `create_handoff`.
- [`scripts/validate_extension.py`](scripts/validate_extension.py) and [`tests/test_gemini_extension.py`](tests/test_gemini_extension.py): Validation script and standard-library test suite.

## Slash Commands

Use the bundled `/knot:*` commands inside Gemini CLI:

```text
/knot:recover orderstream webhook retry policy
/knot:supersede OrderStream retry policy is now max 3 exponential backoff retries instead of 5 fixed retries
/knot:handoff claude Implement the verified webhook handler and update integration tests
```

## Self-Hosted Enterprise VPC Override (`Knot EnterpriseBrain`)

Regulated engineering teams can run the exact same Knot engine inside their own cloud or on-prem network (`KNOT_DEPLOYMENT_MODE=self_hosted`) on PostgreSQL with `pgvector`.

Start your internal **Knot EnterpriseBrain** service with zero outbound model traffic:

```bash
export KNOT_DEPLOYMENT_MODE=self_hosted
export KNOT_ALLOW_REMOTE_MODELS=false
export DATABASE_URL="postgres://knot:password@postgres.internal:5432/knot"
export KNOT_ORG_LICENSE="<offline-ed25519-license>"
```

Then override `mcpServers.knot.httpUrl` in your local or organization `~/.gemini/settings.json` to route Gemini CLI to your private in-VPC `/mcp` endpoint instead of the hosted cloud endpoint:

```json
{
  "mcpServers": {
    "knot": {
      "httpUrl": "https://knot.internal.corp/mcp",
      "oauth": {
        "enabled": true
      }
    }
  }
}
```

See the full architecture and Helm preset guide at [Knot EnterpriseBrain](https://connectknot.com/enterprise-brain).

## Security, Privacy, and VPC FAQ

### How does Knot authenticate Gemini CLI without static API keys?

Knot uses OAuth 2.1 with PKCE and Dynamic Client Registration discovered via `https://api.connectknot.com/.well-known/oauth-protected-resource`. Running `/mcp auth knot` opens a standard consent flow where you approve exact scopes (`context:read`, `context:propose`, `context:contribute:project`) that you can revoke in one click from your Knot dashboard.

### How does Knot prevent outdated v1 decisions from leaking into active answers?

Flat vector stores retrieve older chunks alongside newer ones and leave the LLM to resolve contradictions. Knot compiles active state at write time: when a new rule passes `supersedes_context_id` or `updates_ref` in `propose_context`, the older `v1` record is marked superseded so `get_relevant_context` and `get_context_recovery` serve only the governing `v2` truth while keeping full audit history available via `query_mode: "trajectory"`.

### What stops API keys, passwords, or payment card numbers from being stored?

`GEMINI.md` and the `/knot:supersede` and `/knot:handoff` commands instruct Gemini never to submit credentials or payment card data. On the server side, Knot's write door rejects raw PAN/CVV payloads with `HTTP 422 PCI_CDE_PAYLOAD_REJECTED` and blocks high-entropy secret assignments (`Shannon entropy H >= 3.55 bits/char`, while allowing git commit SHAs and UUIDv4s) before embedding or persistence.

### How is data isolated across personal notes and shared team projects?

OAuth 2.1 grants restrict Gemini CLI to only the personal or shared project Knots you explicitly authorize. Within a session, `knot_list_scopes` and `knot_set_active_scope` keep personal context separate from shared workspace scopes, and personal profile kinds (`preference`, `person`, `relationship`) wait in a manual review queue before other AIs can read them.

### Can we deploy Knot inside our own VPC with zero outbound egress?

Yes. **Knot EnterpriseBrain** runs the single Knot codebase inside AWS EKS, GCP GKE, Azure AKS, or air-gapped Kubernetes clusters using `KNOT_DEPLOYMENT_MODE=self_hosted` and `KNOT_ALLOW_REMOTE_MODELS=false`. That disables outbound model calls, telemetry, and license phone-home traffic while keeping all MCP traffic inside your private network.

### How do KMS encryption custody and subject deletion work in EnterpriseBrain?

EnterpriseBrain unwraps 3-level HKDF keys (`K_org_root -> K_domain -> K_subject`) at boot using AWS KMS (SigV4), GCP Cloud KMS, Azure Key Vault, or HashiCorp Vault. Deleting a subject key (`DELETE /v1/subjects/:id/key`) renders all associated ciphertext permanently unreadable in under 100ms without expensive index rewrites.

### What happens when we ingest URLs or documents into Knot?

When another client or workflow uses `ingest_url` or `create_ingest_drop`, Knot extracts quote-grounded facts and immediately shreds the raw HTML or uploaded file. You can also delete an ingest receipt and its extracted items at any time with `purge_ingest_receipt`.

## Links and Documentation

- Knot Homepage: https://connectknot.com
- Knot EnterpriseBrain (Self-Hosted VPC): https://connectknot.com/enterprise-brain
- Whitepaper (CARMA-16 and UCS): https://connectknot.com/whitepaper
- Quickstart and MCP Setup: https://connectknot.com/quickstart
- Full Architecture and Tool Reference: https://connectknot.com/llms-full.txt

## Validation

Run the test suite and extension validator locally:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_extension.py
```

## License

MIT License. See [LICENSE](LICENSE).

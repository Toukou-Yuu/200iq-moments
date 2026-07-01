# 200iq-moments MCP Tools

`200iq-moments` exposes native MCP tools for Alice/Hermes alongside the REST API. The MCP adapter shares repository and sync-service logic with FastAPI; it does not call the local REST endpoints.

## Start commands

Local stdio MCP:

```bash
uv run 200iq-moments mcp
```

Local HTTP/Streamable HTTP MCP:

```bash
uv run 200iq-moments mcp-http --host 127.0.0.1 --port 8201 --path /mcp
```

REST API:

```bash
uv run 200iq-moments serve --host 127.0.0.1 --port 8200
```

Production Docker uses the same image with a separate MCP sidecar process:

```text
200iq-moments       -> REST API on 127.0.0.1:8200/v1
200iq-moments-mcp   -> MCP HTTP on 127.0.0.1:8201/mcp
```

## Hermes configuration

```yaml
mcp_servers:
  cases:
    url: http://127.0.0.1:8201/mcp
    timeout: 120
    connect_timeout: 60
```

Verify after deployment:

```bash
hermes mcp list
hermes mcp test cases
```

Current Hermes sessions may need `/reload-mcp`, `/new`, or a process restart before new tools appear.

## Tool inventory

| Tool | Permission | Side effects |
|---|---:|---|
| `case_get_template` | read | None |
| `case_validate` | read | None |
| `case_preview` | read | None |
| `case_create` | write | Writes a Markdown case and enqueues retrieval sync unless `dry_run=true`. |
| `case_update` | write | Updates a case and enqueues retrieval sync unless `dry_run=true`. |
| `case_search` | read | None |
| `case_get` | read | None |
| `case_archive` | write | Archives or soft-deletes a case and enqueues retrieval sync unless `dry_run=true`. |
| `case_sync_index` | write | Enqueues retrieval sync for one case unless `dry_run=true`. |
| `case_rebuild_index` | admin | Enqueues a full retrieval-index rebuild. Dry-run by default. |
| `case_stats` | read | None |

## Safe write flow

For new records, use:

1. `case_get_template`
2. `case_validate`
3. `case_preview`
4. `case_create` with `dry_run=true` if unsure
5. `case_create` with `dry_run=false` when approved

For broad index operations, call `case_rebuild_index` first with the default `dry_run=true`, then explicitly set `dry_run=false` only when ready to enqueue the rebuild.

## Response envelope

Success:

```json
{
  "ok": true,
  "summary": "Created 200iq case 001: 机场套餐误判",
  "data": {},
  "warnings": []
}
```

Error:

```json
{
  "ok": false,
  "error": {
    "code": "CASE_NOT_FOUND",
    "message": "Case not found: 999",
    "retryable": false,
    "suggested_action": "Call case_search first, then retry with an existing case_id."
  }
}
```

## Common errors

- `CASE_NOT_FOUND`: call `case_search` before `case_get`, `case_update`, or `case_archive`.
- `CASE_VALIDATION_ERROR`: call `case_get_template`, fix the payload, then retry.
- `INVALID_ARCHIVE_MODE`: use `archive` or `delete`.
- `TOOL_CALL_FAILED`: inspect service settings, data directory ownership, and sync database state.

## Tests

```bash
uv run --extra dev pytest tests/mcp -q
uv run --extra dev pytest -q
python -m compileall app

docker compose config --quiet
```

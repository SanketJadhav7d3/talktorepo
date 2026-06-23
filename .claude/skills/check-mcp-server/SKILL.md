---
name: check-mcp-server
description: Verify the TalkToRepo MCP server (app/mcp_server.py) is registered and connected, and that its tools are usable. Use when asked whether the server works, to check/test it, or to troubleshoot the talktorepo MCP connection. Do NOT start the server manually — the Claude Code harness owns its lifecycle.
---

# Verify the TalkToRepo MCP Server

The TalkToRepo MCP server (`app/mcp_server.py`, **stdio** transport) exposes
repository-intelligence tools: `index_repo`, `search_codebase`,
`get_file_dependencies`, `get_file_dependents`, `list_all_files`.

## What this skill is for (and what it is NOT)

This skill is for **verifying and troubleshooting** the server, not launching it.

The server is registered as an MCP server in the Claude Code config (the
`talktorepo` entry). The **harness spawns, manages, and reconnects its own copy**
of the process and exposes the tools as `mcp__talktorepo__*`. That managed copy
is the only one that matters.

**Do NOT run the server manually** (e.g. `uv run python -m app.mcp_server`):

- A hand-started process has no MCP client attached, so it serves no tools — it
  is pointless for actually using the server.
- Running a second copy alongside the harness's copy invites confusion and
  cleanup mistakes (a too-broad "kill mcp_server" can take down the managed
  process and break the connection).

The only reason to launch it by hand is a pure startup smoke test (does the
module import / boot without crashing?) — and even then, prefer the checks below.

## Verify it

1. **Is it registered and connected?**

   ```
   claude mcp list
   ```

   Look for: `talktorepo: .\.venv\Scripts\python.exe -m app.mcp_server - ✔ Connected`

2. **Are the tools accessible to Claude?** Confirm the `mcp__talktorepo__*`
   tools (e.g. `mcp__talktorepo__list_all_files`) are loadable/callable in the
   session. If they are, the server is working end to end.

## If it is NOT connected / tools are missing

- MCP tools bind at session startup. A server that connected late, or was added
  mid-session, may not be injected until a refresh.
- Fix: the **user** runs `/mcp reconnect talktorepo` (or restarts the session).
  This respawns the harness-managed copy and re-injects the tools. Claude cannot
  run `/mcp` itself.
- If it is not registered at all, add it (config / `claude mcp add`) using the
  entry below — do not work around a missing registration by starting the
  process by hand.

## Registration reference

The MCP host config entry that makes the tools available:

```json
{
  "command": "<repo>/.venv/Scripts/python.exe",
  "args": ["-m", "app.mcp_server"],
  "cwd": "<repo>/talktorepo",
  "env": { "PINECONE_API_KEY": "..." }
}
```

## Requirements & notes

- `PINECONE_API_KEY` must be set in the environment (used for vector search).
  `GOOGLE_API_KEY` is **not** needed for the MCP server itself — the MCP host
  (Claude) acts as the agent.
- Dependencies are managed with `uv`; run `uv sync` if something is missing
  (or `pip install -r requirements.txt` in a plain venv).
- The NetworkX dependency graph persists to `.mcp_state/dependency_graph.pkl`
  and reloads on startup (stdio servers can restart per session). Pinecone
  vectors persist on their own.
- A repo must be indexed (`index_repo`) before the search/graph tools return
  results; otherwise they report "No repository indexed yet."

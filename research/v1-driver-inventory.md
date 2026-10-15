---
role: derived
---

# v1 Claude Driver inventory

Historical document-wide evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/server.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/jsonl.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/rate_limit.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/system_prompt.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/__main__.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/state_main.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/claude_cli.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/native_domain.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/native_streams.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_authority.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/state/provider_runtime.py`
- `arbol_deprecated_v1:daemons/core/arbol_core/orchestration/agent_attempt_execution.py`
- `arbol_deprecated_v1:tests/unit/test_claude_native_turn.py`

Read in full: every file under `drivers/claude/arbol_driver_claude/`, `daemons/shared/arbol_shared/claude_cli.py`, and the tests named `test_claude_*`. Read as far as the driver uses them: the shared helpers (socket server, IPC codec, turn store, native process domain and its worker, provider authority/launch/admission/retirement wrappers, system-instruction loader, state-mode provider runtime), the caller side in `daemons/core/arbol_core/orchestration/`, and the other tests that import `arbol_driver_claude`. Commit `f2227d2` of the frozen `arbol_deprecated_v1` repository; the working checkout has one uncommitted entry (`git status --short | wc -l` = 1: the untracked directory `renderer/storybook-static/`, unrelated to the driver). Nothing in the repo was executed: no driver code, no tests. The only command run was `claude --help` / `claude -p --help` on the installed CLI 2.1.289 (section 14). Corpus documents are named in prose by their path below `~/Artifacts/arbol_deprecated_v1/`. Historical evidence lists preserve source paths and symbols as ordinary `arbol_deprecated_v1:` locators; they are not Source Ref declarations and create no provenance edges. Unmarked statements were read in source; "(inferred)" marks conclusions drawn from the code but not read as a single statement or pinned by a test.

## 1. Process and hosting

One daemon process serves every Intelligence Provider on the `claude` Driver. The install script registers two of them on the same socket: `claude` (Anthropic) and `glm` (z.ai gateway). They differ only per Turn, by the `options` handed in (section 3).

| Aspect | `__main__.py` (binary `arbol-driver-claude`) | `state_main.py` |
|---|---|---|
| First statement | `sys.argv[1:2] == ["--native-domain-worker"]` → run `arbol_shared.native_domain_worker.main` and exit (the same executable doubles as the one-shot CLI launcher, section 4) | same |
| Import boundary | none | `install_import_boundary()` before daemon imports: importing `arbol_shared.turn_store` and other legacy modules raises `ImportError` |
| Start-up gates | `native_service_admission.enter()` before daemon imports; `exit_if_import_selftest("arbol-driver-claude")` (env `ARBOL_IMPORT_SELFTEST=1` prints a report and exits 0) | same |
| Binding requirement | none | `require_binding_environment()`: `ARBOL_STATE_RUNTIME_FILE` must be set |
| Receiver selection | `configured_runtime('claude', factory)`; a runtime → serve `runtime.handle` **without a stream handler**; `None` → serve `server.build_handler()` + `server.build_stream_handler()` (legacy receiver) | runtime `None` → raise `StateRefused('state-only Provider requires a verified state authority binding')`; never serves the legacy receiver |
| Runner | `TurnRunner(claude_bin=os.environ.get('CLAUDE_BIN') or 'claude')`, built lazily by `server._get_runner` in legacy mode | built by the factory when the runtime is configured |

- **Legacy vs state.** `configured_runtime` returns a runtime only when `ARBOL_STATE_RUNTIME_FILE` names a binding file. Without it, `configured_binding` opens a read-only Postgres connection (legacy DSN, `ARBOL_PG_SCHEMA` default `public`) and refuses to start unless the persisted authority mode is `legacy`. So driver start-up depends on the database being reachable even in legacy mode. The corpus (`product-spec/03-turn-execution.md`, "What is real and what is not") says the state runtime never became the production path.
- **Transport.** Unix stream socket `<app support>/run/<name>.sock`; `<app support>` = `ARBOL_APP_SUPPORT` or `~/Library/Application Support/Arbol`; `<name>` = `ARBOL_DRIVER_CLAUDE_SOCKET_NAME`, default `driver.claude`. A stale path is unlinked, the socket is `chmod 0600`, and on shutdown the file is removed only if it is still the inode this process bound. Frames are a 4-byte big-endian length followed by compact JSON. Envelope `kind`: `hello`, `request`, `response`, `subscribe`, `event`, `unsubscribe`, `error`. Requests on one connection run concurrently and are demultiplexed by `id`; events by `sub_id`. Closing a connection cancels its request and subscription tasks (mutating handlers shield themselves, section 2).
- **Launch.** launchd job `com.arbol.driver.claude`: `RunAtLoad`, `KeepAlive`, `ThrottleInterval` 10, `ProcessType` `Background`; env `HOME`, `PATH`, `PYTHONUNBUFFERED=1`, `CLAUDE_BIN` (resolved at install time with `command -v claude`, fallback `claude`), `ARBOL_DRIVER_CLAUDE_SOCKET_NAME`, `ARBOL_PROVIDER_BUILD_ID`, `ARBOL_PROVIDER_INSTANCE_ID`. `SIGINT`/`SIGTERM` stop the server. `startup_guard=provider_retirement.startup('claude')` refuses to bind when this instance id carries a durable retirement marker or exit receipt.
- **Identity** (reported by `healthz`, checked on every launch): `provider` `"claude"`; `build_id` = `ARBOL_PROVIDER_BUILD_ID` or `dev`; `instance_id` = `ARBOL_PROVIDER_INSTANCE_ID` or `claude@<build_id>`; `execution` = `{provider_id: "claude", driver_id: ARBOL_PROVIDER_DRIVER_ID or "arbol_driver_claude", execution_id: <uuid4 minted once per process start>, generation: ARBOL_PROVIDER_GENERATION or "provider-r1", build_id, protocol_revision: 2}`; `turn_protocol` = `{version: 2, capabilities: [...]}` with `els_attempt_observations_v1`, `els_attempt_commands_v1`, `els_attempt_launch_v1`, `dispatcher_commands_v1`, `quiescent_retirement_v1`, `witnessed_retirement_v1`, `launch_seal_v1`, `pinned_launch_v1`, `detached_execution`, `replay_since_seq`, `turn_attach`, `terminal_ack`, `feed_results_recovery`, `feed_permission_recovery`. Package constants: `VERSION = "1.0.0"`, `DRIVER_NAME = "claude"`, `PROVIDER = "claude"`.
- **Logging.** `alog.setup("driver.claude")`: one rotating JSON-lines file `<app support>/logs/driver.claude.log` (10 MiB × 5 backups), root level INFO; fields `ts`, `level`, `logger`, `msg`, `exc`. Every request logs `rpc_in` / `rpc_out` (`ok`, `error`, `elapsed_ms`, `method`, `caller_daemon`, `request_id` taken from the first of `request_id`/`batch_id`/`turn_id`, `chat_session_id`). Logger names: `arbol.ip.claude2.turn`, `arbol.ip.claude2.server`, `arbol.turn_store`, `arbol.socket`. launchd stdout/stderr go to `logs/driver.claude.stdout.log` / `.stderr.log`. Driver-specific lines: once per process `claude binary=%s version=%s`; CLI stderr at WARNING (first 1024 bytes); a malformed permission ask at ERROR with the whole record (`%r`, so tool input is logged); permission-feed refusals. No statement in the driver logs argv, environment or the token.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/__main__.py#main`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/state_main.py#main`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/__init__.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/server.py#_get_runner`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/state/provider_entrypoint.py#configured_runtime`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/state/bootstrap.py#configured_binding`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/state/profile.py#install_import_boundary`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/socket_server.py#serve`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/socket_server.py#_handle_connection`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/ipc.py#encode`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/paths.py#socket_path`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/logging.py#setup`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_protocol.py#health_identity`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_protocol.py#provider_execution_identity`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_retirement.py#startup`
- `arbol_deprecated_v1:launchd/com.arbol.driver.claude.plist.in`
- `arbol_deprecated_v1:scripts/install.sh`
- `arbol_deprecated_v1:tests/smoke/test_ip_claude_ping.py`

## 2. Wire surface

**Legacy receiver.** The handler is `authenticated_handler(retirement_launches(owned_mutations(handle)))`.

- `ping` and `healthz` are public. Every other request must carry a `dispatcher` grant in the envelope (validated together with the kernel peer pid); `turn.execute` additionally needs a 64-character `attempt_authority` in the envelope. Any credential or admission refusal is answered `ok: false`, error `Provider dispatcher authority refused`.
- For a Turn launched with attempt authority, every later command and **every published event** is revalidated against the Event Log Service over its own socket (`ARBOL_ELS_SOCKET` or `run/event-log-service.sock`) before it takes effect.
- `MUTATION_METHODS` (`turn.cancel`, `turn.feed_results`, `turn.feed_permission`, `turn.admit_permission_waits`, `turn.release_permission_admission`) run under `TurnStore.mutate`: the Turn must be retained by the store, the handler is shielded from caller disconnect, and an exception sets `mutation_failed` on the Turn permanently. Any other handler exception becomes `ok: false` with `str(exception)`.

| Method | Params read | Result | Errors (`ok: false`) | Effect |
|---|---|---|---|---|
| `ping` | – | `{"pong": true}` | – | none |
| `healthz` | – | `status: "ok"`, `version`, `uptime_seconds`, `pid`, identity block (section 1), `claude_binary`, `claude_version` | – | never launches the CLI; `claude_version` is always `"unknown"` (section 13, finding 9) |
| `turn.execute` | `turn_id`, `chat_session_id`, `history`, `workspace_dirs`, `options`, `launch_protocol` (must be `1`), `expected_execution` (must equal this process's `execution`), optional `attempt_context`, `observation_protocol` | `{"ok": true, "turn_id", "already_running": bool, "launch_receipt": <sha256 hex>}` | `missing turn_id`; `Provider launch requires the pinned launch protocol`; `Provider launch execution identity changed`; `attempt launch request differs from retained receipt`; `attempt replay was collected; launch cannot be repeated`; `receiver launch admission is sealed` | computes the receipt (SHA-256 of all params except `attempt_authority`), runs `gc_completed`, then `start_once`: starts `TurnRunner.run(turn_id, params, publish)` as a detached task, or returns `already_running: true` for a retained Turn with the same receipt |
| `turn.cancel` | `turn_id` | `{"ok": true}` | mutation refusals | `runner.cancel` then `store.cancel` (section 9) |
| `turn.feed_permission` | `turn_id`, `ask_id`, `behavior` (default `"deny"`), `message`, `interrupt`, `answers` | `{"ok": bool}` | mutation refusals; a drain timeout surfaces as an error | writes one `control_response` to the CLI; on `ok` removes the store's unresolved wait (section 8) |
| `turn.permission_waits` | `turn_id` | `{"ask_ids": [sorted]}` | – | snapshot of outstanding asks |
| `turn.admit_permission_waits` | `turn_id`, `ask_ids` | `{"admitted": bool, "admission_token": str or null}` | mutation refusals | compare-and-seal one permission generation (section 8) |
| `turn.release_permission_admission` | `turn_id`, `admission_token` | `{"ok": bool}` | mutation refusals | drops the seal if the token matches |
| `turn.feed_results` | `turn_id`, `batch_id`, `results` | none reachable | `'TurnRunner' object has no attribute 'feed_results'` (inferred from the missing method) | dead on this driver (section 13, finding 6) |
| `turn.inventory` | `participant_challenge` (wrapper) | identity block, `pid`, `turns[]` (one `describe` each), `running`, `unacknowledged_terminal`; the wrapper merges the admission status | – | read-only |
| `turn.describe` | `turn_id` | `{"found": bool, "turn_id", ...}` (section 10) | `missing turn_id` | read-only |
| `turn.attach` | `turn_id`, `since_seq`, `core_generation` | section 10 | `missing turn_id`; `str(TypeError/ValueError)` | records `core_generation` when replay is available |
| `turn.ack` | `turn_id`, `terminal_seq` | section 10 | same | marks the terminal acknowledged |
| `turn.recover`, `turn.cleanup` | `turn_id`, `terminal_seq`, `session_id` | `{"attempt_id", "recovered"/"historical"/"disposed", ...}`; `{"disposed": true, "terminal_seq"}` | authority refusal | handled inside `authenticated_handler`, never reach `handle`; attempt-authority recovery and final disposition |
| `turn.admission.status`, `turn.admission.seal`, `turn.deployment.census`, `turn.retirement.prepare`, `turn.retirement.status` | protocol/identity/challenge fields | admission status report | identity mismatch messages | deployment sealing and retirement of this process; not Turn behaviour |
| anything else | | | `unknown method: <name>` | |

**Stream `turn.events`** (legacy receiver only). Subscribe params `turn_id`, `since_seq` (default 0). Replays every buffered event with `seq > since_seq`, then tails live events, and ends after `done`. Event `data` always carries `_ip_seq` (per-Turn, starting at 1, identical on replay). Missing `turn_id` → one event `error` `{"message": "missing turn_id in subscribe params"}`; other stream names → `error` `{"message": "unknown stream: <name>"}`. An unknown Turn yields nothing in the bare handler; through the authenticated wrapper it ends as a stream error frame `{"kind": "error", "error": "Provider dispatcher authority refused"}` (inferred). Each emission is sent with a 10 s timeout. Unsubscribing or disconnecting never touches the Turn.

| Event | Payload (plus `_ip_seq`) | Emitted when |
|---|---|---|
| `assistant_text_delta` | `turn_id`, `text` | each `text_delta`; or a whole `text` block of an `assistant` record when no text delta has been seen in this Turn |
| `assistant_thinking_delta` | `turn_id`, `text` (the thinking chunk travels under `text`; Core renames it to `thinking`) | each `thinking_delta`; or a whole `thinking` block when no thinking delta has been seen |
| `native_tool_invoked` | `turn_id`, `tool_use_id`, `tool_name`, `input` | at `content_block_stop` of a `tool_use` block; fallback from a full `assistant` record; once per `tool_use_id` |
| `native_tool_settled` | `turn_id`, `tool_use_id`, `ok`, then `error` (string) when `is_error`, else `result` when content is not null | each `tool_result` block of a `user` record; once per `tool_use_id` |
| `native_permission_ask` | `turn_id`, `ask_id` (= CLI `request_id`), `tool_name`, `input`, `tool_use_id`, optional `blocked_path` | each well-formed `control_request` / `can_use_tool`, after registration |
| `native_permission_ask_cancelled` | `turn_id`, `ask_id` | `control_cancel_request` for a registered ask |
| `usage` | `turn_id`, `model`, `input_tokens`, `output_tokens`, `cost_usd` | at the `result` record when any counter is known; before `cycle_complete` |
| `cycle_complete` | `turn_id`, `cycle_n` (always `1`) | at a `result` record that is neither a rate limit nor an authentication failure |
| `rate_limited` | `turn_id`, `reason` (≤200 chars), optional `recovery_hint_seconds` | rate-limit signal; followed at once by `done` |
| `error` | `turn_id`, `message`, optional `authentication_error: true` | validation failure, authentication failure, protocol drift, CLI ended without a result, launch failure, runner crash (store backstop) |
| `done` | `turn_id`, `reason` ∈ `no_more_requests`, `error`, `cancelled`, `rate_limited`, `max_cycles` (with `cycles`, `cap`; unreachable) | exactly one terminal per Turn; the store adds it when the runner ends without one |

Core treats `cycle_complete`, `native_permission_ask`, `native_permission_ask_cancelled`, `done`, `error` (and the unused `arbol_request_batch`) as durable frames with a replay cursor; deltas, `usage`, `rate_limited` and tool events are consumed without advancing it.

**State receiver** (`StateProviderRuntime.handle`). Methods: `healthz`, `turn.inventory`, `turn.retirement.prepare`, `turn.retirement.status`, `state.deliver` (`attempt_id`, `command_id`, `request_digest`, `action` ∈ `launch`, `admit`), `state.checkpoint` (`attempt_id`; long-poll for the next checkpoint), `state.acknowledge` (`attempt_id`, `result`), `state.cleanup`; anything else → `unsupported state Provider method`. The same runner events are translated by `DriverOutput.emit` into bounded checkpoints (text buffered to 32 KiB or 0.25 s, one unacknowledged checkpoint at a time, back-pressure on the runner). `done` becomes a terminal phase: `cancelled`; `failed` when an `error`/`rate_limited` was seen or the reason is `error`/`rate_limited`; else `completed`. A delivered native-permission decision calls `runner.feed_permission(attempt_id, ask_id, 'allow' if decision == 'approved' else 'deny', answers=..., message=reason or details)`; a cancel calls `runner.cancel` and cancels the task. This path uses neither `interrupt` nor the admission calls.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/server.py#handle`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/server.py#stream`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._run_native`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._handle_stream_record`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_authority.py#authenticated_handler`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_authority.py#authenticated_stream`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_mutations.py#owned_mutations`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_admission.py#admission_response`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_launch.py#receiver_receipt`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore.publish`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore.subscribe`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore.mutate`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/attempt_authority.py#_relay_once`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/state/provider_runtime.py#StateProviderRuntime.handle`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/state/provider_runtime.py#StateProviderRuntime._deliver`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/state/driver_output.py#DriverOutput.emit`
- `arbol_deprecated_v1:daemons/core/arbol_core/orchestration/ip_events.py#IpEventsMixin._handle_ip_event`
- `arbol_deprecated_v1:daemons/core/arbol_core/orchestration/support.py#_DURABLE_IP_EVENTS`

## 3. Turn options

**Params of `turn.execute` as the caller builds them:** `turn_id` (the attempt id, not the Exchange id), `chat_session_id`, `history`, `workspace_dirs`, `options`, `launch_protocol`, `expected_execution`, `attempt_context`, optionally `observation_protocol`.

| Param | Type | Read by | Effect |
|---|---|---|---|
| `turn_id` | string, ≤512 bytes | server, store | key for every later call; echoed in every event |
| `chat_session_id` | string | `TurnRunner.run` | required (else `error` `missing chat_session_id or workspace_dirs` + `done(error)`); the `--resume` id and transcript file name on follow-ups |
| `workspace_dirs` | list of paths | `TurnRunner.run` | required, non-empty; first entry is the CLI working directory; every entry becomes `--add-dir` and a line of the system prompt |
| `history` | list of `{role, content, attachments?}` | `TurnRunner.run` | must be non-empty and end with `role == "user"` (else `error` `history must end with a user message`); the last entry is sent on stdin, the rest becomes the resume transcript |
| `options` | dict | below | |
| `launch_protocol`, `expected_execution`, `attempt_context`, `observation_protocol` | | receipt, authority wrapper, store | launch identity and authority; no effect on the CLI |

History entries: `role` (`user` / `assistant`; other roles are dropped from the transcript), `content` (string; a list is passed through as content blocks; anything else is `str()`-ed), `attachments` (only `{type: "image", data: <base64>, mime_type | mimeType}`; default media type `image/png`). `message_type` (Chat Notes arrive as `user` entries carrying `message_type: "note"`) is ignored.

| `options` key | Values | Default when absent | Effect |
|---|---|---|---|
| `model` | string | flag omitted (CLI default) | `--model <value>`; also the initial `model` of the `usage` event until an `assistant` record reports one |
| `thinking_level` | `minimum`, `low`, `medium`, `high`, `xhigh`, `max`, `none` | flag omitted | `--effort` via the mapping in section 4 |
| `oauth_token` | string (the Subscription's access token, or a gateway's static key) | no credential set; the CLI uses whatever login its profile directory holds (inferred) | env `CLAUDE_CODE_OAUTH_TOKEN`, or `ANTHROPIC_AUTH_TOKEN` when `provider_base_url` is set |
| `provider_base_url` | string, stripped | `""` | env `ANTHROPIC_BASE_URL`; profile directory `~/.claude` instead of `~/.claude-anthropic`; `--settings ~/.claude/settings-zai.json` when the host is exactly `api.z.ai` and the file exists; transcript location |
| `additional_instructions` | string | none | appended to the system prompt after a blank line |

- **Set by `compose_turn_options` but ignored by this driver:** `full_permissions`, `account_id`, `fast_mode` (set only for `codex` providers). `session_decision_instructions` is popped by the caller and merged into `additional_instructions` before the first launch.
- On the caller's authentication-refresh relaunch the options are recomposed and only the Cue instructions are re-added: `session_decision_instructions` then travels as an unread key and the session decisions are missing from that attempt's system prompt.
- State mode adds a param `output_contract: "state-checkpoints-v1"` (ignored) and resolves `oauth_token` / `account_id` inside the driver process from the accepted credential reference (Keychain read and, for Anthropic, refresh under a file lock) just before `runner.run`. That resolution is the only place the driver process touches a stored credential; in legacy mode Core hands the token over in `options`.
- The driver reads no limit from the params: no turn timeout, no turn count, no budget, no tool allow-list.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner.run`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._build_argv_native`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#_env_overrides_for`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/jsonl.py#message_content_blocks`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/claude_cli.py#alias_args`
- `arbol_deprecated_v1:daemons/core/arbol_core/orchestration/agent_attempt_execution.py#AgentAttemptExecutionService.compose_turn_options`
- `arbol_deprecated_v1:daemons/core/arbol_core/orchestration/agent_attempt_execution.py#AgentAttemptExecutionService._run_one_attempt`
- `arbol_deprecated_v1:daemons/core/arbol_core/orchestration/agent_attempt_execution.py#AgentAttemptExecutionService._start_ip_attempt`
- `arbol_deprecated_v1:daemons/core/arbol_core/db/turns.py#turn_path_history`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/state/provider_runtime.py#StateProviderRuntime._run`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/state/credentials.py#ProviderCredentials.options`

## 4. CLI invocation

One CLI process per Turn. Complete argv, in order (`protocol.build_argv`, then `claude_cli.alias_args`):

| # | Argument(s) | Added when | Reason given in code |
|---|---|---|---|
| 0 | `<claude_bin>` | always | `CLAUDE_BIN` or `claude` |
| 1 | `--session-id <fresh uuid4>` | no prior history (root Turn) | "`--session-id` refuses an existing ID"; a root edit or retry may already have a CLI transcript under the stable id |
| 1 | `--resume <chat_session_id>` | prior history exists | "claude 2.1.x errors on --resume of an empty session — first turn must use --session-id" |
| 2 | `--input-format stream-json` | always | wire format |
| 3 | `--output-format stream-json` | always | wire format |
| 4 | `--verbose` | always | none given |
| 5 | `--include-partial-messages` | always (`include_partials=True`) | "streaming deltas for live UIs" |
| 6 | `--setting-sources ""` | always (`pin_settings=True`) | "deterministic behavior on any account, no ambient user settings" |
| 7 | `--permission-mode default` | always (`pin_settings=True`) | same; "Never `bypassPermissions`" |
| 8 | `--permission-prompt-tool stdio` | always (`permission_bridge=True`) | "route every tool ask through stdin/stdout so the CALLER answers it" |
| 9 | `--disallowedTools NotebookEdit,WebFetch,WebSearch,Task,TodoWrite` | always (`_NATIVE_DISALLOWED`, one comma-joined value) | "Still-disallowed tools per decision 10 (revisit in Phase 7)" |
| 10 | `--append-system-prompt <text>` | always | rendered prompt plus `additional_instructions` |
| 11 | `--add-dir <os.path.expanduser(dir)>` | once per workspace dir, the working directory included | allowed directories |
| 12 | `--model <model>` | `options.model` truthy | |
| 13 | `--effort <tier>` | mapping returns a tier | one map shared with the detached wrapper |
| 14 | `--max-turns <n>` | never (`build_argv` supports it; the driver passes no `max_turns`) | |
| 15 | `--settings <~/.claude/settings-zai.json>` | host of `provider_base_url` is `api.z.ai` and the file exists | "claude-zai adds an explicit settings file even with setting-sources off"; "Never load z.ai settings for a different Anthropic-compatible gateway" |

`-p` / `--print` is not passed and no prompt argument is given. `build_argv` raises `ValueError("exactly one of session_id/resume is required")` otherwise.

**Thinking level → `--effort`** (`_EFFORT_BY_THINKING`):

| `thinking_level` | `minimum` | `low` | `medium` | `high` | `xhigh` | `max` | `none`, empty, unknown |
|---|---|---|---|---|---|---|---|
| tier | `low` | `low` | `medium` | `high` | `max` | `max` | flag omitted |

Comment: "Probed live 2026-07-09: the flag accepts exactly low|medium|high|max". Thinking is not set through the environment (`MAX_THINKING_TOKENS` was retired 2026-07-11).

**System prompt** (re-read from disk on every launch; `<root>` = `ARBOL_ARTIFACTS_ROOT` or `~/Artifacts`, `<repo>` = `ARBOL_SYSTEM_INSTRUCTIONS_REPO` or `Arbol`), concatenated:

1. `<root>/<repo>/system-instructions/claude-native.md.tmpl` with `$workspace_dirs` → one line `  - <dir>` per dir (`  (none configured)` when empty). Required: a missing or empty template, or an unknown placeholder, raises `RuntimeError`.
2. Blank line + `workspace-boundary.md.tmpl` when dirs are given.
3. Blank line + the fixed `PROTECTED_LIFECYCLE_INSTRUCTION` + every visible `.md`/`.markdown` file (case-insensitive name order) of the shared chapter and of the repository-specific chapters; the repository is resolved through the `mycel` library (`RepositoryLocations`, `organizations`).
4. Blank line + `code-navigation.md.tmpl` when a workspace dir equals, lies inside, or contains `ARBOL_KN_CODE_ROOT` (default `~/repo/sylvan-stack/Arbol`).
5. Blank line + `options.additional_instructions`.

**Environment**, in order:

1. Copy the driver's own environment, removing every variable whose name starts with `ANTHROPIC_`, and `CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `CLAUDE_CODE_USE_FOUNDRY`.
2. Set `CLAUDE_CONFIG_DIR`: `~/.claude` when a gateway address is set; otherwise `~/.claude-anthropic` if that directory exists, else `~/.claude`.
3. With a gateway address: `ANTHROPIC_BASE_URL=<address>`.
4. Overlay: `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` ("Arbol must never let a driver invocation create or update it").
5. Overlay credential: gateway → `ANTHROPIC_BASE_URL` again and, if a token exists, `ANTHROPIC_AUTH_TOKEN` ("never presenting the OAuth beta headers"); otherwise, if a token exists, `CLAUDE_CODE_OAUTH_TOKEN`.
6. Overlay `PATH=<PATH>:<~/bin>` when `~/bin` is a directory and not already listed ("the daemon's launchd PATH does not include the user's bin directory" — for the installed Arbol and Mycel CLIs used from the native Bash tool).
7. `BASH_DEFAULT_TIMEOUT_MS=300000` ("the first Bash feedback checkpoint, not a maximum") and `BASH_MAX_TIMEOUT_MS=1800000` ("never run unbounded").

**Working directory:** `workspace_dirs[0]`; the launcher resolves it strictly (must exist).

**Process ownership.** The driver calls `native_domain.launch(*argv, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=..., env=..., start_new_session=True)`. This is not a direct child:

- the driver writes a launchd job `dev.arbol.native.<nonce>` (`gui/<uid>`, `KeepAlive` false, job env only `PATH=/usr/bin:/bin` and a private `TMPDIR`) that starts the driver's own executable with `--native-domain-worker` (frozen build; from source, the worker script);
- the worker connects four Unix-socket channels (`control`, `stdin`, `stdout`, `stderr`), authenticates the driver by kernel identity, receives argv/cwd/env over the control channel, and runs `subprocess.Popen(argv, cwd, env, stdin/stdout/stderr = the sockets, close_fds=True, shell=False)`; it reports `{"returncode", "child_reaped": true}` when the direct child exits;
- ownership is the job's kernel resource coalition, recorded in a journal under `run/native-domains/`. The executable is resolved with `shutil.which(argv[0], path=<composed PATH>)`; a missing one raises `NativeDomainError('native command executable is unavailable')`;
- a launch is only possible inside a `native_domain.scope(binding)` opened by the store for an authority launch or by the state runtime; otherwise `launch` raises `NativeDomainError('native execution requires an exact bounded owner')`. `start_new_session` is accepted and unused: no process group or session is created, and nothing signals a process group (section 9).

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#build_argv`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#effort_for_thinking`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#_EFFORT_BY_THINKING`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._build_argv_native`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#_env_overrides_for`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#_NATIVE_DISALLOWED`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._launch_process`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/system_prompt.py#render_system_prompt`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/system_instructions.py#render_instruction_template`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/system_instructions.py#render_system_instructions`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/claude_cli.py#config_dir`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/claude_cli.py#alias_args`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/claude_cli.py#environment`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/native_domain.py#launch`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/native_domain.py#NativeProcess._start`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/native_domain_worker.py#run`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore._supervise_run`
- `arbol_deprecated_v1:tests/unit/test_claude_account_profiles.py`

## 5. Input protocol to the CLI

Newline-delimited JSON on stdin, UTF-8.

| Frame | Shape | Written |
|---|---|---|
| User message | `{"type": "user", "message": {"role": "user", "content": [<blocks>]}}`; blocks = one `{"type": "text", "text": ...}` (omitted for empty text unless nothing else exists) followed by `{"type": "image", "source": {"type": "base64", "media_type": ..., "data": ...}}` per image attachment | once, right after launch; a broken pipe is swallowed (`write_record` returns `False`, unchecked) |
| Permission allow | `{"type": "control_response", "response": {"subtype": "success", "request_id": <ask_id>, "response": {"behavior": "allow", "updatedInput": {...}, "toolUseID": <id>}}}` | per `feed_permission`; `updatedInput` is the ask's original `input`, plus `answers` when supplied; `toolUseID` only when the ask carried one |
| Permission deny | same envelope with `{"behavior": "deny", "message": <text>, "interrupt": <bool>, "toolUseID": <id>}` | any `behavior` other than `"allow"`; default message `Arbol denied this tool call` |

- No `session_id`, `parent_tool_use_id` or `uuid` field is sent on the user frame. The driver never sends a control request of its own (no `initialize`, no `interrupt`, no model or permission-mode change).
- **Why stdin stays open:** "Stdin stays open for the whole invocation: the initial user message, control_response frames, and provider control frames ride it until the turn completes." It is closed when stdout consumption ends (terminal record, EOF, cancel) — "Close stdin so the CLI exits."
- **Continuation with tool results:** none. After the first user frame the driver only writes control responses; there is no second user message and no `feed_results` on the runner. The test double's `await_user` action ("fence-results continuation") has no counterpart.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._run_native`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner.feed_permission`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#encode_control_response`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#frame_bytes`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/jsonl.py#message_content_blocks`
- `arbol_deprecated_v1:tests/fixtures/mock_claude_native.py`

## 6. Conversation continuity

Arbol's history is the authority; the CLI's saved session is rewritten from it.

| Case | CLI identity | Transcript |
|---|---|---|
| Root Turn (history is only the new user message) | fresh `uuid4` per launch via `--session-id`; never stored or reported by the driver | none written; whatever the CLI saves under that uuid is never read or deleted (inferred: the driver has no delete call) |
| Follow-up (any prior entry; Chat Notes count, inferred from the caller's history builder) | `--resume <chat_session_id>` | regenerated before launch from `history[:-1]` |

- **Path:** `<profile dir>/projects/<encoded cwd>/<chat_session_id>.jsonl`. Profile dir = `claude_cli.config_dir(base_url)`, the same value exported as `CLAUDE_CONFIG_DIR`. Encoded cwd = `os.path.realpath(os.path.expanduser(cwd))` with every `/` and every space replaced by `-`.
- **Write:** parent directories created; body written to `<name>.jsonl.tmp`, then `os.replace`. The whole file is replaced on every follow-up, so anything the CLI appended during the previous Turn (tool calls, tool results, thinking, its own bookkeeping) is discarded: the next Turn sees prose only.
- **Records:** one per `user`/`assistant` entry, compact JSON, one per line: `type`, `message: {role, content: [blocks]}`, `uuid` (new `uuid4` at every regeneration), `parentUuid` (previous record's `uuid`; `null` for the first), `timestamp` (`%Y-%m-%dT%H:%M:%S.000Z`; record *i* of *n* is stamped `now − (n + 1) + i` seconds: strictly increasing, all in the past), `isSidechain: false`, `chat_sessionId`, `cwd` (real path), `userType: "external"`, `version: "synthetic-arbol"`.
- **Stated reasons:** without `parentUuid` links every record is an independent root and the CLI "behaves as if each prompt were the first one"; equal timestamps make the resume loader "mis-pick the visible leaf and append a spurious sibling that shadows the last assistant message".
- The new user message is never in the file; it arrives on stdin. `parse_chat_session_jsonl` (inverse reader) is used only by tests.
- Nothing from the CLI's side is ever read back: not the `session_id` of its init record, not its transcript.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._run_native`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/jsonl.py#encode_cwd`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/jsonl.py#chat_session_jsonl_path`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/jsonl.py#history_to_jsonl_lines`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/jsonl.py#write_chat_session_jsonl`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/jsonl.py#parse_chat_session_jsonl`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/claude_cli.py#config_dir`
- `arbol_deprecated_v1:daemons/core/arbol_core/db/turns.py#turn_path_history`
- `arbol_deprecated_v1:tests/unit/test_jsonl_roundtrip.py`
- `arbol_deprecated_v1:tests/unit/test_claude_root_retry.py`
- `arbol_deprecated_v1:tests/unit/test_claude_account_profiles.py#test_resume_transcript_matches_spawned_account_directory`

## 7. Output parsing

Stdout is read in 64 KiB chunks and split on `\n` by the driver itself (no per-line size limit; UTF-8 with replacement; trailing `\r` stripped). Blank lines and lines that are not JSON are skipped silently. Per record, in this order:

| # | Record | Condition | Result |
|---|---|---|---|
| 1 | any | Turn id is in the cancelled set | stop reading |
| 2 | `result` | rate-limit signal (section 9), first one only | stop reading; `rate_limited`, `done(rate_limited)`; no `usage`, no `cycle_complete` |
| 3 | `result` | authentication signal (section 9) | `error` with `authentication_error: true`; stop reading; `done(error)` after process cleanup |
| 4 | `control_request` | `request.subtype == "can_use_tool"` | section 8 |
| 4 | `control_request` | other subtype | ignored (debug log), never answered |
| 5 | `control_cancel_request` | `request_id` matches a registered ask | `native_permission_ask_cancelled` |
| 6 | `keep_alive`, `rate_limit_event` | | skipped |
| 7 | `assistant` | | `message.model` remembered; `message.usage` added to the fallback counters; `text` / `thinking` blocks emitted only if no delta of that kind was seen earlier in the Turn; `native_tool_invoked` for each `tool_use` block not yet reported |
| 8 | `stream_event` | `event.type == "content_block_delta"`, delta `text_delta` / `thinking_delta` | `assistant_text_delta` (`delta.text`) / `assistant_thinking_delta` (`delta.thinking`); empty chunks skipped |
| 8 | `stream_event` | `message_start`; `content_block_start` (tool_use); `input_json_delta`; `content_block_stop` | tool-block tracker by block `index`: cleared at `message_start`; `partial_json` pieces joined and parsed at stop (`{}` when empty or unparsable); then `native_tool_invoked` |
| 9 | `user` | `tool_result` blocks | `native_tool_settled` once per `tool_use_id`: `ok = not is_error`; error text = content (JSON-encoded if not a string) cut to 204 800 chars; success `result` = content, cut to 204 800 chars only when it is a string |
| 10 | `result` | everything else, whatever its `subtype` / `is_error` | `usage` (if any counter), `cycle_complete {cycle_n: 1}`, stop reading; `done(no_more_requests)` after the CLI exits |
| – | `system` and any other type | | ignored |

- **Ordering.** A tool invocation is emitted at its block boundary so that in `[text, tool, text, tool]` each prose chunk lands before the tool that follows it; the full `assistant` record is the de-duplicated fallback for streams without partial messages.
- **Thinking.** Streamed chunks only; `signature_delta` and redacted thinking are not handled. The whole-block fallback reads `block.thinking` or `block.text`.
- **Usage** (`protocol.extract_usage`, at `result`): `input_tokens` = `usage.input_tokens + cache_read_input_tokens + cache_creation_input_tokens` (`null` when none of the three is present); `output_tokens` = `usage.output_tokens`; `cost_usd` = `total_cost_usd`. Counters summed from `assistant` records fill a field only when the `result` lacks it and the sum is > 0 ("zero is a reported value, not a missing field"; gateways send zero placeholders on assistant records). No usage is emitted when every field is unknown. `model` = last `assistant.message.model`, else `options.model`, else `""`.
- **Not read:** the `result` text, `num_turns`, `duration_ms`, `modelUsage`, `session_id`, `parent_tool_use_id`, `stop_reason`.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._run_native`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._handle_stream_record`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._emit_native_invoke_in_order`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#_cap_result_content`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#extract_usage`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#assistant_usage`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#context_tokens`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/streams.py#iter_lines`
- `arbol_deprecated_v1:tests/unit/test_claude_native_turn.py#test_native_invokes_interleave_with_text_in_stream_order`
- `arbol_deprecated_v1:tests/unit/test_claude_native_turn.py#test_result_usage_takes_precedence_over_assistant_counts`

## 8. Tools and permissions

- **Native tools are the only mode.** The CLI runs its own tools. The driver removes five by name (`NotebookEdit`, `WebFetch`, `WebSearch`, `Task`, `TodoWrite`) and passes no allow-list, so every other tool of the installed CLI is available. `native_tool_invoked` / `native_tool_settled` are observations of what the CLI did, asked or not.
- **Bridge.** With `--permission-prompt-tool stdio` the CLI writes `{"type": "control_request", "request_id", "request": {"subtype": "can_use_tool", "tool_name", "input", "tool_use_id", "blocked_path"?}}` and waits for the matching `control_response`. The driver registers the ask under `(turn_id, request_id)` ("Claude commonly reuses short request ids such as `a1`" across Turns) with its `tool_use_id` and `input`, then emits `native_permission_ask`. Concurrent asks are normal and may be answered in any order.
- **Protocol-drift backstop.** An ask without `request_id`, or whose `tool_name` is not a string, or whose id was already registered, answered or left ambiguous in this Turn, sets the process-wide flag `_native_protocol_broken`, emits `error` (`native permission protocol probe failed; native mode disabled; restart the driver` / `native permission protocol reused an ask id; ...`) and ends the Turn with `done(error)`. Every later Turn in that process fails at once with `native permission protocol is unavailable; restart the driver`.
- **Withdrawal.** `control_cancel_request` removes the ask (also from an active seal) and emits `native_permission_ask_cancelled`; a later answer returns `false`.

**`feed_permission(turn_id, ask_id, behavior, message, interrupt, answers)`**, serialized by a per-Turn lock:

| Situation | Outcome |
|---|---|
| `ask_id` already answered in this Turn | `true`, nothing written (idempotent retry) |
| `ask_id` marked ambiguous | `false`, logged, never rewritten |
| a seal is active and `ask_id` is outside it | `false` |
| unknown ask, or no live CLI (`stdin` missing or exit code known) | `false` |
| `write` raises `BrokenPipeError` / `ConnectionResetError` before returning | `false`; the ask stays and may be retried |
| `write` returned, then `drain` fails (reset, or > `_PERMISSION_DRAIN_TIMEOUT_SECONDS` = 10 s) | the ask is marked ambiguous and stays in the wait list; reset → `false`, timeout → raised |
| success | the ask moves to the answered set; when the sealed generation is fully answered the seal is released and its token kept until Turn teardown; `true` |

The write runs in a shielded task: cancelling the caller never cancels the write, and the cancellation is re-raised only after the local outcome is recorded.

**Wait generations.** `permission_wait_ids` returns the outstanding ask ids, sorted. `admit_permission_waits(turn_id, expected_ask_ids)` succeeds (returning a fresh uuid token) only when the outstanding set equals the expected set. It also returns the existing token for the exact admitted set, for its exact outstanding remainder, and for a subset of an already completed generation. While a seal is active, a newly arriving ask is not registered and not emitted: stdout handling parks until the seal is released (`_register_native_ask` waits on an event), so the ask belongs to the next generation. `release_permission_admission` drops the seal only for the matching token. Caller side: Core calls `turn.permission_waits`, admits the full set once it holds an answer for every member, writes its durable response boundary, then feeds answers in sorted order and stops at the first failure. Consequence: when the CLI raises several asks at once, none is answered until all are decided.

- **Answers to agent questions.** `answers` (the AskUserQuestion reply) is copied into `updatedInput["answers"]` on allow.
- **Deny.** Reaches the model as an error tool result with the message; `interrupt: true` is sent by Core only when it cancels an in-flight ask (`turn cancelled by user`, `native ask interrupted by attempt failure`).
- **Legacy fence path.** Absent. The driver parses no fenced blocks, never emits `arbol_request_batch`, and has no `feed_results`. The corpus document `architecture/native-tools.md` still describes a fence fallback, a "legacy fence path" and a per-provider `ip_settings.native_tools` toggle; none exists in this driver (`product-spec/06-tools-and-permissions.md` already lists this as stale).
- **Limits.** Tool results in events: 204 800 characters for string content (section 7). Native Bash: first feedback at 300 000 ms, ceiling 1 800 000 ms, both enforced by the CLI from the environment. No cap on the number of tool calls or asks.
- **Teardown.** Outstanding asks, answered sets, ambiguous marks, completed tokens and the seal are cleared together after process cleanup, under the same lock.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._run_native`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._register_native_ask`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._withdraw_native_ask`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner.feed_permission`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner.permission_wait_ids`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner.admit_permission_waits`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner.release_permission_admission`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._clear_permission_state`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#parse_can_use_tool`
- `arbol_deprecated_v1:daemons/core/arbol_core/orchestration/batches.py#BatchesMixin._submit_permission_answer`
- `arbol_deprecated_v1:daemons/core/arbol_core/native_tools.py#map_native_tool`
- `arbol_deprecated_v1:tests/unit/test_claude_native_turn.py`
- `arbol_deprecated_v1:tests/unit/test_permission_agent_turn_boundaries.py`

## 9. Failures, limits and cancel

**Rate-limit detection** (`is_rate_limit_signal`). A record matches when `type == "result"`, `subtype` is `error` or `error_during_execution`, and the lower-cased, space-joined string values of its `error`, `result` and `message` keys contain any of: `rate limit`, `rate_limit`, `429`, `too many requests`, `quota exceeded`, `quota`, `usage limit`, `overloaded`. "Intentionally permissive: a false positive triggers a failover ..., a false negative keeps the chat_session pinned." The emitted `reason` is the first 200 characters of `rec["error"] or rec["result"]`. Retry-after hint (`extract_recovery_seconds`), searched in that lower-cased text; first match wins, seconds patterns before minutes patterns, all case-insensitive:

```
retry[\-\s]*after[:\s]+(\d+)\s*(?:s|sec|seconds?)?        -> N seconds
retry\s+in\s+(\d+)\s*(?:s|sec|seconds?)\b                 -> N seconds
try\s+again\s+in\s+(\d+)\s*(?:s|sec|seconds?)\b           -> N seconds
wait\s+(\d+)\s*(?:s|sec|seconds?)\b                       -> N seconds
retry\s+in\s+(\d+)\s*(?:m|min|minutes?)\b                 -> N * 60 seconds
try\s+again\s+in\s+(\d+)\s*(?:m|min|minutes?)\b           -> N * 60 seconds
```

No match → no `recovery_hint_seconds`. Hours, clock times and epoch timestamps are not parsed. `rate_limit_event` records are skipped, not interpreted.

**Authentication failure** (`is_auth_error_signal`). Same gate (`result` + the two subtypes); matches when the joined text contains `failed to authenticate`, `authentication_error`, `invalid authentication` or `api error: 401`. The driver emits `error {message: <text, ≤1024 chars>, authentication_error: true}` and ends with `done(error)`. It refreshes nothing itself: Core recognises the same wording in the message, refreshes the Subscription token and relaunches once if no output was produced.

| Situation | What the driver emits |
|---|---|
| Params invalid | `error` (section 3 messages), `done(error)`; no CLI started |
| Launch raises `FileNotFoundError` | `error` `claude not found: <exception>`, `done(error)`; cleanup then raises (section 13, finding 11) |
| Launch raises anything else (for example `claude` is not on the composed `PATH`) | the launch exception is superseded by `RuntimeError('Claude native launch outcome remains unresolved')` raised from cleanup; the store backstop emits `error` with that message and `done(error)` (inferred) |
| `result` record, not rate limit, not auth | `usage`?, `cycle_complete`, `done(no_more_requests)` — also for error subtypes and for a non-zero exit afterwards |
| Stdout ends without a `result` | `error` `Claude CLI ended without a result (exit status <code>).` followed by the stderr text when there is any; `done(error)` |
| Runner raises mid-stream | store backstop `error` + `done(error)`; the Turn is marked `runner_failed` |
| CLI stderr | read concurrently; only the first 1024 bytes are kept (`STDERR_LIMIT`); logged at WARNING; reaches the Leather Bag only in the "ended without a result" message |

**Timeouts.** There is no overall Turn timeout, no idle timeout and no heartbeat. After stdout handling ends normally the driver closes stdin and waits `TERMINAL_EXIT_SECONDS` = 10 s for the CLI to exit; then, exited or not, it closes the process domain. After a rate limit, an authentication failure or a cancel it closes the domain at once.

**Domain cleanup** (`NativeProcess._cleanup`): close stdin, `launchctl bootout` the job, then every 50 ms send every remaining coalition member `SIGTERM` during the first 2 s and `SIGKILL` afterwards, until the coalition is gone or `CLEANUP_SECONDS` = 15 s have passed (then `native descendant retirement remains unresolved` is raised). Everything the CLI started — background shell commands included — dies with the Turn (inferred from signalling every coalition member). There is no process-group signal anywhere; tests forbid `os.killpg`.

**Max cycles.** `_max_cycles_per_turn()` reads `ARBOL_MAX_CYCLES_PER_TURN` (default 200, ceiling 500; invalid or ≤ 0 → 200), but nothing ever sets the `max_cycles` reason: the cycle counter is incremented once, at the `result` record. The cap is inert here.

**Cancel.** `turn.cancel` → `runner.cancel(turn_id)` adds the id to the cancelled set and cancels the running task; `store.cancel` cancels the store task. The cancellation enters `supervise`'s `finally`: close the domain, cancel and join the reader tasks, re-raise. No interrupt is sent to the CLI. `done(cancelled)` comes from the reader loop if it observes the flag after stdout closes, otherwise from the store (legacy) or the state runtime. `run`'s `finally` joins `_cleanup_turn` under `asyncio.shield`: repeated cancels cannot detach it, a cancel during launch waits for the launch to resolve before cleaning up, and the cancellation is re-raised only after cleanup.

**Order of terminals.** For rate limit and cancel, `done` is published before cleanup finishes; for success and other errors, after the CLI is gone. The store treats the Turn as pending until the task has finished and cleanup is confirmed, whatever was published. If cleanup raises, the process handle and permission state stay in the runner, the Turn is `runner_failed`, and it is never garbage-collected.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/rate_limit.py#is_rate_limit_signal`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/rate_limit.py#is_auth_error_signal`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/rate_limit.py#extract_recovery_seconds`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#RATE_LIMIT_INDICATORS`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#AUTH_ERROR_INDICATORS`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._run_native`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner.run`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner.cancel`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._launch_process`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._cleanup_turn`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#_max_cycles_per_turn`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/native_streams.py#supervise`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/native_domain.py#launch`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/native_domain.py#NativeProcess._cleanup`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore._supervise_run`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore.cancel`
- `arbol_deprecated_v1:daemons/core/arbol_core/orchestration/support.py#_is_claude_auth_error`
- `arbol_deprecated_v1:daemons/core/arbol_core/orchestration/agent_attempt_execution.py#AgentAttemptExecutionService._run_one_attempt`
- `arbol_deprecated_v1:tests/unit/test_claude_rate_limit_detect.py`
- `arbol_deprecated_v1:tests/unit/test_claude_turn_cleanup.py`
- `arbol_deprecated_v1:tests/unit/test_claude_root_retry.py#test_cli_startup_failure_emits_actionable_error_before_terminal`

## 10. Recovery surface

All recovery state is in the driver process's memory (`TurnStore._turns`); nothing is persisted, so a driver crash loses the running agent and its replay copy.

Per Turn the store keeps: the task, the launch receipt, the caller identity, **every event since the start** (the list is only appended to; there is no compaction), `next_seq`, `status`, terminal flag, `runner_failed`, pending/failed mutation counters, unresolved waits (`native_permission` entries with `ask_id`, `tool_use_id`, `tool_name`, `input`, `seq`), terminal acknowledgment and its time, and `core_generation`.

| Call | Semantics |
|---|---|
| `turn.execute` (repeat) | same `turn_id` and same receipt → `already_running: true`, no second process, also when the Turn has finished; different receipt → refused; a collected id → refused for good |
| `turn.describe` | `found`, `turn_id`, `launch_receipt`, `dispatcher_owner`, `status` (`running`, `completed`, `failed`, `cancelled`), `terminal`, `task_finished`, `runner_failed`, `authority_disposed`, `pending_mutations`, `mutation_failed`, `work_pending`, `earliest_seq`, `next_seq`, `last_seq`, `replay_available` (always `true`), `subscriber_count`, `unresolved_waits`, `terminal_acknowledged`, `terminal_acknowledged_at`, `core_generation`; unknown → `{"found": false, "turn_id"}` |
| `turn.inventory` | `describe` of every retained Turn plus counters |
| `turn.attach` | proves the Turn and the requested range exist: `replay_available` is true when `since_seq >= earliest_seq − 1` (or the buffer is empty and the cursor is 0); then stores `core_generation`. Unknown → `found: false`, `reason: "turn not found"` |
| `turn.events` with `since_seq` | replays `seq > since_seq` from the buffer, then live; any number of subscribers; the subscriber is registered before the snapshot so nothing is lost in between |
| `turn.ack` | only for a Turn whose last event is `done`, and only when `terminal_seq == last_seq`: sets `terminal_acknowledged`. Otherwise `acknowledged: false` with `reason` (`turn is not terminal`, `terminal_seq N does not match last_seq M`). Any event published after an ack clears it |
| `turn.cleanup`, `turn.recover` | attempt-authority disposition and successor-authority recovery (section 2) |

- **Waits.** An ask event adds an unresolved wait; an accepted `turn.feed_permission`, a cancelled ask, or `done` removes it. `describe` and `attach` expose the open asks to a reconnecting Core.
- **Status.** `done` reason `cancelled` → `cancelled`; `error` → `failed`; anything else → `completed`.
- **Retention.** `gc_completed` runs only at the start of a `turn.execute`. A Turn is dropped when it is terminal, acknowledged, its task finished cleanly, process cleanup is confirmed, no mutation is pending or failed, the authority is disposed (when one exists), and more than `DEFAULT_COMPLETED_TTL_SECONDS` = 300 s have passed **since the acknowledgment**. Unacknowledged terminals and Turns with failed cleanup are kept indefinitely. A dropped id is remembered (with its receipt) so it can never be launched again; at most `MAX_LAUNCH_RECORDS` = 100 000 ids are held and nothing is evicted to make room. No GC runs while an admission or retirement seal is set.
- The corpus (`product-spec/03-turn-execution.md`) states "kept 300 s after the Attempt ends"; in code the clock starts at the terminal acknowledgment and collection waits for the next launch.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/server.py#handle`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnState`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore._start_once`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore._publish`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore.describe`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore.attach`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore.subscribe`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore.acknowledge_terminal`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore.gc_completed`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#TurnStore.resolve_wait`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#_status_for_done`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py#_cleanup_complete`
- `arbol_deprecated_v1:tests/unit/test_provider_admission.py`

## 11. Constants and limits

| Name | Value | Defined in | Purpose |
|---|---|---|---|
| `VERSION` | `"1.0.0"` | `arbol_driver_claude/__init__.py` | `healthz.version` |
| `CLAUDE_BIN` (env) | default `claude` | `server.py#_claude_bin`, `__main__.py` | CLI executable |
| `ARBOL_DRIVER_CLAUDE_SOCKET_NAME` (env) | default `driver.claude` | `__main__.py` | socket file stem |
| `ARBOL_APP_SUPPORT` (env) | default `~/Library/Application Support/Arbol` | `arbol_shared/paths.py` | socket, logs, journals |
| `ARBOL_PROVIDER_BUILD_ID`, `ARBOL_PROVIDER_INSTANCE_ID`, `ARBOL_PROVIDER_DRIVER_ID`, `ARBOL_PROVIDER_GENERATION` (env) | defaults `dev`, `claude@<build>`, `arbol_driver_claude`, `provider-r1` | `arbol_shared/provider_protocol.py` | process identity |
| `TURN_PROTOCOL_VERSION` / `LAUNCH_PROTOCOL` | `2` / `1` | `arbol_shared/provider_protocol.py`, `provider_launch.py` | `turn_protocol.version` and `protocol_revision`; required `launch_protocol` |
| `_NATIVE_DISALLOWED` | `NotebookEdit,WebFetch,WebSearch,Task,TodoWrite` | `turn.py` | `--disallowedTools` |
| `_NATIVE_BASH_DEFAULT_TIMEOUT_MS` | `"300000"` | `turn.py` | env `BASH_DEFAULT_TIMEOUT_MS` |
| `_NATIVE_BASH_MAX_TIMEOUT_MS` | `"1800000"` | `turn.py` | env `BASH_MAX_TIMEOUT_MS` |
| `_NATIVE_RESULT_TRUNCATE` | `200 * 1024` (characters) | `turn.py` | cap on tool-result strings in events |
| `_CLAUDE_CODE_DISABLE_AUTO_MEMORY` | `"1"` | `turn.py` | env of the same name |
| `_PERMISSION_DRAIN_TIMEOUT_SECONDS` | `10.0` | `turn.py` | drain of a permission answer |
| `_DEFAULT_MAX_CYCLES` / `_MAX_CYCLES_CEILING` / `ARBOL_MAX_CYCLES_PER_TURN` (env) | `200` / `500` | `turn.py` | inert cycle cap |
| rate-limit `reason` length | 200 chars | `turn.py#TurnRunner._run_native` | `rate_limited.reason` |
| authentication message length | 1024 chars | `turn.py#TurnRunner._run_native` | `error.message` |
| `ARBOL_ARTIFACTS_ROOT`, `ARBOL_SYSTEM_INSTRUCTIONS_REPO`, `ARBOL_REPO_ROOT`, `ARBOL_KN_CODE_ROOT` (env) | `~/Artifacts`, `Arbol`, `~/repos`, `~/repo/sylvan-stack/Arbol` | `arbol_shared/system_instructions.py`, `system_prompt.py` | prompt sources |
| `_CHUNK` | `64 * 1024` | `arbol_shared/streams.py` | stdout read size (not a line limit) |
| `STDERR_LIMIT` | `1024` bytes | `arbol_shared/native_streams.py` | stderr kept |
| `TERMINAL_EXIT_SECONDS` | `10` | `arbol_shared/native_streams.py` | wait for CLI exit after the terminal record |
| `CLEANUP_SECONDS` | `15` (SIGTERM for the first 2 s, 50 ms polling) | `arbol_shared/native_domain.py` | domain cleanup budget |
| `WORKER_START_SECONDS` / `HANDSHAKE_SECONDS` | `60` / `12` (worker side `15.0`) | `arbol_shared/native_domain.py`, `native_domain_worker.py` | launcher start-up |
| `DEFAULT_COMPLETED_TTL_SECONDS` | `300.0` | `arbol_shared/turn_store.py` | replay retention after acknowledgment |
| `MAX_LAUNCH_RECORDS` | `100_000` | `arbol_shared/turn_store.py` | retained + collected Turn ids |
| stream emission send timeout | `10.0` s | `arbol_shared/provider_authority.py#authenticated_stream` | per event to a subscriber |
| caller: `EXECUTE_TIMEOUT_SECONDS` / `DESCRIBE_TIMEOUT_SECONDS` / attempts / backoff; permission RPC timeouts | `20` / `10` / `3` each / `(0.25, 1.0)`; `10` s (`5` s for the cancel-time deny) | `arbol_core/chat_session_orchestrator.py#ChatSessionOrchestrator`, `arbol_core/orchestration/batches.py` | launch coordination; permission calls |

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/server.py#_claude_bin`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/system_prompt.py#_covers_code_corpus`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/paths.py#app_support`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_protocol.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_launch.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/streams.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/native_streams.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/native_domain.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/native_domain_worker.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_authority.py#authenticated_stream`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/system_instructions.py`
- `arbol_deprecated_v1:daemons/core/arbol_core/chat_session_orchestrator.py#ChatSessionOrchestrator`
- `arbol_deprecated_v1:daemons/core/arbol_core/orchestration/batches.py#BatchesMixin._submit_permission_answer`

## 12. Tests as evidence

| Test file | Behaviours it pins |
|---|---|
| `tests/unit/test_claude_native_turn.py` | allow/deny round trip over the bridge; invoke → ask → settle order; text and tool events in true stream order with input rebuilt from `input_json_delta`; concurrent asks answered out of order; `control_cancel_request`; `turn.feed_permission` forwards `answers`; cancel while an ask is open; malformed ask sets `_native_protocol_broken`; authentication result → `error` + `done(error)`; usage = input + cache read + cache creation; result usage wins over assistant counters; `usage` precedes `cycle_complete`; `additional_instructions` in the prompt; `~/bin` on `PATH`; auto memory disabled; Bash ceiling constant |
| `tests/unit/test_claude_turn_cleanup.py` | a published terminal does not make the store drained before cleanup; repeated cancel during launch still joins launch then cleanup; cleanup failure keeps the handle, blocks GC and drain even after an ack; a stream exception still joins the child; no `os.killpg`; a failed launch stays in `_unresolved_launches`; the normal path waits for the child |
| `tests/unit/test_claude_root_retry.py` | root attempts use a fresh uuid `--session-id` each and leave earlier transcripts alone; a follow-up uses `--resume <chat_session_id>` and regenerates the prior history; CLI exit without a result → `error` naming the exit status and stderr, then `done(error)` |
| `tests/unit/test_claude_account_profiles.py` | `--settings` only for the `api.z.ai` host; inherited `ANTHROPIC_*`, OAuth token, config dir and cloud switches are removed; profile directory per route; standard directory without alias profiles; the transcript is written into the directory the CLI is launched with |
| `tests/unit/test_claude_rate_limit_detect.py` | each indicator phrase; error subtype and `result` type required; retry-after seconds and minutes; authentication detection via `result` and `error` fields; a rate limit is not an authentication failure |
| `tests/unit/test_jsonl_roundtrip.py` | cwd encoding; file path; write/parse round trip; system entries skipped; single parent chain; `chat_sessionId` key; strictly increasing past timestamps without gaps |
| `tests/unit/test_seqoya_usage.py` | `--session-id` vs `--resume`; `extract_usage` and `assistant_usage` arithmetic and `None` cases; caller's option composition (model, token, `account_id`, logged-out, no settings) |
| `tests/unit/test_permission_agent_turn_boundaries.py` | idempotent and concurrent permission retries write once; failed write is retryable; ambiguous drain fails closed; cancellation after write settles locally; per-Turn lock and ask-id isolation; compare-and-seal admission; registration parks behind a seal; stale release cannot unseal a newer generation; a cancelled ask shrinks or releases the seal; lost-reply recovery of a sealed or completed generation; cleanup survives repeated cancellation |
| `tests/unit/test_system_prompts.py` | shared and repository chapters loaded and re-read after edits; missing template fails loudly; only visible Markdown files; Bash checkpoint wording; workspace boundary template |
| `tests/unit/test_provider_admission.py`, `test_provider_mutation_ownership.py`, `test_native_domain_callers.py`, `test_native_service_admission.py` | sealing before any runner starts; ack is not GC permission; late output invalidates an ack; permission mutations own the whole handler; a failed mutation remains unsettled; launch cancellation joins the exact handle; `_claude_version()` is `unknown` and starts no process; worker dispatch precedes daemon imports; terminal timeout falls back to domain cleanup |
| `tests/state/test_claude_state_execution.py`, `tests/state/test_native_retry.py`, `tests/state/test_intake_policy.py` | state mode end to end with the real runner and a scripted CLI: refreshed token reaches `CLAUDE_CODE_OAUTH_TOKEN` and no table; permission, thinking, text, native result, release; rate-limit and credential-refresh retries; wrong or unavailable credential binding refused |
| `tests/smoke/test_ip_claude_ping.py` | the daemon binds `run/driver.claude.sock`; `ping`; `healthz` has `status` and `claude_binary` |
| `tests/integration/conftest.py` | wires the real runner with the mock CLI behind Core and the Effector |

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:tests/unit/test_claude_native_turn.py`
- `arbol_deprecated_v1:tests/unit/test_claude_turn_cleanup.py`
- `arbol_deprecated_v1:tests/unit/test_claude_root_retry.py`
- `arbol_deprecated_v1:tests/unit/test_claude_account_profiles.py`
- `arbol_deprecated_v1:tests/unit/test_claude_rate_limit_detect.py`
- `arbol_deprecated_v1:tests/unit/test_jsonl_roundtrip.py`
- `arbol_deprecated_v1:tests/unit/test_seqoya_usage.py`
- `arbol_deprecated_v1:tests/unit/test_permission_agent_turn_boundaries.py`
- `arbol_deprecated_v1:tests/unit/test_system_prompts.py`
- `arbol_deprecated_v1:tests/unit/test_provider_admission.py`
- `arbol_deprecated_v1:tests/unit/test_provider_mutation_ownership.py`
- `arbol_deprecated_v1:tests/unit/test_native_domain_callers.py`
- `arbol_deprecated_v1:tests/unit/test_native_service_admission.py`
- `arbol_deprecated_v1:tests/state/test_claude_state_execution.py`
- `arbol_deprecated_v1:tests/state/test_native_retry.py`
- `arbol_deprecated_v1:tests/state/test_intake_policy.py`
- `arbol_deprecated_v1:tests/smoke/test_ip_claude_ping.py`
- `arbol_deprecated_v1:tests/integration/conftest.py`
- `arbol_deprecated_v1:tests/fixtures/mock_claude_native.py`

## 13. Defects, dead code and oddities

Refs in the table are abbreviated: bare file names are under `drivers/claude/arbol_driver_claude/`, `tests/...` under the repo root, the rest under `daemons/shared/arbol_shared/` or `daemons/core/arbol_core/`; full refs are in the block below.

| # | Finding | Ref |
|---|---|---|
| 1 | An error `result` that is neither rate limit nor authentication wording ends the Turn as success (`cycle_complete`, `done(no_more_requests)`); `is_error` and `subtype` are not consulted; `protocol.result_summary` / `is_error_text` exist but the driver does not call them | `turn.py#TurnRunner._run_native` |
| 2 | Rate-limit and authentication detection require `subtype` ∈ `error`, `error_during_execution`; a record flagged only by `is_error` is missed (the cleanup test feeds exactly such a record and patches the detector) | `rate_limit.py#is_rate_limit_signal`, `tests/unit/test_claude_turn_cleanup.py` |
| 3 | `retry after 5 minutes` yields 5 seconds: the first pattern's unit is optional and the minutes patterns cover only "retry in" / "try again in" (inferred) | `rate_limit.py#extract_recovery_seconds` |
| 4 | `reason` is `(rec["error"] or rec["result"])[:200]`; a truthy non-string `error` raises `TypeError` and crashes the stream; `message` is matched but never reported (inferred) | `turn.py#TurnRunner._run_native` |
| 5 | `_native_protocol_broken` is process-wide: one malformed or repeated ask id fails every later Turn of every session until the daemon restarts. The message says "native mode disabled" although no other mode exists | `turn.py#TurnRunner._run_native`, `turn.py#TurnRunner.run` |
| 6 | `turn.feed_results` (and the state runtime's `results` delivery) calls `runner.feed_results`, which `TurnRunner` does not define; the legacy call would also set `mutation_failed` on the Turn (inferred); `feed_results_recovery` is still advertised | `server.py#handle`, `state/provider_runtime.py#StateProviderRuntime._deliver`, `provider_protocol.py#BASE_CAPABILITIES` |
| 7 | Cycle cap is dead: `_max_cycles_per_turn`, both constants, the env override and the `done(max_cycles)` branch can never fire | `turn.py#_max_cycles_per_turn` |
| 8 | Unused code: `TurnRunner.stash` / `_pending` (the module docstring's "stash on turn.execute, run on subscribe" state machine is stale); `assistant_parts` is filled and never read; `protocol.encode_user` is not called by the driver (the frame is built inline) | `turn.py#TurnRunner.stash`, `turn.py#TurnRunner._run_native` |
| 9 | `_claude_version_cache` is never assigned: `claude_version` is always `unknown`, as is the "pin the observed version" log line | `server.py#_claude_version` |
| 10 | `start_new_session=True` is passed to a launcher that ignores it; the test only greps the source for the string | `turn.py#TurnRunner._run_native`, `native_domain.py#launch` |
| 11 | Launch failures are misreported. `except FileNotFoundError` → `claude not found`, but a missing executable raises `NativeDomainError`, so that message would mostly describe a missing working directory (inferred). Any launch failure leaves the Turn id in `_unresolved_launches` for the life of the process (pinned as intended retention), and `_cleanup_turn` then raises `Claude native launch outcome remains unresolved`, which is the message a missing `claude` binary ends up with (inferred) | `turn.py#TurnRunner._run_native`, `turn.py#TurnRunner._launch_process`, `native_domain.py#launch`, `tests/unit/test_claude_turn_cleanup.py` |
| 12 | Transcript records use the key `chat_sessionId` (a rename artefact, pinned by a test) and `version: "synthetic-arbol"` | `jsonl.py#history_to_jsonl_lines` |
| 13 | Root-Turn CLI transcripts (one fresh uuid per attempt) are never cleaned up (inferred) | `turn.py#TurnRunner._run_native` |
| 14 | "Saw a delta" flags are per Turn, not per message: after the first streamed delta, text in any later non-streamed `assistant` record is dropped (inferred) | `turn.py#TurnRunner._handle_stream_record` |
| 15 | The usage fallback sums every `assistant` record; the pinned test shows two identical records of 12 counted as 24 | `tests/unit/test_claude_native_turn.py#test_result_usage_takes_precedence_over_assistant_counts` |
| 16 | The result cap applies only to strings and counts characters; list-shaped tool results are unbounded; a JSON-encoded error is cut mid-document | `turn.py#_cap_result_content` |
| 17 | `control_request` subtypes other than `can_use_tool` are never answered; if the CLI blocks on one the Turn hangs with no timeout (inferred) | `turn.py#TurnRunner._run_native` |
| 18 | The replay buffer keeps every delta in memory with no compaction; collection only happens on the next launch; `done(rate_limited)` maps to status `completed` | `turn_store.py#TurnStore._publish`, `turn_store.py#_status_for_done` |
| 19 | The launch receipt hashes all params, token included. Core's authentication-refresh relaunch reuses the attempt id with a new token, so it meets `attempt launch request differs from retained receipt` (inferred; not exercised by a legacy-path test) | `provider_launch.py#launch_receipt`, `turn_store.py#TurnStore._start_once`, `agent_attempt_execution.py#AgentAttemptExecutionService._run_one_attempt` |
| 20 | "One vocabulary, no drift" is not true: Core keeps its own copy of the authentication phrases and decides the retry from message wording, not from `authentication_error` | `protocol.py#AUTH_ERROR_INDICATORS`, `orchestration/support.py#_is_claude_auth_error` |
| 21 | Stale comments: "the six native tools enabled" (only five are denied, nothing is allow-listed); `turn.cancel` "SIGTERM→SIGKILL the subprocess + wake batch waiters"; transcript "before every resumed cycle"; logger names `arbol.ip.claude2.*` | `turn.py#TurnRunner._build_argv_native`, `server.py#handle`, `jsonl.py#history_to_jsonl_lines` |
| 22 | Per published event the authority path makes one or two round trips to the Event Log Service (`attempt_effect` + `attempt_settle`, or one `attempt_observe`); start-up needs Postgres; the prompt needs the `mycel` library and files outside the repo, and a missing template fails the Turn | `turn_store.py#TurnStore.publish`, `attempt_authority.py#effect`, `state/bootstrap.py#configured_binding`, `system_instructions.py#render_instruction_template` |
| 23 | State-mode branch of `__main__` passes no stream handler and its handler does not treat `ping` as public | `__main__.py#main`, `state/provider_runtime.py#StateProviderRuntime.handle` |

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/server.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/jsonl.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/rate_limit.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/__main__.py#main`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/native_domain.py#launch`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/attempt_authority.py#effect`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_launch.py#launch_receipt`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/provider_protocol.py#BASE_CAPABILITIES`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/state/provider_runtime.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/state/bootstrap.py#configured_binding`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/system_instructions.py#render_instruction_template`
- `arbol_deprecated_v1:daemons/core/arbol_core/orchestration/support.py#_is_claude_auth_error`
- `arbol_deprecated_v1:daemons/core/arbol_core/orchestration/agent_attempt_execution.py#AgentAttemptExecutionService._run_one_attempt`
- `arbol_deprecated_v1:tests/unit/test_claude_turn_cleanup.py`
- `arbol_deprecated_v1:tests/unit/test_claude_native_turn.py`
- `arbol_deprecated_v1:tests/unit/test_jsonl_roundtrip.py`

## 14. Installed CLI comparison

Source of the right-hand columns: the output of `claude --help` on the installed 2.1.289 (`claude -p --help` is identical apart from the usage line and the command list). No session was started and no prompt was sent. v1's bridge was verified on 2.1.81 according to the test double and the corpus.

| v1 argument | Listed in 2.1.289 help | Note |
|---|---|---|
| (no `-p` / `--print`) | `-p, --print` exists | help says `--input-format`, `--output-format` and `--include-partial-messages` "only works with --print"; v1 passes all three without it. `protocol.py` records "`claude -p` unsupported" |
| `--session-id <uuid>` | yes | "must be a valid UUID" |
| `--resume <id>` | yes (`-r, --resume [value]`) | v1 passes the Arbol session id; new related flag `--fork-session` |
| `--input-format stream-json` | yes | print mode only |
| `--output-format stream-json` | yes | print mode only |
| `--verbose` | yes | |
| `--include-partial-messages` | yes | print mode + stream-json only |
| `--setting-sources ""` | flag yes | help names the values `user, project, local`; an empty value is not described |
| `--permission-mode default` | flag yes, **value no** | listed choices: `acceptEdits`, `auto`, `bypassPermissions`, `manual`, `dontAsk`, `plan`. `manual` looks like the replacement (inferred) |
| `--permission-prompt-tool stdio` | **not listed** as an option | named only inside the text of the new `--permission-prompts <target>` (`host` = "the SDK host or --permission-prompt-tool", `none` = deny anything that would prompt; default `host`) |
| `--disallowedTools <csv>` | yes (`--disallowedTools, --disallowed-tools <tools...>`) | "Comma or space-separated" |
| `--append-system-prompt <text>` | yes | new `--system-prompt-snapshot` (`on` or `off`, default `on`): a resumed conversation reuses the recorded prompt "even when a later launch passes different text" |
| `--add-dir <dir>` (repeated) | yes (`<directories...>`) | |
| `--model <model>` | yes | |
| `--effort <tier>` | yes | levels now `low, medium, high, xhigh, max`; v1 folds `xhigh` into `max` because `xhigh` was not accepted when probed |
| `--max-turns <n>` (never passed by the driver) | **not listed** | new `--max-budget-usd` is the only listed spend limit |
| `--settings <file>` | yes (`<file-or-json>`) | |

Listed flags with no v1 counterpart that bear on the same concerns: `--tools` (select the built-in tool set; `""` disables all), `--allowedTools`, `--no-session-persistence`, `--replay-user-messages`, `--strict-mcp-config`, `--mcp-config`, `--disable-slash-commands`, `--system-prompt`, `--exclude-dynamic-system-prompt-sections`, `--include-hook-events`, `--forward-subagent-text`, `--fallback-model`, `--bare` (skips auto-memory and settings discovery, but "OAuth and keychain are never read"), `--restricted`, `--safe-mode`. Environment variables are not part of the help output, so `CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY`, `BASH_DEFAULT_TIMEOUT_MS` and `BASH_MAX_TIMEOUT_MS` could not be compared.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#build_argv`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#_EFFORT_BY_THINKING`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._build_argv_native`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#_env_overrides_for`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/claude_cli.py#alias_args`
- `arbol_deprecated_v1:tests/fixtures/mock_claude_native.py`

## 15. Not established

- Whether the installed CLI still accepts `--permission-prompt-tool stdio`, `--permission-mode default`, `--setting-sources ""` and stream-json input/output without `--print`. Help text alone does not settle it and no session was started.
- The real shapes of the installed CLI's records: `control_request` / `control_cancel_request` fields, whether other control subtypes arrive unprompted, and the `subtype` / `is_error` values of a rate-limited, usage-limited or unauthenticated `result`. v1's shapes are pinned only against a test double written for 2.1.81.
- Whether a real CLI resumes correctly from records carrying `chat_sessionId`, `version: "synthetic-arbol"` and no tool history, and whether its project-directory encoding matches `encode_cwd` for paths containing characters other than `/` and space.
- Whether the tool names in `_NATIVE_DISALLOWED` still exist under those names, and which tools the installed CLI enables by default (the driver has no allow-list).
- Whether the environment variables of section 4 are still honoured by 2.1.289, and what the CLI does for credentials when `options.oauth_token` is absent.
- Which permission asks the CLI raises on its own judgement versus runs unasked; this is CLI behaviour outside the repo.
- Whether the legacy authentication-refresh relaunch (finding 19) fails in practice, and whether a non-streamed `assistant` record after streamed ones occurs (finding 14). Both are readings of the code, not observations.
- Whether production ever ran the state receiver (the corpus says it did not; the source cannot say), and the behaviour of the `infer` wrapper that shares `protocol.py` (`max_turns`, `encode_user`, `result_summary`): it is not in this repo.
- Cost and latency of per-event authority round trips, and memory growth of the replay buffer on long Turns: nothing was measured.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._run_native`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/jsonl.py#encode_cwd`
- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/rate_limit.py`
- `arbol_deprecated_v1:tests/fixtures/mock_claude_native.py`
- `arbol_deprecated_v1:daemons/shared/arbol_shared/turn_store.py`

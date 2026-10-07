---
role: authored
spec: CLD-4
status: implemented
---
# Claude Driver · 04 Errors and limits

How the Claude Driver meets [DRV-4](../../arbol/driver-contract/04-errors-and-limits.md): which fields of the `claude` tool's records decide the error code of a failed run, how a rejected credential is caught before the tool has finished retrying, what the tool reports about the account's limits, and the time limits. It matters because the installed tool states most failures in fields that version 1 did not read, and because the one place where wording is still needed, a limit that has actually been reached, could not be observed.

The original observations about the installed tool were made on 5 October 2026 with `claude` 2.1.289 and are recorded in the [probe record](../research/tool-probes-2026-10-05.md).

## Scope

Covered: the mapping from the tool's records and exits to error codes, the tool's own retries, limit information in the stream, time limits, the tool's version.

Not covered: the contract (DRV-4); the events of a run (CLD-2); tools (CLD-3).

## Behaviour

### From the tool's fields to an error code

A failed run is one whose `result` record has its error flag set, or that ends without a `result` record (CLD-2.15). The code is decided by the first row that matches:

| What the tool states | Code | Remedy |
|---|---|---|
| The `assistant` record's error is `authentication_failed`, or the result's status is 401 or 403 | `credential_rejected` | `anthropic`: sign in again. `zai`: replace the key |
| The error is `model_not_found`, or the status is 404 | `invalid_input` | Choose a model from the catalog |
| The error names a rate limit, or the status is 429 | `rate_limited` | Wait |
| The status is 500 or above, or the error is `server_error`, which is also what the tool reports when it could not reach the vendor | `vendor_unavailable` | Try again |
| The status is 400 and the text says the prompt or conversation is too long | `context_exceeded` | Start a new chat |
| Another status of 400 to 499, or another error code of the tool | `vendor_error` | |
| The result's reason for ending is a reached number of turns | `limit_reached` | Not expected: the Driver passes no limit on turns |
| No `result` record: the tool was not found | `tool_missing` | Install the tool |
| No `result` record: standard error names an unknown option or argument | `tool_unsupported` | Update the tool |
| No `result` record, anything else | `tool_failed`, with the exit status and the end of standard error | |
| None of the above, and the result's text matches the wording lists | `rate_limited` or `credential_rejected`, with the detail saying it was decided by wording | |
| Nothing matches | `vendor_error` | |

A result that ends a run the caller stopped is not a failure (CLD-2). A refused resume is not a failure either: the Driver rebuilds (CLD-2.10).

The message of the error is the text of the tool's `assistant` error record or of the result's error list.

Observed with the installed tool: a missing login gives the error `authentication_failed` without a status and the text "Not logged in · Please run /login". A wrong gateway key gives the same error with status 401. An unknown model gives `model_not_found` with status 404. All three end with a result of subtype `success` whose error flag is set and whose reason for ending is `api_error`, and with exit code 1. A reached number of turns ends with subtype `error_max_turns`. Argument errors and an occupied session identifier produce no record at all, only a line on standard error and exit code 1. A termination signal gives exit code 143 and no result.

Observed in version 1: a result counted as a failure only when its subtype was one of two error subtypes and its text held a phrase from the rate-limit or the authentication list. Every other error result ended the turn as completed.

<!-- sources:
arbol:drivers/claude/arbol_driver_claude/rate_limit.py#is_rate_limit_signal
arbol:drivers/claude/arbol_driver_claude/rate_limit.py#is_auth_error_signal
arbol:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._run_native
-->

### The wording lists

Used only by the last-but-one row above. They are version 1's, with one correction.

| Class | Phrases, matched without regard to case |
|---|---|
| Rate limit | `rate limit`, `rate_limit`, `too many requests`, `quota exceeded`, `usage limit`, `overloaded` |
| Rejected credential | `failed to authenticate`, `authentication_error`, `invalid authentication` |

Version 1 also matched the bare fragments `429`, `401` and `quota`. They are dropped: the status now comes from its own field, and a bare number matches identifiers and paths.

A wait is read from the text when it says "retry after", "retry in", "try again in" or "wait", followed by a number and a unit. Seconds and minutes are understood, and a number without a unit is seconds only after "retry after". Version 1 read "retry after 5 minutes" as five seconds; the unit is now required to be read with the number.

<!-- sources:
arbol:drivers/claude/arbol_driver_claude/rate_limit.py#extract_recovery_seconds
arbol:drivers/claude/arbol_driver_claude/protocol.py#AUTH_ERROR_INDICATORS
-->

### The tool's own retries

The tool retries a failed request to the vendor by itself and writes a `system` record of subtype `api_retry` before each retry, with the attempt, the maximum, the delay and the vendor's status. The Driver emits a `notice` for each. When such a record carries status 401 or 403, the Driver stops the run at once and finishes it as `failed` with `credential_rejected`: the credential will not become valid by waiting.

The Driver also limits the tool's retries to three through the environment variable `CLAUDE_CODE_MAX_RETRIES`.

Observed with the installed tool: with a wrong gateway key the tool made ten retries with growing delays and gave up after 175 seconds. With the variable set to 1 it gave up after one retry and 1.4 seconds.

Observed on 6 October 2026, with the vendor made unreachable through a proxy address where nothing listens, and the variable set to 3: three `api_retry` records without a status, with the error `unknown` and delays of 0.6, 1.1 and 2.0 seconds. Then came an `assistant` record with the error `server_error` and the text "API Error: Connection refused — a firewall or proxy may be blocking it (ECONNREFUSED)", and a `result` with the error flag, the reason for ending `api_error` and no status. The tool exited with code 1, 4.2 seconds after its start.

### Limit information in the stream

On an Anthropic Subscription the tool writes a `rate_limit_event` record once per run, after the first request to the model. The Driver turns the latest one into the Subscription's usage report when the run ends (DRV-4.13, CLD-1.14):

| Usage report | Taken from |
|---|---|
| Window of kind `session`, 300 minutes | `unifiedWindows.five_hour`: the share used as a percentage, the reset time |
| Window of kind `weekly`, 10,080 minutes | `unifiedWindows.seven_day`, the same |
| `limitReached` of a window | The share used is 1 or more |
| `extra` | The record's status, the window it names as the limiting one, and whether usage beyond the plan is in use |

When a run fails with `rate_limited` and the text names no wait, the wait is the time until the reset of the window the latest record names as the limiting one, if a record arrived in that run.

On a z.ai Subscription no such record arrives. Its usage report comes from z.ai's quota address on request (CLD-1.13), and a `rate_limited` error carries a wait only when the text names one.

Observed with the installed tool: the record's reset times are in seconds since 1970 and the share used is a number between 0 and 1. The original probe saw the status `allowed_warning` and the limiting window `seven_day`. The raw run of 6 October also records `allowed` and `five_hour`; these values are retained without changing the window mapping.

Observed in version 1: the record was skipped.

<!-- sources:
arbol:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._run_native
-->

### Time limits

| Limit | What counts for this tool |
|---|---|
| Start | The `system` record of subtype `init`, which the tool writes after it has received the message |
| Idle | Any record on standard output is a sign of life, including the tool's records about thinking in progress and its retries |
| Shell commands | The tool's own two settings, passed in the environment (CLD-2): first report after 5 minutes, end after 30 minutes |

A question that is open and a tool call that is running stop the idle clock (DRV-4.10). For this tool a tool call is running from its `tool_started` to its `tool_finished`. A command the agent left in the background stops the clock for as long as the tool's list of background tasks names it (CLD-3).

### The tool's version

The Driver reads the version by running `claude --version`. It keeps the answer in its state directory, together with the size and the change time of the executable's file, so that a later invocation asks the tool again only when that file has changed (DRV-6). A version below the oldest supported one, 2.1.289, refuses every operation that needs the tool with `tool_unsupported`, naming both versions. The run's `started` event carries the version the tool itself states in its first record.

Observed in version 1: the version was never read; health reports always said "unknown".

<!-- sources:
arbol:drivers/claude/arbol_driver_claude/server.py#_claude_version
-->

## Requirements

| ID | The Claude Driver must… | Refines | Origin | Verified by |
|---|---|---|---|---|
| CLD-4.1 | decide the error code of a failed run by the mapping table, first matching row | DRV-4.4 | Changed | `errors.precedence`, `C26` |
| CLD-4.2 | use the wording lists only when the tool states no error code and no status, and mark the error as decided by wording | DRV-4.4 | Changed | `errors.precedence`, `C26` |
| CLD-4.3 | read seconds and minutes with the number; without a unit assume seconds only after "retry after" | DRV-4.5 | Changed | `errors.wait`, `C27` |
| CLD-4.4 | emit a `notice` for every `api_retry` record | DRV-4.12 | New | `C28`, `probe.errors` |
| CLD-4.5 | stop the run at the first `api_retry` record with status 401 or 403 and finish it as `credential_rejected` | DRV-4.8 | New | `C28`, `probe.errors` |
| CLD-4.6 | limit the tool's retries to three | DRV-4.12 | New | `probe.errors` |
| CLD-4.7 | build the usage report of an `anthropic` Subscription from the latest `rate_limit_event` of a run by the table above | DRV-4.13 | Changed | `errors.usage`, `C30`, `live.errors-usage` |
| CLD-4.8 | take the wait of a `rate_limited` error from the text, else from the reset of the limiting window, else give none | DRV-4.5 | Changed | `errors.wait`, `C27` |
| CLD-4.9 | treat every record on standard output as a sign of life | DRV-4.9 | New | `errors.clocks`, `C29` |
| CLD-4.10 | give the exit status and at most 1 KiB of standard error with `tool_failed` and `tool_unsupported` | DRV-4.2 | Kept | `errors.diagnostics`, `C26` |
| CLD-4.11 | read the tool's version by running it, and refuse to use a version below the oldest supported one | DRV-4.14 | Changed | `base.tool-cache`, `base.tool-old`, `probe.base-info` |

## Not established

- What a run looks like when a limit has actually been reached, when the vendor is overloaded, and when the conversation no longer fits: which error code the `assistant` record carries, which status, which text. None occurred. Until one has been seen, the rows for 429, for 500 and above, and for a conversation that is too long rest on the status alone, and the wording lists stay in place.
- Other values of the limit record's status and limiting window.
- Limit and quota signals of z.ai.
- Whether the tool honours a retry limit of zero.

## Known problems in version 1

Not to be reproduced.

- **Most error results ended as completed turns**, among them, on the installed tool, a missing login and an unknown model.
- **`retry after 5 minutes` was read as five seconds.**
- **The limit records of the stream were skipped**, while the account's usage was read from a web page.
- **The tool's version was always "unknown".**

<!-- sources:
arbol:drivers/claude/arbol_driver_claude/rate_limit.py#extract_recovery_seconds
arbol:drivers/claude/arbol_driver_claude/server.py#_claude_version
-->

## SYL-87 verification, 7 October 2026

All 38 shared conformance scenarios pass, with C5 checking an actual run, C7 covering output/state/argument redaction and C32 covering the command line and development checks. The Driver passes 81 automated tests and the suite passes 10 runner tests under Node 24.21. The compiled `dev probe` passes against installed Claude 2.1.289 without a prompt, including the existing test login; shapes-only evidence is `research/dev-probe-2026-10-07.json`. The compiled `dev build-check` passes with one tools-off Haiku message on `test-anthropic`, recorded in `research/dev-build-check-2026-10-07.json`. The six-turn live command is checked by `dev.live-check` against the stand-in and refuses missing, signed-out or exhausted accounts in `dev.gates` and C32. Its fresh six-turn vendor run was not requested; earlier task live records remain the evidence for the tool, question, background, continuity and stop behaviors. Anthropic preflight uses the timestamped cached usage, by CLD-D2. A first build-check attempt failed before inference because the clean child PATH omitted the discovered tool folder; that was fixed before the passing record. Numbered Builds remain SYL-76/SYL-93.

## Decisions

| ID | Question | Proposed default | Outcome |
|---|---|---|---|
| CLD-D11 | How many retries may the tool make by itself? | Three. The tool's own default of ten can take minutes | Decided 6 October 2026 by the owner: the proposed default (SYL-61) |
| CLD-D12 | Are the wording lists kept at all? | Yes, as the last resort, until a reached limit has been observed on the installed tool | Decided 6 October 2026 by the owner: the proposed default (SYL-62) |
| CLD-D17 | How are the run clocks and early credential refusal implemented? | Use monotonic time. Start is measured per tool invocation and ends at init; idle starts there, refreshes on every stdout record and is suspended while calls, questions or background tasks are present. Total spans a refused-resume replacement too and never pauses. Caller limits are not scaled; a total of zero expires immediately and idle zero is off. Clamp individual timer waits to Node's maximum and recheck the deadline before expiring. A reached limit or visible credential refusal uses the existing interrupt and cleanup path, preserving its failed outcome | Decided 7 October 2026 during SYL-85, a technical choice; `errors.clocks`, `C28`, `C29`, `probe.errors` |
| CLD-D18 | How does a run save usage and rejected credentials without losing simultaneous changes? | Merge under the short Subscription lock. Keep the later fetchedAt report, current label and account fields. Save only against the same checkedAt login/check, without restoring a signed-out account or replacing a newer sign-in. Request the tool stop immediately on a credential refusal, then store the refusal under the short lock; its same problem may receive the last usage report at completion. Never poll the vendor for Anthropic usage | Decided 7 October 2026 during SYL-85, a technical choice; `errors.run-report`, `C4`, `C30`, `live.errors-usage` |

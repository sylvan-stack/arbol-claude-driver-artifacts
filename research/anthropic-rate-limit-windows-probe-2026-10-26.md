---
role: authored
---
# Probe: the windows in the Anthropic stream's `rate_limit_info` · 26 October 2026

The research record behind SGM-D26 of [Subscriptions Vigor](../../arbol/sagas/01-subscriptions-vigor.md) and SYL-290: does the limit information the `claude` tool writes during a run carry model-specific weekly windows beside `five_hour` and `seven_day`? Vigor would add such windows scoped by model if the stream reported them.

## What was probed

One real run of the installed tool, Claude Code `2.1.304`, on 26 October 2026 at 22:38 UTC, from a clean login shell, in the test Subscription's own home (`test-anthropic`, plan `max`, CLD-D20): `claude -p --output-format stream-json --verbose --model haiku "Answer with the single word: ready"`, started in an empty folder with `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`. One Haiku message was spent. The raw stream stays outside Git; this record keeps shapes only, no account values.

## What the stream carried

Four records: `system` (`init`), `assistant`, `rate_limit_event` and `result` (`success`). The one `rate_limit_event` record holds `rate_limit_info` with these keys and nothing else:

| Key | Type | Meaning |
|---|---|---|
| `status` | string | `allowed` |
| `resetsAt` | number | seconds since 1970, the reset of the window named by `rateLimitType` |
| `rateLimitType` | string | `five_hour` |
| `overageStatus` | string | `rejected` |
| `overageDisabledReason` | string | `org_level_disabled` |
| `isUsingOverage` | boolean | |
| `unifiedWindows` | object | exactly two keys, `five_hour` and `seven_day`; each an object with `utilization`, a fraction of 1, and `resetsAt`, seconds since 1970 |

No key names a model. `unifiedWindows` has no third entry, and no other record of the stream carries limit information. The record of 7 October 2026 in the repository's `test/errors-protocol-2026-10-07.json` (Claude Code `2.1.289`) has the same key set.

## Outcome for SGM-D26

The stream reports no model-specific weekly window for this account and tool version, so the Driver maps nothing more than the five-hour and the seven-day window, both counting tokens (CLD-1, DRV-1.27). The probe covers one account on the `max` plan; a plan with a model-scoped weekly limit was not available to probe. Should a later tool version add a model-scoped key to `unifiedWindows`, it is mapped as a further `weekly` window scoped by model with `resource: "tokens"`, by the proposal recorded in SGM-D26.

<!-- sources: arbol-claude-driver:src/arbol_claude_driver/protocol.py#limit_report -->

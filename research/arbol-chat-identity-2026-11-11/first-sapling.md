---
role: authored
---
# Live check: a real First Sapling Exchange sees its Root and chat · 11 November 2026

SYL-399 step 12 checks RCT-2.23, TRV-0.14, CLD-2.26 and DRV-2.37 end to end. One real message went to First Sapling through the installed Trivial Trunk and Claude Driver. The run used the owner's own Claude login, the native `anthropic` Subscription in the normal Claude Driver state, by the owner's 11 November 2026 scope change. No `CLAUDE_CONFIG_DIR` was set, no test profile or bridge was used, and no sign-in was launched.

**Result: passed.** The agent's real shell printed `sapling c60d4ff8-0301-4644-8e14-afb35adcf2e0`. That is First Sapling's Root identifier and the chat the Trunk accepted, checked against independent sources, with no masking. The request named no chat, so this is the first-message path of TRV-0.14.

## What ran

| Item | Value |
|---|---|
| Root | First Sapling, `sapling` (`~/Library/Application Support/Arbol/roots/sapling/root.json`) |
| Trunk | Trivial Trunk Build `d` (`arbol-trunk@142e4fc`), working and chosen for `sapling` |
| Driver | Installed Claude Driver Build 11 (`arbol-claude-driver@87301fb`), normal state `~/Library/Application Support/Arbol/drivers/claude` |
| Subscription and model | `anthropic`, `haiku` (`claude-haiku-5-5`) |
| Command | `arbol-root --root sapling start --exchange bc74fc1c-84ba-492f-9113-8f784de8a00c --request request.json`, with no `--bin-dir` |
| Request | `message`: "Run this exact shell command with your shell tool and reply with its output only, nothing else: echo $ARBOL_ROOT $ARBOL_CHAT"; `route`: `claude`, `anthropic`, `haiku`; no `chat` |

## Independent expected values

| Value | Source |
|---|---|
| Root `sapling` | The Root record's `root` field |
| Chat `c60d4ff8-0301-4644-8e14-afb35adcf2e0` | The acceptance line `arbol-root` printed: `accepted` true, number 1, Build `d` |
| The same chat | The `chats` row of `arbol_sapling`, reached from `exchanges.chat_id` |

## What First Sapling stored

The Exchange folder is removed when an Exchange ends (RCT-1), so the stored rows of `arbol_sapling` stand in for `events.jsonl`.

| Table | Content |
|---|---|
| `exchanges` | `completed`, chat `c60d4ff8-0301-4644-8e14-afb35adcf2e0`, number 1, Build `d` |
| `tool_calls` | `shell`, input `echo $ARBOL_ROOT $ARBOL_CHAT`, output `sapling c60d4ff8-0301-4644-8e14-afb35adcf2e0` |
| `messages`, assistant | `sapling c60d4ff8-0301-4644-8e14-afb35adcf2e0` |
| `runs` | `agent`, `completed`, `started.subscriptionId` `anthropic`; 63,136 input tokens (38,522 cached), 294 output tokens, 144 reasoning tokens, reported cost USD 0.0055 |

The Exchange stays in First Sapling as chat `c60d4ff8-…`. It was the owner-authorized real message of this check.

## How Trunk Build `d` became working

Its gate ran with `ARBOL_BUILD_LIVE_SUBSCRIPTION=anthropic` and `ARBOL_BUILD_TEST_STATE_DIR` set to the normal state (TRV-D12). It passed all three top-tier cases and its live check: one completed Exchange in the test Root `rct`, on `anthropic`, at a reported cost of USD 0.006. Two Builds before it failed:

- **Build `b` (`ff9db44`)**: the live check's Driver bridge did not pass `USER`, so Claude Code reported "Not logged in". Commit `142e4fc` fixed the bridge.
- **Build `c`**: the Driver refused before starting, because Build `b`'s rejection had set `anthropic` to `needs_attention`. The Driver's free `subscriptions check anthropic`, which runs no inference and is not a sign-in, set it back to `signed_in`.

## How to repeat it

Write a request like the one above, then run `arbol-root --root sapling start --exchange <new UUID> --request request.json`. When `exchanges.state` is `completed`, compare the `shell` call's output and the assistant message with `sapling` and the chat on the acceptance line. It sends one real message on the owner's account and adds a chat to First Sapling, so run it only when asked.

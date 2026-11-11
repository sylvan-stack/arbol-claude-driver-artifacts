---
role: authored
---
# Live check: the agent's shell sees the Arbol chat identity · 11 November 2026

SYL-399 qualifies CLD-2.26 and DRV-2.37 at the real tool boundary. This record holds one tools-on message through the installed Claude Driver on the test Subscription `test-anthropic`.

**Result: passed.** The agent's own shell printed the request's `rootId` and `chatSessionId`, not the stale values in the caller's environment. It did not see an unrelated caller variable.

## What ran

| Item | Value |
|---|---|
| Driver | Installed Build 11, source `arbol-claude-driver@87301fb` (SYL-207 code `eea4f95` included) |
| Tool | Claude Code 2.1.322 |
| Subscription | `test-anthropic`, in the test state directory `~/Library/Application Support/Arbol/drivers/arbol-claude-driver` |
| Model | `haiku` (`claude-haiku-5-5`) |
| Caller environment | Clean: `HOME`, `USER`, `LOGNAME`, `SHELL`, `PATH`, `LANG`, plus stale `ARBOL_ROOT=stale`, `ARBOL_CHAT=0f0e0d0c-0b0a-4908-8706-050403020100` and the unrelated `SYL399_UNRELATED=caller` |
| Request | `tools: "all"`, `rootId: "qualify399"`, `chatSessionId: "7d274e6e-582b-4716-97d4-746407af7c25"`, empty history |
| Message | "Run this exact shell command with your shell tool and reply with its output only, nothing else: `echo "$ARBOL_ROOT $ARBOL_CHAT ${SYL399_UNRELATED:-unset}"`" |

Usage before the check: five-hour window 20 %, weekly window 39 %, read by Build 11's own build check a minute earlier. The check spent one run: 58,506 input tokens (26,760 cached), 229 output tokens, 77 reasoning tokens, reported cost USD 0.0067.

## What the Driver reported

| Event | Content |
|---|---|
| `tool_started` | `shell`, command `echo "$ARBOL_ROOT $ARBOL_CHAT ${SYL399_UNRELATED:-unset}"` |
| `tool_finished` | `ok: true`, output `qualify399 7d274e6e-582b-4716-97d4-746407af7c25 unset` |
| `text` | `qualify399 7d274e6e-582b-4716-97d4-746407af7c25 unset` |
| `finished` | `completed`, exit status 0 |

## How to repeat it

Write a request file like the one above with a fresh UUID. Then run, from any folder:

```sh
env -i HOME="$HOME" USER="$USER" LOGNAME="$USER" SHELL=/bin/zsh \
  PATH="$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin" LANG=en_US.UTF-8 \
  ARBOL_ROOT=stale ARBOL_CHAT=0f0e0d0c-0b0a-4908-8706-050403020100 SYL399_UNRELATED=caller \
  arbol-claude-driver --state-dir "$HOME/Library/Application Support/Arbol/drivers/arbol-claude-driver" \
  run --request request.json
```

It passes when the `shell` call's output is `<rootId> <chatSessionId> unset`. It spends one small message, so run it only when asked (DRV-5.4).

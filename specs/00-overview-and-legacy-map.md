---
role: authored
spec: CLD-0
status: implemented
sources:
  - arbol-claude-driver:research/v1-driver-inventory.md
---
# Claude Driver · 00 Overview and legacy map

The Claude Driver is the Arbol 2 [Driver](../../arbol/GLOSSARY.md#driver) for the `claude` command-line tool. This specification says what it is in one page and where every part of the version 1 code went: carried over, changed, moved to the caller or dropped. It matters because the version 1 Driver is about 1,900 lines resting on some 4,500 lines of shared process, authority and recovery helpers, and a rewrite that ports the wrong part reproduces the problems the rewrite exists to remove.

## Scope

Covered: what this Driver is, its requirements beyond [DRV-0](../../arbol/driver-contract/00-overview-and-boundary.md), the fate of each part of version 1, what changed in the installed tool since version 1 was written.

Not covered: behaviour in detail. Each row of the legacy map names the specification that carries it.

## What this Driver is

- One command-line program, `arbol-claude-driver`, written in TypeScript. Its command line is its only interface, and Arbol holds none of its code (DRV-0).
- It serves two vendor families through one tool: `anthropic` and `zai` ([CLD-1](01-subscriptions.md)).
- Every Subscription has its own home for the tool. Every inference run is one `claude` process started in that home, spoken to over the tool's stream format, and gone when the run ends.
- A run is given what it needs in the request: system prompt text, working folders, conversation, and the Subscription, model and effort where the caller names them. What is left out comes from the Driver's settings file. Beyond that file, the request file and the owner's own skills and list of MCP servers, which it hands to the tool (CLD-3), it uses nothing outside its state directory and the Subscription's home.
- It has no socket, no launch job, no database connection and no knowledge of Chat Sessions, routes or repositories.

## Requirements

| ID | The Claude Driver must… | Refines | Origin | Verified by |
|---|---|---|---|---|
| CLD-0.1 | find the `claude` executable from `toolPath` in its settings file or else on the search path, read its version by running it, and report both | DRV-0.6 | Changed | `base.info`, `base.tool-cache`, `probe.base-info` |
| CLD-0.2 | refuse to run with a tool older than the oldest supported version, naming both versions | DRV-0.6 | New | `base.tool-old` |
| CLD-0.3 | need nothing but the tool, its state directory and the Keychain to start: no database, no other Arbol service, no file from an Artifact Corpus | DRV-0.8 | Changed | `base.info`, `C1`, `C10`, `C32` |
| CLD-0.4 | take the system prompt as text in the request and add nothing to it | DRV-0.2 | Changed | `run.request`, `C10` |
| CLD-0.5 | confine the effect of a malformed message from the tool to the run it arrived in | DRV-0.7 | Changed | `run.protocol`, `C18` |

Check names beginning with `base.` or `state.` select the tests with that literal name prefix in this Driver's Node.js test runner (`--test-name-pattern`). `probe.base-info` is the separate no-prompt check in `test/probe-info.mjs`, recorded in `research/base-info-2026-10-06.json`. Shared-contract rows name the complete Claude conformance evidence separately and leave Codex pending.

## SYL-87 verification, 7 October 2026

All 38 shared conformance scenarios pass, with C5 checking an actual run, C7 covering output/state/argument redaction and C32 covering the command line and development checks. The Driver passes 81 automated tests and the suite passes 10 runner tests under Node 24.21. The compiled `dev probe` passes against installed Claude 2.1.289 without a prompt, including the existing test login; shapes-only evidence is `research/dev-probe-2026-10-07.json`. The compiled `dev build-check` passes with one tools-off Haiku message on `test-anthropic`, recorded in `research/dev-build-check-2026-10-07.json`. The six-turn live command is checked by `dev.live-check` against the stand-in and refuses missing, signed-out or exhausted accounts in `dev.gates` and C32. Its fresh six-turn vendor run was not requested; earlier task live records remain the evidence for the tool, question, background, continuity and stop behaviors. Anthropic preflight uses the timestamped cached usage, by CLD-D2. A first build-check attempt failed before inference because the clean child PATH omitted the discovered tool folder; that was fixed before the passing record. Numbered Builds remain SYL-76/SYL-93.

## Decisions

| ID | Question | Proposed default | Outcome |
|---|---|---|---|
| CLD-D16 | How is a numbered Claude Build packaged and checked? | The repository describes it in arbol-build.json. After npm ci and compilation, copy bin/, dist/src/, dist/test/, package.json, README and the five JSON records needed by runtime stand-ins and unit tests into the Build, retaining their relative paths. Unit tests run from that Build and compare info with its own record; the contract check compiles the shared suite from ARBOL_CONFORMANCE_REPO, or ~/repos/sylvan-stack/arbol, and starts the Build entry directly. The live check starts that same entry with a clean environment, runs one Haiku message and uses ARBOL_BUILD_TEST_STATE_DIR when supplied, otherwise the Driver default state directory. Existing signed-in test state is selected explicitly, never copied or migrated. | Decided 7 October 2026 during SYL-93, a technical choice |
| CLD-D13 | How is the base developed and checked? | Compile strict TypeScript ESM with `tsc`; use the Node.js test runner. The package has one executable, and no public library exports. During the staged implementation, recognised operations whose task has not been implemented return `unsupported`; unknown commands and options return `invalid_input` | Decided 6 October 2026 during SYL-75, a technical choice |
| CLD-D15 | How are the checks carried by the executable? | Compiled TypeScript modules behind the three dev commands, without a build-time dependency on the source test harness. The package explicitly includes bin/, dist/src/ and the four JSON protocol records read by its stand-ins; the extracted package passes the suite without source files or node_modules. Probe records are shapes-only JSON in research/ under the selected Driver state directory, so a read-only Build can be checked and the suite writes only to its isolated home; implementation evidence is also copied to the Driver's Artifact Corpus research folder, with an actual tool version and UTC date. Probes use disposable config homes, and optionally the existing test-anthropic home for a no-prompt status/catalog check; they never send a user record. They cover version, auth/browser handoff, initialization, applied settings, session acceptance, interrupt, skill/MCP loading, and argument errors. Historical raw failed-request and live records remain evidence; they are not replayed as quota-free probes. The live command uses six small Haiku messages for plain output/usage, tools/questions, background attribution, conversation continuation (two), and stopping. Build-check uses exactly one Haiku message with tools off. Before each real message, require test-anthropic signed in and check its last usage report; this is cached by the accepted CLD-D2 and its time is reported. Report attempts, token totals, usage before/after and percentage changes, also on failure. | Decided 7 October 2026 during SYL-87, a technical choice |
| CLD-D14 | Does `info` need a supported tool? | No. It succeeds with `supported: false` for a missing or older tool, so callers can inspect the installation. Operations that need the tool use the typed refusal of DRV-4.14. A version probe uses an empty temporary config home inside the state directory and a clean environment, and removes that home afterward | Decided 6 October 2026 during SYL-75, a technical choice |

## Legacy map

Fate is one of: **Kept** (same behaviour, rewritten), **Changed** (same purpose, different behaviour), **Caller** (the purpose remains and belongs to the Driver's caller), **Dropped**.

### Process, transport and recovery

| Version 1 part | What it did | Fate | Specified in |
|---|---|---|---|
| `__main__.py`, launch job `com.arbol.driver.claude`, socket `driver.claude.sock` | One resident process for all Claude-transport routes, framed JSON over a Unix socket | Dropped | DRV-0 |
| Build, instance and generation identity; admission sealing; retirement | Ran old and new Driver builds side by side during an upgrade | Dropped | DRV-0 |
| Dispatcher grants, attempt authority, launch receipts | Proved for every command and every published event that the caller still owned the turn, with a round trip to the Event Log Service per event | Dropped | DRV-0 |
| `state_main.py`, the state receiver and its checkpoints | Second receiver for the state runtime, which did not become the production path | Dropped | none |
| Start-up check against the database | The process refused to start unless it could read the authority mode | Dropped | CLD-0.3 |
| `turn.execute`, `turn.cancel`, the `turn.events` stream | Start, stop and observe one turn | Changed: the run operations of the contract | DRV-2, CLD-2 |
| `turn.inventory`, `turn.describe`, `turn.attach`, `turn.ack`; the in-memory replay buffer | Let a restarted Root find running turns and replay their events. Everything was held in the Driver's memory, every delta included | Caller: a run is one process started by its caller and ends with it, so there is nothing to reattach to. What a caller keeps for a reopened window is its own matter | DRV-D2 |
| The launcher job and its worker (`native_domain`) | Started the tool under a launch job of its own so that every process the tool spawned could be found and ended | Changed: an ordinary child process, given a shell of the Driver's own making that notes every shell call, so that what a command left in the background is found and ended (CLD-2.21). A program that makes itself a background service is no longer found (DRV-D33) | DRV-0.10, CLD-2 |

### Starting the tool

| Version 1 part | What it did | Fate | Specified in |
|---|---|---|---|
| `protocol.build_argv` | Stream input and output, partial messages, ambient settings off, permission questions routed to the caller, five tools disallowed, appended system prompt, allowed folders, model, effort | Changed. The stream arguments and the system prompt are kept and re-verified against the installed tool, see below. Permission questions are no longer routed to the caller, no tool is disallowed (DRV-D12), and the settings of the working folder are no longer switched off (DRV-D26) | CLD-2, CLD-3 |
| The seven thinking levels mapped to four effort tiers | `xhigh` and `max` both became `max`; `ultra` and `none` requested nothing | Dropped. The caller names an effort from the model catalog, in the tool's own words | DRV-1.21, CLD-2 |
| `claude_cli.py`: profile folder, alias arguments, environment | Rebuilt the owner's shell aliases: a shared profile folder, a personal settings file for z.ai, a removal list for inherited variables | Changed: a home per Subscription, an allow-list, no settings file | CLD-1 |
| Extra environment: auto memory off, Bash time limits, `~/bin` added to the search path | Kept the tool from writing its own memory, bounded shell commands, made Arbol's own commands reachable | Kept. The addition to the search path becomes a setting of the request | CLD-2 |
| `system_prompt.py` and the instruction templates | Built the system prompt from template files in the Artifact Corpus, repository chapters found through the Mycel library, and extra text from the caller | Caller. The Driver receives the finished text | CLD-0.4 |

### Conversation

| Version 1 part | What it did | Fate | Specified in |
|---|---|---|---|
| A fresh session identifier for a first message; `--resume` with the chat's identifier afterwards | Kept the tool's saved session from ever being the source of truth | Changed, see the next row | CLD-2 |
| `jsonl.py`: transcript regeneration | Before every follow-up, overwrote the tool's saved session with one rebuilt from Arbol's history: text only, so the tool's own record of its tool calls was lost between turns | Changed, following the Product Specification's default: Arbol's history stays the authority; the tool's own session is resumed when it exists and matches that history, and rebuilt from the history otherwise, with the run saying which happened | CLD-2 |
| First-message sessions left behind | One saved session per attempt, never read again, never removed | Dropped | CLD-2 |

<!-- sources:
arbol:product-spec/12-lessons-and-invariants.md#Decisions for the successor's design
-->

### Reading the tool's output

| Version 1 part | What it did | Fate | Specified in |
|---|---|---|---|
| Stream handling in `TurnRunner._run_native` | Text and thinking deltas, tool calls at their block boundary, tool results, the final result | Kept, with contract event names | CLD-2 |
| Usage arithmetic (`extract_usage`) | Input tokens include cached input; the final record wins over sums from earlier records | Kept | CLD-2 |
| An error result treated as success | Only rate-limit or authentication wording made a result a failure; any other error ended the turn as completed | Changed: a result the tool marks as an error is an error | CLD-4 |
| "Saw a delta" remembered for the whole turn | After the first streamed piece, text of a later message that arrived whole was dropped | Changed: remembered per message | CLD-2 |
| Limits on result size | 204,800 characters for text results; none for structured ones | Changed: one limit for every shape | CLD-3 |

### Tools and permissions

| Version 1 part | What it did | Fate | Specified in |
|---|---|---|---|
| The permission bridge (`can_use_tool` requests, allow and deny answers, withdrawal) | Carried each permission question to Root and the answer back; answers to questions for the Leather Bag travelled the same way | Changed. Decided 6 October 2026: permission questions are gone, since the agent runs as trusted (DRV-D12). Questions from the agent to the person still travel this way (DRV-D25) | CLD-3 |
| Answer delivery rules | A repeated answer is written once; an answer whose delivery is uncertain is never rewritten | Kept, for the answers to the agent's questions | CLD-3 |
| Wait generations: admit, seal, release | Froze the set of open questions so Root could record its decisions before answering any | Dropped with the durable boundary it served | CLD-3 |
| The process-wide "protocol broken" flag | One malformed question failed every later turn of every chat until the process was restarted | Changed: the failure ends that run only | CLD-0.5 |
| `turn.feed_results`, the fence path | Called a method that does not exist; no fenced requests are parsed | Dropped | none |
| The disallowed-tool list | `NotebookEdit`, `WebFetch`, `WebSearch`, `Task`, `TodoWrite` | Dropped. Decided 6 October 2026 (CLD-D9): every tool of the installed version is available | CLD-3 |

### Failures and limits

| Version 1 part | What it did | Fate | Specified in |
|---|---|---|---|
| `rate_limit.py`: wording match and retry hint | Recognised a limit from phrases in the result text and read "retry after" seconds or minutes from it. The tool's own limit records were skipped | Changed: the tool's limit records first, the wording match as the fallback. The misread of "retry after 5 minutes" as five seconds is not carried over | CLD-4 |
| Authentication wording match, repeated in Root | The Driver flagged the failure; Root matched the same phrases again to decide a retry | Changed: one typed error, and the Subscription moves to `needs_attention` | DRV-1.7, CLD-4 |
| No time limit of any kind | A turn could wait forever, also on a question from the tool the Driver did not understand | Changed: limits are settings of the request, and an unknown question from the tool is answered or ends the run | CLD-4 |
| The cycle limit | Could never trigger | Dropped | none |
| Cancel | Ended the tool's processes without telling the tool | Changed: the tool is asked to stop first, then ended | CLD-2 |
| Launch failures | A missing executable surfaced as "launch outcome remains unresolved" | Changed: a typed error naming the tool | DRV-0.6 |

### Account code that lived outside the Driver

| Version 1 part | What it did | Fate | Specified in |
|---|---|---|---|
| `subscription_oauth.py`, `subscription_login.py` | Arbol's own Anthropic authorisation and renewal | Dropped. Decided 5 October 2026 (CLD-D1): the tool's own login, which the vendor's terms require | CLD-1.8 |
| `subscriptions.py` credential store, `macos_keychain.py` | Keychain items written through the Security framework | Changed: the z.ai key is read with the system's `security` command, or taken from a command the owner names | CLD-1.10, DRV-D4 |
| `rpc/subscription.py` | Sign-in, sign-out, key entry, usage, as Root operations | Changed: the Subscription operations of the contract | DRV-1 |
| `zai_usage.py` | z.ai quota reading and its normalisation | Kept | CLD-1.13 |
| `provider_models.py`: Anthropic list and entitlement probes | One request per listed model | Dropped | CLD-1.15 |
| `provider_models.py`: z.ai list | z.ai's own model interface | Kept | CLD-1.16 |
| Usage reading in the Swift application | The vendor's usage web page in a hidden browser session | Dropped | CLD-D2 |
| `vscode_launch.py` | An editor instance per account, with the account's credential in its environment | Dropped | DRV-D6 |
| `completion.py` | One prompt in, one text out through the tool, in an empty folder with every tool disallowed | Kept as a run without tools. Retries are the caller's | CLD-2 |
| `rate_limit_tracker.py`, route selection, failover | Cooldown per route, choice of route per turn | Caller | none |

## The installed tool has moved on

Version 1's arguments were verified against version 2.1.81 of the tool. Compared with the help text of the installed 2.1.289 on 5 October 2026:

| Version 1 passes | Installed tool |
|---|---|
| No `--print` | Help says stream input, stream output and partial messages work only with `--print`. A control request sent with `--print` was answered (CLD-1, probes) |
| `--permission-mode default` | `default` is no longer among the listed values; `manual` is |
| `--permission-prompt-tool stdio` | Not listed as an option. A new `--permission-prompts` names it only in passing |
| `--setting-sources ""` | The flag exists; an empty value is not described |
| Effort `low`, `medium`, `high`, `max` | `xhigh` is accepted as well |
| `--max-turns` (supported by the code, never passed) | Not listed |

Flags the installed tool offers for concerns version 1 solved by other means: `--tools` and `--allowedTools` (which tools exist at all), `--no-session-persistence`, `--system-prompt`, `--strict-mcp-config`, `--bare`.

None of this is settled by help text. CLD-2 and CLD-3 are written against probes of the installed tool.

## Tests as evidence

The version 1 unit tests pin many of the behaviours marked Kept: the order of text and tool events, usage arithmetic, rate-limit phrases, account environment. They are listed with what each pins in the [inventory](../research/v1-driver-inventory.md#12-tests-as-evidence) and are the starting point for this Driver's test cases. They ran against a scripted stand-in for the tool, written for version 2.1.81, so they show what version 1 expected, not what the installed tool does.

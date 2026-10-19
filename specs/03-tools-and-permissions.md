---
role: authored
spec: CLD-3
status: accepted
---
# Claude Driver · 03 Tools and permissions

How the Claude Driver meets [DRV-3](../../arbol/driver-contract/03-tools-and-permissions.md): how the `claude` tool is started so that the agent has every tool and everything the owner set up for `claude`, nothing of the tool is switched off but its memory, and nothing asks for permission; what a run without tools gets; and how a question from the agent travels to the caller and back. It matters because the tool's own starting mode differs by home and by model, and because a run in the wrong mode does not ask: it refuses calls silently.

Everything stated about the installed tool was observed on 5 October 2026 with `claude` 2.1.289 and is recorded in the [probe record](../research/tool-probes-2026-10-05.md).

## Scope

Covered: the arguments that give a run its tools, what a run has because nothing but memory is switched off, the owner's own setup of `claude`, the mode that asks for no permission, a request for permission that arrives nonetheless, questions from the agent, calls the tool refuses by itself, sub-agents.

Not covered: the contract (DRV-3); the rest of a run's arguments and its events (CLD-2).

## Behaviour

### Tools

| Run | Argument | The agent has |
|---|---|---|
| With tools | None that names a tool | Every tool the installed version offers with the owner's own setup, for the account and the model in use |
| Without tools | `--tools ""` | No tool |

For a run with tools the Driver passes neither `--tools`, nor `--allowedTools`, nor `--disallowedTools`.

Towards the caller `Bash` is named `shell`, in events and in the history (DRV-3.19). The Driver translates in both directions. Every other tool keeps its own name.

Observed with the installed tool: a new home offers 22 tools by default: `Task`, `Bash`, `CronCreate`, `CronDelete`, `CronList`, `DesignSync`, `Edit`, `EnterWorktree`, `ExitWorktree`, `ListAgents`, `NotebookEdit`, `Read`, `ReportFindings`, `ScheduleWakeup`, `SendMessage`, `Skill`, `TaskStop`, `ToolSearch`, `WebFetch`, `WebSearch`, `Workflow`, `Write`. The list grows with the login and the model: 32 on one model, 28 on another, 23 through z.ai. `AskUserQuestion` and the two plan-mode tools appear only when the stream is named as the place for permission questions. `--tools Bash,Read` leaves exactly those two, and an unknown name is dropped silently.

Observed in version 1: `--disallowedTools NotebookEdit,WebFetch,WebSearch,Task,TodoWrite` and no list of allowed tools. `TodoWrite` no longer exists.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._build_argv_native`

### Nothing is switched off but memory

The one part of the tool the Driver switches off is its own memory: every run gets `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` in its environment (DRV-3.25). The Driver passes no other argument and sets no other variable that switches a part of the tool off. Two switches of earlier drafts are gone: `--setting-sources ""` and `--strict-mcp-config`. A run with tools therefore has:

| Part of the tool | What it means in a run |
|---|---|
| The settings and the instruction file of the working folder | The tool reads them as it does for anyone who starts it in that folder |
| The MCP servers of the signed-in account | The services connected to the account are available to the agent |

Observed with the installed tool on 6 October 2026, with one real message each: in a folder holding a `CLAUDE.md` the agent knew what the file said; with `--setting-sources ""` it did not; in a folder holding only an `AGENTS.md` it knew that file. In a signed-in home the account's servers were listed 2.0 to 2.6 seconds after the start, three connected and two waiting for a sign-in. They load beside the run and do not hold it up. Observed on 5 October with the memory on: the agent wrote memory files into the home without asking, and in a later run a memory file was believed over the conversation.

### The owner's own setup

A run starts in the tool's default home, `~/.claude` (CLD-1.2), so it has everything the owner set up for `claude`, as when the owner starts the tool by hand (DRV-3.31, [DRV-D42](../../arbol/driver-contract/00-overview-and-boundary.md#the-vendor-tools-home)).

| What | Where the owner keeps it |
|---|---|
| Settings, among them hooks and permission rules | `~/.claude/settings.json` |
| Plug-ins | Installed and switched on in the owner's settings |
| Skills | `~/.claude/skills`, with the account's synced skills in its `synced` folder |
| MCP servers, with their sign-ins | The list `mcpServers` in `~/.claude.json` |
| Instruction file | `~/.claude/CLAUDE.md` and what it imports |

The Driver passes no argument for any of them, links or copies nothing, and changes nothing there. A run of any Subscription has the same setup; only the account differs (CLD-1). An MCP server that needs a sign-in uses the owner's sign-in of it, so a sign-in the owner made serves every run as well.

Observed until 19 October 2026: each Subscription had a home of its own, with links to the owner's user skills and `--mcp-config ~/.claude.json` on a run with tools, so a run had none of the owner's settings, hooks, plug-ins or instruction file, and an MCP server that needs a sign-in was signed in once for each home.

Observed with the installed tool on 6 October 2026: in a new home with that link the tool listed 40 of the owner's 41 skills, and wrote nothing into the linked folder. Given `~/.claude.json` as it stands, with its many other entries, the tool took the three servers listed there: one connected, one failed as it does in the owner's own folder, and one, which signs in through the browser, reported that it needs a sign-in.

### Nothing asks for permission

Every run gets `--permission-mode bypassPermissions`. The tool then carries out every call without a question: it reads and writes files, runs commands and uses the network as the owner's account can.

The mode is named on every run. It is never left to the owner's settings or to the home, because a new home starts in a mode named `auto`, and what that mode did differed by model.

A run with tools that has a control input also gets `--permission-prompt-tool stdio`. It is there for one reason: only with it does the tool offer the agent `AskUserQuestion` (below). It causes no permission question under `bypassPermissions`.

Observed with the installed tool under `bypassPermissions`, with the stream named as the place for questions: reading a file in the working folder, a shell command that creates a file there, and creating and changing a file there all ran without a question. The same mode without that argument, which a run without a control input gets, was not probed.

Observed in version 1: always the tool's ordinary mode, with the stream as the place for questions.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/protocol.py#build_argv`

### A request for permission that arrives nonetheless

None is expected. Should the tool write a `control_request` of subtype `can_use_tool` for anything but a question from the agent, the Driver answers it at once with a `control_response` naming the request's identifier, and emits a `notice`.

| The request | The Driver's answer |
|---|---|
| Names a tool call and carries its input | `behavior: "allow"`, with the input unchanged |
| Has an identifier but no usable tool name or input | `behavior: "deny"`, with a message saying so |
| Has no identifier | None is possible. The run fails, and no other run is affected |

Observed with the installed tool: a deny without a message is not an error of the stream. The call fails with a text about an invalid permission result and the run goes on, which is why every deny carries a message.

### Questions from the agent

The tool `AskUserQuestion` arrives as a `can_use_tool` request marked as needing the person. The Driver emits `ask_opened`: one entry per question of the tool's input, with its text as the identifier, its header, its options and whether several may be chosen. The caller's answer goes back as an allow whose input is the tool's input with the chosen labels added per question text. Each answer must name every question exactly once, choose at least one distinct offered label, and choose only one label where `multiSelect` is false. Claude receives a string per question: the label for a single choice, or the selected labels joined by `, ` for several choices. Duplicate answers to an answered ask are accepted without another response; withdrawn or unknown asks return `not_found`. A decline goes back as a deny that interrupts, which ends the run.

When the tool withdraws a question it writes `control_cancel_request`, and the Driver emits `ask_closed` as withdrawn.

A run without a control input gets no `--permission-prompt-tool`, so the tool does not offer `AskUserQuestion` at all and the agent cannot ask (DRV-3.30).

A sub-agent is not offered `AskUserQuestion`. Every question therefore comes from the agent itself, and `ask_opened` never carries a `parentCallId`.

Observed with the installed tool on 6 October 2026, one real run under `bypassPermissions` with the stream named as the place for questions: `AskUserQuestion` was among the 32 tools, the tool sent one `can_use_tool` request for it, marked `requires_user_interaction`, with the keys `header`, `multiSelect`, `options` and `question` per question, and the agent went on with the label that was given. A shell command later in the same run caused no request. Observed on 5 October under the tool's ordinary mode: the answer `allow` with `answers` added to the input was accepted, and the agent received the chosen label. A choice of several labels was not probed. After a deny that also interrupts, the run ends with a result whose reason is `aborted_tools`. An unanswered request stayed open for 40 seconds without any record from the tool. Observed on 6 October, one real run: a sub-agent that was told to ask the person answered that it had no such tool, and the tool sent no request.

Observed in version 1: the same path; `answers` was copied into the input on allow.

Historical evidence (frozen version 1; ordinary locators, not Source Refs):

- `arbol_deprecated_v1:drivers/claude/arbol_driver_claude/turn.py#TurnRunner.feed_permission`

### Calls the tool refuses by itself

The shell tool refuses some commands before it runs them, such as a bare long sleep put in the background. Such a call arrives as a tool result marked as an error. The Driver emits `tool_finished` as a failure with the tool's text, and nothing else.

### Sub-agents

The tool that starts a sub-agent is among the tools of every run with tools. In the signed-in test account it is named `Agent`; the list of a new home names `Task`. Sub-agents run inside the same `claude` process, and by default in the background: the agent does not wait for them.

| What happens | What the tool writes |
|---|---|
| The agent starts a sub-agent | An `assistant` record with a tool-use block for `Agent`, a `system` record `task_started` that names that call, and at once a tool result for the call that only says the sub-agent was launched |
| The agent has nothing more to do for now | Its text, then a `result` record, although the sub-agent still works |
| The sub-agent works | `assistant` and `user` records whose `parent_tool_use_id` is the identifier of the `Agent` call: thinking, tool calls, tool results, text. No stream events come for a sub-agent, so its text arrives in whole blocks |
| The sub-agent ends | `system` records `background_tasks_changed` with an empty list, `task_updated` and `task_notification` with the sub-agent's summary |
| The agent goes on | A second `system` record `init` for the same session, the agent's further records, and another `result` |

The Driver sets `parentCallId` from `parent_tool_use_id` on every event it builds from such a record, and keeps the text of such records out of the answer (DRV-3.24).

A `result` record therefore ends the run only when no background task is left. The Driver knows that from the `system` records of subtype `background_tasks_changed`, whose `tasks` list names the tasks still running. If the tool exits while the last list still names active tasks, the run fails rather than reporting completion. A task is a sub-agent (`task_type` `local_agent`) or a command the agent started with the shell tool's background option (`local_bash`), and the Driver waits for both. While tasks are left the Driver keeps the tool's input open and goes on reading, and it emits `finished` after the `result` record that leaves none (DRV-3.32).

Observed with the installed tool on 6 October 2026, one real run, repeated once: the order above. With the input closed after the first `result`, the tool went on by itself, wrote the second `result` and ended with status 0. The token counts of each `result` covered its own part; `total_cost_usd` ran on from the first to the second.

Observed the same day, further real runs. A stop while a background sub-agent worked ended it at once: `background_tasks_changed` with an empty list, `task_updated` with the status `killed`, `task_notification` with the status `stopped`, and no further `result`. A command of 12 seconds that the agent started with the background option appeared in the list with `task_type` `local_bash`; its `Bash` call ended at once. When the command had ended the tool wrote `task_notification` with the summary "Background command … completed (exit code 0)", a new `init` record, and a second `result` with what the agent said about it.

## Requirements

| ID | The Claude Driver must… | Refines | Origin | Verified by |
|---|---|---|---|---|
| CLD-3.12 | report a call the tool refused by itself as `tool_finished`, failed, with the tool's text | DRV-3.23 | Changed | Python: `C35`; historical TypeScript/probes: `C35` |
| CLD-3.14 | pass no argument that names, allows or forbids a tool for a run with tools, and `--tools ""` for a run without | DRV-3.20 | Changed | Python: `C35`, `test_runtime.RequestTests.test_typed_request_cli_replacement_labels_and_literal_prompt`; historical TypeScript/probes: `tools.arguments`, `C35`, `probe.tools` |
| CLD-3.15 | pass `--permission-mode bypassPermissions` on every run, and `--permission-prompt-tool stdio` only for a run with tools that has a control input | DRV-3.21, DRV-3.30 | Changed | Python: `C33`, `C35`, `test_runtime.RequestTests.test_typed_request_cli_replacement_labels_and_literal_prompt`; historical TypeScript/probes: `tools.arguments`, `C33`, `C35`, `probe.tools`, `live.tools` |
| CLD-3.16 | answer at once a `can_use_tool` request that is not a question from the agent, by the table above, with a message on every deny and a `notice`, and fail the run on a request without an identifier | DRV-3.22 | Changed | Python: `C25`; historical TypeScript/probes: `C25`, `tools.unexpected permissions` |
| CLD-3.17 | set `parentCallId` from `parent_tool_use_id` on every event built from a record that carries one, and keep the text of such records out of the answer | DRV-3.24 | New | Python: `C35`; historical TypeScript/probes: `C35`, `tools.recorded sub-agent envelopes`, `live.tools` |
| CLD-3.21 | treat a `result` record as the end of the run only when no background task is left, by the `tasks` list of the last `background_tasks_changed` record, and keep the tool's input open and go on reading until then | DRV-3.32 | New | Python: `C35`; historical TypeScript/probes: `C35`, `live.tools` |
| CLD-3.18 | switch the tool's own memory off with `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, and pass no other argument and set no other variable that switches a part of the tool off | DRV-3.25 | Changed | Python: `C35`; historical TypeScript/probes: `C35`, `probe.tools` |
| CLD-3.19 | carry `AskUserQuestion` to the caller as `ask_opened` and answer it through the answers added to the tool's input; decline through a deny that interrupts; emit `ask_closed` as withdrawn on `control_cancel_request` and refuse a later answer with `not_found` | DRV-3.26, DRV-3.28, DRV-3.29 | Kept | Python: `C36`, `test_runtime.ProtocolTests.test_questions_validate_answers_duplicate_ack_and_withdrawal`, `test_runtime.ProtocolTests.test_utf8_tool_result_cut_and_single_final_cleanup`; historical TypeScript/probes: `C36`, `tools.questions`, `tools.decline`, `tools.failed answer delivery`, `live.tools` |
| CLD-3.20 | give a run the owner's whole setup of `claude` by starting it in `~/.claude` alone: pass no `--mcp-config`, `--settings` or `--setting-sources`, and link, copy or change nothing of the owner's | DRV-3.31 | New | contract |

CLD-3.1 to CLD-3.11 and CLD-3.13 described tool sets, levels of asking and permission questions. They were withdrawn on 6 October 2026 with DRV-D12, and their numbers are not used again.

## Historical TypeScript implementation checks, 7 October 2026

`npm test` passes 68 tests. The shared suite passes 33 scenarios, including C9, C25, C33, C35, C36 and C37 for this chapter. `probe.tools` observed the installed Claude 2.1.289 in trusted mode, with the owner's user skills and MCP servers, no inference, and the entire owner tree unchanged. Two Haiku messages on `test-anthropic` passed `live.tools`: a carried and answered question, a file write and shell call without permission requests, sub-agent attribution with its text excluded, and completion of a background command. The final live owner snapshot was inconclusive because another Claude process was writing its own session log in `Artifacts/mycel`; that original snapshot failure is retained beside the successful behavior record. The separate zero-quota probe verified owner setup preservation. Account MCP sign-in stays out of scope. C35's idle-limit check belongs to SYL-85.

## Not established

- A stop while a sub-agent works is verified by `live.stopping` on 7 October 2026. A sub-agent question remains unavailable in the recorded tool version.
- An answer to a question that offers several choices, and several questions open at once.
- Which settings of a working folder the tool applies beyond its instruction file. Its hooks, its permission rules and its own list of MCP servers were not tried.
- What the owner's own setup does to a run the Driver started: a hook that blocks a call or asks, a permission rule, a setting that turns `bypassPermissions` off, a `model` or an `env` block in the settings. A hook that waits for a person can hold a run until the idle limit ends it.
- Which account's synced skills and connected services a run of a `zai` or a token Subscription has in `~/.claude`, where both belong to the owner's own sign-in.
- What a run meets outside its working folder under `bypassPermissions`. Reading and writing elsewhere were not probed in this mode.
- Which of the default tools are of use in a process that lives for one message. The tools for scheduled work and for worktrees are in the list; nothing was done with them.

## Known problems in version 1

Not to be reproduced.

- **A list of forbidden tools** that still named one that is gone, without anybody noticing.
- **The mode of a run was whatever the arguments happened to give.** It was pinned, but nothing recorded why; left to a new home, it would differ by model.
- **Nothing checked an answer** before it was written, and the installed tool turns a malformed one into a failed call the agent then works around.

## Historical TypeScript verification — SYL-87, 7 October 2026

All 38 shared conformance scenarios pass, with C5 checking an actual run, C7 covering output/state/argument redaction and C32 covering the command line and development checks. The Driver passes 81 automated tests and the suite passes 10 runner tests under Node 24.21. The compiled `dev probe` passes against installed Claude 2.1.289 without a prompt, including the existing test login; shapes-only evidence is `research/dev-probe-2026-10-07.json`. The compiled `dev build-check` passes with one tools-off Haiku message on `test-anthropic`, recorded in `research/dev-build-check-2026-10-07.json`. The six-turn live command is checked by `dev.live-check` against the stand-in and refuses missing, signed-out or exhausted accounts in `dev.gates` and C32. Its fresh six-turn vendor run was not requested; earlier task live records remain the evidence for the tool, question, background, continuity and stop behaviors. Anthropic preflight uses the timestamped cached usage, by CLD-D2. A first build-check attempt failed before inference because the clean child PATH omitted the discovered tool folder; that was fixed before the passing record. Numbered Builds remain SYL-76/SYL-93.

## SYL-95 Python migration verification, 7 October 2026

The implementation uses the pinned CPython 3.14.8 standalone runtime and Python standard-library transports. Package version 1.0.0, contract 1, format 1, CLI behavior, recorded fixture bytes and prior account/chat state remain compatible. The verified source commit is `2699d3839f69acf69c9e4926058ca027d407e9f1`. Source validation passes 35 Python unittest tests, strict mypy and Ruff; all 38 unchanged shared scenarios pass. The final artifact also passes its copied tests from a relocated folder whose path contains spaces. Exact source and Build provenance, runtime pin, packaged files and checksums are in [package-manifest.json](../research/python-migration-2026-10-07/package-manifest.json). The verification index and adjacent source/packaged test reports are in [verification.json](../research/python-migration-2026-10-07/verification.json). Historical TypeScript test identifiers and vendor observations are retained below and in the requirement table, with their original dates and scope.

The 12 mixed TypeScript/Python checks are recorded in [compatibility.json](../research/python-migration-2026-10-07/compatibility.json); they exercise both directions of state reuse, concurrent creation, native history continuation and peer stopping. The independent settings comparison is [migration.claude-settings-compatibility.json](../research/python-migration-2026-10-07/migration.claude-settings-compatibility.json). Actual vendor checks without inference are recorded in [no-prompt-probes.json](../research/python-migration-2026-10-07/no-prompt-probes.json), and the production Build5 gates are recorded in [numbered-build-5.txt](../research/python-migration-2026-10-07/numbered-build-5.txt).

Current tools and question coverage includes shared C9, C25, C33 and C35–C37. The named Python question test verifies rejected labels, one delivery for duplicate answers and withdrawal; finalization verifies a remaining question and tool call close once before the final event. Request tests preserve trusted mode and control-dependent permission arguments. Historical real tool/question/background records remain evidence for behavior observed with Claude 2.1.289; the migration does not claim a fresh six-message vendor run or new observations of account MCP sign-in.

The packaged no-prompt probe and account/catalog/usage checks use the existing test account and preserve owner configuration. The working production Build5 gate sent one Haiku message with tools disabled through dev build-check; its outcome, tool version, spending and the preceding Build records are preserved in the final verification evidence. The migration used two inference requests in total, one in Build4 and one in Build5. Deliberately failed Build6 spent no inference quota and left Build5 as the default. No new real vendor rate-limit, overload or oversized-context failure was intentionally produced. The six-message live command remains opt-in.

## Decisions

| ID | Question | Proposed default | Outcome |
|---|---|---|---|
| CLD-D9 | Which tools are standard? | `Bash`, `Read`, `Edit`, `Write`, `Glob`, `Grep`: what the agent needs to work in a repository, and nothing that reaches the network | Decided 6 October 2026 by the owner, against the proposed default: there is no standard set. The agent may use any tool of `claude` without restriction (SYL-59) |
| CLD-D10 | How is `read_only` realised? | `dontAsk` | Withdrawn 6 October 2026: only the trusted mode is built, so there is no `read_only` (SYL-60) |
| CLD-D14 | Which home supplies the owner's skills and MCP list? | The Driver's `HOME`, the same home that supplies its settings file | Superseded on 19 October 2026 by DRV-D42: no links and no MCP argument; a run has the owner's setup because it starts in `~/.claude`. Decided 7 October 2026 during SYL-84: use that home. Prepare the individual user-skill links whenever a Subscription home is created or used; replace old links atomically, remove stale links, preserve the tool's private synced directory, and refuse a conflicting ordinary skill entry. Omit user-skill links and the MCP argument when the source does not exist. A prior whole-directory link is replaced by a private directory without touching its target. The Driver never parses the owner's MCP file |
| CLD-D16 | Can the entire skills directory be linked to the owner's? | Link individual user-skill folders instead | Superseded on 19 October 2026 by DRV-D42: nothing is linked any more. Decided 7 October 2026 during SYL-84: no. The real test account already holds Claude-managed account skills under `skills/synced`. A whole-directory link risks mixing account sync into the owner's setup. Keep that folder private and expose the owner's custom user skills by individual links, so account features stay enabled and the owner's setup stays unchanged |
| CLD-D15 | How are several selected labels sent through Claude's string-valued answers? | Join them with `, ` | Decided 7 October 2026 during SYL-84: use that form, validate against the opened questions, and retain answered identifiers until the run ends so duplicate answers have no effect |
| CLD-D13 | Are the account's MCP servers and the tool's own memory switched on? | No, in the first release: both bring something into a run that is neither in the request nor in the saved conversation | Decided 6 October 2026 by the owner, against the proposed default: yes for the account's MCP servers. The tool's own memory stays off, as the owner said later that day (DRV-D26, SYL-71) |

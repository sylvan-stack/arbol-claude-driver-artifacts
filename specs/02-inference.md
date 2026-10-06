---
role: authored
spec: CLD-2
status: accepted
---
# Claude Driver · 02 Inference

How the Claude Driver meets [DRV-2](../../arbol/driver-contract/02-inference.md) with the `claude` command-line tool. Every run is one `claude` process, started in the Subscription's home, given one message over the tool's stream format, and ended when the tool has written its result. It matters because the installed tool behaves in ways version 1 never met: a new config folder starts in a mode of its own, closing the input does not stop a run, and commands the agent put in the background survive the tool.

Everything stated here about the installed tool was observed on 5 October 2026 with `claude` 2.1.289 and is recorded in the [probe record](../research/tool-probes-2026-10-05.md).

## Scope

Covered: the arguments and environment of a run, what is written to the tool, sessions and conversation continuity, the mapping from the tool's records to contract events, usage, ending and stopping a run, what differs on a z.ai Subscription.

Not covered: the contract (DRV-2); which tools the agent has, how the tool is kept from asking for permission, and the agent's questions (CLD-3); the mapping of failures to error codes, limit information and time limits (CLD-4).

## Behaviour

### Starting the tool

One process per run, with the request's working folder as its working directory and the environment of [CLD-1](01-subscriptions.md). The arguments:

| Argument | When | Why |
|---|---|---|
| `-p`, `--input-format stream-json`, `--output-format stream-json`, `--verbose` | Always | The stream format. Without `--verbose` the tool refuses to start |
| `--include-partial-messages` | Always | Pieces of text as they are produced |
| `--permission-mode bypassPermissions` | Always (CLD-3) | The mode in which the tool carries out every call without asking. It is named on every run, because a new home otherwise starts in a mode of its own |
| `--permission-prompt-tool stdio` | A run with tools that has a control input | Makes the tool offer the agent its question tool, `AskUserQuestion`, and send the question to the Driver (CLD-3) |
| `--mcp-config ~/.claude.json` | A run with tools, where the owner has that file | The owner's own MCP servers (CLD-3) |
| `--tools ""` | A run without tools | Leaves the agent no tool. A run with tools gets no argument about tools at all (CLD-3) |
| `--model`, `--effort` | When the request or the settings file names them | |
| `--append-system-prompt` | When the request has a system prompt | Adds the text to the tool's own prompt, which describes its tools |
| `--system-prompt-snapshot off` | Always | A conversation that is continued then follows the system prompt of the request at hand. As shipped, a continued conversation keeps the prompt it was started with |
| `--add-dir` | Once per additional folder | Further folders the agent is told to work in |
| `--session-id` or `--resume` | By continuity, below | |
| `--no-session-persistence` | A run without tools and without a working folder | Leaves no saved session |

Added to the environment of CLD-1: `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`; the two time limits for shell commands, `BASH_DEFAULT_TIMEOUT_MS=300000` and `BASH_MAX_TIMEOUT_MS=1800000`; the request's extra search-path folders appended to the search path; `CLAUDE_CODE_SHELL`, which names the shell of the Driver's own making described under "Ending and stopping a run".

The tool writes nothing until it has received the message. The Driver writes one line, the user record: the message's text as a text block followed by one image block per image. Every line the Driver writes is one complete JSON object; a line that is not JSON ends the tool.

Before the message the Driver sends one `get_settings` control request and compares the model and effort the tool reports as applied with the request. An effort the tool did not apply refuses the run with `invalid_input`, before anything is sent to the vendor. A model the vendor does not know cannot be seen this way: it fails the run at the first request, at no cost.

The request's `serviceTier` has no counterpart here: the tool's catalog lists no tiers, and a request that names one is refused with `invalid_input`.

Observed with the installed tool: `--permission-mode default` is accepted although the help text no longer lists it. `auto` mode with one model ran a file write, a file edit and a shell command that creates a file without any question. With auto memory on, the agent wrote memory files into the home without asking, and in a later run a memory file was believed over the conversation. An unknown effort is a warning on standard error and the default is used; on a model without effort levels the effort is dropped without a word.

Observed on 6 October 2026, the cost of one process for every run: the tool answered its first request 0.2 seconds after its start in an empty home and 0.5 to 1.0 seconds after it in a signed-in one. A real message had its first text 2.0 seconds after the start, and the vendor's own answer time was 1.5 of them. The owner accepted a start cost of about half a second per message on the same day.

Observed on 6 October 2026, real runs on one conversation: started as shipped, the continued conversation answered by the system prompt of its first run, both when the next run named another prompt and when it named none. Started with `--system-prompt-snapshot off` on every run, it answered by the prompt of the run at hand, and by none when none was given.

Observed in version 1: the same stream arguments without `-p`; `--permission-mode default` and `--permission-prompt-tool stdio`; five tools disallowed by name, one of which no longer exists; auto memory off; the same two time limits. No `--strict-mcp-config`, and no check of what the tool applied.

<!-- sources:
arbol:drivers/claude/arbol_driver_claude/protocol.py#build_argv
arbol:drivers/claude/arbol_driver_claude/turn.py#_env_overrides_for
arbol:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._run_native
-->

### Sessions and continuity

| Continuity | What the Driver does |
|---|---|
| `fresh` | Starts with `--session-id` and a new random identifier |
| `resumed` | Starts with `--resume` and the session the Driver's map names |
| `rebuilt` | Writes a session file for a new identifier from the request's history, then starts with `--resume` and that identifier |

A *session* in this specification is the `claude` tool's own saved conversation, kept in the Subscription's home. The Driver keeps none of its own (DRV-2). The Driver's map (DRV-2) names, for a chat session and a Subscription, the tool's session and what it covers. An entry is written after a completed run that saved its session, and removed when a run on that session ends any other way. The Driver resumes when every check of DRV-6 holds; otherwise it rebuilds, with the reason in `started`.

A rebuilt session file has one line per earlier message: the role, the content as blocks (text, and images for a user message), an identifier of its own, the identifier of the line before it, a timestamp later than the one before it and earlier than now, the session identifier, and the working folder. A tool call of the history becomes two lines: an assistant line with a tool-use block that holds the call's name and input, and a user line with a tool-result block that holds its result. A `shell` call is written as a `Bash` block with the command as its input. Any other tool call that the other Driver reported is written the same way, under the name it was reported with. When the tool does not accept such a file, the Driver starts a fresh session instead and sends the earlier messages as one labelled text before the new message, with a `notice` saying so.

The tool keeps a session in the home under a folder named after the working folder: the folder's real path with every character that is not a letter or a digit replaced by `-`.

Observed with the installed tool: a second process started with `--resume` knew a word given in the first run and the command the first run had executed. Resuming also worked from another working folder. A session identifier that already exists is refused for `--session-id`. A hand-written two-line session file was accepted and the model answered from it. On 6 October 2026 so was a hand-written file that held a tool call and its result as tool-use and tool-result blocks: in one real turn the model answered with a value that stood only in that result. A second file held a picture in a user line and a tool call under a name the run has no tool for (`shell`, as the Codex Driver reports it): the model named the picture's colour and the call's result. Session files hold account-related data of the tool's own. A path whose encoded form exceeds 200 characters is cut and given a suffix the probe could not derive.

Observed in version 1: a first message got a new random identifier each time. Before every follow-up the session file was overwritten with one rebuilt from Arbol's history, text only, and resumed under the chat's identifier, so whatever the tool had recorded of its own tool calls was lost. The folder name was derived by replacing only `/` and spaces, which the installed tool no longer matches for other characters.

<!-- sources:
arbol:drivers/claude/arbol_driver_claude/jsonl.py#history_to_jsonl_lines
arbol:drivers/claude/arbol_driver_claude/jsonl.py#encode_cwd
arbol:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._run_native
-->

### Building a session from a history

A rebuilt session is a file the Driver writes before it starts the tool: `projects/<folder name>/<session identifier>.jsonl` in the Subscription's home, under a new random identifier. The folder name is the working folder's real path with every character that is not a letter or a digit replaced by `-`. Each line is one JSON object:

| Key | Value |
|---|---|
| `type` | `user` or `assistant` |
| `message` | `{ role, content }`: the role equals `type`, and the content is a list of blocks |
| `uuid` | A new random identifier for the line |
| `parentUuid` | The `uuid` of the line before; `null` on the first line |
| `timestamp` | A time in UTC. The lines are one second apart, and the last one lies one minute before the file is written |
| `sessionId` | The session identifier |
| `cwd` | The working folder's real path |
| `isSidechain` | `false` |
| `userType` | `external` |
| `version` | `synthetic-arbol` |

The items of the history become lines in their order, one line per block:

| History item | Lines |
|---|---|
| A message of the user | One `user` line: a `text` block with the message's text, then one `image` block per picture, with a `source` of type `base64` that holds the picture's media type and data |
| A message of the assistant | One `assistant` line with one `text` block |
| A tool call | An `assistant` line with one `tool_use` block (`id`, `name`, `input`), then a `user` line with one `tool_result` block (`tool_use_id`, `content`, and `is_error: true` when the call failed) |

For a tool call:

- The Driver makes the identifier up: `toolu_` followed by 24 random letters and digits, the same in both blocks.
- A `shell` call is written under the name `Bash`, with `{ "command": … }` as its input. A folder the call named is left out, because `Bash` takes none.
- Every other call keeps the name and the input it was reported with.
- `content` is the result as text, by the rule of DRV-2.

The run is then started with `--resume` and the new identifier, and the tool appends its own lines to the file.

Two cases end in the text form of DRV-2 instead:

- The folder name is longer than 200 characters. The tool shortens such a name in a way that has not been established. The Driver then writes the file into the folder the tool has already made for that working folder, the one whose name begins with the same 200 characters, and where there is none yet it uses the text form for this run.
- The tool refuses the file: the start with `--resume` ends with a `result` whose error says that no conversation was found. The Driver starts the tool once more, with a fresh session and the text form.

The tool still has a session, for the check of DRV-6, when a file named after it exists in any folder under `projects`.

### From records to events

| The tool writes | The Driver emits |
|---|---|
| `system` / `init` | `started`, with the continuity, the model and the tool's version the record names. The session identifier is kept for the map |
| `stream_event` with a text delta | `text_delta` |
| `stream_event` with a thinking delta that has text | `thinking_delta` |
| `assistant` with a text block | `text` with the block's whole text. A block cut by a stop is emitted as it stands |
| `assistant` with a thinking block that has text | `thinking` |
| `assistant` with a tool-use block | `tool_started`: the block's identifier, tool name and input. A `Bash` block is shown as `shell` with its command (DRV-3.19); the tool states no folder per call |
| `assistant` carrying an error code | Nothing. The record's text is the tool's error message, not an answer; code and text go to the final event (CLD-4) |
| `user` with a tool result | `tool_finished` for the call it names: failure when the result is marked as an error or the tool did not run; the content is the result, for `shell` as its `output` |
| Any of the records above with `parent_tool_use_id` set | The same event with `parentCallId` set to that identifier: it reports what a sub-agent did. Its text is no part of the answer (CLD-3) |
| `control_request` asking to use the tool `AskUserQuestion` | `ask_opened` (CLD-3) |
| Any other `control_request` asking to use a tool | Not expected, since nothing asks for permission. Approved at once as CLD-3 says, with a `notice` |
| `control_cancel_request` | `ask_closed`, withdrawn |
| `system` / `api_retry` | `notice` with the attempt and the reason |
| `rate_limit_event` | Nothing in the stream. Its content becomes the Subscription's usage report (CLD-4) |
| `result` without the error flag | `usage`, then `finished` with outcome `completed`, unless a background task is left: then `usage` only, and the run goes on (CLD-3) |
| `result` with the error flag | `usage`, then `finished` with outcome `failed`; `cancelled` when the caller asked for the stop |
| The process ends without a `result` | `finished` with outcome `failed`, naming the exit status and the end of standard error |
| `system` / `background_tasks_changed` | Nothing in the stream. Its list of tasks tells the Driver whether a `result` ends the run (CLD-3) |
| `system` records of other subtypes, among them those about a sub-agent's task, and stream events that open, close or sign a block | Nothing |

The tool writes one `assistant` record per block, before that block is closed in the stream, so a text block is emitted before the tool call that follows it. A control request of a kind the Driver does not know is answered with an error, never left open. A record the Driver cannot use, such as a control request without an identifier, fails that run and no other.

Observed with the installed tool: a failed run is marked by the error flag of the `result` record and by exit code 1. Its subtype is no guide: a missing login and an unknown model both end with subtype `success`. On an Anthropic Subscription the thinking text is empty; on z.ai it is streamed in full. After its `result` the tool keeps running until its input is closed.

Observed in version 1: a tool call was emitted when its block closed, with the input rebuilt from the pieces of the stream. Whole blocks were used only when no piece had been seen in the turn, which dropped later text that arrived whole. Control requests of other kinds were ignored, and one malformed question disabled the Driver for every chat until restart.

<!-- sources:
arbol:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._handle_stream_record
arbol:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._run_native
-->

### Usage

Final usage comes from the `result` record: input tokens are the sum of plain, cache-read and cache-written input; cached input is the cache-read count; output and thinking tokens as given; the model is the one named in the record's per-model usage. Before that, the Driver emits a `usage` event after each request to the model, adding up what the stream reports per request. The `result` record's figures replace those sums.

Cost is reported when the tool states it at list prices, and left out when the tool marks its basis as unknown.

Observed with the installed tool: the `assistant` records carry placeholder token counts; the real counts per request are in the stream's message events, and the `result` total equalled their sum over four requests. Through z.ai the tool reported a cost for a model it does not know, with the basis `unknown`.

Observed in version 1: usage was taken from the `result` record with the same arithmetic for input. Counts from intermediate `assistant` records filled gaps and could count the same tokens twice.

<!-- sources:
arbol:drivers/claude/arbol_driver_claude/protocol.py#extract_usage
arbol:drivers/claude/arbol_driver_claude/protocol.py#assistant_usage
-->

### Ending and stopping a run

When a `result` record has arrived that leaves no background task (CLD-3), the Driver closes the tool's input and waits for it to exit, for 2 seconds; a tool that has not exited is ended by signal.

Stopping:

| Step | Action | Limit |
|---|---|---|
| 1 | Write an `interrupt` control request | |
| 2 | Wait for the `result` record, or for the answer to the request where the agent's own part had already ended and only background tasks were left. Then close the input and wait for the exit | 2 seconds in all |
| 3 | End the tool by signal | Whatever remains of the 15 seconds of DRV-2.16 |

Closing the input is not a way to stop a run: the tool then fails the open question and lets the model continue. The input is closed only after the `result` record has arrived.

A stop ends a background sub-agent with the request, and a command the agent started with the tool's background option at the latest when the tool exits: the tool ends such a command itself.

After the tool has exited, on every path, the Driver ends what the agent's shell commands left behind. The tool starts every shell command as the leader of a process group of its own, and a process that a command leaves in the background stays in that group when the command and the tool have ended. To know those groups, the Driver gives the tool a shell of its own making: a small script in the run's folder, named like the shell it stands for, that appends its own process number and the time to a file beside it, sets `SHELL` back to the real shell, and then becomes that shell. `CLAUDE_CODE_SHELL` names the script. The real shell is the `SHELL` of the Driver's environment where that is `zsh` or `bash`, and `/bin/zsh` otherwise. After the exit the Driver signals every noted group, first to terminate and after 2 seconds to kill. A group whose number now belongs to a process that started after the note is left alone, because the system has given that number to something else.

A process that left its group, by taking a process group or a session of its own, is not found this way and stays (DRV-D33).

Observed with the installed tool: an `interrupt` is answered within milliseconds, a pending question is withdrawn, and a `result` follows at once, with the part of the text produced so far in an `assistant` record. A termination signal gives exit code 143 and no `result`. Each shell command runs in a process group of its own, apart from the tool's. A command put in the background was still running after a normal end and after a termination signal, with the system's first process as its parent.

Observed on 6 October 2026, real runs: every shell call was the leader of a session and of a process group of its own. A process left behind with `nohup … &` stayed in that group after the tool had exited, and a signal to the group ended it. A script named through `CLAUDE_CODE_SHELL` ran once for every shell call, three times in a run with one command, and the command saw the script's path as `SHELL`. A command started with the tool's own background option was ended by the tool when its input closed. On this macOS the list of processes does not show a process's session and `pgrep` cannot select by session, which is why the Driver goes by groups. A stop that arrived while only a background sub-agent was left was answered at once: the tool reported the task as killed, wrote no further `result`, and exited with status 0 when its input was closed.

Observed in version 1: stop ended the processes without asking the tool. The tool ran under a launch job of its own so that every process it had started could be found and ended.

<!-- sources:
arbol:drivers/claude/arbol_driver_claude/turn.py#TurnRunner.cancel
arbol:daemons/shared/arbol_shared/native_domain.py#launch
-->

### On a z.ai Subscription

The same arguments and records apply. What differs: a model is named by its GLM identifier or by one of the tool's names that the Subscription's model map points at a GLM model; the model a record names can lack a suffix the request carried; no limit information arrives in the stream; the tool's cost figure is an estimate and is left out; tool-call identifiers have another form. The tool warns on standard error that it does not recognise the model; the warning has no effect.

Observed with the installed tool: a plain run and a run with tools worked in a new, empty home with the z.ai values in the environment and no settings file, which is the design of CLD-1.

## Requirements

| ID | The Claude Driver must… | Refines | Origin | Verified by |
|---|---|---|---|---|
| CLD-2.1 | carry out a run as one `claude` process with the stream arguments, in the Subscription's home and the request's working folder, and start the tool a second time within a run only when its first start was refused for the conversation it was to continue (CLD-2.10, CLD-2.11) | DRV-2.21 | Kept | `C10`, `C18`, `C14` |
| CLD-2.3 | pass `--permission-mode bypassPermissions` on every run, whatever mode the home would start in | DRV-3.21 | Changed | `probe.run-settings`, `C10` |
| CLD-2.4 | switch the tool's auto memory off for every run | DRV-3.25 | Kept | `probe.run-settings`, `run.images` |
| CLD-2.5 | pass the request's system prompt with `--append-system-prompt` and add no text of its own | DRV-2.1 | Changed | `run.request`, `C10` |
| CLD-2.6 | read what the tool applied with `get_settings` before sending the message, and refuse the run when the effort differs from the request | DRV-2.2 | New | `C40`, `probe.run-settings` |
| CLD-2.7 | refuse a request whose working folder or additional folder does not exist, since the tool accepts a missing folder silently | DRV-2.2 | New | `run.validation`, `C40` |
| CLD-2.8 | write only complete JSON objects, one per line, to the tool | DRV-2.3 | New | `run.images`, `run.protocol` |
| CLD-2.9 | start a fresh conversation under a new random session identifier and never reuse one | DRV-2.12 | Kept | `C10`, `C14` |
| CLD-2.10 | resume a session only when its file is in the Subscription's home and no other run in progress uses it, and rebuild otherwise | DRV-2.12 | Changed | `C14`, `continuity.concurrent`; live verification pending renewed test-anthropic sign-in |
| CLD-2.11 | rebuild by writing a session file from the request's history, with its tool calls as tool-use and tool-result blocks and its images as image blocks, and fall back to a fresh session with the earlier messages as one labelled text when the tool does not accept the file | DRV-2.11 | Changed | `C14`, `continuity.session`, `probe.continuity` |
| CLD-2.12 | derive the session folder from the working folder's real path by replacing every character that is not a letter or a digit with `-` | DRV-2.11 | Changed | `continuity.session`, `continuity.long-folder`, `probe.continuity` |
| CLD-2.13 | map the tool's records to events by the table above | DRV-2.3 | Changed | `run.protocol`, `C10`, `C11`, `C12`, `C13`, `C42` (fresh records); questions and background tasks pending SYL-84 |
| CLD-2.14 | emit `text`, `thinking` and `tool_started` from the tool's whole-block records | DRV-2.4 | Changed | `C10`, `C11`, `run.protocol` |
| CLD-2.15 | decide `completed` or `failed` by the error flag of the `result` record, never by its subtype or its wording | DRV-2.7 | Changed | `C12`, `live.run` (completed results); failure envelopes recorded in `tool-probes-2026-10-05.md` |
| CLD-2.16 | answer a control request of an unknown kind with an error | DRV-2.3 | Changed | `run.protocol` |
| CLD-2.17 | fail only the run in which a record it cannot use arrived | CLD-0.5 | Changed | `C18`, `run.protocol` |
| CLD-2.18 | take final usage from the `result` records, the token counts added up over them and the cost from the last one, and report cost only when the tool states it at list prices | DRV-2.15 | Changed | `run.usage`, `run.zai`, `C13`, `live.run` |
| CLD-2.19 | close the tool's input after the `result` record that leaves no background task, and end the tool by signal when it has not exited after 2 seconds | DRV-2.19 | Changed | contract |
| CLD-2.20 | stop a run with the `interrupt` control request, and never by closing the input | DRV-2.16 | Changed | contract, probe |
| CLD-2.21 | give the tool, through `CLAUDE_CODE_SHELL`, a shell of the Driver's own making that notes every shell call, and after the tool has exited end every process still in the process group of a noted call, leaving alone a group whose number a later process has taken | DRV-2.19 | Changed | contract, probe |
| CLD-2.22 | run a request without tools with `--tools ""`, and without a working folder also with `--no-session-persistence` in an empty folder of its own, removing a session file it wrote for such a run when the run ends | DRV-2.20 | Changed | `probe.run-settings`, `C19`, `live.run`, `C14` |
| CLD-2.23 | send images as image blocks of the user record, and of the earlier user messages in a rebuilt session | DRV-2.23 | Kept | `run.validation`, `run.images`, `C14`, `continuity.session` |
| CLD-2.24 | write a rebuilt session file with the keys, the order of lines, the made-up call identifiers and the result texts stated above, and use the text form of DRV-2 where no file can be written or the tool refuses it | DRV-2.36 | New | `continuity.session`, `continuity.results`, `continuity.unwritable-session`, `C14`, `probe.continuity` |
| CLD-2.25 | pass `--system-prompt-snapshot off` on every run, and continue a saved conversation also when the request's system prompt is not the one it was last run with | DRV-2.1 | New | `C14`, `probe.run-settings`; live verification pending renewed test-anthropic sign-in |

CLD-2.2 switched off the settings of the working folder and the account's MCP servers. It was withdrawn on 6 October 2026 with DRV-D26, and its number is not used again.

## Not established

- A process that takes a process group of its own inside a shell call. The checks left one in the call's own group and one that had been started with the tool's background option.
- How long a system prompt may be as an argument, and whether a file variant of the argument exists.
- A failed tool call (`is_error`) and a result written as JSON text in a hand-written session file. The checks used plain text results.
- How the tool names the session folder of a working folder whose encoded path exceeds 200 characters. Until known, such a folder cannot be rebuilt by session file and falls back to the labelled text.
- Two runs resuming one session at the same moment.
- A second message to the same process after its `result`.
- What a rate-limited or overloaded run looks like. None occurred.

## Known problems in version 1

Not to be reproduced. The legacy map in [CLD-0](00-overview-and-legacy-map.md) lists them by part; those that concern a run:

- **A failure could end as a completed turn.** Only wording about rate limits or authentication made a result a failure, and only for two subtypes. The installed tool reports a missing login and an unknown model under the subtype `success`.
- **The agent forgot its tool calls between messages**, because the session was rewritten as text before every follow-up.
- **A turn could wait forever** on a control request the Driver did not answer.
- **One malformed question disabled every later turn** until the Driver was restarted.
- **Later text could be lost** when part of a turn was streamed and a later block arrived whole.

<!-- sources:
arbol:drivers/claude/arbol_driver_claude/rate_limit.py#is_rate_limit_signal
arbol:drivers/claude/arbol_driver_claude/turn.py#TurnRunner._run_native
arbol:product-spec/03-turn-execution.md#Known problems and lessons
-->

## Decisions

| ID | Question | Proposed default | Outcome |
|---|---|---|---|
| CLD-D5 | System prompt added to the tool's own, or replacing it? | Added. Replacing saves about 1,900 input tokens per request and removes the tool's own guidance for its tools | Decided 6 October 2026 by the owner: added. The agent gets the tool's own instructions and Arbol's (SYL-56) |
| CLD-D6 | Is the tool's cost figure reported on an Anthropic Subscription? | Yes, as the tool states it: the price at list rates, which is not what a Subscription is charged | Decided 6 October 2026 by the owner: yes (SYL-57) |
| CLD-D7 | How long are saved sessions kept in a Subscription's home? | 30 days after their last run, removed at the start of a later run. A removed session only costs a rebuild | Decided 6 October 2026 by the owner, against the proposed default: a Driver never removes a saved session. Cleaning up is a feature of Arbol, and how Arbol reaches these files is settled with that feature (SYL-58). The one-off run of DRV-D11 belongs to no chat: the tool saves no session for it, and a session file the Driver wrote for it is removed when the run ends |
| CLD-D10 | How is continuity recorded and a refused resume retried? | Hash and count complete main-agent text blocks as they are emitted, without retaining reply text. Reserve a conversation together with the run record under the Subscription lock. Retry at most once, using a fresh identifier and the labelled text form, only after a resume is refused as a missing conversation before answer text or tool calls; other errors never restart the tool. A refusal may arrive as a result or on standard error before the stream begins. Emit one started event for the successful start and a notice for the text form | Decided 7 October 2026 during SYL-82, a technical choice |
| CLD-D9 | How are fresh requests validated and streamed? | Read JSON once, apply command-line replacements, then validate before starting inference. Keep the run record by atomic exclusive creation. Consume records in order and await output backpressure. A tool result larger than 200 KiB becomes a UTF-8 prefix of its text or JSON representation with `truncated: true`; smaller structured results keep their shape | Decided 6 October 2026 during SYL-80, a technical choice |
| CLD-D8 | How is a conversation rebuilt? | By a session file written from the history, as version 1 did and the installed tool still accepts, with the labelled text as the fallback | Decided 6 October 2026 by the owner: the Driver writes the session file. Confirmed with the installed tool, tool calls and pictures included |

---
role: authored
spec: CLD-1
status: accepted
---
# Claude Driver · 01 Subscriptions

How the Claude Driver meets [DRV-1](../../arbol/driver-contract/01-subscriptions.md) with the `claude` command-line tool. It serves two vendor families through that one tool: Anthropic accounts, and z.ai accounts that reach z.ai's Anthropic-compatible gateway with a static key. It matters because both families share a transport and nothing else: a z.ai turn that picks up an Anthropic login, or the reverse, bills the wrong vendor and sends repository content to a vendor that may be forbidden for it.

## Scope

Covered: the two families and their settings, the home and environment each Subscription gives the vendor tool, sign-in and sign-out per family, status checks, usage, model catalogs, taking over the existing `claude-zai` setup.

Not covered: the contract itself (DRV-1); arguments, input and output of an inference run (CLD-2); recognising a rate limit or a rejected credential in the output of a run (CLD-4).

## Behaviour

### Families

| Family | Vendor | Sign-in | Reaches the vendor through |
|---|---|---|---|
| `anthropic` | Anthropic | The vendor tool's own login | The tool's default address |
| `zai` | Z.AI | A static key | The gateway address in the Subscription's settings, by default `https://api.z.ai/api/anthropic` |

Settings of a `zai` Subscription, none of them secret. They are written in the Driver's settings file, `~/.arbol/arbol-claude-driver.json`, under the Subscription's `settings` (DRV-0):

| Setting | Meaning | Default |
|---|---|---|
| `baseUrl` | Gateway address. Must be an http or https address | `https://api.z.ai/api/anthropic` |
| `modelMap` | Which gateway model stands in for the tool's `haiku`, `sonnet` and `opus` names, which the tool also uses for its own background requests | Empty: the gateway decides |
| `toolEnvironment` | Tuning variables for the tool. Only names on the Driver's allow-list are accepted | Empty |

An `anthropic` Subscription has no settings.

The Driver has two Subscriptions from the start, `anthropic` and `zai`. `anthropic` is the default: a run that names no Subscription uses it, unless the Driver's settings file names another (DRV-0).

Observed in version 1: one built-in Anthropic account and one built-in z.ai account. The z.ai route was a Claude-transport route whose settings carried the gateway address; the key was stored like any other credential.

<!-- sources:
arbol:daemons/core/arbol_core/subscriptions.py#DEFAULT_SUBSCRIPTIONS
arbol:daemons/core/arbol_core/subscriptions.py#seed_default_ip_bindings
arbol:product-spec/05-intelligence-providers.md#Concept model
-->

### The existing `claude-zai` setup

Observed on the owner's machine on 5 October 2026. The shell alias `claude-zai` runs the tool with `CLAUDE_CONFIG_DIR` set to `~/.claude` and with `--settings ~/.claude/settings-zai.json`. That file's environment block holds the gateway address, the z.ai key in plain text, three model-name variables (`ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`) and three tuning variables (`API_TIMEOUT_MS`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`). Plain `claude` uses the default folder `~/.claude` and the owner's Anthropic login stored for it. The separate `~/.claude-anthropic` profile that version 1 looked for is retired: the folder is gone, while the Keychain still holds the login once made for it.

A Driver cannot use the alias: an alias exists only inside an interactive shell, and a program that starts another program never sees it. Version 1 met the same limit and rebuilt the alias by hand: profile folder `~/.claude` for a gateway route, the settings file added only when the gateway host was exactly `api.z.ai` and the file existed, the key placed in the environment.

Proposed: the alias is replaced by a `zai` Subscription. The key moves into the Keychain; the gateway address, the model names and the tuning variables become the Subscription's settings; the Driver sets them in the environment of each child process. No settings file is read when a turn runs, so a turn does not change when that file is edited, and the alias keeps working for the Leather Bag's own terminal sessions. A one-time import command, `subscriptions import <id> --from <file>`, reads the existing file and writes those settings into the Driver's settings file. It stores the key in the Subscription's Keychain item by handing the `security` program its instruction on standard input, so that the key is never an argument of any program.

<!-- sources:
arbol:daemons/shared/arbol_shared/claude_cli.py#config_dir
arbol:daemons/shared/arbol_shared/claude_cli.py#alias_args
arbol:product-spec/05-intelligence-providers.md#Account profiles for the Claude tool
-->

### Home and environment

Every Subscription has a folder of its own in the Driver's state directory. The Driver passes it to the tool as `CLAUDE_CONFIG_DIR` for every child process it starts for that Subscription: status checks, catalog requests, runs. The tool keeps its configuration, and for an `anthropic` Subscription its login, relative to that folder.

The environment of a child process is built in this order:

1. Start from an allow-list of inherited variables: home, path, user, locale, temporary directory, proxy and certificate settings. Nothing named `ANTHROPIC_*`, `CLAUDE_*` or `CLAUDECODE` is inherited.
2. Set `CLAUDE_CONFIG_DIR` to the Subscription's home.
3. Apply the account. For `anthropic`: nothing more, the tool finds its login in the home. For `zai`: `ANTHROPIC_BASE_URL` from `baseUrl`, `ANTHROPIC_AUTH_TOKEN` with the key read at that moment from the Keychain, or from the owner's command where the settings file names one (DRV-0), the three model-name variables from `modelMap`, and the variables of `toolEnvironment`.

Observed in version 1: the environment was the service's own environment minus `ANTHROPIC_*` and five named variables, with the token then applied as `CLAUDE_CODE_OAUTH_TOKEN` for an Anthropic route, or as gateway address plus `ANTHROPIC_AUTH_TOKEN` for a gateway route. The profile folder was shared: `~/.claude-anthropic` when it existed, otherwise `~/.claude`, for Anthropic; `~/.claude` for a gateway.

<!-- sources:
arbol:daemons/shared/arbol_shared/claude_cli.py#environment
arbol:drivers/claude/arbol_driver_claude/turn.py#_env_overrides_for
-->

### Signing in and out

**`anthropic`.** Proposed, and decided as [CLD-D1](#decisions): the Driver runs the tool's own commands inside the Subscription's home, with the clean environment of CLD-1.3: `claude auth login --claudeai` to sign in, `claude auth status --json` to read the result, `claude auth logout` to sign out. The Driver never sees the credential and does not renew it; the tool does. The Driver starts the login with the variable `BROWSER` set to a command of its own. The tool then hands the sign-in address to that command instead of opening the system browser, and the Driver returns it to the caller as `open_url`: the page is shown in the caller's window, as in version 1. That address ends at a listener the tool itself opens on `localhost`. The tool also prints a second form of the address, which ends on a vendor page that shows a code. Where the caller's window cannot reach the listener, the caller starts the sign-in with `--by-code` (DRV-1): the Driver returns that second form, then `enter_code`, and writes the code to the tool.

The command behind `BROWSER` is a small program that the Driver writes into a folder of the sign-in, under `tmp` in its state directory, when the attempt starts, and removes with the attempt. It does one thing: it writes the address it is given into a file in that folder. The `sign-in` command waits for that file and returns the address as `open_url`. It then waits for the tool's login command to end. When that command ends with status 0, the Driver reads the account with `claude auth status --json` and returns `done`. When it ends with another status, or the five minutes pass, the step is `failed`.

The host list of `open_url` is `claude.com`, `claude.ai`, `platform.claude.com`, and `localhost` for the return to the tool's listener.

Observed on 6 October 2026, in one real sign-in by the owner, done with these steps by hand in a browser window that was not the system browser: the tool handed its address to the `BROWSER` command and opened no browser. The page went from `claude.com` to `claude.ai`, returned to the tool's listener on `localhost` and ended on `platform.claude.com`. The login command printed "Login successful." and ended with status 0, and `claude auth status --json` then reported the login, the method `claude.ai` and the plan. The tool had also printed a prompt for a pasted code, and did not need one.

The vendor's published terms for the tool, read on 5 October 2026, require that sign-in to a Claude account completes through the vendor's own flow. They do not permit another application to offer that login or to collect and store its tokens, and they name signing in to the unmodified tool with one's own subscription as permitted. This proposal stays within that. Version 1's own authorisation did not.

Observed in version 1: Arbol implemented the authorisation itself with the vendor tool's public client identifier, an Arbol-owned window, a callback listener on the local machine, its own code exchange and its own renewal, and stored the result in its own Keychain item. That implementation is not carried over.

**`zai`.** The step is `store_secret`. It names the Subscription's Keychain item: the service of CLD-1.10, with the Subscription's identifier as the account. The caller stores the key there, or the owner does so by hand; the Driver is never handed the key. It reads the key from the item with the system's `security` command (DRV-D4), checks its form (DRV-1.4), then checks it against z.ai's quota address. If z.ai rejects it, the Driver removes it from the item and the step is `failed`. If z.ai accepts it, or cannot be reached, the key stays and the Subscription is `signed_in`; an unreachable vendor leaves `checkedAt` empty. Replacing a key is a new sign-in. Signing out deletes the Keychain item. A static key has no renewal: when z.ai rejects it later, the Subscription moves to `needs_attention` with the remedy "replace the key". Where the settings file names a command as the source of the key, there is no step: the Driver takes the key from the command, checks it in the same way, and fails the sign-in when z.ai rejects it.

Observed in version 1: the key was stored without contacting z.ai. A later rejection read "z.ai rejected the API key … re-paste the key using Replace key".

<!-- sources:
arbol:daemons/shared/arbol_shared/subscription_oauth.py
arbol:daemons/core/arbol_core/subscription_login.py#start_login
arbol:daemons/core/arbol_core/subscription_login.py#logout
arbol:daemons/core/arbol_core/rpc/subscription.py#_set_token
arbol:daemons/core/arbol_core/zai_usage.py#fetch_raw
-->

### Status check

`check` contacts the vendor without inference. For `anthropic` it runs `claude auth status --json` in the home and reads whether the tool is logged in, by which method, and the account details the tool reports. For `zai` it calls the quota address with the key: accepted means `signed_in`, a 401 or 403 means `needs_attention`, anything else leaves the state as it was and reports `vendor_unavailable`.

Observed in version 1: the accounts page's Test performed a usage read for Anthropic and a live quota call for z.ai.

<!-- sources:
arbol:product-spec/05-intelligence-providers.md#Intelligence Provider settings
-->

### Usage

**`zai`.** One request to `https://api.z.ai/api/monitor/usage/quota/limit` with the key. The address is undocumented; its shape was taken from the vendor's own console. The answer is turned into a usage report by these rules, all carried over:

| Rule | Detail |
|---|---|
| Which entries count | Entries of type `TOKENS_LIMIT`, `CREDIT_LIMIT` and `TIME_LIMIT` that carry a percentage. Others are ignored |
| Window length | `number` × the unit: 1 = days, 3 = hours, 5 = minutes, 6 = weeks |
| Kinds | Token and credit entries are plan windows, sorted by length: the shortest is `session`, any other `weekly`; a single one is `session`. A `TIME_LIMIT` entry is `other`, labelled "MCP" |
| Labels | 300 minutes: "5-hour window". 10,080 minutes: "Weekly window". Otherwise "*n* *unit*s window", or "Usage window" when the length is unknown |
| Percentage | When the entry has a total and either a remaining or a current count, the percentage is computed from the counts; otherwise the vendor's percentage is used. Clamped to 0–100, one decimal |
| Reset time | `nextResetTime`. For a 300-minute plan window a reset more than 5 hours and 1 minute ahead is dropped, because the vendor at times reports it in another time zone |
| Plan | The first non-empty of `planName`, `plan`, `plan_type`, `packageName`, `level` |
| Per-model totals | Summed across entries by model code, largest first, returned in `extra` |
| Failures | 401 or 403: the credential is rejected. Another status, an unreadable answer or `success` not true: outcome `unavailable` with the vendor's message, at most 240 characters |

The request is a `GET` with the header `Authorization: Bearer <key>` and has 20 seconds to answer. Its address is on the host of the Subscription's `baseUrl`, with the path `/api/monitor/usage/quota/limit`. The answer is JSON: `success`, and under `data.limits` a list of entries with `type`, `unit`, `number`, `percentage`, `usage` (the total), `currentValue`, `remaining`, `nextResetTime` in milliseconds, and `usageDetails`, a list of `modelCode` and `usage`. The vendor's message for a failure is the first of `msg`, `message` and `error` in the answer.

**`anthropic`.** Proposed: the tool reports the account's limit windows in the stream of a run, once after the first request to the model: a five-hour window and a seven-day window, each with the share used and its reset time. The Driver stores the latest such report with the Subscription and returns it when usage is asked for, with the time it was received. Before the first run of a Subscription the outcome is `unsupported`. Plan and account come from the status check. See [CLD-D2](#decisions).

Observed in version 1: Anthropic usage was read from the vendor's usage web page inside a hidden browser session owned by the Swift application, one persistent session per account. A Driver has no browser, and that reading is not carried over.

<!-- sources:
arbol:daemons/core/arbol_core/zai_usage.py#normalize
arbol:daemons/core/arbol_core/zai_usage.py#_parse_limit
arbol:daemons/core/arbol_core/zai_usage.py#_window_label
arbol:daemons/core/arbol_core/zai_usage.py#_collect_models
arbol:daemons/core/arbol_core/zai_usage.py#fetch_raw
arbol:app/Arbol/ContentView.swift
-->

### Model catalog

**`anthropic`.** Proposed: the Driver starts the tool in the Subscription's home with stream input and output and sends one `initialize` control request, no prompt. The answer lists the models the tool offers. Source `tool`.

| Catalog field | Taken from |
|---|---|
| `id` | `value` |
| `label` | `displayName` |
| `description` | `description` |
| `efforts` | `supportedEffortLevels`, when `supportsEffort` is true |
| `isDefault` | `value` is `default` |

Observed in a second round of probes with a signed-in folder ([probe record](../research/tool-probes-2026-10-05.md)): the `account` part of the answer then names the provider, e-mail address, organisation and plan. The list holds the tool's short names (`default`, `opus`, `sonnet`, `haiku`, `fable`) and, in later calls, full model identifiers as well. A full identifier that is not in the list is still accepted by the tool, so the catalog is what the tool offers, not everything it accepts. One model reports no effort levels.

**`zai`.** One request to `https://api.z.ai/api/paas/v4/models` with the key. Each entry gives a model by `id`, `model` or `name` and optionally a label. Source `vendor`. When the request fails the Driver answers with its built-in z.ai list, source `builtin`. It never answers with Anthropic's list: the gateway cannot run Anthropic models. The request is a `GET` with the header `Authorization: Bearer <key>` and has 30 seconds to answer. Its address is on the host of the Subscription's `baseUrl`, with the path `/api/paas/v4/models`, and the answer holds the entries as a list under `data`. The built-in list is the models named in the Subscription's `modelMap`.

Observed in version 1: the Anthropic list was read from `api.anthropic.com/v1/models` with the account's token, and each listed model was then sent a one-token request to learn whether the account may run it.

<!-- sources:
arbol:daemons/core/arbol_core/provider_models.py#fetch_claude_models
arbol:daemons/core/arbol_core/provider_models.py#_probe_claude_entitlement
arbol:daemons/core/arbol_core/provider_models.py#fetch_zai_models
-->

## Requirements

| ID | The Claude Driver must… | Refines | Origin | Verified by |
|---|---|---|---|---|
| CLD-1.1 | offer the families `anthropic` (vendor login) and `zai` (key) with the settings listed above, with one Subscription of each from the start, named `anthropic` and `zai`, and `anthropic` as the default unless the settings file names another | DRV-1.1 | Kept | `subscriptions.local`, `subscriptions.create`, `C1`; default inference pending SYL-80 |
| CLD-1.2 | set `CLAUDE_CONFIG_DIR` to the Subscription's home for every child process of that Subscription | DRV-1.2 | Changed | `subscriptions.environment`, `C39`, `probe.subscriptions`, `live.subscriptions`; run children pending SYL-80 |
| CLD-1.3 | build each child's environment from an allow-list; no inherited `ANTHROPIC_*`, `CLAUDE_*` or `CLAUDECODE` variable reaches the tool | DRV-0.5 | Changed | `subscriptions.environment`, `base.environment`, `C8`; run children pending SYL-80 |
| CLD-1.4 | apply a `zai` account as gateway address, key, model names and allowed tuning variables in the child's environment, with the key read from its source (DRV-0.14) when the child is started | DRV-0.3 | Kept | `subscriptions.environment`, `subscriptions.secret-source`, `C2`, `C7`; run children pending SYL-80 |
| CLD-1.5 | accept a `baseUrl` only if it is an http or https address | DRV-0.16 | Kept | `subscriptions.settings` |
| CLD-1.6 | accept in `toolEnvironment` only variable names on its allow-list, and never one that selects an account or an address | DRV-0.5 | New | `subscriptions.settings`, `subscriptions.environment` |
| CLD-1.7 | read no settings file from the Leather Bag's own tool configuration when a child is started | DRV-0.4 | Changed | `C8`, `probe.subscriptions`, `live.subscriptions` (owner configuration unchanged) |
| CLD-1.8 | sign an `anthropic` Subscription in and out with the tool's own `auth` commands run in the Subscription's home, with `BROWSER` set so that the sign-in address reaches the caller instead of the system browser, and hold no Anthropic credential itself | DRV-1.8 | Changed | `C2`, `C6`, `C7`, `probe.subscriptions`, `live.subscriptions` (existing tool-owned login) |
| CLD-1.9 | on `zai` sign-in read the key from its source (DRV-0.14), check it against z.ai, remove a rejected key from the Keychain item when it came from there, and keep it when z.ai cannot be reached | DRV-1.26 | Changed | `C2`, `C3`, `C4` |
| CLD-1.10 | keep a `zai` key as one Keychain item per Subscription, under the service `com.sylvan-stack.arbol.claude-driver`, extended as DRV-1 says when the state directory is not the default one, with the Subscription's identifier as the account, separate from version 1's items, and read it with the system's `security` command. A Subscription whose settings name a command as the source of its key has no item | DRV-0.3 | New | `subscriptions.keychain`, `C2`, `C3`, `subscriptions.import` |
| CLD-1.11 | never attempt to renew a `zai` key; a rejection moves the Subscription to `needs_attention` with the remedy "replace the key" | DRV-1.7 | Kept | `C4`, `C41` |
| CLD-1.12 | check an `anthropic` Subscription with `claude auth status --json` and a `zai` Subscription with the quota address; neither spends inference quota | DRV-1.14 | Kept | `C4`, `probe.subscriptions`, `live.subscriptions` |
| CLD-1.13 | turn z.ai's quota answer into a usage report by the rules in the Usage table | DRV-1.17 | Kept | `subscriptions.quota`, `C41` |
| CLD-1.14 | build the `anthropic` usage report from the limit information the tool writes during a run, keep the latest with the Subscription, and answer `unsupported` while there is none | DRV-1.17 | Changed | `subscriptions.update`, `C41`, `errors.usage`, `C30`, `live.errors-usage` |
| CLD-1.15 | take the `anthropic` catalog from the tool's `initialize` answer, without a prompt and without a request to the vendor's model interface | DRV-1.20 | Changed | `probe.subscriptions`, `live.subscriptions`, `C41` |
| CLD-1.16 | take the `zai` catalog from z.ai and fall back only to its built-in z.ai list | DRV-1.19 | Kept | `C41` |
| CLD-1.17 | provide a one-time import command, `subscriptions import <id> --from <file>`, that reads a `claude` settings file, writes its gateway address, model names and allowed tuning variables into the `zai` entry of the Driver's settings file, stores its key in the Keychain through the standard input of the `security` program, prints no value from it and leaves the `claude` file unchanged | DRV-0.4 | New | `subscriptions.import` (synthetic file and key only) |
| CLD-1.18 | leave the renewal of an `anthropic` login to the tool, and ask for a new sign-in only when the tool reports that it is not logged in or the vendor has rejected the login | DRV-1.7 | New | `C4`, `C7`, `C28`, `live.subscriptions`, `probe.errors` |

## Probes recorded

Run on 5 October 2026 against `claude` 2.1.289, with a clean environment. The first runs were inside a sandbox that cannot read the Keychain; the runs marked *outside the sandbox* repeated them without it.

| Probe | Result |
|---|---|
| `claude auth login --help`, `claude auth status --help` | Login options `--claudeai` (default), `--console`, `--email`, `--sso`. Status prints JSON by default |
| `claude auth status --json`, not logged in | Exit code 1. Keys: `loggedIn`, `authMethod`, `apiProvider`, `configDirectory`, `projectsDirectory`, `analyticsDisabled` |
| `initialize` control request over stream input | Answered with `models`, `account`, `commands` and other keys, while not logged in. Each model: `value`, `resolvedModel`, `displayName`, `description`, `supportsEffort`, `supportedEffortLevels`, `supportsAdaptiveThinking`, `supportsFastMode`, `supportsAutoMode`. Five models listed: `default`, `opus`, `sonnet`, `haiku` and one full model identifier |
| Environment of a shell started from a Claude desktop session | 28 variables named `ANTHROPIC_*`, `CLAUDE_*` or `CLAUDECODE`. Version 1's removal list covers `ANTHROPIC_*` and five others |
| Keychain item names, outside the sandbox | `Claude Code-credentials` for the default folder; `Claude Code-credentials-` followed by the first 8 hexadecimal digits of the SHA-256 of the folder path for any other `CLAUDE_CONFIG_DIR`. An item of the second kind was present and its suffix matched `~/.claude-anthropic` |
| `claude auth status --json` in two folders, outside the sandbox | An empty folder: not logged in. `~/.claude-anthropic`, whose Keychain item still held a login: logged in, `authMethod` `claude.ai`. The login is kept per folder. Running the command recreated that folder with the tool's bookkeeping files; it was moved away afterwards |
| A `claude` subcommand started with a desktop session's environment | `claude mcp login`, run from a shell that carried a Claude desktop session's `CLAUDE_*` and `ANTHROPIC_*` variables, recreated the default folder's Keychain item holding only the new MCP token. The Anthropic login stored in it was lost, and plain `claude` answered "Not logged in" until the owner signed in again. The same command run from a clean shell updated the item and kept what it held. Inferred from the item's creation time and contents; not reproduced |
| `claude auth login --claudeai`, from a clean shell | The tool opened the system browser itself and printed the address as well: on `claude.com`, with a fallback that shows a code to paste, returned through `platform.claude.com`. It reported success 7 seconds after the approval. The item then held both the login and the MCP token |
| `claude auth login --claudeai` in an empty config folder, with `BROWSER` set to a stand-in command, cancelled after 10 seconds | The tool printed "Opening browser to sign in…" and called the stand-in with the sign-in address; the tool opened no browser. That address is on `claude.com` and ends at `http://localhost:<port>/callback`. The address printed for the terminal ends at `platform.claude.com/oauth/code/callback`, and the tool then waits for a pasted code. Both ask for seven scopes, one more (`user:plugins`) than version 1 requested, and neither uses the authorisation address version 1 used. The folder received only the tool's bookkeeping file, and the default folder's login was untouched |
| `claude auth status --json`, logged in | Additional keys: `email`, `orgId`, `orgName`, `subscriptionType` |
| One real turn in the default folder while it held no login | Records `system/init`, `system/status`, `assistant`, `result`. The `assistant` record carries `error: "authentication_failed"`. The `result` record has `subtype: "success"` with `is_error: true` and `terminal_reason: "api_error"`. Exit code 1. Version 1's detection, which requires an error subtype and matching wording, would have reported this turn as completed |

Not established:

- why the tool's model list changed during the probes, from five entries to twelve, on the same login;
- how long a login lasts without a new sign-in, and whether several runs that renew one login at the same moment can lose it. The tool renews its login by itself; both logins stored on the owner's machine were less than two days old on 5 October 2026, so nothing could be measured. The owner's condition in CLD-D1 is to be watched with the first Subscription in use;
- whether macOS asks the owner for permission when the `security` command first reads a Keychain item that another program stored. An item that `security` stored itself was read back without a question on 6 October 2026, with made-up keys of 80, 300 and 2,000 characters;
- the hosts a sign-in with a Google or an Apple account passes through. They are added to the host list when a real sign-in has shown them;
- how a key that holds a double quote or a backslash has to be written for the `security` program.

## Known problems in version 1

Not to be reproduced.

- **A shared profile folder.** Two Anthropic accounts would have shared one folder; only the token differed. Whatever the tool keeps there was common to both.
- **Run-time dependence on a personal file.** A z.ai turn loaded `~/.claude/settings-zai.json`. Editing that file for terminal use changed Arbol's turns, and the file holds the key in plain text beside the copy in the Keychain.
- **The vendor's sign-in was imitated.** See DRV-1. The exchange also failed once inside a bundled service that had no certificate store.
- **The Anthropic usage reading needed a browser.** It broke with page changes and had its own login state, separate from the account's credential.
- **Each catalog fetch spent one request per model.**

<!-- sources:
arbol:product-spec/05-intelligence-providers.md#Can two accounts of one vendor run at the same time, isolated?
arbol:product-spec/05-intelligence-providers.md#Known problems and lessons
arbol:daemons/shared/arbol_shared/subscription_oauth.py#_default_opener
arbol:daemons/shared/arbol_shared/claude_cli.py#alias_args
-->

## Decisions

| ID | Question | Proposed default | Outcome |
|---|---|---|---|
| CLD-D16 | How are subscription credentials read, imports checked and catalog failures handled? | Run secret commands without a shell in a clean environment, with a 20-second limit, and remove one final line ending from stdout. The unsuffixed Keychain service is reserved for the operating-system user's actual default state path, not a default derived from an overridden HOME; temporary test homes therefore always use a hashed service. Read and delete Keychain items by explicit service and account; write imported keys through quoted standard input of security -i and verify the item by reading it back. Escape double quotes and backslashes in that input (confirmed with made-up keys on 6 October 2026). Preserve unrelated Driver settings and all defaults during import; reject imports into a command-source Subscription. Anthropic catalog failures fall back to the short names default, opus, sonnet and haiku, without invented effort levels. Credential rejection in a catalog still moves the account to needs_attention. Status and catalog commands run in the private config home, with CLAUDE_CONFIG_DIR set to it, with bounded output and no prompt. HOME is the actual operating-system home for Keychain discovery. security -w writes a value containing non-ASCII characters as hexadecimal; decode that representation before key validation, and disambiguate an all-hex ASCII key with a metadata-only -g read whose password line quotes ASCII but leaves binary values unquoted | Decided 6 October 2026 during SYL-78, a technical choice |
| CLD-D15 | How are family settings returned and isolated before an operation? | Known settings are validated when the Subscription is read; unknown names are ignored with notices and their values are never returned. Anthropic accepts no family settings. The gateway model map accepts haiku, sonnet and opus, and its three allowed tuning variables have string values. CLAUDE_CONFIG_DIR and the working directory are the private Subscription home. On macOS HOME remains the operating-system user's actual home for Keychain discovery: a probe on 6 October showed that an overridden HOME hides the login Keychain. Claude keeps its configuration in CLAUDE_CONFIG_DIR; the subscription probes verify that the owner's own configuration is unchanged | Decided 6 October 2026 during SYL-78, a technical choice |
| CLD-D1 | How does an `anthropic` Subscription sign in? | The tool's own login inside the Subscription's home (CLD-1.8). The isolation this depends on is confirmed: the tool keeps one login per config folder (see the probes). The fallback, should the tool's login prove unusable from a Driver, is `claude setup-token`, with the Driver keeping the resulting long-lived token in the Keychain and passing it as `CLAUDE_CODE_OAUTH_TOKEN`, the variable version 1 used. Version 1's own authorisation code is dropped in both cases. The page stays in the caller's window: with `BROWSER` set, the tool hands the address over and opens no browser (see the probes). The vendor's terms require its own sign-in flow, which version 1's authorisation code did not use | Decided 5 October 2026 by the owner (SYL-9): the proposed default. The owner's conditions are that signing in is simple and is not needed again from day to day (CLD-1.18). A first choice of version 1's own authorisation was given up once the vendor's terms and the `BROWSER` probe were known |
| CLD-D2 | Where does `anthropic` usage come from? | From the limit information the tool writes during a run (probed: five-hour and seven-day windows with share used and reset time). It costs nothing and needs no credential, but it is only as fresh as the last run. A reading on demand, like the tool's own usage display, is not offered | Decided 6 October 2026 by the owner: the proposed default (SYL-53) |
| CLD-D3 | Which tuning variables may a `zai` Subscription set? | The three in the owner's file: `API_TIMEOUT_MS`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | Decided 6 October 2026 by the owner: the proposed default (SYL-54) |
| CLD-D4 | Other Anthropic-compatible gateways | Not in the first release. Each would be a family of its own, with its own usage and catalog source, never a `zai` Subscription with another address | Decided 6 October 2026 by the owner: the proposed default (SYL-55) |

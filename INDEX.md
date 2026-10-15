# Arbol Claude Driver: Catalog

## Chapters

### `specs/`: what this Driver does

How this Driver meets the [Driver Contract](../arbol/driver-contract/README.md) with the `claude` command-line tool. Start at the chapter's [README](specs/README.md).

- [`00-overview-and-legacy-map.md`](specs/00-overview-and-legacy-map.md) (CLD-0): what the Driver is, and where each part of the version 1 code went.
- [`01-subscriptions.md`](specs/01-subscriptions.md) (CLD-1): vendor families, home and environment per Subscription, sign-in, status, usage, model catalog.
- [`02-inference.md`](specs/02-inference.md) (CLD-2): arguments and environment of a run, sessions and continuity, the mapping from the tool's records to events, usage, ending and stopping a run, z.ai differences.
- [`03-tools-and-permissions.md`](specs/03-tools-and-permissions.md) (CLD-3): how the tool is started with every tool, with nothing switched off and in the mode that asks for no permission; questions from the agent; helper agents.
- [`04-errors-and-limits.md`](specs/04-errors-and-limits.md) (CLD-4): the mapping from the tool's records to error codes, the wording fallback, the tool's own retries, limit information in the stream, time limits, the tool's version.

### `research/`: evidence the specifications rest on

- [`v1-driver-inventory.md`](research/v1-driver-inventory.md): what the version 1 Driver does, read from the deprecated source, with Source Refs.
- [`tool-probes-2026-10-05.md`](research/tool-probes-2026-10-05.md): what the installed tool does, observed in real runs: start-up arguments, the record catalogue, the permission bridge, effort and model, sessions, stopping, errors, z.ai.
- [`probe-scripts-2026-10-06/`](research/probe-scripts-2026-10-06/README.md): the scripts behind the probes of 6 October 2026 and the raw records of one real run, kept as records of what was run against the installed `claude`.

## Conventions

- Every artifact goes into a chapter folder, never directly into the corpus root. `README.md`, `INDEX.md` and a `GLOSSARY.md` are the exceptions.
- List a chapter here when it is created.
- Tasks are tracked in Linear, not in this corpus: project [Arbol Claude Driver](https://linear.app/sylvan-stack/project/arbol-claude-driver-46bb03105787) in the Sylvan Stack workspace. Specifications are copied there as documents; `.linear.json` maps each file to its copy. The files here are the originals. There is no `plans/` chapter.

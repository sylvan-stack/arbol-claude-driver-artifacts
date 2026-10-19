---
role: authored
---
# Claude Driver specifications

How `arbol-claude-driver` meets the [Driver Contract](../../arbol/driver-contract/README.md) with the `claude` command-line tool. The contract says what every Driver does; these specifications say how this one does it, and carry the requirements only this Driver has.

Conventions (shape of a specification, requirement identifiers, origin, checks, status, decisions) are defined once in the [contract's README](../../arbol/driver-contract/README.md#conventions). Identifiers here start with `CLD`; the specification number matches the contract's.

Source Refs name enabled repositories only. Evidence from the frozen version 1 repository or corpus uses ordinary Markdown links or `arbol_deprecated_v1:path#symbol` locators, never machine-readable source declarations or provenance edges. Active references to the Driver Contract remain Source Refs.

| Spec | Title | Refines | Status |
|---|---|---|---|
| [CLD-0](00-overview-and-legacy-map.md) | Overview and legacy map | DRV-0 | accepted |
| [CLD-1](01-subscriptions.md) | Subscriptions | DRV-1 | accepted |
| [CLD-2](02-inference.md) | Inference | DRV-2 | accepted |
| [CLD-3](03-tools-and-permissions.md) | Tools and permissions | DRV-3 | accepted |
| [CLD-4](04-errors-and-limits.md) | Errors and limits | DRV-4 | implemented |

Evidence the specifications rest on is in `research/`: the [inventory of the version 1 Driver](../research/v1-driver-inventory.md) and the [record of probes against the installed tool](../research/tool-probes-2026-10-05.md).

---
role: authored
---
# Justifications

## run_failure

Reason: Use only the existing default Claude profile for live operations and refuse additional routes before tool startup.

Origins: CLD-1.2, CLD-1.19, DRV-1.11, OG-5 · Intention i-004ce942 · 2026-11-21

## RunProtocol.accept

Reason: Handle Claude Code progress and summary records as activity so a running tool reaches its result.

Origins: CLD-2.14, CLD-2.15, DRV-3.32 · Intention i-78e58d80 · 2026-11-22


# CodeCommit Engineering Workflow

## 1. Project Identity

Project:
CodeCommit

Product:
Emergency Resource Orchestration Platform

Primary purpose:
Coordinate emergency resources across changing disaster situations through
incident understanding, needs assessment, prioritization, constrained
optimization, inter-agency coordination, human approval, and dynamic
re-planning.

The public product must not contain hackathon-specific branding.

Do not use these in public UI:

- Kurukshetra
- HACKFEST
- HACKFEST 2026
- SIH
- PS20
- Problem Statement
- Judge
- Judges
- Hackathon
- Submission
- Team ID
- Competition
- NEXUS-R

These references may remain in internal documentation when required.

---

# 2. Core Engineering Principle

Build for:

1. Correctness
2. Reliability
3. Demonstrability
4. Maintainability
5. UX quality
6. Performance

Do not optimize for code volume.

Do not add complexity merely to make the architecture look sophisticated.

Every feature must solve a real operational problem.

---

# 3. Source of Truth

When documentation and implementation disagree:

1. Inspect the source code.
2. Run the application.
3. Run the relevant tests.
4. Determine the actual behavior.
5. Update documentation to match reality.

Never document a feature as implemented when it is only planned,
simulated, or partially implemented.

Use these labels:

- IMPLEMENTED
- PARTIALLY IMPLEMENTED
- SIMULATED
- ADAPTER READY
- PLANNED
- BLOCKED

---

# 4. Repository Safety

Before changing an existing subsystem:

- inspect the current implementation
- identify dependencies
- identify existing callers
- understand state transitions
- check relevant tests
- preserve working behavior

Do not rewrite working functionality without a clear reason.

Do not delete files simply because a new implementation seems cleaner.

Prefer incremental changes.

---

# 5. Git Workflow

Use small, meaningful commits.

Preferred:

```text
feature/<name>
fix/<name>
refactor/<name>
ui/<name>
test/<name>
docs/<name>
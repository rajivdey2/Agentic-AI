"""SimWorld: the simulated logistics environment.

Design (from CLAUDE.md): every state change is an **event** appended to an
append-only store. All *current state* views ("projections") are derived by
replaying the log. This gives auditability, point-in-time replay and a clean
read/write split for the agent.
"""
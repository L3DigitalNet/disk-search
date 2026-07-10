# Claude Code

@AGENTS.md

Agent Handoff injects `docs/handoff/state.md` plus Git status. On closeout,
use the repo-local `$agent-handoff` skill and the files described in `AGENTS.md`.

<!-- BEGIN agent-handoff managed instructions -->
Use the repo-local `$agent-handoff` skill at startup and closeout.
Do not reread `docs/handoff/state.md` when SessionStart already injected it.
Keep current status and tasks in `docs/STATUS.md` and `docs/TODO.md`; route durable facts through `docs/handoff/`.
At closeout, update only changed facts, preserve user-authored work, store credential references only, and run relevant validation.
<!-- END agent-handoff managed instructions -->

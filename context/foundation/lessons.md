# Lessons Learned

> Append-only register of recurring rules and patterns. Re-read at start by /10x-frame, /10x-research, /10x-plan, /10x-plan-review, /10x-implement, /10x-impl-review.

## Touched-set per phase (git commit scope)

**Context:** `git add` podczas phase-end commit w `/10x-implement` (np. change metadata-and-import obok norms-replacement w tym samym commicie).

**Problem:** Szeroki commit miesza niepowiązane foldery `context/changes/<inny-change>/` z kodem bieżącej zmiany — utrudnia review i rollback.

**Rule:** Przy commicie fazy stage wyłącznie touched-set bieżącej zmiany + `plan.md`; nie używaj `git add -A`. Niezwiązane dirty paths zostaw lub commituj w osobnym change.

**Applies to:** `/10x-implement`, `/10x-archive`, ręczne commity agenta

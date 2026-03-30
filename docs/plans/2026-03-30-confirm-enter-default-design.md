# Confirm Prompt Default Yes Design

**Goal:** Allow `mackup` confirmation prompts to treat a direct Enter keypress as `Yes` while keeping explicit `No` behavior unchanged.

**Architecture:** All interactive confirmations already flow through `mackup.utils.confirm()`, so the change should stay centralized there. The prompt text should advertise the new default, and tests should lock the behavior at the utility level so every CLI callsite inherits it automatically.

**Components:**
- [`src/mackup/utils.py`](/Users/jiyee/Developer/mackup/src/mackup/utils.py): Update `confirm()` to accept an empty response as `Yes` and change the displayed prompt to `Enter|Yes|No`.
- [`tests/test_utils.py`](/Users/jiyee/Developer/mackup/tests/test_utils.py): Add a focused regression test for an empty response returning `True`.

**Data Flow:** `confirm(question)` reads a single user response through `input()`. If the normalized answer is empty, `yes`, or `y`, it returns `True`; if it is `no` or `n`, it returns `False`; otherwise it loops and asks again.

**Error Handling:** Invalid non-empty input should continue to re-prompt exactly as today. `--force` and `--force-no` stay untouched because they short-circuit before interactive input.

**Testing:** Add one failing unit test for the empty-input case, verify it fails, then implement the minimal change and rerun both targeted and full test suites.

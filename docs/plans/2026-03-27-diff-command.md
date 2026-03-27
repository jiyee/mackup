# Diff Command Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `mackup diff` command that compares local config paths against the backup directory and prints the results as an ASCII table.

**Architecture:** Extend the existing `docopt` CLI in `src/mackup/main.py` with a new read-only command. Reuse `Mackup`, `ApplicationsDatabase`, and `ApplicationProfile.getFilepaths()` to enumerate config paths, add pure comparison helpers in `src/mackup/utils.py`, and keep table rendering dependency-free. Cover behavior with CLI-focused tests first, then implement the minimal code to satisfy them.

**Tech Stack:** Python 3.9+, docopt-ng, unittest via pytest collection

---

### Task 1: Add failing CLI coverage for `diff`

**Files:**
- Modify: `tests/test_cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write the failing test**

Add CLI tests that invoke `mackup diff` and assert:
- identical file reports `identical`
- modified local file reports `different`
- missing local file reports `missing_local`
- missing backup file reports `missing_backup`
- directory entries can also be compared

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -k diff -v`
Expected: FAIL because `diff` is not a recognized command yet.

**Step 3: Write minimal implementation**

No implementation in this task.

**Step 4: Run test to verify it still fails for the expected reason**

Run: `pytest tests/test_cli.py -k diff -v`
Expected: FAIL with command parsing or missing behavior.

### Task 2: Implement structured diff collection

**Files:**
- Modify: `src/mackup/application.py`
- Modify: `src/mackup/utils.py`
- Test: `tests/test_cli.py`

**Step 1: Write the failing test**

Rely on Task 1 failures as the active red test.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -k diff -v`
Expected: FAIL before implementation.

**Step 3: Write minimal implementation**

Add helper functions that:
- detect path type
- compare file contents
- compare directory trees
- derive a stable diff status for one config path

Expose a method on `ApplicationProfile` that returns structured diff rows for the app.

**Step 4: Run test to verify progress**

Run: `pytest tests/test_cli.py -k diff -v`
Expected: still failing until the CLI wiring and output formatting are added.

### Task 3: Wire the `diff` CLI and render the table

**Files:**
- Modify: `src/mackup/main.py`
- Modify: `src/mackup/utils.py`
- Test: `tests/test_cli.py`

**Step 1: Write the failing test**

Reuse the active CLI tests.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -k diff -v`
Expected: FAIL before command dispatch exists.

**Step 3: Write minimal implementation**

Update CLI usage/help text and dispatch logic to:
- support `mackup diff [--] [<application> ...]`
- iterate the selected apps
- collect rows from `ApplicationProfile`
- print a dependency-free ASCII table

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -k diff -v`
Expected: PASS.

### Task 4: Run targeted regression verification

**Files:**
- Test: `tests/test_cli.py`
- Test: `tests/test_application.py`
- Test: `tests/test_utils.py`

**Step 1: Run focused verification**

Run: `pytest tests/test_cli.py tests/test_application.py tests/test_utils.py -v`

**Step 2: Check for regressions**

Confirm the new diff behavior passes and existing application or utility tests still pass.

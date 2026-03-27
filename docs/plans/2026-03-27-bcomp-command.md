# Bcomp Command Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `mackup bcomp` command that launches `bcomp` for every managed path in a selected application, using the configured backup root by default and an optional override when requested.

**Architecture:** Extend the `docopt` CLI in `src/mackup/main.py` with a single-application `bcomp` command. Keep path resolution and command execution inside `ApplicationProfile` so the CLI remains a thin dispatcher. Use `bash -lc` plus shell quoting to invoke `bcomp` with the local and backup paths, and support `--dry-run` by printing the command instead of executing it.

**Tech Stack:** Python 3.9+, docopt-ng, unittest via pytest collection, subprocess

---

### Task 1: Add failing CLI coverage for `bcomp`

**Files:**
- Modify: `tests/test_cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write the failing test**

Add CLI tests that assert:
- `mackup bcomp test-app` invokes `bash -lc` with the local path and configured backup path
- `mackup bcomp test-app --backup-root=~/Custom` uses the override root

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -k bcomp -v`
Expected: FAIL because `bcomp` is not a recognized command yet.

**Step 3: Write minimal implementation**

No implementation in this task.

**Step 4: Run test to verify the red state is correct**

Run: `pytest tests/test_cli.py -k bcomp -v`
Expected: FAIL due to missing CLI support.

### Task 2: Implement `bcomp` path execution

**Files:**
- Modify: `src/mackup/application.py`
- Test: `tests/test_cli.py`

**Step 1: Reuse the failing tests**

Use the Task 1 tests as the active red suite.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -k bcomp -v`
Expected: FAIL before implementation.

**Step 3: Write minimal implementation**

Add an `ApplicationProfile` method that:
- resolves the local and backup path for each managed file
- accepts an optional backup-root override
- invokes `bash -lc "bcomp ..."` with shell-safe quoting
- prints the command instead of executing it in dry-run mode

**Step 4: Run the tests again**

Run: `pytest tests/test_cli.py -k bcomp -v`
Expected: still failing until the CLI dispatch exists.

### Task 3: Wire `bcomp` into the CLI

**Files:**
- Modify: `src/mackup/main.py`
- Test: `tests/test_cli.py`

**Step 1: Reuse the failing tests**

Keep the Task 1 tests as the active red suite.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -k bcomp -v`
Expected: FAIL before the command is exposed.

**Step 3: Write minimal implementation**

Update the usage text, options, and command dispatch to:
- support `mackup bcomp <application> [--backup-root=<path>]`
- validate the application name like `show`
- instantiate `ApplicationProfile`
- delegate execution to the new `bcomp` method

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -k bcomp -v`
Expected: PASS.

### Task 4: Run focused regression verification

**Files:**
- Test: `tests/test_cli.py`

**Step 1: Run targeted verification**

Run: `pytest tests/test_cli.py -k "bcomp or diff" -v`

**Step 2: Confirm no regression**

Verify the new command passes and existing diff CLI coverage still passes.

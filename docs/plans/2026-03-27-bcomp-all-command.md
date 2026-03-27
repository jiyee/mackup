# Bcomp All Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a batch `mackup bcomp --all` mode that opens a single read-only Beyond Compare session for all managed paths matching a selected diff status, defaulting to `different`.

**Architecture:** Reuse the existing diff row generation to collect managed paths across applications, filter them by status, materialize two temporary directory trees containing only the matching local and backup paths, then launch one `bcomp -ro <left> <right>` process. Keep CLI parsing in `src/mackup/main.py` and filesystem staging helpers in `src/mackup/utils.py`.

**Tech Stack:** Python 3.9+, docopt-ng, unittest via pytest collection, subprocess, tempfile

---

### Task 1: Add failing CLI coverage for batch bcomp

**Files:**
- Modify: `tests/test_cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write the failing test**

Add CLI tests that assert:
- `mackup bcomp --all` includes only paths with `different` status in the staged trees
- `mackup bcomp --all` skips identical paths
- `mackup bcomp --all` reports no matches and does not launch `bcomp` when nothing is different

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -k "bcomp_all or no_different" -v`
Expected: FAIL because batch mode does not exist yet.

**Step 3: Write minimal implementation**

No implementation in this task.

**Step 4: Re-run to confirm the red state**

Run: `pytest tests/test_cli.py -k "bcomp_all or no_different" -v`
Expected: FAIL for missing CLI support.

### Task 2: Implement batch staging helpers

**Files:**
- Modify: `src/mackup/utils.py`
- Test: `tests/test_cli.py`

**Step 1: Reuse the failing tests**

Use Task 1 tests as the active red suite.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -k "bcomp_all or no_different" -v`
Expected: FAIL before staging logic exists.

**Step 3: Write minimal implementation**

Add helpers that:
- resolve a backup root override
- materialize local and backup comparison trees for a list of managed paths
- launch `bcomp -ro` against the two staged roots

**Step 4: Run tests again**

Run: `pytest tests/test_cli.py -k "bcomp_all or no_different" -v`
Expected: still failing until CLI wiring exists.

### Task 3: Wire `bcomp --all` into the CLI

**Files:**
- Modify: `src/mackup/main.py`
- Test: `tests/test_cli.py`

**Step 1: Reuse the failing tests**

Keep the Task 1 tests as the active red suite.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -k "bcomp_all or no_different" -v`
Expected: FAIL before command dispatch exists.

**Step 3: Write minimal implementation**

Update the CLI usage and dispatch to:
- support `mackup bcomp --all`
- default batch mode to `--status=different`
- collect rows from all managed applications
- call the new batch helper
- print a clear message when there are no matching paths

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -k "bcomp_all or no_different" -v`
Expected: PASS.

### Task 4: Run focused CLI regression verification

**Files:**
- Test: `tests/test_cli.py`

**Step 1: Run verification**

Run: `pytest tests/test_cli.py -k "bcomp or diff" -v`

**Step 2: Confirm no regressions**

Verify the single-app `bcomp`, batch `bcomp --all`, and `diff` behaviors all pass together.

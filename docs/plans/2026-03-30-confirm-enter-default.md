# Confirm Prompt Default Yes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `mackup` confirmation prompts accept a direct Enter keypress as `Yes`.

**Architecture:** Keep the behavior change isolated to `mackup.utils.confirm()` so every existing confirmation callsite inherits it automatically. Protect the change with a focused unit test in `tests/test_utils.py`, then verify with targeted and full test runs.

**Tech Stack:** Python 3, unittest, pytest via `uv`

---

### Task 1: Add the failing confirmation test

**Files:**
- Modify: `tests/test_utils.py`
- Test: `tests/test_utils.py`

**Step 1: Write the failing test**

```python
def test_confirm_enter_defaults_yes(self):
    def custom_input(_):
        return ""

    utils.input = custom_input
    assert utils.confirm("Press Enter for yes")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_utils.py -k enter_defaults_yes -v`
Expected: FAIL because `confirm()` does not yet accept an empty response.

### Task 2: Implement the minimal confirmation change

**Files:**
- Modify: `src/mackup/utils.py`
- Test: `tests/test_utils.py`

**Step 1: Write minimal implementation**

```python
answer: str = input(question + " <Enter|Yes|No> ").lower()

if answer == "" or answer == "yes" or answer == "y":
    confirmed = True
    break
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_utils.py -k enter_defaults_yes -v`
Expected: PASS

### Task 3: Run regression verification

**Files:**
- Test: `tests/test_utils.py`
- Test: `tests/test_cli.py`

**Step 1: Run focused utility tests**

Run: `uv run pytest tests/test_utils.py -v`
Expected: PASS

**Step 2: Run full test suite**

Run: `uv run pytest -q`
Expected: PASS

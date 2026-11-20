# JARVIS Variant 1 UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable PySide6 desktop dashboard matching approved Variant 1.

**Architecture:** Separate UI rendering from mutable assistant state. Keep camera, gesture and voice integrations outside this milestone so they can later update a stable state interface.

**Tech Stack:** Python 3.10+, PySide6, pytest, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-09-10-jarvis-variant1-ui-design.md`

## Global Constraints
- Windows 10/11 target.
- Ukrainian UI copy.
- Offline-first architecture.
- PySide6/Qt Widgets.

---

### Task 1: Assistant runtime state
**Files:** `jarvis_ui/state.py`, `tests/test_state.py`
- [x] Write failing tests for initial, start, stop and command states.
- [x] Run tests and observe missing module failure.
- [x] Implement minimal state model.
- [x] Re-run tests to green.

### Task 2: Declarative UI specification
**Files:** `jarvis_ui/ui_spec.py`, `tests/test_ui_spec.py`
- [x] Write failing tests for required navigation and four status cards.
- [x] Run tests and observe missing module failure.
- [x] Implement immutable navigation/card specifications.
- [x] Re-run tests to green.

### Task 3: Desktop presentation
**Files:** `jarvis_ui/theme.py`, `jarvis_ui/widgets.py`, `jarvis_ui/window.py`, `main.py`
- [x] Implement reusable status card.
- [x] Implement sidebar, dashboard, last-command panel and log panel.
- [x] Connect start/stop control to `AssistantState`.
- [x] Apply QSS Jarvis theme.

### Task 4: Distribution scaffold
**Files:** `requirements.txt`, `build_exe.bat`, `run_windows.bat`, `README.md`
- [x] Record runtime/dev dependencies.
- [x] Add Windows launch script.
- [x] Add PyInstaller one-file build script.
- [x] Document setup and next milestone.

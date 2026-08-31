---
name: py-package-check
description: Run the Python package release gate for geobr — sync the locked environment, run the offline and network test suites, build the distribution, and review the source against the Python conventions. Use when the user says "check the python package", "run pytest", "is the python side ready", "prepare a PyPI release", or points at python-package/. Produces a check report in quality_reports/. Mirrors .github/workflows/Python-CMD-check.yaml so local and CI cannot diverge.
author: geobr
version: 1.0.0
argument-hint: "[--network] [--no-review]"
disable-model-invocation: true
allowed-tools: ["Read", "Grep", "Glob", "Bash", "Write", "Task", "Monitor"]
effort: high
---

# `/py-package-check` — Python Release Gate

The Python counterpart to [`/r-package-check`](../r-package-check/SKILL.md). Sync → test → build →
review, then a verdict.

**Input:** `$ARGUMENTS` — `--network` also runs the online suite (hits `geobr_prep_data`);
`--no-review` skips the agent review pass.

---

## Constraints

- **Mirror CI exactly.** [`.github/workflows/Python-CMD-check.yaml`](../../../.github/workflows/Python-CMD-check.yaml)
  is the source of truth for the commands. If they drift, CI wins and this file is updated.
- **Follow [`python-package-conventions.md`](../../rules/python-package-conventions.md).**
- **Do not bump the version and do not publish.** This skill checks; the maintainer releases.

---

## Phase 0: Toolchain pre-flight — this is the gate on the gate

```bash
command -v uv || echo "uv: ABSENT"
command -v python || command -v python3 || echo "python: ABSENT"
```

**If `uv` is absent** (the expected case on the maintainer's Windows machine), **stop here** and
report:

```markdown
## Pre-Flight — HALTED

**Python toolchain:** not available on this machine (no `uv`, no `python`, no `.venv`).

This skill cannot run. Your options:
1. Push the branch and let `Python-CMD-check.yaml` run it (ubuntu/macOS/windows x py3.10-3.13).
2. Install uv — https://docs.astral.sh/uv/getting-started/installation/ — then re-run.
3. Run `/py-package-check --no-review` on a machine that has Python.

**Falling back to static review**, which needs no interpreter: [proceed to Phase 4].
```

Then run **Phase 4 only** and label the verdict `STATIC-ONLY`. Never simulate the test output.
Never substitute `pip install -e .` for `uv sync --frozen` — a different resolution is a different
answer.

**If `uv` is present**, emit the normal pre-flight and continue:

```markdown
## Pre-Flight Report — Python Package Check

**Package:** geobr [version from pyproject.toml]
**Root:** python-package/
**Python:** [version] · **uv:** [version]
**Public readers:** [count of read_* in geobr/__init__.py]
**Runtime deps:** [from pyproject.toml]
**Plan:** sync --frozen -> pytest (offline) -> [network] -> build -> review
```

## Phase 1: Sync the locked environment

```bash
cd python-package && uv sync --frozen 2>&1 | tail -20
```

`--frozen` is not optional — it is what CI does. A failure here almost always means `pyproject.toml`
changed without regenerating `uv.lock`. Report that as the root cause rather than retrying without
the flag.

## Phase 2: Test

Offline suite — the one that gates commits:

```bash
cd python-package && uv run pytest -n 2 -m "not network" --durations=10 2>&1 | tail -60
```

With `--network`, also run the online suite (slow, and it depends on the data server being up):

```bash
cd python-package && uv run pytest -m network --durations=10 2>&1 | tail -60
```

Long runs: background-launch via Bash `run_in_background` and stream with the **Monitor tool**.

Report passed / failed / skipped / xfailed, plus the slowest tests. **Investigate a rising skip
count** — a skip is not a pass.

## Phase 3: Build

```bash
cd python-package && uv build 2>&1 | tail -20
```

Confirm both an sdist and a wheel are produced, and that the wheel contains `geobr/data` (declared in
`[tool.pdm.build].includes`). A wheel missing its bundled data installs cleanly and fails at runtime.

## Phase 4: Source review (skip with `--no-review`)

Spawn the **python-package-reviewer** agent (`Task`) on the changed files, or on `python-package/geobr/`
for a full release check. Address Critical findings before declaring the package releasable.

This phase is the whole value of the run when Phase 0 halted — a static review is the only pre-CI
signal available on a machine without Python.

## Phase 5: Verdict

Save to `quality_reports/audits/python_package_check.md`:

```markdown
## Release Gate — geobr (Python) [version]
- uv sync --frozen: PASS / FAIL
- pytest (offline): P passed, F failed, S skipped
- pytest (network): P passed, F failed, S skipped / NOT RUN
- Build: sdist + wheel OK / FAIL
- python-package-reviewer: C critical, M major
- **Verdict:** RELEASABLE / FIX-FIRST / STATIC-ONLY

### Release checklist
[ ] Offline suite green; network suite green or knowingly deferred
[ ] pyproject.toml version bumped + CHANGELOG.md entry
[ ] uv.lock regenerated if dependencies changed
[ ] R parity checked (/parity-check) or the gap recorded
[ ] CI green on all three OS x four Python versions
```

`STATIC-ONLY` means no test actually ran here. Say so in one plain sentence and name the CI job that
does cover it.

---

## Important

- **`--frozen` or it does not count.** A resolution that differs from `uv.lock` is not the thing CI
  installs.
- **The offline suite must pass with no network.** A test that needs the data server belongs behind
  `@pytest.mark.network`.
- **This skill does not publish.** `uv publish` / a PyPI release is the maintainer's call.

---
name: deep-audit
description: |
  Deep consistency audit of the geobr repository — configuration, documentation,
  and the two packages. Launches parallel specialist agents to find factual errors,
  dead references, drift between the R and Python sides, and claims that no longer
  match disk. Then fixes what is genuinely broken and loops until clean.
  Use after broad changes, before a release, or when the user says "audit",
  "find inconsistencies", "check everything".
author: geobr
version: 2.0.0
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Task"]
disable-model-invocation: true
effort: high
---

# Deep Repository Audit

## When to Use

- After broad changes to `.claude/`, `CLAUDE.md`, or either package's public surface
- Before a CRAN or PyPI release
- When the user asks to "find inconsistencies", "audit", or "check everything"

## Workflow

### PHASE 0: Mechanical checks (run FIRST — cheap and deterministic)

There is no check script in this repo, so run these directly. Each is a class of bug that agent
prompts historically miss because attention drifts across a long checklist.

```bash
# 1. Dead rule globs — a rule whose paths: match nothing never fires. This is THE bug
#    that made the inherited config inert; check it every time.
for f in .claude/rules/*.md; do
  echo "== $f"
  awk '/^paths:/{p=1;next} /^[a-z]/{p=0} p&&/^ *- /{gsub(/^ *- "|"$/,"");print}' "$f" |
    while read -r g; do
      n=$(ls $g 2>/dev/null | wc -l)
      [ "$n" -eq 0 ] && echo "   DEAD GLOB: $g"
    done
done

# 2. Referenced-but-missing files across all config
grep -rhoE '\]\(\.\./[^)]+\)|\]\([a-z0-9_./-]+\.md\)' .claude CLAUDE.md | sort -u

# 3. Commands named in config that do not exist on this machine
grep -rhoE '(python3?|uv|gh|quarto|Rscript) [a-z-]+' .claude CLAUDE.md | sort -u

# 4. Skills/agents/rules on disk vs. the inventory in CLAUDE.md
ls .claude/skills/ ; ls .claude/agents/ ; ls .claude/rules/
grep -n "Rules\|Skills\|Agents" CLAUDE.md
```

Fix P0/P1 findings here **before** launching agents — the mechanical layer is cheaper and more
precise than a prompt for these classes.

### PHASE 1: Launch parallel audit agents

Launch simultaneously via `Task` with `subagent_type=general-purpose`. Every agent prompt **must**
include the claim-vs-reality lens: *does every documented command, path, count, and cross-reference
actually resolve in this repo?*

#### Agent 1: Configuration integrity
Focus: `.claude/rules/*.md`, `.claude/skills/*/SKILL.md`, `.claude/agents/*.md`
- Valid YAML frontmatter everywhere
- **`allowed-tools` covers every tool the body invokes.** If the body says "spawn X via `Task`",
  `Task` must be in `allowed-tools` — otherwise a runtime permission error or a silent bypass.
- **Rule `paths:` globs match real files** (Phase 0 catches this; confirm the fix)
- **Rule ↔ skill parity:** if a rule names a skill, that skill actually implements the protocol
- No contradictions between rules
- No references to skills, agents, hooks, or scripts that do not exist here

#### Agent 2: Documentation accuracy
Focus: `CLAUDE.md`, `MEMORY.md`, `README.md`, `r-package/README.md`, `python-package/README.md`
- Every file path mentioned exists on disk
- Every command is runnable, or is explicitly marked as needing an absent toolchain
- The surface inventory in `CLAUDE.md` matches `ls .claude/{skills,agents,rules}` exactly
- Architecture claims match the code (line numbers in `CLAUDE.md` and `MEMORY.md` still point at
  what they say they do — these rot whenever `utils.R` / `utils.py` is edited)
- No stale counts, no placeholder text (`[YOUR ...]`), no lecture/Beamer/Quarto leftovers

#### Agent 3: R ↔ Python drift
Focus: `r-package/R/`, `python-package/geobr/`
- The parity contract in [`cross-language-parity.md`](../../rules/cross-language-parity.md)
- Release tag consistent across its five hardcoded copies
- A public reader present on one side but not the other, with no changelog record
- **Do not report native-idiom differences as drift** (`sf` vs `GeoDataFrame`, arrow/dplyr vs
  duckdb/pandas). See the false-alarm list below.
- Prefer running `/parity-check` and auditing its report over re-deriving the comparison

#### Agent 4: Package hygiene
Focus: `r-package/DESCRIPTION`, `r-package/NAMESPACE`, `python-package/pyproject.toml`,
`python-package/uv.lock`, `.github/workflows/`
- `DESCRIPTION` Imports/Suggests match what `R/` actually uses
- `pyproject.toml` dependencies match what `geobr/` actually imports
- `pyproject.toml` and `uv.lock` are coherent
- CI workflow paths still match the repo layout
- Metadata agrees across surfaces (URLs, versions, license, maintainer)

### PHASE 2: Triage

Categorize each finding as **genuine bug** (fix) or **false alarm** (discard, and record why so the
next round does not re-raise it).

**Known false alarms — do not "fix" these:**

| Looks wrong | Why it is fine |
|---|---|
| R returns `sf`, Python returns `GeoDataFrame` | Native idiom. Parity is about API and data, not types. |
| R uses arrow + dplyr, Python uses duckdb + pandas | Same. |
| `# nocov start` / `# nocov end` in `utils.R` | Deliberate coverage scoping on network paths. |
| `read_quilombos` (R) vs `read_quilombola_land` (Python) | Pre-existing naming exception, documented in the parity rule. |
| R pins `data_release`; Python calls `releases/latest` | Documented divergence, not a bug. Do not harmonize as a drive-by. |
| `python`/`uv`/`gh` commands "fail" | Not installed on this machine by design. Config must mark them, not remove them. |
| `docs/` content differing from source | Generated by pkgdown; regenerated on release, not hand-edited. |
| Counts inside `quality_reports/` session logs and archives | Historical records, not live docs. |
| `geobr_data_release` in `utils.R:4` unused | Known dead constant, documented. Removing it is a separate deliberate change. |

### PHASE 3: Fix

Apply fixes in parallel where safe. For each: read the file, apply, verify (grep for the stale
value). **Configuration and documentation only** — a finding in `r-package/R/` or
`python-package/geobr/` is *reported*, not silently patched. Package source changes need the
maintainer, because they change what users get.

### PHASE 4: Loop-until-dry

Relaunch a fresh set of agents to verify. This is the loop-until-dry primitive
([`orchestrator-protocol.md`](../../rules/orchestrator-protocol.md)):

- **Converge** when a round surfaces 0 new genuine issues (deduped on file+issue).
- Otherwise fix and loop.
- **Fallback cap: 5 rounds.** A finding surviving rounds N and N+2 is escalated to the user, not
  patched a third time ([`summary-parity.md`](../../rules/summary-parity.md)).

## Output Format

```
## Round N Audit Results

### Issues: X genuine, Y false alarms

| # | Severity | File | Issue | Status |
|---|----------|------|-------|--------|
| 1 | Critical | .claude/rules/foo.md | Dead glob: matches 0 files | Fixed |
| 2 | Medium | CLAUDE.md:47 | utils.R:266 line ref is stale | Fixed |

### Reported, not fixed (package source — needs maintainer)
| File | Issue |
|---|---|

### Verification
- [ ] Every rule glob matches >= 1 file
- [ ] Every documented command exists or is marked as unavailable
- [ ] CLAUDE.md inventory matches disk
- [ ] No references to absent skills/agents/scripts

### Result: [CLEAN | N issues remaining]
```

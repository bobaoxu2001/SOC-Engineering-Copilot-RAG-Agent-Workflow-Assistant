# Build Flow and Makefile Notes

General notes on hardware build flows driven by Make or a Make-like wrapper. These notes describe common patterns and triage steps for build failures. Project-specific flows always take precedence.

## Typical Hardware Build Flow

A reproducible hardware build flow usually has the following stages, each with its own Make target:

1. **Setup** — sources environment scripts, validates tool versions, prepares output directories.
2. **Compile** — runs the simulator's compile step over the RTL and verification files.
3. **Elaborate** — links compiled units and resolves cross-module references.
4. **Simulate** — runs one or more testbenches, optionally in parallel.
5. **Lint** — runs the static checker.
6. **Synthesize** — runs the synthesis tool against the synthesizable subset.
7. **Report** — collects logs and surfaces pass/fail.

Each stage produces artifacts the next stage depends on. A Makefile encodes those dependencies so a developer can rebuild only what changed.

## Makefile Targets

A typical Makefile exposes user-facing targets such as:

- `make compile` — runs only the compile stage.
- `make sim TEST=<name>` — compiles if needed and runs a single test.
- `make regress` — compiles if needed and runs the regression suite.
- `make lint` — runs the linter.
- `make clean` — removes build artifacts but keeps the workspace.
- `make distclean` — removes everything generated.

Each target should be idempotent and should not depend on hidden state in the user's shell.

## Dependency Errors

The most common Make error is a missing rule for a target. The error reads similar to:

```
make: *** No rule to make target 'sim/regress.log'
```

Triage steps:

- Confirm the target name is spelled exactly as defined in the Makefile.
- Confirm the file the target depends on exists. Make will report a missing-rule error if a prerequisite cannot be built.
- Confirm the variable expansions in the Makefile point at real paths. A typo in `$(SIM_DIR)` produces a cryptic missing-target error.
- Run `make -n <target>` to print the commands without executing them; this often reveals the actual broken path.

If the dependency graph is confused after a partial build, `make distclean` followed by a fresh build is a fast recovery.

## Environment Variables

Hardware build flows depend on a long list of environment variables. Common categories:

- Tool roots (`SIM_ROOT`, `SYN_ROOT`).
- Project roots (`PROJ_ROOT`, `RTL_ROOT`).
- License servers (`LM_LICENSE_FILE`).
- Per-user output dirs (`WORK_DIR`).

A reproducible flow validates these at the top of the build. A common failure is that a developer's shell has a stale value pointing at a previous tool version. The fix is to re-source the project's setup script.

## Missing File and Path Errors

Errors of the form:

```
Error: cannot open include file "axi_pkg.svh"
```

usually come from one of:

- The include directory list passed to the compiler does not contain the file's parent directory.
- The file was renamed or moved without updating the file list.
- A new dependency was added to the design but not added to the file list.
- A submodule or external repository was not initialized.

Triage steps:

- Search the workspace for the file name.
- If the file exists, add its directory to the include list (`+incdir+`) or to the file list (`-f` flag).
- If the file does not exist, the dependency is missing; ask the IP owner whether it was renamed, moved, or removed.
- Document the fix in the file list so it does not regress.

This category of issue is usually low risk and can be resolved by the integration or methodology team without requiring a hardware-design review.

## Reproducible Build Tips

- Pin tool versions and environment scripts in the repository rather than relying on the user's shell.
- Treat warnings as errors during compile and elaborate. A noisy build hides real problems.
- Cache compiled libraries when possible, but invalidate the cache on tool-version change.
- Make every target write its log to a deterministic path so CI can attach it on failure.

## Human Review Required

Build failures are usually low risk, but if a build error is the symptom of a deeper issue (for example a reset-timing error caught by elaboration), escalate to a hardware engineer. Use this note for triage; sign-off remains a human responsibility.

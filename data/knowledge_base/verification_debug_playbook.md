# Verification Debug Playbook

A general triage playbook for simulation and regression failures. This is reference guidance only. Sign-off on any verification failure remains a human responsibility.

## Simulation Failure Triage

When a single simulation fails, work through the following steps before changing RTL:

1. **Read the failure message.** The simulator usually points at the file and line of the failing assertion or the last printed message before the crash.
2. **Check the seed.** A failure that reproduces only on one seed is a real bug. A failure that reproduces on every seed is likely a structural issue.
3. **Check recent changes.** Run `git log` against the testbench, the RTL, and any shared libraries that were updated since the last green run.
4. **Reproduce locally.** Confirm the failure reproduces outside the regression environment with the same seed and configuration.
5. **Open the waveform.** Capture a focused view around the failure cycle. Most failures are visible within a few hundred cycles of the assertion.
6. **Check for upstream warnings.** Many "real" failures are downstream of a warning that was suppressed earlier in the run.

## Regression Failure Categories

Regression failures usually fall into one of the following categories:

- **Build failure** — compile or elaborate failed. Triage with the build-flow note.
- **Timeout** — the test ran past its time budget. Often a hang in the design or a stuck handshake. Always escalate hangs.
- **Assertion failure** — a concurrent or immediate assertion fired. Read the assertion text first.
- **Score-board mismatch** — the testbench saw a value different from what it expected. Check both the design and the reference model.
- **Coverage shortfall** — the test ran clean but did not hit a required coverage point. Usually a stimulus issue, not a design bug.
- **Infrastructure failure** — license server, file system, or compute farm. Re-run before debugging.

Tag each failure with one of these categories before triage so the team can spot trends.

## Waveform and Debug Notes

A productive waveform debug session usually proceeds as follows:

- Start at the failure point and walk backward in time until the symptom first appears.
- Group signals by interface (clock, reset, request, response) so the protocol is readable at a glance.
- Use markers to annotate the cycles where interesting transitions happen.
- Save the wave configuration so future debug sessions reproduce the same view.

If the failure cycle does not show a clear cause, expand the time range and look for resets, clock-gating events, or upstream stalls.

## Assertion Failures

Assertion failures are high-signal events. The common causes are:

- A real design bug.
- A bug in the assertion itself (most often a missing disable on reset).
- A testbench driving an illegal stimulus that should have been constrained.
- A timing assumption that no longer holds after a recent design change.

Treat every assertion failure as a real bug until proven otherwise. Waiving an assertion without root cause is a recurring source of silent regressions.

## Testbench Configuration

A common source of "false positive" failures is a stale testbench configuration:

- Plus-args mismatched between the test list and the testbench.
- A reference model that was not regenerated after the spec changed.
- A coverage exclusion that was scoped too broadly.
- A constraint that was tightened or relaxed without updating the test plan.

Before chasing a design bug, confirm that the testbench is configured correctly for the test under debug.

## Escalation Rules

Escalate to a hardware engineer or to the design owner when:

- The failure crosses a clock domain.
- The failure involves reset deassertion timing.
- The failure involves an integration boundary (IP-to-IP or IP-to-fabric).
- A waiver is being considered without an identified root cause.
- The failure reproduces only on hardware-realistic timing, not in functional simulation.

These topics are explicitly high risk and require human review. The playbook is a starting point, not a sign-off authority.

## Human Review Required

Verification failures touching reset, clock-domain crossing, or integration must be triaged by a qualified hardware engineer. Use this playbook to gather evidence; do not waive failures based on the playbook alone.

# SystemVerilog Notes

General-purpose notes on SystemVerilog constructs that come up frequently in RTL and verification reviews. This is background guidance only; project coding standards always take precedence.

## always_ff and always_comb

SystemVerilog introduced specialized always blocks that document intent and let the linter catch mistakes early.

- `always_ff @(posedge clk or negedge rst_n)` is for sequential logic. The tool will warn if the block infers combinational behavior.
- `always_comb` is for combinational logic. The tool will warn on inferred latches and missing assignments. Prefer this over the legacy `always @(*)` form.
- `always_latch` is for the rare case where a latch is intentional. Most projects ban this construct.

Inside `always_ff`, use non-blocking assignment. Inside `always_comb`, use blocking assignment. Mixing the two inside one block is almost always a bug.

## Module Interfaces

SystemVerilog `interface` blocks bundle related signals and modports together so a single connection covers many ports. They reduce the wiring boilerplate at integration time and make it harder to forget a signal.

A typical interface includes:

- Signal declarations grouped by direction.
- One or more `modport` declarations naming the role of each side (for example `master` and `slave`).
- Optional clocking blocks for testbench use.

Interfaces are powerful but can hide signals from grep-based reviews. Many projects allow interfaces in verification but require flat ports at synthesizable boundaries. Confirm with your project's style guide.

## Parameters and localparams

Parameters make a module reusable across widths and configurations. Localparams are derived constants that should not be overridden from outside.

- Use parameters for widths, depths, and feature toggles.
- Use localparams for derived values such as address-width log2 calculations.
- Validate parameter combinations with `initial` checks or `assert` statements so an illegal configuration fails loudly.
- Avoid using parameters to swap entire architectures inside one module. Prefer a separate module per architecture.

## Assertions Basics

Inline assertions document design intent and catch violations during simulation.

- **Immediate assertions** (`assert (...)`) check a condition at a single point in time and are useful inside procedural code.
- **Concurrent assertions** (`assert property (...)`) check a property over time using sequence and property operators. They are typically placed in a separate assertion block or bound to the design from verification code.
- **Assumptions** (`assume`) constrain inputs during formal verification.
- **Cover** statements record that a scenario was exercised, which feeds functional coverage.

Assertion failures should be treated as build-breaking unless explicitly waived. A single waived assertion accumulating over time is how silent regressions enter a release.

## Common Coding Pitfalls

- Using `logic` everywhere without thinking about whether a signal is intended to be a register or a wire. `logic` is fine syntactically but reviewers still need to know intent.
- Width mismatches in port connections. SystemVerilog will silently extend or truncate; some lint rules promote this to an error.
- Using `==` to compare signals that may contain `X` or `Z`. Use `===` only in testbenches; never in synthesizable RTL.
- Forgetting that `unique case` and `priority case` change synthesis behavior in addition to acting as lint hints.
- Calling `$display` from synthesizable code. It will be ignored by synthesis, but it is a sign the author was debugging in production code.

## Review Checklist

- Every always block uses the SystemVerilog-specific form (`always_ff` or `always_comb`).
- Width of each assignment matches both sides.
- No `always_latch` unless reviewed and justified.
- Assertions guard high-risk transitions (reset, handshake completion, pointer wrap).
- No `$display` or `$strobe` in synthesizable code paths.

## Human Review Required

Assertion failures, width-mismatch warnings escalated to errors, and any use of `unique` or `priority` modifiers warrant a careful human review. Use this note as a starting point, not as sign-off authority.

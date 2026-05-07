# RTL Design Basics

This note summarizes general, public-domain guidance for engineers writing or reviewing register-transfer-level (RTL) hardware designs. It is reference material only and is not a substitute for project-specific coding standards, tool documentation, or human review by a qualified hardware engineer.

## Overview of RTL

Register-transfer-level design describes a digital circuit in terms of the data flow between registers and the combinational logic that operates on that data. Typical RTL is written in Verilog or SystemVerilog and is later synthesized into a gate-level netlist. The two key building blocks are:

- **Combinational logic** — outputs are a pure function of current inputs. No state is implied. Modeled with `assign`, ternary expressions, or `always_comb`.
- **Sequential logic** — outputs depend on stored state and update on a clock edge. Modeled with `always_ff @(posedge clk)`.

A clean RTL module separates combinational next-state logic from sequential state updates. Mixing them leads to simulation-synthesis mismatches and review pushback.

## Module Structure

A reviewable Verilog or SystemVerilog module typically contains, in order:

1. Header comment describing purpose, owner, and known limitations.
2. Module declaration with explicit port directions and widths.
3. Parameters and localparams.
4. Internal signal declarations grouped by function.
5. Combinational blocks (`always_comb` / `assign`).
6. Sequential blocks (`always_ff`).
7. Assertions and coverage (if used).

Avoid hidden state created by inferred latches, missing default cases, or partially-assigned variables in `always_comb`.

## Blocking vs Non-Blocking Assignment

This is one of the most common review findings.

- Use **non-blocking assignment** (`<=`) for sequential logic inside `always_ff`. Non-blocking assignments evaluate the right-hand side at the start of the time step and update the left-hand side at the end, which models real flip-flop behavior and avoids race conditions between concurrent always blocks.
- Use **blocking assignment** (`=`) for combinational logic inside `always_comb`. Blocking assignments execute in order, which is what you want when computing an intermediate value before producing an output.
- Never mix the two inside the same always block, and never use blocking assignment for a register that is read by another always block.

## Reset Strategy

Every flop should have a defined reset value or a documented reason it is reset-exempt. The two common styles are:

- **Synchronous reset** — reset is sampled with the clock edge. Easier to time, but requires the clock to be running for reset to take effect.
- **Asynchronous reset, synchronous deassertion** — reset takes effect immediately, but its release is synchronized to the clock to avoid metastability on the deassertion edge. This is the most common SOC style.

Mixing reset styles inside a single clock domain is a recurring source of bugs and is itself a high-risk topic that should be reviewed by a hardware engineer; do not infer a reset strategy from this guide alone.

## Common RTL Review Checklist

- All ports have explicit direction and width.
- No inferred latches in `always_comb` blocks (every signal assigned on every path).
- Sequential blocks use non-blocking assignment.
- Combinational blocks use blocking assignment.
- All flops have a reset value or are explicitly noted as reset-exempt.
- No magic numbers in port widths or counters; use parameters.
- Module names, signal names, and file names follow project naming conventions.
- Outputs of one clock domain are never read directly by another clock domain (see the CDC note).

## Common Pitfalls

- Using `always @(*)` instead of `always_comb`, which loses the linter's ability to flag missing assignments.
- Reading a registered signal in the same cycle it is written.
- Driving the same net from two always blocks.
- Forgetting to reset a counter, which leads to nondeterministic post-reset behavior.
- Implicit width truncation in arithmetic, which silently drops bits and is hard to find in waveforms.

## Human Review Required

Reset architecture choices, the boundary between combinational and sequential logic in pipelined designs, and any change that crosses a clock domain are high-risk topics. Treat the guidance above as background reading. A qualified hardware engineer must review the final implementation before it lands.

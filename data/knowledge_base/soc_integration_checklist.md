# SOC Integration Checklist

A general-purpose checklist for engineers integrating an IP block into a system-on-chip top-level. This is reference material for review preparation and is not an integration sign-off authority. Final integration sign-off must come from a qualified hardware engineer.

## IP Integration Checklist

Before instantiating a new IP block at the SOC top level, confirm the following items have been reviewed with the IP owner:

- The IP version and release notes match what was integrated.
- The integration guide and known-issues list have been read.
- All required clocks, resets, and power domains exist at the planned instantiation point.
- Configuration parameters have been chosen and documented.
- The register map has been reviewed and merged into the SOC address map.
- Interrupt outputs are routed to the interrupt controller.
- DFT and scan signals are connected per the DFT methodology.

Each of these items is itself a high-risk topic and should be reviewed by a qualified engineer with project context.

## Interface Consistency

Mismatched interfaces are the most common integration bug.

- Confirm protocol family and version match between producer and consumer (for example, AXI4 master to AXI4 slave, with the same data width and ID width).
- Confirm endianness and byte-enable conventions.
- Confirm response ordering assumptions; some IP blocks expect strict order, others can absorb out-of-order responses.
- Confirm that user-defined sideband signals are sized and assigned consistently on both sides.

A protocol checker placed at the SOC boundary catches a large fraction of these issues during simulation and is recommended for any new integration.

## Clock and Reset Connections

Clock and reset connections are a high-risk integration topic. The integrator must:

- Identify every clock domain the IP uses, including gated, divided, and asynchronous clocks.
- Identify every reset, its polarity, and its synchronization style.
- Confirm that any signal crossing between clock domains uses an approved CDC structure (see the CDC note).
- Confirm reset deassertion ordering across the IP and its dependents.

Do not infer the correct connection from this checklist. Always confirm against the IP integration guide and have a hardware engineer review the final wiring.

## Register Map Review

The integrator merges the IP register map into the SOC-level memory map.

- Confirm the IP's base address has no overlap with existing peripherals.
- Confirm address alignment matches the bus protocol requirements.
- Confirm reserved fields are documented as read-as-zero or read-as-undefined.
- Confirm software-visible registers have access types (RO, RW, W1C) that match the hardware behavior.
- Re-run the address-map generator and diff the output against the previous release.

## Dependency Handoff

A clean handoff from the IP team to the integrator includes:

- A version-stamped release tarball or repository tag.
- The integration guide.
- A simulation testbench that runs against the released IP standalone.
- A list of synthesis attributes or constraints required by the IP.
- A contact owner for follow-up questions.

If any of these are missing, escalate to the IP owner before integrating.

## Integration Risk Examples

Common integration failure modes seen across many projects:

- Connecting an IP that requires an asynchronous reset to a top-level synchronous reset tree.
- Forgetting to constrain the relationship between two clocks the IP assumes are asynchronous.
- Driving an IP's configuration strap from a register that resets later than the IP itself.
- Tying an unused interrupt output directly to ground, which suppresses a real interrupt if the IP is later enabled.
- Mismatching the AXI ID width and silently truncating transactions.

## Human Review Required

Integration is one of the highest-risk activities at the SOC level. Every item on this checklist warrants a human review. This note is a preparation aid only; the final integration must be reviewed and signed off by a qualified hardware engineer.

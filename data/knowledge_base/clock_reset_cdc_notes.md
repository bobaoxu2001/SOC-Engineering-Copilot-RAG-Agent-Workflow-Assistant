# Clock, Reset, and CDC Notes

General reference notes on clock domains, reset synchronization, and clock-domain crossing (CDC). Every topic in this note is a high-risk hardware area. The notes are background reading only; final architecture decisions and sign-off must come from a qualified hardware engineer.

## Clock Domains

A clock domain is the set of flops that share the same clock source, with a defined frequency, phase, and duty cycle. Modern SOCs contain many clock domains because different IP blocks operate at different speeds and because power management gates clocks aggressively.

When reviewing a design that contains multiple clock domains, expect:

- A clock-tree definition document or constraint file naming each clock and its source.
- A list of asynchronous-clock relationships (which pairs of clocks have no defined phase relationship).
- A list of synchronous-clock relationships (which pairs of clocks share a source and a defined ratio).

Any signal that crosses from one clock domain to another is a CDC path and must use an approved CDC structure.

## Reset Synchronization

Reset deassertion is one of the most common failure modes in SOCs.

- Reset assertion is usually asynchronous so the design can be forced into a known state regardless of clock state.
- Reset deassertion is synchronized to the clock so that all flops in a domain leave reset on the same edge. Without synchronization, flops can leave reset on different cycles and the design enters an undefined state.
- Each clock domain typically has its own reset synchronizer, fed by a common reset source.
- Reset polarity (active-high vs active-low) must be consistent within a domain.

A reset architecture review asks the following questions:

- How many reset domains exist?
- How is each reset deasserted, and is the deassertion synchronized to the local clock?
- What is the reset deassertion ordering between IP blocks?
- Is the reset asserted long enough for every flop to capture it?

These questions cannot be answered from this note alone. They require hardware-engineer review against the project's specific reset architecture.

## CDC Risks

Clock-domain crossing is a high-risk topic. The most common CDC structures are:

- **Two-flop synchronizer** — for single-bit asynchronous control signals. Cheap and well understood, but only safe for slowly-changing signals.
- **Handshake (req/ack) synchronizer** — for multi-bit data transfers where the source can hold the data stable until the destination acknowledges.
- **Asynchronous FIFO** — for high-throughput data transfer between two clock domains.
- **Gray-coded counter crossing** — for pointer-style information where only one bit changes at a time.

Common CDC bugs:

- Sending a multi-bit bus through two-flop synchronizers and assuming the bits will stay aligned. They will not.
- Forgetting that the destination domain must have a defined reset before sampling synchronized data.
- Allowing the source data to change before the destination has captured a stable value.
- Mixing synchronous and asynchronous logic on the same path so the structure is not recognized by CDC tools.

CDC issues often pass functional simulation because the simulator does not model metastability. They fail in silicon. A dedicated CDC tool run is required for any design that touches a CDC path.

## Metastability Basics

A flop sampled in its setup-or-hold window can enter a metastable state where its output is neither a clean 0 nor a clean 1 for a short window of time. Synchronizers do not eliminate metastability; they reduce its probability of propagating to acceptable levels by allowing it to settle across multiple clock cycles.

Practical implications:

- Mean-time-between-failure (MTBF) for a synchronizer depends on clock frequency, transition rate, and the chosen number of stages. Project methodology defines the required stages.
- A path that "almost always works" in simulation is not safe. Metastability is a statistical event.

## Review Checklist

- Every clock used by a flop has a constraint defining its frequency and source.
- Every cross-domain signal uses an approved CDC structure named in the methodology.
- Every reset has a defined synchronization style and polarity.
- A CDC tool has been run on the latest RTL and its waivers have been reviewed.
- Reset deassertion ordering across IPs is documented.

## Human Review Required

Every topic in this note — clock-domain definitions, reset architecture, CDC structures, and metastability mitigation — is high risk and must be reviewed by a qualified hardware engineer. Treat this material as preparation for that review, not as a substitute for it.

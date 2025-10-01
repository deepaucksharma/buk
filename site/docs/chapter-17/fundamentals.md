# CRDT Fundamentals: The Mathematics of Convergence

## The Convergence Problem

In distributed systems, replicas must stay consistent despite network delays, partitions, and concurrent updates. Traditional solutions use coordination: locks prevent conflicts, consensus protocols order operations, leader election serializes writes. But coordination has costs - latency, availability, complexity.

CRDTs take a different approach: eliminate conflicts through mathematical design. By restricting operations to those with specific algebraic properties, CRDTs guarantee automatic convergence without coordination. This is not conflict resolution - it's conflict prevention through mathematical structure.

The insight: if operations commute (produce the same result regardless of order), and merge is associative, commutative, and idempotent, then replicas will converge to the same state regardless of message delays or reordering. This is Strong Eventual Consistency - eventual consistency with a guarantee that replicas seeing the same operations will be in the same state.

## Guarantee Vector for CRDT Theory

The theoretical foundation of CRDTs can be expressed through a guarantee vector that captures the essential properties:

```
CRDT Theory G-Vector = ⟨Regional, Causal, RA, EO, Idem(lattice), Auth⟩

Where:
  Regional      → Complete autonomy (no coordination ever)
  Causal        → Causality preserved through structure
  RA            → Read Always available (no blocking)
  EO            → Eventual Order through lattice convergence
  Idem          → Idempotent merge (lattice join)
  Auth          → Authority through causality (not centralized)

Mathematical Foundation:
  Convergence = lim[t→∞] ⊔{replica₁(t), replica₂(t), ..., replicaₙ(t)}

  Where ⊔ is the join operation satisfying:
    ∀ a,b,c ∈ Lattice:
      a ⊔ b = b ⊔ a              (Commutativity)
      (a ⊔ b) ⊔ c = a ⊔ (b ⊔ c)  (Associativity)
      a ⊔ a = a                  (Idempotency)
      a ⊔ (b ⊔ c) = (a ⊔ b) ⊔ (a ⊔ c) (Distributivity, optional)
```

### Strong Eventual Consistency

Strong Eventual Consistency (SEC) is the key guarantee:

```
SEC Definition:
  ∀ replicas r₁, r₂:
    (r₁.history = r₂.history) ⟹ (r₁.state = r₂.state)

  Where history = set of operations received

Stronger than Eventual Consistency:
  EC:  Replicas eventually converge
  SEC: Replicas with same ops are in same state (deterministic)

SEC Theorem:
  Given:
    1. All operations eventually delivered to all replicas
    2. Merge is commutative, associative, idempotent
  Then:
    All replicas converge to same state (LUB of operations)

  Proof:
    By induction on number of operations
    Base: Empty operation set → all replicas at bottom (⊥)
    Step: Adding operation op
      For replicas r₁, r₂ with same history H:
        r₁ = ⊔ H
        r₂ = ⊔ H
        By associativity and commutativity of ⊔:
          ⊔ H is independent of order
        Therefore: r₁ = r₂
    QED
```

## Context Capsules: Theory in Action

Context capsules mark theoretical boundaries where CRDT properties are verified:

### Lattice Join Capsule

```
╔══════════════════════════════════════════════════════════╗
║ LATTICE JOIN CONTEXT CAPSULE                             ║
║ Location: Semilattice Merge Operation                    ║
╠══════════════════════════════════════════════════════════╣
║ Pre-Join State:                                          ║
║   State A: {x, y}    Position in lattice: L₁            ║
║   State B: {y, z}    Position in lattice: L₂            ║
║                                                          ║
║ Lattice Structure:                                       ║
║   Partial Order: A ⊆ B defined by subset relation       ║
║   Join Operation: ⊔ = set union                          ║
║   L₁ and L₂ are concurrent (neither ⊆ other)            ║
║                                                          ║
║ Join Computation:                                        ║
║   L₁ ⊔ L₂ = {x, y} ∪ {y, z} = {x, y, z}                 ║
║                                                          ║
║ Algebraic Verification:                                  ║
║   Commutativity: {x,y} ∪ {y,z} = {y,z} ∪ {x,y} ✓        ║
║   Associativity: ({a}∪{b})∪{c} = {a}∪({b}∪{c}) ✓       ║
║   Idempotency:   {x,y} ∪ {x,y} = {x,y} ✓                ║
║                                                          ║
║ Post-Join State:                                         ║
║   State A ⊔ B: {x, y, z}    Position: LUB(L₁, L₂)      ║
║                                                          ║
║ Guarantee Witness:                                       ║
║   ✓ Join is well-defined (unique LUB)                   ║
║   ✓ Result higher in lattice: {x,y,z} ⊇ {x,y}, {y,z}   ║
║   ✓ Join is commutative (order independent)             ║
║   ✓ Convergence guaranteed (all paths lead to LUB)      ║
╚══════════════════════════════════════════════════════════╝
```

### Commutativity Verification Capsule

```
╔══════════════════════════════════════════════════════════╗
║ COMMUTATIVITY CONTEXT CAPSULE                            ║
║ Location: Concurrent Operation Application               ║
╠══════════════════════════════════════════════════════════╣
║ Initial State: S₀ = {a}                                 ║
║                                                          ║
║ Concurrent Operations:                                   ║
║   op₁: add(b)                                           ║
║   op₂: add(c)                                           ║
║   Causal: op₁ ∥ op₂ (neither happened-before other)     ║
║                                                          ║
║ Execution Path 1:                                        ║
║   S₀ → apply(op₁) → S₁ = {a, b}                        ║
║   S₁ → apply(op₂) → S₂ = {a, b, c}                     ║
║                                                          ║
║ Execution Path 2:                                        ║
║   S₀ → apply(op₂) → S₁' = {a, c}                       ║
║   S₁' → apply(op₁) → S₂' = {a, b, c}                   ║
║                                                          ║
║ Commutativity Verification:                              ║
║   apply(op₁, apply(op₂, S₀)) = {a, b, c}               ║
║   apply(op₂, apply(op₁, S₀)) = {a, b, c}               ║
║   Therefore: S₂ = S₂' ✓                                 ║
║                                                          ║
║ Algebraic Proof:                                         ║
║   apply(add(x), S) = S ∪ {x}                            ║
║   (S ∪ {b}) ∪ {c} = (S ∪ {c}) ∪ {b}  (set union comm) ║
║                                                          ║
║ Guarantee Witness:                                       ║
║   ✓ Operations commute                                  ║
║   ✓ Order doesn't affect final state                    ║
║   ✓ Concurrent execution safe                           ║
║   ✓ No coordination needed                              ║
╚══════════════════════════════════════════════════════════╝
```

### Monotonicity Enforcement Capsule

```
╔══════════════════════════════════════════════════════════╗
║ MONOTONICITY CONTEXT CAPSULE                             ║
║ Location: State Transition in Lattice                    ║
╠══════════════════════════════════════════════════════════╣
║ Lattice Definition:                                      ║
║   L = (States, ≤) where S₁ ≤ S₂ iff S₁ ⊆ S₂            ║
║                                                          ║
║ Current State:                                           ║
║   S_current = {x, y}                                     ║
║   Position: Point P in lattice                           ║
║                                                          ║
║ Operation: add(z)                                        ║
║                                                          ║
║ Monotonicity Check:                                      ║
║   S_new = S_current ∪ {z} = {x, y, z}                   ║
║   Verify: S_current ≤ S_new                             ║
║   Check: {x, y} ⊆ {x, y, z} ✓                           ║
║                                                          ║
║ Lattice Movement:                                        ║
║   Old Position: P                                        ║
║   New Position: P' where P ≤ P'                         ║
║   Movement: Upward in lattice (monotonic)               ║
║                                                          ║
║ Invariant Verification:                                  ║
║   ∀ operations op: apply(op, S) ≥ S                     ║
║   Proof: add only increases set, never decreases ✓      ║
║                                                          ║
║ Guarantee Witness:                                       ║
║   ✓ State evolution is monotonic                        ║
║   ✓ No information loss                                 ║
║   ✓ Causal consistency possible                         ║
║   ✓ Lattice structure preserved                         ║
╚══════════════════════════════════════════════════════════╝
```

## Sacred Diagrams: Visualizing CRDT Theory

### Diagram 1: Join-Semilattice Structure

```
                        ┌─────────────────┐
                        │   {a, b, c, d}  │ ← Top (LUB)
                        │      (⊤)        │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
       ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
       │  {a, b, c}  │    │  {a, b, d}  │    │  {a, c, d}  │
       └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
              │                  │                  │
        ┌─────┼─────┐      ┌─────┼─────┐      ┌─────┼─────┐
        │           │      │           │      │           │
   ┌────▼────┐ ┌────▼────┐│      ┌────▼────┐│      ┌────▼────┐
   │ {a, b}  │ │ {a, c}  ││      │ {a, d}  ││      │ {c, d}  │
   └────┬────┘ └────┬────┘│      └────┬────┘│      └────┬────┘
        │           │     │           │     │           │
        └─────┬─────┘     │     ┌─────┘     │     ┌─────┘
              │           │     │           │     │
         ┌────▼────┐  ┌───▼─────▼───┐  ┌────▼─────▼────┐
         │  {a}    │  │    {b}      │  │    {c}        │
         └────┬────┘  └──────┬──────┘  └──────┬────────┘
              │              │                 │
              └──────────────┼─────────────────┘
                             │
                      ┌──────▼──────┐
                      │      ∅      │ ← Bottom
                      │     (⊥)     │
                      └─────────────┘

Properties:
  • Partial Order: ≤ defined by ⊆ (subset)
  • Join Operation: ⊔ = ∪ (union)
  • Every pair has LUB: a ⊔ b always exists
  • Bounded: has bottom (∅) and top ({a,b,c,d})
  • Complete: every subset has LUB

Convergence Proof:
  Any two states S₁, S₂ → S₁ ⊔ S₂ (unique)
  All paths to same operations → same LUB
```

### Diagram 2: State-based vs Operation-based CRDTs

```
┌─────────────────────────────────────────────────────────────┐
│                  STATE-BASED CRDTs (CvRDT)                  │
└─────────────────────────────────────────────────────────────┘

Replica A                                        Replica B
┌───────────┐                                   ┌───────────┐
│ State: S₁ │                                   │ State: S₂ │
│ {x, y}    │                                   │ {y, z}    │
└─────┬─────┘                                   └─────┬─────┘
      │                                               │
      │ 1. Send                               1. Send│
      │    entire                             entire │
      │    state                              state  │
      │                                               │
      │                ┌─────────────┐               │
      └───────────────►│   Network   │◄──────────────┘
                       │   (State    │
                       │   Transfer) │
                       └──────┬──────┘
                              │
                              │ 2. Merge
                              │    S₁ ⊔ S₂
                              ▼
                    ┌─────────────────┐
                    │  Merged State:  │
                    │  {x, y, z}      │
                    │  (LUB)          │
                    └─────────────────┘

Properties:
  • Ship: Entire state (can be large)
  • Merge: Lattice join operation
  • Order: Any order works (commutative)
  • Idempotent: Repeated sends OK
  • Bandwidth: O(state size) per sync

┌─────────────────────────────────────────────────────────────┐
│                OPERATION-BASED CRDTs (CmRDT)                │
└─────────────────────────────────────────────────────────────┘

Replica A                                        Replica B
┌───────────┐                                   ┌───────────┐
│ State: S  │                                   │ State: S  │
│ {x}       │                                   │ {x}       │
└─────┬─────┘                                   └─────┬─────┘
      │                                               │
      │ op₁: add(y)                     op₂: add(z)  │
      ▼                                               ▼
┌───────────┐                                   ┌───────────┐
│ State: S₁ │                                   │ State: S₂ │
│ {x, y}    │                                   │ {x, z}    │
└─────┬─────┘                                   └─────┬─────┘
      │                                               │
      │ 1. Send                               1. Send│
      │    operation                          op     │
      │    add(y)                             add(z) │
      │                                               │
      │        ┌───────────────────────┐             │
      └───────►│      Network          │◄────────────┘
               │   (Op Broadcast +     │
               │    Causal Delivery)   │
               └───────┬───────────────┘
                       │
                       │ 2. Apply ops
                       │    (both sides)
                       ▼
            ┌─────────────────────┐
            │   Both Replicas:    │
            │   apply(add(y))     │
            │   apply(add(z))     │
            │   Final: {x, y, z}  │
            └─────────────────────┘

Properties:
  • Ship: Individual operations (small)
  • Apply: Execute operation on state
  • Order: Requires causal delivery
  • Idempotent: Need op deduplication
  • Bandwidth: O(op size) per operation
```

### Diagram 3: Causality and Vector Clocks

```
Event Timeline (Three Replicas):

Replica A:  e₁ ──────► e₂ ──────────────────────► e₅
             │          │                          ▲
        add(x)     add(y)                          │
      VC:{A:1}   VC:{A:2}                          │
             │          │                          │
             │          └─────────(op)─────────────┘
             │                                     │
             │                                     │
Replica B:   └────(op)────► e₃ ─────────────────► e₆
                             │                     ▲
                        add(z)                     │
                      VC:{A:1,B:1}                 │
                             │                     │
                             └────────(op)─────────┘
                                                   │
                                                   │
Replica C:                          e₄ ───────────┘
                                    │
                               remove(x)
                             VC:{A:1,C:1}

Causal Relations:
  e₁ → e₂  (same replica, sequential)
  e₁ → e₃  (operation sent from A to B)
  e₁ → e₄  (operation sent from A to C)
  e₂ ∥ e₃  (concurrent - different replicas)
  e₂ ∥ e₄  (concurrent)
  e₃ ∥ e₄  (concurrent)
  {e₂, e₃, e₄} → e₅  (all causally precede e₅)

Vector Clock Comparison:
  VC1 ≤ VC2  iff  ∀i: VC1[i] ≤ VC2[i]
  VC1 ∥ VC2  iff  neither VC1 ≤ VC2 nor VC2 ≤ VC1

Examples:
  {A:1} ≤ {A:2}         → e₁ → e₂ (causal)
  {A:1,B:1} ∥ {A:1,C:1} → e₃ ∥ e₄ (concurrent)
  {A:2} ≤ {A:2,B:1,C:1} → e₂ → e₅ (causal)

Merge Rule:
  VC1 ⊔ VC2 = {A: max(VC1[A], VC2[A]),
               B: max(VC1[B], VC2[B]),
               C: max(VC1[C], VC2[C])}
```

### Diagram 4: CvRDT vs CmRDT Duality

```
┌─────────────────────────────────────────────────────────────┐
│                       CvRDT ↔ CmRDT                         │
│                                                             │
│  State-based                        Operation-based         │
│                                                             │
│     State                                Operation          │
│       ↕                                      ↕              │
│     Merge                                  Apply            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  CvRDT Requirements:           CmRDT Requirements:          │
│  • State forms semilattice     • Operations commute         │
│  • Merge = lattice join        • Causal delivery           │
│  • Any order merge OK          • At-most-once delivery     │
│                                • Ops eventually delivered   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Advantages:                   Advantages:                  │
│  • No delivery constraints     • Bandwidth efficient        │
│  • Simpler correctness proof   • Lower latency             │
│  • Works over any network      • Captures intent clearly    │
│                                                             │
│  Disadvantages:                Disadvantages:               │
│  • Bandwidth intensive         • Needs causal broadcast     │
│  • State can grow large        • Delivery tracking needed   │
│  • Merge can be expensive      • More complex protocol     │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Conversion:
  CvRDT → CmRDT:
    • State becomes initial state
    • Each state update becomes operation
    • Merge becomes sequential operation application

  CmRDT → CvRDT:
    • Operations become state changes
    • Track all operations in state
    • Merge = union of operation sets
```

### Diagram 5: Convergence Timeline

```
Timeline of Replica Convergence:

T₀: Initial Sync
    ┌─────┐  ┌─────┐  ┌─────┐
    │  A  │  │  B  │  │  C  │  All: {x}
    │ {x} │  │ {x} │  │ {x} │  VC: {A:0,B:0,C:0}
    └─────┘  └─────┘  └─────┘
    ▲────────────┴────────────▲  Converged ✓

T₁: Divergence Begins
    ┌─────┐  ┌─────┐  ┌─────┐
    │  A  │  │  B  │  │  C  │
    │{x,y}│  │ {x} │  │ {x} │  A: add(y)
    └─────┘  └─────┘  └─────┘  VC: A:{A:1,B:0,C:0}
                                Diverged (degree: 1)

T₂: More Divergence
    ┌─────┐  ┌─────┐  ┌─────┐
    │  A  │  │  B  │  │  C  │
    │{x,y}│  │{x,z}│  │{x,w}│  B: add(z), C: add(w)
    └─────┘  └─────┘  └─────┘  All concurrent
                                Diverged (degree: 3)

T₃: Partial Sync (A ↔ B)
    ┌─────┐  ┌─────┐  ┌─────┐
    │  A  │  │  B  │  │  C  │
    │{x,y,│  │{x,y,│  │{x,w}│  A,B merge
    │  z} │  │  z} │  │     │  VC: A,B:{A:1,B:1,C:0}
    └─────┘  └─────┘  └─────┘  Partially converged

T₄: Full Sync
    ┌─────┐  ┌─────┐  ┌─────┐
    │  A  │  │  B  │  │  C  │
    │{x,y,│  │{x,y,│  │{x,y,│  All merge
    │ z,w}│  │ z,w}│  │ z,w}│  VC: {A:1,B:1,C:1}
    └─────┘  └─────┘  └─────┘
    ▲────────────┴────────────▲  Converged ✓

Metrics:
  Divergence Degree: max differences between replicas
  Convergence Time: T₄ - T₁ = time to full sync
  Sync Rounds: 2 (T₃ partial, T₄ full)
```

## Algebraic Foundations

### Join-Semilattice

A join-semilattice is the fundamental structure for state-based CRDTs:

```
Definition:
  A join-semilattice is (S, ⊔) where:
    1. ∀a,b ∈ S: a ⊔ b ∈ S               (Closure)
    2. ∀a,b ∈ S: a ⊔ b = b ⊔ a           (Commutativity)
    3. ∀a,b,c ∈ S: (a⊔b)⊔c = a⊔(b⊔c)    (Associativity)
    4. ∀a ∈ S: a ⊔ a = a                 (Idempotency)

Partial Order:
  Define a ≤ b iff a ⊔ b = b
  This creates a partial order (reflexive, antisymmetric, transitive)

LUB (Least Upper Bound):
  For any subset X ⊆ S, if it has an upper bound,
  it has a unique least upper bound: ⊔ X

Examples:
  1. (ℕ, max): Natural numbers with max
     Join: max(a, b)
     Order: a ≤ b iff a ≤ b (usual ordering)

  2. (𝒫(U), ∪): Powerset with union
     Join: A ∪ B
     Order: A ⊆ B (subset)

  3. (ℕ × ℕ, ⊔): Pairs with element-wise max
     Join: (a₁,a₂) ⊔ (b₁,b₂) = (max(a₁,b₁), max(a₂,b₂))
     Order: (a₁,a₂) ≤ (b₁,b₂) iff a₁≤b₁ ∧ a₂≤b₂
```

### Monotonic Functions

Operations on CRDTs must be monotonic:

```
Definition:
  A function f: L₁ → L₂ between semilattices is monotonic if:
    ∀a,b ∈ L₁: a ≤ b ⟹ f(a) ≤ f(b)

  Preserves the partial order

Inflation:
  A function f: L → L is inflationary if:
    ∀a ∈ L: a ≤ f(a)

  Always moves up the lattice

Examples:
  Monotonic:
    • add(element) to a set
    • increment on a counter
    • max(value, new_value)

  Non-monotonic (breaks CRDTs):
    • remove(element) without tombstone
    • set(value) without timestamp
    • decrement without N-counter
```

### Commutativity

Operations must commute for convergence:

```
Definition:
  Operations op₁, op₂ commute if:
    ∀ state S:
      apply(op₁, apply(op₂, S)) = apply(op₂, apply(op₁, S))

Commutativity Classes:

  1. Syntactic Commutativity:
     Operations that obviously commute
     Example: add(x) and add(y) where x ≠ y

  2. Semantic Commutativity:
     Operations commute given CRDT semantics
     Example: add(x,t1) and remove(x,t2) in OR-Set
               (add wins if t1 and t2 concurrent)

  3. Conditional Commutativity:
     Operations commute under conditions
     Example: increment(n) always commutes
              set(v) only commutes if timestamps used

Testing Commutativity:
  For all operation pairs (op₁, op₂):
    1. Start from same state S
    2. Apply in both orders
    3. Verify result equality
    4. If not equal: operations don't commute
```

## Causality and Vector Clocks

Causality is crucial for preserving user intent:

### Happens-Before Relation

```
Definition (Lamport):
  The happens-before relation → is defined:
    1. If a and b are events on same replica, and a before b,
       then a → b
    2. If a is send(m) and b is receive(m), then a → b
    3. If a → b and b → c, then a → c (transitivity)

  Events are concurrent (a ∥ b) if neither a → b nor b → a

Causal History:
  The causal history of event e is:
    H(e) = {e' | e' → e}

  The set of all events that causally precede e
```

### Vector Clocks

```
Definition:
  A vector clock VC is a function: Replicas → ℕ
  VC[r] = number of events on replica r

Operations:
  1. Initialize: VC[r] = 0 for all replicas r

  2. Local event on replica r:
     VC[r] := VC[r] + 1

  3. Send message m from replica r:
     Attach VC to message: m.vc = VC

  4. Receive message m at replica r:
     VC[r] := max(VC[r], m.vc[r]) for all replicas
     VC[r] := VC[r] + 1

Comparison:
  VC₁ ≤ VC₂  iff  ∀r: VC₁[r] ≤ VC₂[r]
  VC₁ < VC₂  iff  VC₁ ≤ VC₂ ∧ VC₁ ≠ VC₂
  VC₁ ∥ VC₂  iff  neither VC₁ ≤ VC₂ nor VC₂ ≤ VC₁

Merge:
  VC₁ ⊔ VC₂ = λr. max(VC₁[r], VC₂[r])

Properties:
  If e₁ → e₂ then VC(e₁) < VC(e₂)
  If VC(e₁) ∥ VC(e₂) then e₁ ∥ e₂
```

## Convergence Proofs

### General Convergence Theorem

```
Theorem (Strong Eventual Consistency):
  Given:
    • State-based CRDT with state forming join-semilattice (S, ⊔)
    • Reliable causal broadcast (all ops eventually delivered)
    • Merge is lattice join

  Then:
    All replicas eventually converge to same state

Proof:
  1. Let Op = {op₁, op₂, ..., opₙ} be set of all operations

  2. Each operation moves state up lattice:
     ∀op: apply(op, s) ≥ s

  3. Merge is commutative and associative:
     order of operations doesn't matter

  4. Therefore, final state is:
     s_final = ⊔{apply(op, s₀) | op ∈ Op}

  5. This LUB is unique (semilattice property)

  6. All replicas compute same LUB

  7. Therefore: all replicas converge to s_final

  QED
```

### Example: G-Set Convergence

```
Proof that G-Set converges:

G-Set Definition:
  • State: S ⊆ Elements
  • Operations: add(e) where e ∈ Elements
  • Merge: S₁ ⊔ S₂ = S₁ ∪ S₂

Proof:
  1. (𝒫(Elements), ∪) is a join-semilattice:
     ✓ Commutativity: A ∪ B = B ∪ A
     ✓ Associativity: (A ∪ B) ∪ C = A ∪ (B ∪ C)
     ✓ Idempotency:   A ∪ A = A

  2. Operations are monotonic:
     add(e): S ↦ S ∪ {e}
     S ⊆ S ∪ {e} (always true)

  3. Operations commute:
     (S ∪ {a}) ∪ {b} = (S ∪ {b}) ∪ {a}
     (set union is commutative)

  4. By General Convergence Theorem:
     All replicas converge to ⋃{added elements}

  QED
```

## Summary: The Theory of Convergence

CRDT theory rests on algebraic foundations:

**Join-Semilattices**: States form a partially ordered set with a join operation. Merge is lattice join - commutative, associative, idempotent.

**Monotonicity**: Operations only move state up the lattice. Information accumulates, never lost (without tombstones).

**Commutativity**: Operations produce same result regardless of order. Enables concurrent execution without coordination.

**Causality**: Happens-before relation captured by vector clocks. Preserves user intent across replicas.

**Strong Eventual Consistency**: Replicas with same operations converge to same state. Deterministic convergence without coordination.

The beauty of CRDT theory: complex distributed systems behavior emerges from simple algebraic properties. Master the algebra, master the convergence.

## Further Exploration

- **types.md**: Concrete CRDT implementations and their algebraic structures
- **production.md**: Theory meets practice - real-world CRDT deployments
- **advanced.md**: Delta-CRDTs, pure operation-based CRDTs, advanced theory

---

*Theory: Where mathematics guarantees what coordination cannot.*

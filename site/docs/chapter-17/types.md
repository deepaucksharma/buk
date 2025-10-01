# CRDT Types: The Convergent Data Structure Zoo

## The CRDT Catalog

CRDTs come in families, each designed for specific data structure semantics. The art lies in encoding familiar data structures (counters, sets, maps, sequences) into convergent forms that maintain their essential properties while guaranteeing automatic conflict resolution.

This chapter catalogs the major CRDT families, their algebraic structures, implementation patterns, and trade-offs. Each CRDT type represents a different point in the design space, balancing semantic richness against implementation complexity.

## Guarantee Vector for CRDT Types

Different CRDT types occupy different regions of the guarantee space:

```
CRDT Type G-Vector = ⟨Regional, Causal, RA, EO, Idem(type), Auth⟩

Counter Family:
  G-Counter:  ⟨Full, Weak, Full, Merge, Max-merge, None⟩
  PN-Counter: ⟨Full, Weak, Full, Merge, Dual-max, None⟩

Set Family:
  G-Set:   ⟨Full, None, Full, Merge, Union, None⟩
  2P-Set:  ⟨Full, None, Full, Merge, Dual-union, Tombstone⟩
  OR-Set:  ⟨Full, Strong, Full, Merge, Tag-union, Unique-tag⟩
  LWW-Set: ⟨Full, Weak, Full, Merge, Timestamp-max, Timestamp⟩

Map Family:
  LWW-Map: ⟨Full, Per-key-weak, Full, Merge, Key-timestamp, Timestamp⟩
  OR-Map:  ⟨Full, Per-key-strong, Full, Merge, Key-tag-union, Unique-tag⟩

Sequence Family:
  RGA:  ⟨Full, Strong, Full, Merge, Causal-sequence, Position-tag⟩
  WOOT: ⟨Full, Strong, Full, Merge, Visible-sequence, Unique-id⟩
```

## Counter CRDTs

Counters are the simplest CRDTs, designed for increment and decrement operations that must commute.

### G-Counter (Grow-only Counter)

The G-Counter supports only increments, making convergence trivial:

```
Algebraic Structure:
  State: S = ℕⁿ (n-dimensional natural numbers)
  Lattice: (ℕⁿ, ⊔) where (a₁,...,aₙ) ⊔ (b₁,...,bₙ) = (max(a₁,b₁),...,max(aₙ,bₙ))
  Value: Σᵢ S[i]

Operations:
  increment(replica_id, amount):
    S[replica_id] += amount

  value():
    return Σᵢ S[i]

  merge(S₁, S₂):
    ∀i: S[i] = max(S₁[i], S₂[i])

Example:
  Replica A:  P[A]=5, P[B]=3, P[C]=7  → value = 15
  Replica B:  P[A]=5, P[B]=8, P[C]=7  → value = 20
  Merged:     P[A]=5, P[B]=8, P[C]=7  → value = 20

Properties:
  ✓ Monotonic: value only increases
  ✓ Commutative: increments commute
  ✓ Space: O(n) where n = number of replicas
  ✗ Cannot decrement
```

### Context Capsule: G-Counter Merge

```
╔══════════════════════════════════════════════════════════╗
║ G-COUNTER MERGE CAPSULE                                  ║
║ Location: Anti-entropy sync between replicas             ║
╠══════════════════════════════════════════════════════════╣
║ Pre-Merge State:                                         ║
║   Replica A: P[A]=10, P[B]=5,  P[C]=3  → value=18       ║
║   Replica B: P[A]=8,  P[B]=12, P[C]=3  → value=23       ║
║                                                          ║
║ Lattice Structure:                                       ║
║   Order: (a₁,b₁,c₁) ≤ (a₂,b₂,c₂) iff aᵢ ≤ bᵢ ∀i        ║
║   Join:  element-wise max                                ║
║                                                          ║
║ Merge Computation:                                       ║
║   P[A] = max(10, 8)  = 10                               ║
║   P[B] = max(5, 12)  = 12                               ║
║   P[C] = max(3, 3)   = 3                                ║
║   Result: P[A]=10, P[B]=12, P[C]=3  → value=25          ║
║                                                          ║
║ Convergence Evidence:                                    ║
║   • Element-wise max is commutative                      ║
║   • Sum is monotonic (25 ≥ 18, 23)                      ║
║   • Idempotent: merging again gives same result         ║
║                                                          ║
║ Guarantee Witness:                                       ║
║   ✓ Both replicas converge to same state                ║
║   ✓ Value accounts for all increments                   ║
║   ✓ No increments lost                                  ║
╚══════════════════════════════════════════════════════════╝
```

### PN-Counter (Positive-Negative Counter)

The PN-Counter extends G-Counter to support decrements:

```
Algebraic Structure:
  State: S = (P, N) where P, N ∈ ℕⁿ
  Lattice: Product lattice of two G-Counters
  Value: Σᵢ P[i] - Σᵢ N[i]

Operations:
  increment(replica_id, amount):
    P[replica_id] += amount

  decrement(replica_id, amount):
    N[replica_id] += amount

  value():
    return Σᵢ P[i] - Σᵢ N[i]

  merge((P₁, N₁), (P₂, N₂)):
    P[i] = max(P₁[i], P₂[i]) ∀i
    N[i] = max(N₁[i], N₂[i]) ∀i

Example:
  Replica A: inc(5), inc(3), dec(2)
    P[A]=8, N[A]=2  → local value = 6

  Replica B: inc(7), dec(4)
    P[B]=7, N[B]=4  → local value = 3

  After merge:
    P[A]=8, P[B]=7, N[A]=2, N[B]=4
    Total value = (8+7) - (2+4) = 9

Properties:
  ✓ Supports increment and decrement
  ✓ Monotonic lattice (both P and N only grow)
  ✓ Commutative operations
  ✓ Space: O(2n) where n = number of replicas
  ~ Value can be negative
```

### Diagram: Counter CRDT Lattices

```
G-Counter Lattice (3 replicas):

        ┌──────────────┐
        │ (10, 12, 8)  │ ← LUB (all increments)
        └───────┬──────┘
                │
      ┌─────────┼─────────┐
      │                   │
┌─────▼─────┐      ┌──────▼──────┐
│(10, 12, 5)│      │ (8, 12, 8)  │
└─────┬─────┘      └──────┬──────┘
      │                   │
      └──────┬────────────┘
             │
      ┌──────▼──────┐
      │ (8, 12, 5)  │ ← Partial state
      └──────┬──────┘
             │
        ┌────▼────┐
        │(0, 0, 0)│ ← Bottom (initial)
        └─────────┘

PN-Counter Lattice (Product of P and N):

  State = (P-vector, N-vector)

  Example progression:
    (0,0,0), (0,0,0)  → initial
         ↓
    (5,0,0), (0,0,0)  → inc(A, 5)
         ↓
    (5,7,0), (0,0,0)  → inc(B, 7)
         ↓
    (5,7,0), (2,0,0)  → dec(A, 2)
         ↓
    (5,7,3), (2,4,0)  → inc(C,3), dec(B,4)

  Value = sum(P) - sum(N) = 15 - 6 = 9
```

## Set CRDTs

Set CRDTs are more complex, as they must handle both additions and removals that may conflict.

### G-Set (Grow-only Set)

The simplest set CRDT - elements can only be added:

```
Algebraic Structure:
  State: S ⊆ Elements
  Lattice: (𝒫(Elements), ⊆, ∪)
  Order: subset relation

Operations:
  add(element):
    S = S ∪ {element}

  lookup(element):
    return element ∈ S

  merge(S₁, S₂):
    return S₁ ∪ S₂

Example:
  Replica A: {x, y}
  Replica B: {y, z}
  Merged:    {x, y, z}

Properties:
  ✓ Simple and efficient
  ✓ Low space overhead: O(|set|)
  ✓ Set union is commutative, associative, idempotent
  ✗ Cannot remove elements
```

### 2P-Set (Two-Phase Set)

The 2P-Set supports removal through a tombstone set:

```
Algebraic Structure:
  State: S = (A, R) where A = added set, R = removed set
  Lattice: Product of two G-Sets
  Lookup: element ∈ A ∧ element ∉ R

Operations:
  add(element):
    A = A ∪ {element}

  remove(element):
    R = R ∪ {element}
    (precondition: element ∈ A)

  lookup(element):
    return (element ∈ A) ∧ (element ∉ R)

  merge((A₁, R₁), (A₂, R₂)):
    A = A₁ ∪ A₂
    R = R₁ ∪ R₂

Example:
  Replica A: A={x, y}, R={y}     → visible: {x}
  Replica B: A={y, z}, R={}      → visible: {y, z}
  Merged:    A={x, y, z}, R={y}  → visible: {x, z}

Properties:
  ✓ Supports add and remove
  ✓ Remove wins over add (bias)
  ✓ Monotonic: A and R only grow
  ✗ Cannot re-add removed element
  ✗ Space: O(|adds| + |removes|), unbounded
```

### Context Capsule: 2P-Set Conflict Resolution

```
╔══════════════════════════════════════════════════════════╗
║ 2P-SET CONFLICT CAPSULE                                  ║
║ Location: Concurrent add/remove operations               ║
╠══════════════════════════════════════════════════════════╣
║ Scenario:                                                ║
║   Replica A: remove(x) at time T                        ║
║   Replica B: observes remove, then add(x) at time T+1   ║
║                                                          ║
║ Pre-Merge States:                                        ║
║   Replica A: A={x, y}, R={x}  → visible: {y}           ║
║   Replica B: A={x, y}, R={x}  → visible: {y}           ║
║                                                          ║
║ Conflict:                                                ║
║   User on B wants to re-add x after seeing removal      ║
║   But 2P-Set cannot distinguish this from original add  ║
║                                                          ║
║ Merge Result:                                            ║
║   A={x, y}, R={x}  → visible: {y}                       ║
║                                                          ║
║ Resolution Evidence:                                     ║
║   • 2P-Set bias: remove wins                            ║
║   • Once in R, element permanently removed              ║
║   • Limitation: cannot re-add after remove              ║
║                                                          ║
║ Guarantee Witness:                                       ║
║   ✓ Deterministic: all replicas agree                   ║
║   ✓ Convergent: merge is well-defined                   ║
║   ✗ Semantic limitation: re-add impossible              ║
║                                                          ║
║ Solution: Use OR-Set for re-add support                 ║
╚══════════════════════════════════════════════════════════╝
```

### OR-Set (Observed-Remove Set)

The OR-Set solves re-add problem with unique tags:

```
Algebraic Structure:
  State: S = {(element, unique_tag)}
  Each add creates new unique tag
  Remove only removes observed tags

Operations:
  add(element):
    tag = unique()  // UUID, (replica_id, counter), etc.
    S = S ∪ {(element, tag)}

  remove(element, observed_tags):
    S = S \ {(element, tag) | tag ∈ observed_tags}

  lookup(element):
    return ∃tag: (element, tag) ∈ S

  merge(S₁, S₂):
    return S₁ ∪ S₂

Example:
  Replica A: add(x) → S_A = {(x, t1)}
  Replica B: receives t1, remove(x, {t1}) → S_B = {}
  Replica A: add(x) again → S_A = {(x, t2)}
  Merged: {(x, t2)}  → x is visible

  The new add (t2) is not removed because t2 wasn't observed
  when remove was called.

Concurrent add/remove:
  Replica A: add(x, t1)
  Replica B: remove(x, {t0})  // t0 from earlier
  Since t1 ∉ {t0}, t1 survives → add wins (observed-remove semantics)

Properties:
  ✓ Supports re-add after remove
  ✓ Add-wins bias for concurrent ops
  ✓ Preserves causal intent
  ✗ Space: O(|elements| × |tags|)
  ✗ Requires unique tag generation
  ✗ Garbage collection needed for tags
```

### Context Capsule: OR-Set Add-Wins Semantics

```
╔══════════════════════════════════════════════════════════╗
║ OR-SET ADD-WINS CAPSULE                                  ║
║ Location: Concurrent add and remove                      ║
╠══════════════════════════════════════════════════════════╣
║ Initial State: S = {(x, t0)}                            ║
║                                                          ║
║ Concurrent Operations (at time T):                       ║
║   Replica A: remove(x, {t0})  → S_A = {}               ║
║   Replica B: add(x) → t1      → S_B = {(x,t0), (x,t1)} ║
║                                                          ║
║ Causal Analysis:                                         ║
║   • Both ops concurrent (happened at same time)         ║
║   • A's remove only saw t0                              ║
║   • B's add created new tag t1                          ║
║   • t1 not in observed set of remove                    ║
║                                                          ║
║ Merge Computation:                                       ║
║   S_A ∪ S_B = {} ∪ {(x,t1)} = {(x, t1)}                ║
║                                                          ║
║ Semantic Interpretation:                                 ║
║   • Remove only affects observed tags                   ║
║   • New add (t1) wasn't observed by remove              ║
║   • Therefore: add wins                                 ║
║                                                          ║
║ Result: x is present (via tag t1)                       ║
║                                                          ║
║ Guarantee Witness:                                       ║
║   ✓ Add-wins bias (user intent: adding important)       ║
║   ✓ Causal consistency (only remove observed)           ║
║   ✓ Convergence (all replicas compute same union)       ║
╚══════════════════════════════════════════════════════════╝
```

### LWW-Set (Last-Write-Wins Set)

The LWW-Set uses timestamps to resolve conflicts:

```
Algebraic Structure:
  State: S = {(element, timestamp, status)}
  where status ∈ {added, removed}
  Lattice: Max on timestamps

Operations:
  add(element):
    timestamp = now()
    S = S ∪ {(element, timestamp, added)}

  remove(element):
    timestamp = now()
    S = S ∪ {(element, timestamp, removed)}

  lookup(element):
    (_, ts, status) = latest entry for element
    return status == added

  merge(S₁, S₂):
    For each element:
      keep entry with max timestamp
      tie-break on status (e.g., add wins)

Example:
  Replica A: add(x, t=100)    → {(x, 100, added)}
  Replica B: remove(x, t=50)  → {(x, 50, removed)}
  Merged: {(x, 100, added)}   → x is visible (100 > 50)

Properties:
  ✓ Simple conflict resolution
  ✓ Bounded space per element: O(|elements|)
  ✓ No tag management
  ✗ Requires synchronized clocks
  ✗ Timestamp conflicts need tie-breaking
  ✗ "Last writer" may not be semantic intent
```

### Diagram: Set CRDT Comparison

```
┌─────────────────────────────────────────────────────────────┐
│              Set CRDT Comparison Matrix                     │
├──────────┬──────────┬───────────┬───────────┬──────────────┤
│   Type   │   Add    │  Remove   │  Re-add   │    Space     │
├──────────┼──────────┼───────────┼───────────┼──────────────┤
│  G-Set   │    ✓     │     ✗     │    N/A    │  O(|set|)    │
│          │  Simple  │    None   │           │   Optimal    │
├──────────┼──────────┼───────────┼───────────┼──────────────┤
│  2P-Set  │    ✓     │     ✓     │     ✗     │ O(A + R)     │
│          │  Simple  │ Once only │  Cannot   │  Unbounded   │
├──────────┼──────────┼───────────┼───────────┼──────────────┤
│  OR-Set  │    ✓     │     ✓     │     ✓     │ O(|set|×|t|) │
│          │With tag  │ Observed  │ New tag   │   Large      │
│          │          │  only     │           │              │
├──────────┼──────────┼───────────┼───────────┼──────────────┤
│ LWW-Set  │    ✓     │     ✓     │     ✓     │  O(|set|)    │
│          │Timestamp │ Timestamp │ Timestamp │   Optimal    │
│          │          │           │  wins     │              │
└──────────┴──────────┴───────────┴───────────┴──────────────┘

Semantic Comparison:

  G-Set:
    Use: Accumulate-only (logs, metrics)
    Bias: None (no conflicts)

  2P-Set:
    Use: Permanent deletion
    Bias: Remove wins

  OR-Set:
    Use: Collaborative editing, shopping cart
    Bias: Add wins

  LWW-Set:
    Use: Caches, session state
    Bias: Recent write wins
```

## Map CRDTs

Map CRDTs apply CRDT principles to key-value stores:

### LWW-Map (Last-Write-Wins Map)

```
Algebraic Structure:
  State: M = {key → (value, timestamp)}
  Per-key LWW-Register

Operations:
  set(key, value):
    timestamp = now()
    M[key] = (value, timestamp)

  get(key):
    if key ∈ M: return M[key].value
    else: return ⊥

  remove(key):
    timestamp = now()
    M[key] = (⊥, timestamp)  // Tombstone

  merge(M₁, M₂):
    For each key in M₁ ∪ M₂:
      if key only in M₁: use M₁[key]
      if key only in M₂: use M₂[key]
      if key in both:
        use entry with max timestamp
        tie-break: arbitrary but deterministic

Example:
  Replica A: set(x, 5, t=100), set(y, 7, t=105)
  Replica B: set(x, 9, t=95),  set(z, 3, t=110)
  Merged:
    x → (5, 100)  // A's value (100 > 95)
    y → (7, 105)  // Only in A
    z → (3, 110)  // Only in B

Properties:
  ✓ Simple per-key conflict resolution
  ✓ Standard map interface
  ✓ Bounded space per key
  ✗ Clock dependency
  ✗ Last writer may not be intent
```

### OR-Map (Observed-Remove Map)

```
Algebraic Structure:
  State: M = {key → OR-Set(value)}
  Each key has an OR-Set of values

Operations:
  set(key, value):
    M[key].add((value, unique_tag()))

  get(key):
    return M[key].lookup()  // Returns set of values
    (or single value if taking max/LWW)

  remove(key):
    M[key].clear()  // Remove all observed tags

  merge(M₁, M₂):
    For each key:
      M[key] = M₁[key].merge(M₂[key])

Properties:
  ✓ Per-key OR-Set semantics
  ✓ Add-wins for concurrent updates
  ✓ Multi-value register possible
  ✗ Space: O(|keys| × |values| × |tags|)
```

### Context Capsule: Map Key Conflict

```
╔══════════════════════════════════════════════════════════╗
║ LWW-MAP CONFLICT CAPSULE                                 ║
║ Location: Concurrent updates to same key                 ║
╠══════════════════════════════════════════════════════════╣
║ Scenario: Shopping cart price update                     ║
║                                                          ║
║ Concurrent Operations:                                   ║
║   Replica A: set("item_5", price=100, t=1000)          ║
║   Replica B: set("item_5", price=95,  t=1001)          ║
║                                                          ║
║ Pre-Merge States:                                        ║
║   Replica A: item_5 → (100, 1000)                       ║
║   Replica B: item_5 → (95, 1001)                        ║
║                                                          ║
║ Timestamp Comparison:                                    ║
║   1001 > 1000  →  Replica B's write is "later"         ║
║                                                          ║
║ Merge Computation:                                       ║
║   max_by_timestamp((100,1000), (95,1001)) = (95,1001)  ║
║                                                          ║
║ Post-Merge State:                                        ║
║   Both replicas: item_5 → (95, 1001)                    ║
║                                                          ║
║ Semantic Interpretation:                                 ║
║   • B's price (95) wins because timestamp is later      ║
║   • Assumes B's clock was accurate                      ║
║   • May not reflect causal intent if clocks skewed      ║
║                                                          ║
║ Guarantee Witness:                                       ║
║   ✓ Deterministic resolution                            ║
║   ✓ Convergence guaranteed                              ║
║   ~ Semantic correctness depends on clock sync          ║
╚══════════════════════════════════════════════════════════╝
```

## Sequence CRDTs

Sequence CRDTs are the most complex, designed for ordered lists and collaborative text editing:

### RGA (Replicated Growable Array)

```
Algebraic Structure:
  State: Sequence of (element, id, tombstone)
  ID = (timestamp, replica_id) - uniquely identifies position
  Causal ordering between insertions

Operations:
  insert(element, after_id):
    id = (now(), my_replica_id)
    Insert (element, id, false) after position with after_id
    Position determined by causal order

  delete(id):
    Mark element with id as tombstone

  merge(S₁, S₂):
    Interleave sequences respecting causal order of IDs

Example:
  Initial: []
  Replica A: insert('H', after=nil, id=1) → ['H']
  Replica A: insert('i', after=1, id=2)   → ['H', 'i']
  Replica B: insert('e', after=1, id=3)   → must go between H and i
  Result: ['H', 'e', 'i']  (id order: 1 < 3 < 2 causally)

Properties:
  ✓ Preserves intent for sequential edits
  ✓ Handles concurrent insertions
  ✓ Tombstones for deletions
  ✗ Tombstone accumulation
  ✗ Complex merge algorithm
```

### WOOT (WithOut Operational Transformation)

```
Algebraic Structure:
  State: Set of characters with:
    - Unique ID
    - Previous character ID
    - Next character ID
  Forms doubly-linked structure

Operations:
  insert(char, prev_id, next_id):
    Generate unique ID
    Insert between prev and next
    Resolve conflicts by ID ordering

  delete(id):
    Mark as deleted (tombstone)

  visible():
    Traverse list, skip tombstones

Properties:
  ✓ Convergence guaranteed
  ✓ Intention preservation
  ✗ Complex algorithm
  ✗ Tombstones never removed
```

### Diagram: Sequence CRDT Evolution

```
RGA Insert Sequence:

Initial State:
  []  (empty)

Operation 1: Replica A inserts 'H' (id=1)
  ['H'₁]

Operation 2: Replica A inserts 'i' after 'H' (id=2)
  ['H'₁ → 'i'₂]

Operation 3 (concurrent): Replica B inserts 'e' after 'H' (id=3)
  Replica B view: ['H'₁ → 'e'₃]
  Causal: 1 → 3 (B saw H before inserting e)

Merge: Need to determine order of 'e'₃ and 'i'₂
  Both inserted after 'H'₁
  Concurrent: 2 ∥ 3
  Tie-break by ID: 2 < 3 (timestamp or replica comparison)

Result: ['H'₁ → 'i'₂ → 'e'₃]
  Or:   ['H'₁ → 'e'₃ → 'i'₂]  (depends on tie-break rule)

Consistent across all replicas (deterministic tie-break)

Deletion Example:

State: ['H'₁ → 'e'₃ → 'l'₄ → 'l'₅ → 'o'₆]

Delete 'l'₄:
  ['H'₁ → 'e'₃ → 'l̶'₄ → 'l'₅ → 'o'₆]
  (tombstone, not rendered)

Visible sequence: "Hello"
Internal state: keeps tombstone for convergence
```

## CRDT Type Selection Guide

### Decision Tree

```
Need a CRDT?
  │
  ├─ Just counting?
  │   ├─ Only increment? → G-Counter
  │   └─ Inc/Dec? → PN-Counter
  │
  ├─ Set of elements?
  │   ├─ Only add? → G-Set
  │   ├─ Add/remove, no re-add? → 2P-Set
  │   ├─ Re-add needed?
  │   │   ├─ Add-wins bias? → OR-Set
  │   │   └─ Recent-wins bias? → LWW-Set
  │   └─ Multi-value OK? → MV-Register per element
  │
  ├─ Key-value map?
  │   ├─ Simple timestamp ordering? → LWW-Map
  │   ├─ Add-wins semantics? → OR-Map
  │   └─ Multi-value? → OR-Map with MV-Register
  │
  └─ Ordered sequence?
      ├─ Simple list? → RGA
      ├─ Text editing? → WOOT or Yjs
      └─ Complex positioning? → Logoot
```

### Use Case Matrix

```
┌──────────────────┬─────────────────────┬──────────────────┐
│    Use Case      │    Recommended      │   Alternative    │
├──────────────────┼─────────────────────┼──────────────────┤
│ Vote counting    │ G-Counter           │ PN-Counter       │
│ Like counter     │ G-Counter           │ -                │
│ Inventory        │ PN-Counter          │ -                │
│ Balance          │ PN-Counter          │ -                │
├──────────────────┼─────────────────────┼──────────────────┤
│ User tags        │ OR-Set              │ LWW-Set          │
│ Shopping cart    │ OR-Set              │ LWW-Set          │
│ Favorites        │ G-Set (add-only)    │ LWW-Set          │
│ Blocked users    │ 2P-Set (permanent)  │ OR-Set           │
├──────────────────┼─────────────────────┼──────────────────┤
│ User profile     │ LWW-Map             │ OR-Map           │
│ Configuration    │ LWW-Map             │ -                │
│ Cache            │ LWW-Map             │ -                │
│ Collaborative    │ OR-Map              │ -                │
├──────────────────┼─────────────────────┼──────────────────┤
│ Chat messages    │ RGA                 │ Append-only log  │
│ Todo list        │ RGA                 │ OR-Map           │
│ Text editing     │ Yjs, Automerge      │ RGA, WOOT        │
│ Ordered items    │ RGA                 │ -                │
└──────────────────┴─────────────────────┴──────────────────┘
```

## Implementation Patterns

### Pattern 1: Tag Generation

```
Unique Tag Strategies:

1. UUID:
   tag = uuid.v4()
   ✓ Globally unique without coordination
   ✗ Large space overhead (16 bytes)

2. Replica ID + Counter:
   tag = (replica_id, counter++)
   ✓ Smaller space (8-16 bytes)
   ✓ Encodes causality
   ✗ Requires replica identity

3. Timestamp + Replica ID:
   tag = (timestamp_ms, replica_id)
   ✓ Natural ordering
   ✓ Efficient merge
   ✗ Clock dependency

4. Hybrid Vector Clock:
   tag = (vector_clock, replica_id, counter)
   ✓ Full causality tracking
   ✗ Large overhead
```

### Pattern 2: Tombstone Management

```
Tombstone Garbage Collection:

Problem: Tombstones accumulate, consuming space

Solutions:

1. Never Remove (safest):
   Keep all tombstones forever
   ✓ Always correct
   ✗ Unbounded growth

2. TTL-based Removal:
   Remove tombstones after time T
   ✓ Bounded space
   ✗ May lose causality if replica offline > T

3. Global Snapshot:
   Coordinate global snapshot, compact
   ✓ Can safely remove old tombstones
   ✗ Requires coordination (defeats purpose)

4. Causal Stability:
   Track causal dependencies, remove when stable
   ✓ Safe removal
   ✗ Complex tracking
```

## Summary: Choosing Your CRDT

The CRDT landscape offers solutions for many distributed data structure needs:

**Counters**: G-Counter for metrics, PN-Counter for mutable counts. Simple, efficient, fundamental building blocks.

**Sets**: G-Set for logs, 2P-Set for permanent removal, OR-Set for add-wins, LWW-Set for timestamp-based. Choose based on removal semantics.

**Maps**: LWW-Map for simplicity and space efficiency, OR-Map for richer semantics and add-wins behavior.

**Sequences**: RGA for lists, WOOT/Yjs for text. Complex but enables real-time collaboration.

The art: match CRDT semantics to application semantics. Understand the biases (add-wins vs remove-wins vs recent-wins) and choose appropriately.

## Further Exploration

- **production.md**: Real-world CRDT implementations in Riak, Redis, Automerge
- **advanced.md**: Delta-CRDTs for efficiency, pure operation-based CRDTs, optimization techniques
- **fundamentals.md**: Theoretical foundations and convergence proofs

---

*Types: Where theory becomes data structures, and convergence becomes concrete.*

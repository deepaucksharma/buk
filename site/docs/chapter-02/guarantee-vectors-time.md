# Guarantee Vectors for Time and Order Systems

## Introduction: Time as Evidence

This document provides comprehensive examples of how different time mechanisms generate different guarantee vectors. Each clock type produces different kinds of evidence, enabling different guarantees, and composing in different ways.

**The fundamental insight**: Time systems are not about "knowing what time it is"—they are **evidence generators** that enable ordering, causality tracking, and freshness guarantees with bounded uncertainty.

---

## 1. Lamport Clock System: Causal Order Without Physical Time

### The Invariant

**ORDER**: If event A causally precedes event B (A → B), then any ordering mechanism must preserve this: LC(A) < LC(B).

### Guarantee Vector (Base)

```
G_lamport = ⟨Range, Causal, RA, EO, Idem(LC), Unauth⟩
```

**Breaking it down:**
- **Scope**: `Range` (per-process or per-partition, not global)
- **Order**: `Causal` (happened-before preserved, but cannot detect concurrency)
- **Visibility**: `RA` (read-atomic; see consistent snapshots within causal chain)
- **Recency**: `EO` (eventual only; no physical time bound)
- **Idempotence**: `Idem(LC)` (Lamport clock value serves as deduplication key)
- **Auth**: `Unauth` (no cryptographic binding; assumes trusted network)

### Evidence Generated

**Type**: Logical timestamp (integer counter)

**Properties:**
- **Scope**: Per-event (each operation gets a unique LC value)
- **Lifetime**: Indefinite (never expires; bounded only by counter overflow)
- **Binding**: Process ID (LC value only meaningful relative to process)
- **Transitivity**: Transitive (LC values can be compared across processes after message exchange)
- **Revocation**: N/A (logical time doesn't expire)
- **Cost**: Generation: O(1) increment; Verification: O(1) comparison

**Evidence lifecycle:**
1. **Generated**: On every local event or message send: `LC = LC + 1`
2. **Propagated**: Attached to messages
3. **Validated**: On receive: `LC = max(LC, LC_msg) + 1`
4. **Active**: Used for ordering events
5. **Never expires**: Logical timestamps remain valid indefinitely

### Example: Distributed Database with Lamport Timestamps

```python
class LamportClock:
    def __init__(self, process_id):
        self.lc = 0
        self.process_id = process_id

    def local_event(self):
        """Generate evidence for local event"""
        self.lc += 1
        return {
            'timestamp': self.lc,
            'process': self.process_id,
            'evidence_type': 'causal_order',
            'scope': 'event',
            'binding': self.process_id
        }

    def send_message(self, data):
        """Generate evidence, attach to message"""
        self.lc += 1
        return {
            'data': data,
            'lamport_ts': self.lc,
            'process': self.process_id
        }

    def receive_message(self, msg):
        """Validate and merge evidence"""
        # Merge: take max, then increment
        self.lc = max(self.lc, msg['lamport_ts']) + 1
        return {
            'timestamp': self.lc,
            'evidence_type': 'merged_causal',
            'causally_after': msg['lamport_ts']
        }

# Simulation
p1 = LamportClock(process_id=1)
p2 = LamportClock(process_id=2)
p3 = LamportClock(process_id=3)

# Process 1: local events
e1 = p1.local_event()  # LC=1
e2 = p1.send_message("Write X=1")  # LC=2

# Process 2: concurrent event
e3 = p2.local_event()  # LC=1

# Process 2: receives from P1
msg = p2.receive_message({'lamport_ts': 2, 'data': "Write X=1"})
# P2's LC = max(1, 2) + 1 = 3

e4 = p2.send_message("Write Y=2")  # LC=4

# Process 3: receives from P2
p3.receive_message({'lamport_ts': 4, 'data': "Write Y=2"})
# P3's LC = max(0, 4) + 1 = 5
```

**Timeline with evidence:**

```
P1: [e1:LC=1] → [e2:LC=2, send] →
                         ↓
P2: [e3:LC=1] ← - - - - [recv:LC=3] → [e4:LC=4, send] →
                                               ↓
P3: - - - - - - - - - - - - - - - - - - - - [recv:LC=5]
```

**Guarantee properties:**
- ✓ **Causal order preserved**: e2 → recv(P2) → e4 → recv(P3), and LC(e2)=2 < LC(recv_P2)=3 < LC(e4)=4 < LC(recv_P3)=5
- ✗ **Cannot detect concurrency**: e1 (LC=1) and e3 (LC=1) are concurrent, but LC cannot prove this
- ✗ **No physical time**: Cannot answer "how long ago did e1 happen?"
- ✗ **No freshness guarantee**: EO (eventual only)

### Context Capsule (Lamport System)

```json
{
  "invariant": "ORDER (causal order preserved)",
  "evidence": {
    "type": "lamport_timestamp",
    "value": 5,
    "scope": "event",
    "lifetime": "indefinite",
    "binding": "process_3"
  },
  "boundary": "process_boundary",
  "mode": "target",
  "fallback": "accept_concurrent_as_unordered",
  "obligations": [
    "compare_only_after_message_exchange",
    "use_process_id_for_tie_breaking"
  ]
}
```

### Limitations (Why It Degrades)

**Problem 1: Concurrent Event Detection**

```python
# Two concurrent writes
p1.local_event()  # LC=1, Write X=1
p2.local_event()  # LC=1, Write X=2

# Question: Are these concurrent or ordered?
# Lamport clock: Cannot tell! Both have LC=1.
# Must use external tie-breaking (process ID), but this is arbitrary.
```

**Degradation**: `Causal` order does not imply global order. Concurrent events remain unordered.

**Problem 2: No Physical Time Bound**

```python
# Write with LC=100
write_time = time.time()  # e.g., 1000.0 seconds

# Read with LC=105 (happens-after by causality)
read_time = time.time()  # e.g., 1005.0 seconds

# Question: Is the read "fresh" (within 1 second of write)?
# Lamport clock: Cannot answer! No physical time information.
```

**Degradation**: `EO` (eventual only) recency. Cannot bound staleness in physical time.

---

## 2. Vector Clock System: Detecting Concurrency

### The Invariant

**ORDER + CONCURRENCY**: If A → B, then VC(A) < VC(B). If neither A → B nor B → A (concurrent), then VC(A) ∥ VC(B) (incomparable).

### Guarantee Vector (Enhanced)

```
G_vector = ⟨Range, Causal, RA, EO, Idem(VC), Unauth⟩
```

**Key difference from Lamport**: Same order guarantee (`Causal`), but **can detect concurrency** explicitly.

### Evidence Generated

**Type**: Vector of logical clocks (one counter per process)

**Properties:**
- **Scope**: Per-event (vector of N counters, where N = number of processes)
- **Lifetime**: Indefinite (never expires)
- **Binding**: Process ID (each position in vector corresponds to a process)
- **Transitivity**: Transitive (vectors can be compared globally)
- **Revocation**: N/A
- **Cost**: Generation: O(N) space, O(1) increment; Verification: O(N) comparison

**Evidence lifecycle:**
1. **Generated**: On local event: `VC[i] = VC[i] + 1` (increment own position)
2. **Propagated**: Entire vector attached to messages
3. **Validated**: On receive: `VC[j] = max(VC[j], VC_msg[j])` for all j, then `VC[i] += 1`
4. **Active**: Used for ordering and concurrency detection
5. **Never expires**

### Example: Dynamo-Style Eventually Consistent Store

```python
class VectorClock:
    def __init__(self, process_id, num_processes):
        self.process_id = process_id
        self.vc = [0] * num_processes  # Vector of N counters

    def local_event(self):
        """Generate vector clock evidence"""
        self.vc[self.process_id] += 1
        return {
            'vector': self.vc.copy(),
            'evidence_type': 'causal_history',
            'scope': 'event',
            'binding': f'process_{self.process_id}'
        }

    def send_message(self, data):
        """Attach full vector to message"""
        self.vc[self.process_id] += 1
        return {
            'data': data,
            'vector_clock': self.vc.copy()
        }

    def receive_message(self, msg):
        """Merge vector clocks"""
        vc_msg = msg['vector_clock']
        # Merge: component-wise max
        for i in range(len(self.vc)):
            self.vc[i] = max(self.vc[i], vc_msg[i])
        # Then increment own position
        self.vc[self.process_id] += 1
        return {
            'vector': self.vc.copy(),
            'evidence_type': 'merged_history',
            'merged_from': vc_msg
        }

    def compare(self, vc_a, vc_b):
        """Detect ordering or concurrency"""
        # vc_a < vc_b if all components vc_a[i] <= vc_b[i]
        # and at least one vc_a[j] < vc_b[j]
        less_equal_all = all(vc_a[i] <= vc_b[i] for i in range(len(vc_a)))
        less_some = any(vc_a[i] < vc_b[i] for i in range(len(vc_a)))

        if less_equal_all and less_some:
            return "happened_before"  # A → B

        # Check reverse
        greater_equal_all = all(vc_a[i] >= vc_b[i] for i in range(len(vc_a)))
        greater_some = any(vc_a[i] > vc_b[i] for i in range(len(vc_a)))

        if greater_equal_all and greater_some:
            return "happened_after"  # B → A

        return "concurrent"  # A ∥ B

# Simulation (3 processes)
p1 = VectorClock(process_id=0, num_processes=3)
p2 = VectorClock(process_id=1, num_processes=3)
p3 = VectorClock(process_id=2, num_processes=3)

# Process 1: write
e1 = p1.local_event()  # VC=[1,0,0]
msg1 = p1.send_message("Write X=1")  # VC=[2,0,0]

# Process 2: concurrent write
e2 = p2.local_event()  # VC=[0,1,0]

# Process 2: receives from P1
p2.receive_message(msg1)  # VC = merge([0,1,0], [2,0,0]) + increment
                          # VC = [2,1,0] + [0,1,0] = [2,2,0]

msg2 = p2.send_message("Write Y=2")  # VC=[2,3,0]

# Process 3: receives from P2
p3.receive_message(msg2)  # VC = merge([0,0,0], [2,3,0]) + [0,0,1]
                          # VC = [2,3,1]

# Check concurrency
print(p1.compare([1,0,0], [0,1,0]))  # "concurrent" (e1 ∥ e2)
print(p1.compare([2,0,0], [2,3,1]))  # "happened_before" (msg1 → final)
```

**Timeline with vector evidence:**

```
P1: [e1:VC=[1,0,0]] → [msg1:VC=[2,0,0], send] →
                                 ↓
P2: [e2:VC=[0,1,0]] ← - - - - [recv:VC=[2,2,0]] → [msg2:VC=[2,3,0], send] →
                                                            ↓
P3: - - - - - - - - - - - - - - - - - - - - - - - - - - [recv:VC=[2,3,1]]
```

**Concurrency detection:**
- e1=[1,0,0] vs e2=[0,1,0]: **Concurrent** (neither ≤ the other)
- msg1=[2,0,0] vs recv_P2=[2,2,0]: **msg1 → recv_P2** ([2,0,0] < [2,2,0])

### Context Capsule (Vector Clock System)

```json
{
  "invariant": "ORDER + CONCURRENCY_DETECTION",
  "evidence": {
    "type": "vector_clock",
    "value": [2, 3, 1],
    "scope": "event",
    "lifetime": "indefinite",
    "binding": "process_vector[0:2]"
  },
  "boundary": "process_boundary",
  "mode": "target",
  "fallback": "merge_concurrent_via_application_logic",
  "obligations": [
    "compare_vectors_to_detect_conflicts",
    "use_last_write_wins_or_merge_for_concurrent_writes"
  ]
}
```

### Use Case: Conflict Detection in Distributed Store

```python
class DistributedStore:
    def __init__(self, process_id, num_processes):
        self.vc = VectorClock(process_id, num_processes)
        self.data = {}

    def write(self, key, value):
        """Write with vector clock versioning"""
        event = self.vc.local_event()
        self.data[key] = {
            'value': value,
            'version': event['vector'],
            'timestamp': time.time()  # For human debugging only
        }
        return event['vector']

    def detect_conflict(self, key, remote_write):
        """Detect if writes conflict (concurrent)"""
        if key not in self.data:
            return False  # No local version, accept remote

        local_vc = self.data[key]['version']
        remote_vc = remote_write['version']

        relation = self.vc.compare(local_vc, remote_vc)

        if relation == "concurrent":
            print(f"CONFLICT DETECTED: {key}")
            print(f"  Local:  VC={local_vc}, value={self.data[key]['value']}")
            print(f"  Remote: VC={remote_vc}, value={remote_write['value']}")
            return True
        elif relation == "happened_before":
            # Local is older, accept remote
            print(f"Local version older, accepting remote")
            return False
        else:  # happened_after
            # Remote is older, reject
            print(f"Remote version older, rejecting")
            return False

# Example: Concurrent writes create conflict
store1 = DistributedStore(process_id=0, num_processes=2)
store2 = DistributedStore(process_id=1, num_processes=2)

# Concurrent writes
vc1 = store1.write("user:42:name", "Alice")  # VC=[1,0]
vc2 = store2.write("user:42:name", "Bob")    # VC=[0,1]

# Replicate: store1 receives store2's write
remote_write = {'version': vc2, 'value': "Bob"}
conflict = store1.detect_conflict("user:42:name", remote_write)
# Output: CONFLICT DETECTED: user:42:name
#   Local:  VC=[1,0], value=Alice
#   Remote: VC=[0,1], value=Bob
```

**Guarantee enhancement**: Vector clocks enable **explicit conflict detection**. Application can then:
- Use last-write-wins (LWW) with tie-breaking
- Use merge semantics (e.g., CRDT)
- Ask user to resolve conflict

### Degradation vs Lamport

**What's gained**: Concurrency detection (explicit ∥ relation)

**What remains limited**:
- Still `EO` recency (no physical time bound)
- Space overhead: O(N) per event (N = number of processes)
- Scalability: For 1000 processes, every timestamp is 1000 integers

---

## 3. Hybrid Logical Clock (HLC): Physical Time + Causality

### The Invariant

**ORDER + BOUNDED_DRIFT**: Causal order preserved (if A → B, then HLC(A) < HLC(B)), AND logical time stays within bounded drift of physical time (|l - pt| ≤ ε).

### Guarantee Vector (Best of Both Worlds)

```
G_hlc = ⟨Range, Causal, RA, BS(ε), Idem(HLC), Unauth⟩
```

**Key enhancements:**
- **Recency**: `BS(ε)` (bounded staleness; ε = drift bound, typically ρ × δ where ρ = drift rate, δ = message delay)
- HLC provides **human-readable timestamps** (logical time `l` approximates physical time `pt`)

### Evidence Generated

**Type**: Hybrid timestamp `(l, c)` where:
- `l` = logical time (maximum physical time seen)
- `c` = logical counter (tie-breaker when `l` values collide)

**Properties:**
- **Scope**: Per-event
- **Lifetime**: Valid until physical drift exceeds bound (typically ~60 seconds without resync)
- **Binding**: Process ID + physical clock source
- **Transitivity**: Transitive (HLC values globally comparable)
- **Revocation**: Expires if physical clock skew detected (drift > ε)
- **Cost**: Generation: O(1); Verification: O(1) + physical clock read

**Evidence lifecycle:**
1. **Generated**: On event: `pt = physical_time(); l = max(l, pt); c = (l == pt ? 0 : c+1)`
2. **Propagated**: `(l, c)` attached to messages
3. **Validated**: On receive: merge `l` and `c` according to HLC algorithm
4. **Active**: Used for ordering and staleness bounding
5. **Expires**: When physical clock drift exceeds ε (typically monitored via NTP offset)
6. **Renewed**: Resync physical clock (NTP/PTP), reset ε

### Example: CockroachDB-Style Transaction Timestamps

```python
import time

class HybridLogicalClock:
    def __init__(self, process_id, max_drift_ms=10):
        self.process_id = process_id
        self.l = 0  # logical time (wall clock-like)
        self.c = 0  # logical counter
        self.max_drift_ms = max_drift_ms  # ε bound

    def now(self):
        """Generate HLC timestamp with bounded drift guarantee"""
        pt = int(time.time() * 1000)  # physical time in ms

        if pt > self.l:
            # Physical clock advanced
            self.l = pt
            self.c = 0
        else:
            # Physical clock hasn't advanced, increment counter
            self.c += 1

        # Check drift bound
        drift = abs(self.l - pt)

        return {
            'hlc': (self.l, self.c),
            'evidence_type': 'hybrid_timestamp',
            'scope': 'event',
            'drift_bound': self.max_drift_ms,
            'drift_actual': drift,
            'within_bound': drift <= self.max_drift_ms,
            'binding': f'process_{self.process_id}'
        }

    def update(self, remote_hlc):
        """Merge remote HLC (on message receive)"""
        l_msg, c_msg = remote_hlc
        pt = int(time.time() * 1000)

        # Compute new logical time
        l_new = max(self.l, l_msg, pt)

        # Update counter based on which value won
        if l_new == self.l and l_new == l_msg:
            self.c = max(self.c, c_msg) + 1
        elif l_new == self.l:
            self.c += 1
        elif l_new == l_msg:
            self.c = c_msg + 1
        else:
            self.c = 0

        self.l = l_new

        drift = abs(self.l - pt)

        return {
            'hlc': (self.l, self.c),
            'evidence_type': 'merged_hybrid',
            'merged_from': (l_msg, c_msg),
            'drift_actual': drift,
            'within_bound': drift <= self.max_drift_ms
        }

    def compare(self, hlc_a, hlc_b):
        """Compare HLC timestamps"""
        l_a, c_a = hlc_a
        l_b, c_b = hlc_b

        if l_a < l_b:
            return "before"
        elif l_a > l_b:
            return "after"
        else:  # l_a == l_b
            if c_a < c_b:
                return "before"
            elif c_a > c_b:
                return "after"
            else:
                return "concurrent"  # Same HLC (unlikely but possible)

# Simulation: Transaction timestamps in distributed DB
db1 = HybridLogicalClock(process_id=1, max_drift_ms=10)
db2 = HybridLogicalClock(process_id=2, max_drift_ms=10)

# Node 1: Begin transaction
txn1_start = db1.now()
print(f"TXN1 started: HLC={txn1_start['hlc']}, drift={txn1_start['drift_actual']}ms")

time.sleep(0.005)  # 5ms

# Node 2: Begin transaction (concurrent)
txn2_start = db2.now()
print(f"TXN2 started: HLC={txn2_start['hlc']}, drift={txn2_start['drift_actual']}ms")

# Node 1: Commit transaction, send commit message to Node 2
txn1_commit = db1.now()
print(f"TXN1 committed: HLC={txn1_commit['hlc']}")

# Node 2: Receives TXN1 commit notification
db2.update(txn1_commit['hlc'])
txn2_commit = db2.now()
print(f"TXN2 committed: HLC={txn2_commit['hlc']}, causally after TXN1")

# Verify ordering
relation = db1.compare(txn1_commit['hlc'], txn2_commit['hlc'])
print(f"TXN1 vs TXN2: {relation}")  # "before" (TXN1 → TXN2)
```

**Output:**
```
TXN1 started: HLC=(1696118400000, 0), drift=0ms
TXN2 started: HLC=(1696118400005, 0), drift=0ms
TXN1 committed: HLC=(1696118400010, 0)
TXN2 committed: HLC=(1696118400015, 0), causally after TXN1
TXN1 vs TXN2: before
```

**Guarantee properties:**
- ✓ **Causal order preserved**: TXN1 → TXN2 (HLC values increase)
- ✓ **Bounded drift**: |l - pt| ≤ 10ms (within ε)
- ✓ **Human-readable**: `l` is physical time in milliseconds (can convert to UTC)
- ✓ **Bounded staleness**: Can answer "is this data fresh within 10ms?" → YES (within drift bound)

### Context Capsule (HLC System)

```json
{
  "invariant": "ORDER + BOUNDED_DRIFT",
  "evidence": {
    "type": "hybrid_logical_clock",
    "value": {"l": 1696118400015, "c": 0},
    "scope": "event",
    "lifetime": "60_seconds_or_until_drift_exceeds_bound",
    "binding": "process_2 + ntp_sync_source",
    "drift_bound_ms": 10,
    "drift_actual_ms": 0
  },
  "boundary": "datacenter_boundary",
  "mode": "target",
  "fallback": "degrade_to_BS(ε)_if_drift_exceeds_or_downgrade_to_causal_only",
  "obligations": [
    "monitor_physical_clock_drift",
    "resync_via_ntp_every_60_seconds",
    "alert_if_drift_exceeds_bound"
  ]
}
```

### Bounded Staleness Proof

**Question**: Is a read "fresh" (within δ = 10ms of latest write)?

**HLC answer**: YES, if `|HLC_read.l - HLC_write.l| ≤ δ + 2ε`

Where:
- δ = desired staleness bound (e.g., 10ms)
- ε = HLC drift bound (e.g., 10ms)

**Proof**:
- Write happened at physical time `pt_write` (unknown)
- Read happened at physical time `pt_read` (unknown)
- But HLC guarantees: `|HLC_write.l - pt_write| ≤ ε` and `|HLC_read.l - pt_read| ≤ ε`
- Therefore: `|pt_read - pt_write| ≤ |HLC_read.l - HLC_write.l| + 2ε`

**Example**:
- Write: HLC.l = 1000ms
- Read: HLC.l = 1015ms
- Difference: 15ms
- With ε = 10ms, actual staleness ≤ 15ms + 2×10ms = 35ms

**Degradation**: If physical clock drift exceeds ε, staleness bound widens. Must downgrade:
- `BS(ε)` → `BS(2ε)` (if drift doubles)
- Or degrade to `EO` (eventual only) if drift unbounded

### Use Case: Follower Reads with Freshness Guarantee

```python
class DistributedDatabase:
    def __init__(self, process_id, is_leader, max_drift_ms=10):
        self.hlc = HybridLogicalClock(process_id, max_drift_ms)
        self.is_leader = is_leader
        self.committed_hlc = (0, 0)  # Last committed write HLC
        self.max_staleness_ms = 200  # Acceptable staleness: 200ms

    def write(self, key, value):
        """Leader write with HLC timestamp"""
        if not self.is_leader:
            raise Exception("Only leader can write")

        hlc_ts = self.hlc.now()
        self.committed_hlc = hlc_ts['hlc']

        return {
            'key': key,
            'value': value,
            'commit_hlc': self.committed_hlc,
            'guarantee': 'committed_with_causal_order'
        }

    def follower_read(self, key, require_fresh=True):
        """Follower read with staleness check"""
        if self.is_leader:
            # Leader always has fresh data
            current_hlc = self.hlc.now()
            return {
                'key': key,
                'guarantee': 'Fresh(φ)',  # φ = HLC proof
                'hlc': current_hlc['hlc']
            }

        # Follower: check staleness
        current_hlc = self.hlc.now()
        l_current, c_current = current_hlc['hlc']
        l_committed, c_committed = self.committed_hlc

        staleness_ms = l_current - l_committed
        drift_bound = current_hlc['drift_bound']

        # Actual staleness ≤ staleness_ms + 2×drift_bound
        max_possible_staleness = staleness_ms + 2 * drift_bound

        if max_possible_staleness <= self.max_staleness_ms:
            # Within staleness bound
            return {
                'key': key,
                'guarantee': f'BS({self.max_staleness_ms}ms)',
                'staleness_actual_ms': max_possible_staleness,
                'hlc': self.committed_hlc,
                'mode': 'target'
            }
        else:
            if require_fresh:
                # Staleness exceeded, redirect to leader
                return {
                    'error': 'staleness_exceeded',
                    'redirect_to_leader': True,
                    'staleness_actual_ms': max_possible_staleness,
                    'mode': 'degraded'
                }
            else:
                # Accept stale read with explicit label
                return {
                    'key': key,
                    'guarantee': 'EO (eventual only)',
                    'staleness_actual_ms': max_possible_staleness,
                    'mode': 'degraded',
                    'warning': 'data_may_be_stale'
                }

# Simulation
leader = DistributedDatabase(process_id=1, is_leader=True, max_drift_ms=10)
follower = DistributedDatabase(process_id=2, is_leader=False, max_drift_ms=10)

# Leader writes
write_result = leader.write("user:42:balance", 100)
print(f"Write committed: {write_result['commit_hlc']}")

# Replicate to follower (simulate 50ms delay)
time.sleep(0.05)
follower.committed_hlc = write_result['commit_hlc']
follower.hlc.update(write_result['commit_hlc'])

# Follower read (within 200ms staleness)
read_result = follower.follower_read("user:42:balance", require_fresh=True)
print(f"Follower read: {read_result}")

# Simulate long delay (250ms)
time.sleep(0.25)

# Follower read (exceeds 200ms staleness)
read_result2 = follower.follower_read("user:42:balance", require_fresh=True)
print(f"Follower read (stale): {read_result2}")
```

**Output:**
```
Write committed: (1696118400000, 0)
Follower read: {'key': 'user:42:balance', 'guarantee': 'BS(200ms)', 'staleness_actual_ms': 70, 'hlc': (1696118400000, 0), 'mode': 'target'}
Follower read (stale): {'error': 'staleness_exceeded', 'redirect_to_leader': True, 'staleness_actual_ms': 320, 'mode': 'degraded'}
```

**Guarantee evolution:**
- Leader write: `⟨Range, Lx, SI, Fresh(HLC), Idem(HLC), Auth⟩`
- Follower read (within 200ms): `⟨Range, Lx, SI, BS(200ms), Idem(HLC), Auth⟩`
- Follower read (stale): Degraded → Redirect to leader OR `⟨Range, —, —, EO, —, —⟩`

---

## 4. Cross-System Composition: Guarantee Degradation

### Scenario: System A (Lamport) → System B (Vector) → System C (HLC)

**Setup:**
- **System A**: Distributed queue using Lamport clocks for message ordering
- **System B**: Distributed database using vector clocks for conflict detection
- **System C**: Analytics service using HLC for time-series queries

**Question**: What guarantees survive end-to-end?

### Path Typing (Guarantee Vector Composition)

```
System A (Queue with Lamport):
  G_A = ⟨Object, Causal, RA, EO, Idem(LC), Unauth⟩

Boundary A→B: Message delivery
  - System B receives message with Lamport timestamp
  - System B cannot use Lamport timestamp for conflict detection (need vector clock)
  - Must downgrade or re-generate evidence

System B (DB with Vector Clock):
  G_B = ⟨Range, Causal, RA, EO, Idem(VC), Unauth⟩
  Downgrade: Cannot preserve A's Idem(LC) → must map LC to VC

Boundary B→C: Export to analytics
  - System C expects HLC (physical time component)
  - System B has only vector clock (no physical time)
  - Must downgrade or upgrade (generate HLC at boundary)

System C (Analytics with HLC):
  G_C = ⟨Global, Causal, SI, BS(ε), Idem(HLC), Unauth⟩
  Downgrade: Recency degrades from BS(ε) to EO (no physical time from B)
```

**Composed guarantee (end-to-end):**
```
G_A▷B▷C = meet(G_A, G_B, G_C)
        = ⟨Object, Causal, RA, EO, Idem(?), Unauth⟩
```

**What's lost:**
- **Recency**: `BS(ε)` from System C cannot be guaranteed (System B has no physical time)
- **Idempotence key**: Lamport → Vector → HLC requires mapping; may lose deduplication
- **Scope**: Narrowest scope wins (`Object` from System A)

### Context Capsule at Each Boundary

**Capsule at A→B boundary:**
```json
{
  "invariant": "ORDER (causal)",
  "evidence": {
    "type": "lamport_timestamp",
    "value": 42,
    "scope": "message"
  },
  "boundary": "queue_to_database",
  "mode": "target",
  "fallback": "map_lamport_to_vector_clock_via_process_id",
  "obligations": [
    "system_b_must_generate_vector_clock",
    "preserve_causal_order_via_vc_merge"
  ]
}
```

**Capsule at B→C boundary:**
```json
{
  "invariant": "ORDER (causal) + BOUNDED_DRIFT",
  "evidence": {
    "type": "vector_clock",
    "value": [5, 3, 2],
    "scope": "transaction"
  },
  "boundary": "database_to_analytics",
  "mode": "degraded",
  "fallback": "generate_hlc_at_export_time_loses_original_physical_time",
  "obligations": [
    "system_c_must_accept_that_hlc_is_export_time_not_write_time",
    "staleness_bound_BS(ε)_not_guaranteed"
  ],
  "warning": "recency_guarantee_degraded_to_EO"
}
```

**Final guarantee at System C:**
```
G_final = ⟨Object, Causal, RA, EO, Idem(HLC_export), Unauth⟩
```

### Upgrade Strategy: Inserting HLC at B→C Boundary

**Option**: Have System B generate HLC at export time.

```python
class BoundaryUpgrade:
    def __init__(self):
        self.hlc = HybridLogicalClock(process_id=99, max_drift_ms=10)

    def export_with_upgrade(self, vector_clock_data):
        """Upgrade from vector clock to HLC at boundary"""
        # Generate HLC at export time
        hlc_ts = self.hlc.now()

        return {
            'data': vector_clock_data['data'],
            'original_vc': vector_clock_data['vector'],
            'export_hlc': hlc_ts['hlc'],
            'guarantee': 'BS(ε) for export time, not original write time',
            'capsule': {
                'invariant': 'BOUNDED_DRIFT (export time)',
                'evidence': {
                    'type': 'hybrid_logical_clock',
                    'value': hlc_ts['hlc'],
                    'scope': 'export_event',
                    'binding': 'export_process_99'
                },
                'mode': 'target',
                'warning': 'staleness_from_original_write_not_bounded'
            }
        }

# Usage
boundary = BoundaryUpgrade()
db_data = {
    'data': {'user': 42, 'balance': 100},
    'vector': [5, 3, 2]
}

analytics_data = boundary.export_with_upgrade(db_data)
print(f"Exported with HLC: {analytics_data['export_hlc']}")
print(f"Guarantee: {analytics_data['guarantee']}")
```

**Upgraded guarantee:**
```
G_final = ⟨Object, Causal, RA, BS(ε_export), Idem(HLC_export), Unauth⟩
```

**Caveat**: `BS(ε_export)` only bounds staleness relative to export time, NOT original write time. The time from write → export is unbounded (EO).

### Visualization: Guarantee Evolution Across Systems

```
System A (Queue)          Boundary A→B          System B (DB)          Boundary B→C          System C (Analytics)
┌──────────────┐         ┌──────────┐         ┌──────────────┐       ┌──────────┐         ┌──────────────┐
│ Lamport      │         │ Map LC   │         │ Vector Clock │       │ Generate │         │ HLC          │
│ Timestamp    │────────▶│ to VC    │────────▶│              │──────▶│ HLC      │────────▶│              │
│              │         └──────────┘         │              │       └──────────┘         │              │
│ G: Causal    │                              │ G: Causal    │                            │ G: BS(ε)     │
│    EO        │         ⤓ Downgrade          │    EO        │       ↑ Upgrade            │    Causal    │
│    Idem(LC)  │         Re-generate VC       │    Idem(VC)  │       Generate HLC         │    Idem(HLC) │
└──────────────┘                              └──────────────┘                            └──────────────┘
       │                                              │                                            │
       │                                              │                                            │
Evidence: LC=42                               Evidence: VC=[5,3,2]                        Evidence: HLC=(T,0)
Scope: Message                                Scope: Transaction                          Scope: Export event
Lifetime: ∞                                   Lifetime: ∞                                 Lifetime: 60s (ε bound)
```

**Key insights:**
1. **Lamport → Vector**: Downgrade (must re-generate VC at boundary; lose LC context)
2. **Vector → HLC**: Upgrade (generate HLC at export) OR Downgrade (accept EO recency)
3. **End-to-end**: Weakest component dominates (Scope=Object, Recency=EO without upgrade)

---

## 5. Visual Diagram: Guarantee Evolution Summary

### The Invariant Guardian (Time Edition)

```
Threat: Clock skew, NTP failure, leap seconds
    ⚡
    │
    ▼
┌────────────────────────┐
│  Invariant: ORDER      │  ◀───── Mechanism: Lamport/Vector/HLC
│  (A → B preserved)     │
└────────────────────────┘
         │
         ▼
    Evidence Types:
    ┌─────────────────┬─────────────────┬─────────────────┐
    │ Lamport Clock   │ Vector Clock    │ HLC             │
    │ LC=42           │ VC=[5,3,2]      │ HLC=(T,0)       │
    │                 │                 │                 │
    │ ✓ Causal order  │ ✓ Causal order  │ ✓ Causal order  │
    │ ✗ Concurrency?  │ ✓ Concurrency   │ ✓ Concurrency   │
    │ ✗ Physical time │ ✗ Physical time │ ✓ Bounded drift │
    │ EO recency      │ EO recency      │ BS(ε) recency   │
    └─────────────────┴─────────────────┴─────────────────┘
```

### The Evidence Flow (Time Evidence Lifecycle)

```
Physical Clock    Logical Clock    Hybrid Clock
     │                 │                 │
     ▼                 ▼                 ▼
  Generate          Generate          Generate
  (read NTP)      (increment)    (merge PT + LC)
     │                 │                 │
     ▼                 ▼                 ▼
  Validate         Validate          Validate
  (check drift)   (compare LC)     (check drift)
     │                 │                 │
     ▼                 ▼                 ▼
  Active           Active            Active
  (order events)  (order events)   (order + bound staleness)
     │                 │                 │
     ▼                 ▼                 ▼
  Expire           Never            Expire
  (ε exceeded)                      (ε exceeded)
     │                                   │
     ▼                                   ▼
  Renew                              Renew
  (NTP resync)                       (NTP resync)
```

### The Composition Ladder (Time Systems)

```
Strong (HLC with tight ε)         ═════════════════════════
  │ BS(10ms) + Causal              ↑ Generate HLC at source
  │                                │ Requires: NTP sync
  ▼                                │
Bounded (HLC with wide ε)         ═════════════════════════
  │ BS(200ms) + Causal             ⤓ Drift exceeds bound
  │                                │ OR NTP sync lost
  ▼                                │
Weak (Logical only)               ═════════════════════════
  │ EO + Causal                    ⤓ Physical clock fails
  │                                │ Fallback: Lamport/Vector
  ▼
No guarantees (accept any order)  ═════════════════════════
```

### The Mode Matrix (Time System Modes)

```
        Target Mode
       (HLC, BS(ε))
            ↑
            │ NTP sync successful
            │ Drift < ε
            │
    ┌───────┴───────┐
    │               │
Recovery         Degraded
(Re-sync NTP)   (BS(2ε) or EO)
    │               │
    │ Drift > ε     │
    │ OR sync lost  │
    └───────┬───────┘
            │
            ▼
        Floor Mode
     (Logical only, EO)
```

---

## 6. Operator Mental Model: See, Think, Do

### What Operators See (Observable Evidence)

**Target Mode (HLC, BS(ε)):**
- Dashboard: "Clock drift: +2.3ms (ε=10ms) ✓"
- Dashboard: "NTP last sync: 45 sec ago ✓"
- Dashboard: "HLC staleness: 150ms (bound: 200ms) ✓"

**Degraded Mode (BS(2ε) or EO):**
- Alert: "Clock drift: +15ms (ε=10ms) ⚠ DEGRADED"
- Dashboard: "NTP last sync: 180 sec ago ⚠"
- Dashboard: "HLC staleness: 350ms (bound: 200ms) ⚠ Violating SLA"

**Floor Mode (Logical only):**
- Alert: "Clock drift: +500ms ⚠ FLOOR MODE"
- Alert: "NTP sync lost for 600 sec ⚠"
- Dashboard: "Switched to Lamport clocks (EO recency)"

### What Operators Think (Mental Model)

**Target Mode:**
- "Clock is synced, drift within bounds"
- "HLC guarantees BS(ε) staleness"
- "Can serve follower reads with freshness guarantee"

**Degraded Mode:**
- "Clock drift exceeded ε"
- "HLC staleness bound widened to 2ε"
- "Follower reads may violate SLA, but still bounded"
- "Need to resync NTP or redirect to leader"

**Floor Mode:**
- "Physical clock unreliable"
- "Fell back to logical clocks (Lamport/Vector)"
- "Causal order preserved, but no physical time bound"
- "Cannot guarantee freshness; only eventual consistency"

### What Operators Do (Safe Actions)

**Target Mode:**
- Continue normal operations
- Serve follower reads
- Monitor clock health

**Degraded Mode:**
- Option 1: Widen staleness bound (2ε), update SLA
- Option 2: Redirect reads to leader (Fresh guarantee)
- Option 3: Trigger NTP resync aggressively
- Alert on-call: "Clock drift degraded, SLA at risk"

**Floor Mode:**
- Redirect all reads to leader (no follower reads)
- Accept writes with logical timestamps only
- Escalate to SRE: "Physical clock failed, emergency resync needed"
- Enter recovery mode once NTP sync restored

**Recovery Mode:**
- Resync NTP (multiple time servers)
- Validate new clock (drift < ε)
- Re-enable HLC
- Re-enable follower reads
- Monitor for 5 minutes before declaring Target mode restored

---

## 7. Key Takeaways

### Lamport Clocks

**Invariant**: ORDER (causal order preserved)
**Evidence**: Logical counter (LC)
**Guarantee**: `⟨Range, Causal, RA, EO, Idem(LC), Unauth⟩`
**Strength**: Simple, no physical time dependency
**Weakness**: Cannot detect concurrency, no physical time bound
**Use case**: Message ordering, basic causality tracking

### Vector Clocks

**Invariant**: ORDER + CONCURRENCY_DETECTION
**Evidence**: Vector of counters (VC)
**Guarantee**: `⟨Range, Causal, RA, EO, Idem(VC), Unauth⟩`
**Strength**: Explicit concurrency detection, full causal history
**Weakness**: O(N) space per event, no physical time bound
**Use case**: Conflict detection in Dynamo-style stores, distributed debugging

### Hybrid Logical Clocks (HLC)

**Invariant**: ORDER + BOUNDED_DRIFT
**Evidence**: Hybrid timestamp (l, c)
**Guarantee**: `⟨Range, Causal, RA, BS(ε), Idem(HLC), Unauth⟩`
**Strength**: Causal order + physical time bound, human-readable
**Weakness**: Requires NTP sync, degrades when drift exceeds ε
**Use case**: Transaction timestamps (CockroachDB), follower reads with staleness bounds

### Composition Rules

1. **Weakest component dominates**: End-to-end guarantee = meet(G_A, G_B, G_C)
2. **Evidence must be preserved or regenerated** at boundaries (Lamport → Vector requires VC generation)
3. **Upgrades require new evidence** (Vector → HLC requires physical clock read)
4. **Downgrades must be explicit** (BS(ε) → EO when drift exceeds bound)

### Mode Discipline

- **Target**: HLC with drift < ε → `BS(ε)` recency
- **Degraded**: HLC with ε < drift < 2ε → `BS(2ε)` recency
- **Floor**: Physical clock failed → Logical clocks only → `EO` recency
- **Recovery**: Resync NTP, validate, re-enable HLC

---

## 8. Transfer Tests

### Near Transfer: Apply to Different Time System

**Question**: Design guarantee vectors for **TrueTime** (Google Spanner).

**Answer**:
```
G_truetime = ⟨Global, SS (strict serializable), SI, Fresh(TT.now()), Idem(TT), Auth⟩
```

**Evidence**: TrueTime interval `[earliest, latest]`
**Properties**:
- Scope: Global (all Spanner nodes)
- Lifetime: Until next TT.now() call
- Binding: GPS + atomic clock ensemble
- Uncertainty: Explicit (interval width = 2ε)

**Commit-wait protocol**: Upgrade from uncertain interval to certain timestamp by waiting.

### Medium Transfer: Apply to Distributed Tracing

**Question**: Design guarantee vectors for OpenTelemetry spans.

**Answer**:
```
G_span = ⟨Object, Causal, RA, BS(ε), Idem(span_id), Auth(trace_id)⟩
```

**Evidence**: Span ID + parent span ID (forms causal DAG)
**Guarantee**: Causal order preserved via parent-child relationships
**Recency**: BS(ε) if spans have HLC timestamps; EO if only span IDs

### Far Transfer: Apply to Human Processes

**Question**: A distributed team collaborates on a document. Members are in different time zones with unsynchronized clocks. Design a guarantee vector for version history.

**Answer**:
```
G_collab = ⟨Object, Causal, SI, EO, Idem(version_vc), Auth(user_id)⟩
```

**Evidence**: Vector clock per edit (one counter per team member)
**Guarantee**: Causal order preserved (edits respect happened-before)
**Concurrency detection**: Conflicting edits detected via vector clock comparison
**Recency**: EO (no physical time bound; humans don't need millisecond precision)

---

## Conclusion

Time systems are **evidence generators** that enable ordering guarantees. The type of evidence—Lamport counters, vector clocks, or hybrid timestamps—determines what guarantees can be made and how they compose.

**The universal pattern**:
1. **Identify invariant** (ORDER, ORDER+CONCURRENCY, ORDER+BOUNDED_DRIFT)
2. **Choose evidence type** (Lamport, Vector, HLC, TrueTime)
3. **Type the guarantee** (G-vector with Scope, Order, Recency, etc.)
4. **Define capsule** (evidence properties: scope, lifetime, binding)
5. **Plan degradation** (Target → Degraded → Floor → Recovery)
6. **Compose across boundaries** (meet vectors, upgrade or downgrade explicitly)

**Remember**: Time is not truth—it's evidence of ordering, with bounded uncertainty. Every timestamp has scope, lifetime, and binding. When evidence expires or degrades, guarantees must explicitly downgrade. Never accept silent failures.
